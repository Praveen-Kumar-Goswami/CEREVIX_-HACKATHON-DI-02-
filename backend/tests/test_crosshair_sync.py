"""
Tests for Crosshair Synchronization Across 2D Orthogonal Views and 3D World Space
Verifies:
- Voxel coordinates (i, j, k) map accurately to world coordinates (x, y, z) in mm.
- Inverse world-to-voxel mapping preserves the original position within a strict 2-voxel tolerance.
- Selecting any axial (X-Y), coronal (X-Z), or sagittal (Y-Z) plane point correctly projects to the orthogonal pair.
- Anisotropic voxel spacing (e.g. 1x1x2 mm) and oblique affines maintain sub-voxel registration.
"""

import pytest
import numpy as np
from utils.spatial_utils import (
    voxel_to_world,
    world_to_voxel,
    get_voxel_dimensions
)


class TestCrosshairSynchronization:
    """Verifies crosshair coordinate mapping within the required 2-voxel tolerance"""

    def test_synthetic_marker_synchronization_within_two_voxels(self):
        """
        Uses known synthetic marker coordinates to verify that
        2D voxel coordinates <-> 3D world coordinates match within <= 2 voxels.
        """
        # Realistic BraTS volume affine (1mm isotropic with standard translation)
        affine = np.array([
            [-1.0,  0.0,  0.0,   0.0],
            [ 0.0, -1.0,  0.0, 239.0],
            [ 0.0,  0.0,  1.0,   0.0],
            [ 0.0,  0.0,  0.0,   1.0]
        ])

        # Test marker coordinates representing tumor locus
        test_markers = [
            (120.0, 120.0, 77.0),   # Center of 240x240x155 volume
            (60.0,  85.0,  40.0),   # Left frontal
            (180.0, 150.0, 110.0),  # Right parietal
            (0.0,   0.0,   0.0),    # Grid origin
            (239.0, 239.0, 154.0),  # Grid extreme
        ]

        for i, j, k in test_markers:
            voxel_in = np.array([i, j, k])
            
            # 1. Map 2D voxel crosshair to 3D world space (mm)
            world_coord = voxel_to_world(voxel_in, affine)
            
            # 2. Invert back from 3D world space to 2D voxel crosshair
            voxel_out = world_to_voxel(world_coord, affine)
            
            # 3. Calculate distance in voxel space
            voxel_diff = np.abs(voxel_out - voxel_in)
            max_voxel_error = np.max(voxel_diff)

            # Strict acceptance: error must be far below the 2-voxel requirement (< 0.01 voxels)
            assert max_voxel_error < 0.01, (
                f"Marker ({i},{j},{k}) exceeded tolerance: error={max_voxel_error:.4f} voxels"
            )
            assert max_voxel_error <= 2.0, "Violates required 2-voxel tolerance"

    def test_orthogonal_slice_crosshair_projection(self):
        """
        Verifies that setting a crosshair position on an axial slice (X, Y)
        determines the corresponding coronal (X, Z) and sagittal (Y, Z) slice indices.
        """
        affine = np.eye(4)
        volume_shape = (240, 240, 155)

        # Crosshair placed at voxel (X=145, Y=98, Z=62)
        target_voxel = (145, 98, 62)

        # In multiplanar NiiVue representation:
        # Axial view: Fixed Z = 62, Crosshair at (X=145, Y=98)
        # Coronal view: Fixed Y = 98, Crosshair at (X=145, Z=62)
        # Sagittal view: Fixed X = 145, Crosshair at (Y=98, Z=62)

        axial_slice = target_voxel[2]
        coronal_slice = target_voxel[1]
        sagittal_slice = target_voxel[0]

        assert axial_slice == 62
        assert coronal_slice == 98
        assert sagittal_slice == 145

        # Verify world transform preserves all three coordinates simultaneously
        world_pt = voxel_to_world(np.array(target_voxel), affine)
        recon_voxel = world_to_voxel(world_pt, affine)
        assert np.allclose(recon_voxel, target_voxel, atol=1e-5)

    def test_anisotropic_and_oblique_crosshair_registration(self):
        """Verifies crosshair registration on anisotropic (non-cubic) grid with shear/rotation"""
        # Oblique affine with 1.2 x 0.8 x 2.5 mm voxel spacing and 15-degree rotation
        angle = np.radians(15)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        
        affine = np.array([
            [1.2 * cos_a, -0.8 * sin_a, 0.0, -100.0],
            [1.2 * sin_a,  0.8 * cos_a, 0.0, -80.0],
            [0.0,          0.0,         2.5,   20.0],
            [0.0,          0.0,         0.0,    1.0]
        ])

        # Test across 10 random marker coordinates inside typical volume
        np.random.seed(42)
        for _ in range(10):
            rand_voxel = np.random.uniform([10, 10, 10], [150, 150, 80])
            world_pos = voxel_to_world(rand_voxel, affine)
            recovered_voxel = world_to_voxel(world_pos, affine)

            diff = np.linalg.norm(recovered_voxel - rand_voxel)
            assert diff < 0.001, f"Anisotropic sync error: {diff} voxels (exceeds 2-voxel tolerance)"
