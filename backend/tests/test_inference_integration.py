"""
Integration tests for inference service
Tests end-to-end inference pipeline with synthetic data.
"""

import pytest
import numpy as np
import nibabel as nib
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.inference_service import BraTSInferenceService
from utils.synthetic_data import create_synthetic_case
from utils.spatial_utils import (
    calculate_volume_ml,
    check_orientation_consistency,
    validate_affine
)


@pytest.fixture(scope="module")
def model_path():
    """Path to trained model"""
    return Path(__file__).parent.parent.parent / "models" / "brats_mri_segmentation" / "models" / "model.pt"


@pytest.fixture(scope="module")
def test_case_dir(tmp_path_factory):
    """Create synthetic test case"""
    test_dir = tmp_path_factory.mktemp("test_cases")
    case_dir = test_dir / "case001"
    
    files = create_synthetic_case(
        output_dir=case_dir,
        case_id="case001",
        shape=(128, 128, 64),  # Smaller for faster testing
        voxel_spacing=(1.0, 1.0, 1.0),
        has_tumor=True
    )
    
    return case_dir, files


@pytest.fixture(scope="module")
def inference_service(model_path):
    """Initialize inference service once for all tests"""
    return BraTSInferenceService(model_path, device='cuda')


class TestInferenceService:
    """Test inference service functionality"""
    
    def test_model_loads(self, inference_service):
        """Test model loads successfully"""
        assert inference_service.model is not None
        assert inference_service.device in ['cuda', 'cpu']
    
    def test_inference_runs(self, inference_service, test_case_dir):
        """Test inference completes without errors"""
        case_dir, files = test_case_dir
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        assert result is not None
        assert result.segmentation is not None
        assert result.affine is not None
        assert result.inference_time_sec > 0
    
    def test_output_shape(self, inference_service, test_case_dir):
        """Test output has correct shape"""
        case_dir, files = test_case_dir
        
        # Load one input to get expected shape
        img = nib.load(files['t1ce'])
        expected_shape = img.shape
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        assert result.segmentation.shape == expected_shape
        assert result.segmentation.ndim == 3
    
    def test_output_labels(self, inference_service, test_case_dir):
        """Test output contains only valid BraTS labels"""
        case_dir, files = test_case_dir
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        unique_labels = np.unique(result.segmentation)
        valid_labels = {0, 1, 2, 4}
        
        assert set(unique_labels).issubset(valid_labels), \
            f"Invalid labels found: {unique_labels}"
    
    def test_affine_preserved(self, inference_service, test_case_dir):
        """Test input affine is preserved in output"""
        case_dir, files = test_case_dir
        
        # Get input affine
        img = nib.load(files['t1ce'])
        input_affine = img.affine
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        # Check affine matches
        np.testing.assert_array_almost_equal(
            result.affine,
            input_affine,
            decimal=6
        )
    
    def test_volumes_calculated(self, inference_service, test_case_dir):
        """Test volume calculations are performed"""
        case_dir, files = test_case_dir
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        # Check all expected volume keys present
        expected_keys = {'ncr_ml', 'ed_ml', 'et_ml', 'wt_ml', 'tc_ml'}
        assert expected_keys.issubset(result.volumes_ml.keys())
        
        # All volumes should be non-negative
        for key, vol in result.volumes_ml.items():
            assert vol >= 0, f"{key} volume is negative: {vol}"
    
    def test_volume_hierarchy(self, inference_service, test_case_dir):
        """Test tumor region volume hierarchy (WT ≥ TC ≥ ET)"""
        case_dir, files = test_case_dir
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        volumes = result.volumes_ml
        
        # WT should be largest (contains all tumor)
        assert volumes['wt_ml'] >= volumes['tc_ml'], \
            "Whole tumor should be ≥ tumor core"
        
        # TC should be ≥ ET
        assert volumes['tc_ml'] >= volumes['et_ml'], \
            "Tumor core should be ≥ enhancing tumor"
    
    def test_label_nesting(self, inference_service, test_case_dir):
        """Test region nesting: WT contains TC contains ET"""
        case_dir, files = test_case_dir
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        seg = result.segmentation
        
        # Create region masks
        wt_mask = np.isin(seg, [1, 2, 4])  # All tumor labels
        tc_mask = np.isin(seg, [1, 4])  # NCR + ET
        et_mask = (seg == 4)
        
        # Check nesting: every ET voxel should be in TC
        et_in_tc = np.all(et_mask <= tc_mask)
        assert et_in_tc, "ET region not contained in TC"
        
        # Check nesting: every TC voxel should be in WT
        tc_in_wt = np.all(tc_mask <= wt_mask)
        assert tc_in_wt, "TC region not contained in WT"
    
    def test_save_segmentation(self, inference_service, test_case_dir, tmp_path):
        """Test segmentation can be saved"""
        case_dir, files = test_case_dir
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        output_path = tmp_path / "segmentation.nii.gz"
        inference_service.save_segmentation(result, output_path)
        
        assert output_path.exists()
        
        # Verify saved file
        saved_nii = nib.load(output_path)
        np.testing.assert_array_equal(saved_nii.get_fdata(), result.segmentation)
        np.testing.assert_array_almost_equal(saved_nii.affine, result.affine)


class TestAnisotropicVoxels:
    """Test inference with anisotropic voxel spacing"""
    
    def test_anisotropic_case(self, inference_service, tmp_path):
        """Test inference on anisotropic voxels (1×1×2mm)"""
        case_dir = tmp_path / "aniso_case"
        
        files = create_synthetic_case(
            output_dir=case_dir,
            case_id="aniso_001",
            shape=(128, 128, 32),  # Half z-resolution
            voxel_spacing=(1.0, 1.0, 2.0),
            has_tumor=True
        )
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        # Verify affine reflects 2mm z-spacing
        assert result.affine[2, 2] == 2.0, \
            f"Expected 2mm z-spacing, got {result.affine[2, 2]}"
        
        # Volumes should account for anisotropic voxels
        assert result.volumes_ml['wt_ml'] >= 0


class TestNegativeCase:
    """Test inference on case without tumor"""
    
    def test_negative_case(self, inference_service, tmp_path):
        """Test inference on healthy brain (no tumor)"""
        case_dir = tmp_path / "negative_case"
        
        files = create_synthetic_case(
            output_dir=case_dir,
            case_id="negative_001",
            shape=(128, 128, 64),
            voxel_spacing=(1.0, 1.0, 1.0),
            has_tumor=False  # No tumor
        )
        
        result = inference_service.run_inference(
            t1ce_path=files['t1ce'],
            t1_path=files['t1'],
            t2_path=files['t2'],
            flair_path=files['flair']
        )
        
        # Volumes should be very small or zero
        # Model may still detect some small regions (false positives)
        # but volumes should be minimal
        assert result.volumes_ml['wt_ml'] < 200.0, \
            "Negative case detected tumor (false positive acceptable on synthetic data)"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])