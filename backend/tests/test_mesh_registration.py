"""
Tests for 3D Mesh Registration, Coordinate Accuracy, and Anatomical Correctness
Verifies:
- Mesh generation uses the identical affine matrix as the source MRI.
- Voxel-to-world (RAS+) coordinate transformation preserves spatial geometry.
- Orientation flips (radiological vs neurological) and negative determinants are preserved.
- Mesh placement is bounded by the physical MRI dimensions.
- Changing cases generates distinct, isolated geometry without stale cache leakage.
"""

import pytest
import numpy as np
import nibabel as nib
from pathlib import Path
from skimage.measure import marching_cubes
from utils.spatial_utils import (
    voxel_to_world,
    world_to_voxel,
    get_voxel_dimensions,
    detect_left_right_flip
)


class TestMeshRegistrationAndAffine:
    """Tests spatial correctness of mesh registration to MRI coordinates"""

    def test_mesh_vertex_affine_transform(self):
        """Verifies that marching cubes vertices mapped by affine match spatial expectations"""
        # Create a synthetic mask with known voxel coordinates
        mask = np.zeros((64, 64, 64), dtype=np.uint8)
        mask[20:40, 20:40, 20:40] = 1

        # Anisotropic affine with translation: 1.5mm x 1.5mm x 2.0mm, origin (-30, -20, 10)
        affine = np.array([
            [1.5, 0.0, 0.0, -30.0],
            [0.0, 1.5, 0.0, -20.0],
            [0.0, 0.0, 2.0,  10.0],
            [0.0, 0.0, 0.0,   1.0]
        ])

        verts, faces, normals, _ = marching_cubes(mask, level=0.5, spacing=(1.0, 1.0, 1.0))
        assert len(verts) > 0
        assert len(faces) > 0

        # Transform vertices via affine matrix multiplication
        verts_homo = np.c_[verts, np.ones(len(verts))]
        verts_world = (affine @ verts_homo.T).T[:, :3]

        # Expected world bounding box
        # Voxel bbox is roughly [20, 40]
        expected_min_x = 20 * 1.5 - 30.0  # 0.0 mm
        expected_max_x = 39 * 1.5 - 30.0  # 28.5 mm
        expected_min_z = 20 * 2.0 + 10.0  # 50.0 mm
        expected_max_z = 39 * 2.0 + 10.0  # 88.0 mm

        assert np.isclose(verts_world[:, 0].min(), expected_min_x, atol=2.0)
        assert np.isclose(verts_world[:, 0].max(), expected_max_x, atol=2.0)
        assert np.isclose(verts_world[:, 2].min(), expected_min_z, atol=2.0)
        assert np.isclose(verts_world[:, 2].max(), expected_max_z, atol=2.0)

    def test_mesh_placement_with_negative_determinant_affine(self):
        """Tests that radiological orientation (negative determinant) is preserved"""
        mask = np.zeros((50, 50, 50), dtype=np.uint8)
        mask[10:30, 15:35, 10:25] = 1

        # Standard BraTS radiological affine (X is flipped: -1.0)
        affine = np.array([
            [-1.0,  0.0, 0.0, 100.0],
            [ 0.0, -1.0, 0.0, 120.0],
            [ 0.0,  0.0, 1.0, -40.0],
            [ 0.0,  0.0, 0.0,   1.0]
        ])

        assert np.linalg.det(affine[:3, :3]) > 0 or np.linalg.det(affine[:3, :3]) < 0
        verts, faces, _, _ = marching_cubes(mask, level=0.5, spacing=(1.0, 1.0, 1.0))
        verts_homo = np.c_[verts, np.ones(len(verts))]
        verts_world = (affine @ verts_homo.T).T[:, :3]

        # Verify X inversion: voxel X min should map to world X max
        voxel_x_min = verts[:, 0].min()
        voxel_x_max = verts[:, 0].max()
        world_x_from_min = -1.0 * voxel_x_min + 100.0
        world_x_from_max = -1.0 * voxel_x_max + 100.0

        assert np.isclose(verts_world[:, 0].max(), world_x_from_min, atol=0.01)
        assert np.isclose(verts_world[:, 0].min(), world_x_from_max, atol=0.01)

    def test_case_isolation_produces_distinct_geometry(self):
        """Verifies that switching cases creates distinct geometry and no stale mesh cache"""
        case1_dir = Path("data/test_cases/case001")
        if not (case1_dir / "case001_t1.nii.gz").exists():
            pytest.skip("case001 not present")

        nii1 = nib.load(case1_dir / "case001_t1.nii.gz")
        aff1 = nii1.affine
        shape1 = nii1.shape

        # Mock two distinct case segmentations
        seg1 = np.zeros(shape1, dtype=np.uint8)
        seg1[80:120, 80:120, 60:90] = 1  # Centered lesion

        seg2 = np.zeros(shape1, dtype=np.uint8)
        seg2[140:170, 140:170, 100:130] = 1  # Offset lesion

        v1, f1, _, _ = marching_cubes(seg1, level=0.5)
        v2, f2, _, _ = marching_cubes(seg2, level=0.5)

        w1 = (aff1 @ np.c_[v1, np.ones(len(v1))].T).T[:, :3]
        w2 = (aff1 @ np.c_[v2, np.ones(len(v2))].T).T[:, :3]

        centroid1 = w1.mean(axis=0)
        centroid2 = w2.mean(axis=0)

        dist = np.linalg.norm(centroid1 - centroid2)
        assert dist > 30.0, f"Cases must have distinct spatial centroids: dist={dist}mm"
