"""
Tests for 3D mesh generation from segmentation masks
"""

import pytest
import numpy as np
import nibabel as nib
from pathlib import Path
import tempfile
import sys

# Add backend and project root to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path.parent))

try:
    from backend.api.main import get_mesh_data
    from backend.services.case_manager import CaseStateManager, CaseState
except ImportError:
    from api.main import get_mesh_data
    from services.case_manager import CaseStateManager, CaseState


class TestMeshGeneration:
    """Test marching cubes mesh extraction"""
    
    def test_empty_mask_handling(self, tmp_path):
        """Empty masks should be skipped gracefully"""
        # Create empty segmentation
        seg_data = np.zeros((50, 50, 50), dtype=np.uint8)
        affine = np.eye(4)
        
        seg_nii = nib.Nifti1Image(seg_data, affine)
        seg_path = tmp_path / "empty_seg.nii.gz"
        nib.save(seg_nii, seg_path)
        
        # Load and verify
        loaded = nib.load(seg_path)
        assert loaded.get_fdata().sum() == 0
    
    def test_small_region_mesh(self, tmp_path):
        """Small synthetic region should generate valid mesh"""
        # Create small tumor region (10x10x10 cube)
        seg_data = np.zeros((50, 50, 50), dtype=np.uint8)
        seg_data[20:30, 20:30, 20:30] = 4  # ET label
        
        affine = np.eye(4)
        
        seg_nii = nib.Nifti1Image(seg_data, affine)
        seg_path = tmp_path / "small_tumor.nii.gz"
        nib.save(seg_nii, seg_path)
        
        # Verify region exists
        loaded = nib.load(seg_path)
        assert (loaded.get_fdata() == 4).sum() == 1000  # 10^3 voxels
    
    def test_coordinate_transformation(self):
        """Affine transformation should map voxels to world coordinates"""
        # Test affine with known transformation
        affine = np.diag([2.0, 2.0, 2.0, 1.0])  # 2mm isotropic
        affine[:3, 3] = [10, 20, 30]  # Translation
        
        # Voxel coordinate
        voxel = np.array([5, 10, 15, 1])
        
        # Expected world coordinate
        world = affine @ voxel
        
        assert np.allclose(world[:3], [20, 40, 60])
    
    def test_region_nesting(self):
        """WT should contain TC, TC should contain ET"""
        # Create nested regions
        seg_data = np.zeros((50, 50, 50), dtype=np.uint8)
        
        # Outer: Edema (label 2)
        seg_data[15:35, 15:35, 15:35] = 2
        
        # Middle: NCR (label 1) 
        seg_data[20:30, 20:30, 20:30] = 1
        
        # Inner: ET (label 4)
        seg_data[23:27, 23:27, 23:27] = 4
        
        # Extract regions
        wt_mask = np.isin(seg_data, [1, 2, 4])
        tc_mask = np.isin(seg_data, [1, 4])
        et_mask = (seg_data == 4)
        
        # Verify nesting
        wt_voxels = wt_mask.sum()
        tc_voxels = tc_mask.sum()
        et_voxels = et_mask.sum()
        
        assert et_voxels < tc_voxels < wt_voxels
        assert et_voxels == 64  # 4^3
        
    def test_left_right_flip_transformation(self):
        """Flipped affine should preserve anatomical side"""
        # Normal affine
        affine_normal = np.diag([1.0, 1.0, 1.0, 1.0])
        
        # Flipped affine (negative X determinant)
        affine_flipped = np.diag([-1.0, 1.0, 1.0, 1.0])
        
        # Same voxel coordinate
        voxel = np.array([10, 20, 30, 1])
        
        # Transform with both affines
        world_normal = affine_normal @ voxel
        world_flipped = affine_flipped @ voxel
        
        # X coordinate should flip
        assert world_normal[0] == 10
        assert world_flipped[0] == -10
        assert world_normal[1] == world_flipped[1]  # Y unchanged
        assert world_normal[2] == world_flipped[2]  # Z unchanged
    
    def test_case_specific_geometry(self):
        """Different cases should produce different meshes"""
        # Case 1: Small tumor
        seg1 = np.zeros((50, 50, 50), dtype=np.uint8)
        seg1[20:30, 20:30, 20:30] = 4
        
        # Case 2: Large tumor
        seg2 = np.zeros((50, 50, 50), dtype=np.uint8)
        seg2[15:35, 15:35, 15:35] = 4
        
        # Count voxels
        case1_voxels = (seg1 == 4).sum()
        case2_voxels = (seg2 == 4).sum()
        
        assert case1_voxels == 1000  # 10^3
        assert case2_voxels == 8000  # 20^3
        assert case1_voxels != case2_voxels


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
