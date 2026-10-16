"""
Test suite for spatial utilities
Covers volume calculation, coordinate transforms, and judge geometric tests.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.spatial_utils import (
    validate_affine,
    voxel_to_world,
    world_to_voxel,
    calculate_volume_ml,
    get_voxel_dimensions,
    check_orientation_consistency,
    detect_left_right_flip,
    calculate_brats_label_volumes
)


class TestAffineValidation:
    """Test affine matrix validation"""
    
    def test_valid_isotropic_affine(self):
        """Valid isotropic 1mm affine should pass"""
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        is_valid, msg = validate_affine(affine)
        assert is_valid
        assert msg == ""
    
    def test_valid_anisotropic_affine(self):
        """Valid anisotropic affine should pass"""
        affine = np.diag([1.0, 1.0, 2.0, 1.0])
        is_valid, msg = validate_affine(affine)
        assert is_valid
    
    def test_invalid_shape(self):
        """Wrong shape should fail"""
        affine = np.eye(3)
        is_valid, msg = validate_affine(affine)
        assert not is_valid
        assert "4x4" in msg
    
    def test_nan_values(self):
        """NaN values should fail"""
        affine = np.diag([1.0, np.nan, 1.0, 1.0])
        is_valid, msg = validate_affine(affine)
        assert not is_valid
        assert "non-finite" in msg.lower()
    
    def test_zero_determinant(self):
        """Singular matrix should fail"""
        affine = np.eye(4)
        affine[0, 0] = 0  # Make singular
        is_valid, msg = validate_affine(affine)
        assert not is_valid
        assert "determinant" in msg.lower()
    
    def test_invalid_bottom_row(self):
        """Bottom row must be [0,0,0,1]"""
        affine = np.eye(4)
        affine[3, 0] = 1.0  # Invalid
        is_valid, msg = validate_affine(affine)
        assert not is_valid
        assert "bottom row" in msg.lower()
    
    def test_unreasonable_voxel_size(self):
        """Extremely large or small voxel sizes should fail"""
        affine = np.diag([100.0, 1.0, 1.0, 1.0])  # 100mm voxel
        is_valid, msg = validate_affine(affine)
        assert not is_valid
        assert "voxel sizes" in msg.lower()


class TestCoordinateTransforms:
    """Test voxel <-> world coordinate transformations"""
    
    def test_voxel_to_world_isotropic(self):
        """Test isotropic 2mm transformation"""
        affine = np.diag([2.0, 2.0, 2.0, 1.0])
        voxel = np.array([10, 20, 30])
        world = voxel_to_world(voxel, affine)
        
        expected = np.array([20.0, 40.0, 60.0])
        np.testing.assert_allclose(world, expected)
    
    def test_voxel_to_world_anisotropic(self):
        """Test anisotropic 1×1×2mm transformation"""
        affine = np.diag([1.0, 1.0, 2.0, 1.0])
        voxel = np.array([5, 10, 15])
        world = voxel_to_world(voxel, affine)
        
        expected = np.array([5.0, 10.0, 30.0])
        np.testing.assert_allclose(world, expected)
    
    def test_voxel_to_world_with_translation(self):
        """Test transformation with translation offset"""
        affine = np.eye(4)
        affine[:3, 3] = [100, 200, 300]  # Translation
        
        voxel = np.array([0, 0, 0])
        world = voxel_to_world(voxel, affine)
        
        expected = np.array([100.0, 200.0, 300.0])
        np.testing.assert_allclose(world, expected)
    
    def test_world_to_voxel_isotropic(self):
        """Test inverse transformation"""
        affine = np.diag([2.0, 2.0, 2.0, 1.0])
        world = np.array([20.0, 40.0, 60.0])
        voxel = world_to_voxel(world, affine)
        
        expected = np.array([10.0, 20.0, 30.0])
        np.testing.assert_allclose(voxel, expected)
    
    def test_round_trip_transform(self):
        """Voxel -> World -> Voxel should return original"""
        affine = np.diag([1.5, 1.5, 3.0, 1.0])
        affine[:3, 3] = [50, 60, 70]
        
        original_voxel = np.array([12.5, 34.7, 56.2])
        world = voxel_to_world(original_voxel, affine)
        recovered_voxel = world_to_voxel(world, affine)
        
        np.testing.assert_allclose(recovered_voxel, original_voxel, rtol=1e-10)
    
    def test_batch_transform(self):
        """Test transformation of multiple points"""
        affine = np.diag([2.0, 2.0, 2.0, 1.0])
        voxels = np.array([
            [0, 0, 0],
            [10, 20, 30],
            [5, 5, 5]
        ])
        
        worlds = voxel_to_world(voxels, affine)
        
        expected = np.array([
            [0, 0, 0],
            [20, 40, 60],
            [10, 10, 10]
        ])
        np.testing.assert_allclose(worlds, expected)


class TestVolumeCalculation:
    """Test volume calculation with various scenarios"""
    
    def test_isotropic_1mm_cube(self):
        """10×10×10 cube at 1mm isotropic = 1.0 mL"""
        mask = np.ones((10, 10, 10), dtype=np.uint8)
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        
        volume = calculate_volume_ml(mask, affine)
        expected = 1.0  # 1000 voxels × 1 mm³/voxel / 1000
        
        assert abs(volume - expected) < 0.01
    
    def test_anisotropic_cube(self):
        """20×20×20 cube at 1×1×2mm = 16.0 mL (JUDGE TEST CASE)"""
        mask = np.ones((20, 20, 20), dtype=np.uint8)
        affine = np.diag([1.0, 1.0, 2.0, 1.0])
        
        volume = calculate_volume_ml(mask, affine)
        expected = 16.0  # 8000 voxels × 2 mm³/voxel / 1000
        
        # Within 1% tolerance
        assert abs(volume - expected) / expected < 0.01
    
    def test_realistic_brain_tumor(self):
        """Simulate realistic tumor: 30×30×15 at 1×1×3mm"""
        mask = np.ones((30, 30, 15), dtype=np.uint8)
        affine = np.diag([1.0, 1.0, 3.0, 1.0])
        
        volume = calculate_volume_ml(mask, affine)
        expected = 40.5  # 13500 voxels × 3 mm³/voxel / 1000
        
        assert abs(volume - expected) < 0.1
    
    def test_empty_mask(self):
        """Empty mask should give 0 mL"""
        mask = np.zeros((50, 50, 50), dtype=np.uint8)
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        
        volume = calculate_volume_ml(mask, affine)
        assert volume == 0.0
    
    def test_sparse_mask(self):
        """Sparse mask with known voxel count"""
        mask = np.zeros((100, 100, 100), dtype=np.uint8)
        mask[10:20, 10:20, 10:20] = 1  # 10×10×10 = 1000 voxels
        
        affine = np.diag([2.0, 2.0, 2.0, 1.0])
        volume = calculate_volume_ml(mask, affine)
        
        expected = 8.0  # 1000 voxels × 8 mm³/voxel / 1000
        assert abs(volume - expected) < 0.01
    
    def test_label_specific_volume(self):
        """Calculate volume for specific label"""
        mask = np.zeros((20, 20, 20), dtype=np.uint8)
        mask[0:10, :, :] = 1  # Half with label 1
        mask[10:20, :, :] = 2  # Half with label 2
        
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        
        vol_label1 = calculate_volume_ml(mask, affine, label=1)
        vol_label2 = calculate_volume_ml(mask, affine, label=2)
        
        # Each half is 4000 voxels = 4.0 mL
        assert abs(vol_label1 - 4.0) < 0.01
        assert abs(vol_label2 - 4.0) < 0.01
    
    def test_brats_label_volumes(self):
        """Test BraTS composite region volumes"""
        # Create synthetic segmentation
        seg = np.zeros((40, 40, 40), dtype=np.uint8)
        seg[10:20, 10:30, 10:30] = 1  # NCR: 10×20×20 = 4000 voxels
        seg[20:30, 10:30, 10:30] = 2  # ED: 10×20×20 = 4000 voxels  
        seg[5:8, 15:25, 15:25] = 4  # ET: 3x10x10 = 300 voxels (non-overlapping)
        
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        
        volumes = calculate_brats_label_volumes(seg, affine)
        
        # Check individual labels
        assert abs(volumes['ncr_ml'] - 4.0) < 0.01  # 4000 mm³ = 4 mL
        assert abs(volumes['ed_ml'] - 4.0) < 0.01
        assert abs(volumes['et_ml'] - 0.3) < 0.01  # 300 mm³ = 0.3 mL
        
        # WT = all labels
        # TC = labels 1 + 4 (with overlap handled)
        # Volumes should be consistent
        assert volumes['wt_ml'] > volumes['tc_ml']
        assert volumes['tc_ml'] >= volumes['et_ml']


class TestGeometricJudgeTests:
    """
    Judge acceptance tests for geometric accuracy.
    Based on JUDGE-001 through JUDGE-004 criteria.
    """
    
    def test_judge_001_anisotropic_volume(self):
        """
        JUDGE-001: System correctly handles anisotropic voxels.
        Create 20×20×20 mask at 1×1×2mm, verify volume = 16.0 mL ±1%
        """
        mask = np.ones((20, 20, 20), dtype=np.uint8)
        affine = np.diag([1.0, 1.0, 2.0, 1.0])
        
        volume = calculate_volume_ml(mask, affine)
        expected = 16.0
        
        error_pct = abs(volume - expected) / expected * 100
        assert error_pct < 1.0, f"Volume error {error_pct:.2f}% exceeds 1% threshold"
    
    def test_judge_002_left_right_flip_detection(self):
        """
        JUDGE-002: System detects left-right flips.
        Negative determinant indicates reflection.
        """
        # Normal right-handed affine
        normal_affine = np.diag([1.0, 1.0, 1.0, 1.0])
        assert not detect_left_right_flip(normal_affine)
        
        # Flipped affine (reflection in x-axis)
        flipped_affine = np.diag([-1.0, 1.0, 1.0, 1.0])
        assert detect_left_right_flip(flipped_affine)
    
    def test_judge_003_orientation_consistency(self):
        """
        JUDGE-003: All modalities have consistent orientation.
        Mismatched orientations should be detected.
        """
        affine1 = np.diag([1.0, 1.0, 2.0, 1.0])
        affine2 = np.diag([1.0, 1.0, 2.0, 1.0])
        
        # Same orientation
        is_consistent, msg = check_orientation_consistency(affine1, affine2)
        assert is_consistent
        
        # Different orientation (rotated)
        affine3 = np.eye(4)
        affine3[:3, :3] = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]  # 90° rotation
        
        is_consistent, msg = check_orientation_consistency(affine1, affine3)
        assert not is_consistent
    
    def test_judge_004_mirrored_anatomy_detection(self):
        """
        JUDGE-004: Detect if segmentation is mirrored.
        This would show as determinant sign mismatch between input and output.
        """
        # Input affine (normal)
        input_affine = np.diag([1.0, 1.0, 1.0, 1.0])
        
        # Output affine (mirrored - should not happen!)
        output_affine = np.diag([-1.0, 1.0, 1.0, 1.0])
        
        # Detect inconsistency
        input_flipped = detect_left_right_flip(input_affine)
        output_flipped = detect_left_right_flip(output_affine)
        
        assert input_flipped != output_flipped, "Mirroring not detected"


class TestVoxelDimensions:
    """Test voxel dimension extraction"""
    
    def test_isotropic_dimensions(self):
        """Extract isotropic voxel dimensions"""
        affine = np.diag([2.0, 2.0, 2.0, 1.0])
        dims = get_voxel_dimensions(affine)
        
        np.testing.assert_allclose(dims, [2.0, 2.0, 2.0])
    
    def test_anisotropic_dimensions(self):
        """Extract anisotropic voxel dimensions"""
        affine = np.diag([1.0, 1.0, 3.0, 1.0])
        dims = get_voxel_dimensions(affine)
        
        np.testing.assert_allclose(dims, [1.0, 1.0, 3.0])
    
    def test_oblique_affine(self):
        """Extract dimensions from oblique (rotated) affine"""
        # 45° rotation in XY plane with 2mm isotropic
        theta = np.pi / 4
        affine = np.eye(4)
        affine[0, 0] = 2 * np.cos(theta)
        affine[0, 1] = -2 * np.sin(theta)
        affine[1, 0] = 2 * np.sin(theta)
        affine[1, 1] = 2 * np.cos(theta)
        affine[2, 2] = 2.0
        
        dims = get_voxel_dimensions(affine)
        
        # Should still be ~2mm in all directions
        np.testing.assert_allclose(dims, [2.0, 2.0, 2.0], rtol=1e-10)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
