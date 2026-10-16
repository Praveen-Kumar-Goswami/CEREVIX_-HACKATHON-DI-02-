"""
Tests for NIfTI Validation Service
Covers all 8 judge failure cases + valid case scenarios
"""

import pytest
import numpy as np
import nibabel as nib
import tempfile
import gzip
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.validation_service import (
    NIfTIValidator, ModalityType, ValidationResult
)

class TestNIfTIValidator:
    
    @pytest.fixture
    def validator(self):
        return NIfTIValidator()
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def create_valid_nifti(self, filepath: Path, shape=(64, 64, 64)):
        """Create a valid 3D NIfTI file"""
        data = np.random.randn(*shape).astype(np.float32) * 100 + 500
        affine = np.eye(4)
        img = nib.Nifti1Image(data, affine)
        nib.save(img, filepath)
        return filepath
    
    def test_valid_single_file(self, validator, temp_dir):
        """Test VAL-001: Valid NIfTI file passes"""
        filepath = temp_dir / "test_t1.nii.gz"
        self.create_valid_nifti(filepath)
        
        result, metadata = validator.validate_single_file(filepath, ModalityType.T1)
        
        assert result.is_valid
        assert metadata is not None
        assert metadata.shape == (64, 64, 64)
        assert metadata.modality == ModalityType.T1
        assert len(metadata.sha256) == 64  # SHA-256 hex length
    
    def test_corrupt_file(self, validator, temp_dir):
        """Test VAL-002 / JUDGE-009: Corrupted file rejected"""
        filepath = temp_dir / "corrupt.nii.gz"
        
        # Create corrupted gzip file
        with gzip.open(filepath, 'wb') as f:
            f.write(b"This is not a NIfTI file, just random bytes\\x00\\x01\\x02")
        
        result, metadata = validator.validate_single_file(filepath, ModalityType.T1)
        
        assert not result.is_valid
        assert "corrupted" in result.error_message.lower() or "unreadable" in result.error_message.lower()
        assert metadata is None
    
    def test_2d_image(self, validator, temp_dir):
        """Test VAL-003 / JUDGE-010: 2D image rejected"""
        filepath = temp_dir / "test_2d.nii.gz"
        
        # Create 2D image (H x W x 1)
        data = np.random.randn(256, 256, 1).astype(np.float32)
        affine = np.eye(4)
        img = nib.Nifti1Image(data, affine)
        nib.save(img, filepath)
        
        result, metadata = validator.validate_single_file(filepath, ModalityType.T1)
        
        assert not result.is_valid
        assert ("3D volume" in result.error_message or "degenerate" in result.error_message)
        assert metadata is None
    
    def test_nan_values(self, validator, temp_dir):
        """Test VAL-004 / JUDGE-012: NaN values rejected"""
        filepath = temp_dir / "test_nan.nii.gz"
        
        data = np.random.randn(64, 64, 64).astype(np.float32)
        data[30:35, 30:35, 30:35] = np.nan  # Insert NaN region
        affine = np.eye(4)
        img = nib.Nifti1Image(data, affine)
        nib.save(img, filepath)
        
        result, metadata = validator.validate_single_file(filepath, ModalityType.T1)
        
        assert not result.is_valid
        assert "non-finite" in result.error_message.lower()
        assert metadata is None
    
    def test_all_zero_volume(self, validator, temp_dir):
        """Test VAL-005 / JUDGE-013: All-zero volume rejected"""
        filepath = temp_dir / "test_zero.nii.gz"
        
        data = np.zeros((64, 64, 64), dtype=np.float32)
        affine = np.eye(4)
        img = nib.Nifti1Image(data, affine)
        nib.save(img, filepath)
        
        result, metadata = validator.validate_single_file(filepath, ModalityType.T1)
        
        assert not result.is_valid
        assert "zero" in result.error_message.lower() or "no signal" in result.error_message.lower()
        assert metadata is None
    
    def test_constant_volume(self, validator, temp_dir):
        """Test: Constant value volume rejected"""
        filepath = temp_dir / "test_constant.nii.gz"
        
        data = np.full((64, 64, 64), 42.0, dtype=np.float32)
        affine = np.eye(4)
        img = nib.Nifti1Image(data, affine)
        nib.save(img, filepath)
        
        result, metadata = validator.validate_single_file(filepath, ModalityType.T1)
        
        assert not result.is_valid
        assert "constant" in result.error_message.lower()
        assert metadata is None
    
    def test_file_too_large(self, validator, temp_dir):
        """Test VAL-006 / JUDGE-014: >1GB file rejected (mocked)"""
        filepath = temp_dir / "large_file.nii.gz"
        
        # Create empty file and mock the size check
        filepath.touch()
        
        # Temporarily increase the file size in os.path.getsize's view
        original_getsize = Path.stat
        
        class LargeFileStat:
            st_size = 2 * 1024 * 1024 * 1024  # 2 GB
        
        def mock_stat(self):
            if self.name == "large_file.nii.gz":
                return LargeFileStat()
            return original_getsize(self)
        
        import os; original_getsize = os.path.getsize; os.path.getsize = lambda p: (2*1024*1024*1024 if "large_file" in str(p) else original_getsize(p))
        
        try:
            result = validator.validate_file_size(filepath)
            assert not result.is_valid
            assert "1 GB" in result.error_message
        finally:
            os.path.getsize = original_getsize
    
    def test_mismatched_shapes(self, validator, temp_dir):
        """Test VAL-007 / JUDGE-011: Mismatched shapes rejected"""
        files = {
            ModalityType.T1: self.create_valid_nifti(temp_dir / "t1.nii.gz", (64, 64, 64)),
            ModalityType.T1CE: self.create_valid_nifti(temp_dir / "t1ce.nii.gz", (64, 64, 64)),
            ModalityType.T2: self.create_valid_nifti(temp_dir / "t2.nii.gz", (128, 128, 128)),  # Different!
            ModalityType.FLAIR: self.create_valid_nifti(temp_dir / "flair.nii.gz", (64, 64, 64)),
        }
        
        result, metadata = validator.validate_four_modalities(files)
        
        assert not result.is_valid
        assert "incompatible shapes" in result.error_message.lower()
    
    def test_mismatched_affines(self, validator, temp_dir):
        """Test VAL-008 / JUDGE-015: Mismatched affines rejected"""
        # Create files with different affines
        affine1 = np.eye(4)
        affine2 = np.eye(4)
        affine2[0, 3] = 10.0  # Different translation
        
        for modality, affine in [
            (ModalityType.T1, affine1),
            (ModalityType.T1CE, affine1),
            (ModalityType.T2, affine2),  # Different affine
            (ModalityType.FLAIR, affine1)
        ]:
            data = np.random.randn(64, 64, 64).astype(np.float32) * 100
            img = nib.Nifti1Image(data, affine)
            nib.save(img, temp_dir / f"{modality.value}.nii.gz")
        
        files = {
            mod: temp_dir / f"{mod.value}.nii.gz"
            for mod in ModalityType
        }
        
        result, metadata = validator.validate_four_modalities(files)
        
        assert not result.is_valid
        assert "incompatible" in result.error_message.lower() and "transform" in result.error_message.lower()
    
    def test_valid_four_modalities(self, validator, temp_dir):
        """Test: All four valid modalities pass"""
        affine = np.eye(4)
        files = {}
        
        for modality in ModalityType:
            filepath = temp_dir / f"{modality.value}.nii.gz"
            data = np.random.randn(64, 64, 64).astype(np.float32) * 100 + 500
            img = nib.Nifti1Image(data, affine)
            nib.save(img, filepath)
            files[modality] = filepath
        
        result, metadata = validator.validate_four_modalities(files)
        
        assert result.is_valid
        assert len(metadata) == 4
        for modality in ModalityType:
            assert modality in metadata
            assert metadata[modality].shape == (64, 64, 64)
    
    def test_missing_modality(self, validator, temp_dir):
        """Test VAL-009: Only 3 modalities provided"""
        files = {
            ModalityType.T1: self.create_valid_nifti(temp_dir / "t1.nii.gz"),
            ModalityType.T1CE: self.create_valid_nifti(temp_dir / "t1ce.nii.gz"),
            ModalityType.T2: self.create_valid_nifti(temp_dir / "t2.nii.gz"),
            # FLAIR missing
        }
        
        result, metadata = validator.validate_four_modalities(files)
        
        assert not result.is_valid
        assert "missing" in result.error_message.lower()
        assert "flair" in result.error_message.lower()
    
    def test_valid_expert_mask(self, validator, temp_dir):
        """Test: Valid expert mask with BraTS labels"""
        # Create reference modality
        ref_filepath = temp_dir / "t1.nii.gz"
        self.create_valid_nifti(ref_filepath)
        result, ref_metadata = validator.validate_single_file(ref_filepath, ModalityType.T1)
        assert result.is_valid
        
        # Create expert mask with valid labels
        mask_filepath = temp_dir / "expert_mask.nii.gz"
        data = np.zeros((64, 64, 64), dtype=np.uint8)
        data[20:30, 20:30, 20:30] = 1  # NCR
        data[30:40, 30:40, 30:40] = 2  # ED
        data[40:50, 40:50, 40:50] = 4  # ET
        img = nib.Nifti1Image(data, ref_metadata.affine)
        nib.save(img, mask_filepath)
        
        result, mask_metadata = validator.validate_expert_mask(mask_filepath, ref_metadata)
        
        assert result.is_valid
        assert mask_metadata is not None
    
    def test_expert_mask_invalid_labels(self, validator, temp_dir):
        """Test: Expert mask with invalid labels rejected"""
        ref_filepath = temp_dir / "t1.nii.gz"
        self.create_valid_nifti(ref_filepath)
        result, ref_metadata = validator.validate_single_file(ref_filepath, ModalityType.T1)
        
        # Create mask with invalid label
        mask_filepath = temp_dir / "bad_mask.nii.gz"
        data = np.zeros((64, 64, 64), dtype=np.uint8)
        data[20:30, 20:30, 20:30] = 5  # Invalid label
        img = nib.Nifti1Image(data, ref_metadata.affine)
        nib.save(img, mask_filepath)
        
        result, mask_metadata = validator.validate_expert_mask(mask_filepath, ref_metadata)
        
        assert not result.is_valid
        assert "invalid labels" in result.error_message.lower()
    
    def test_no_crash_on_failures(self, validator, temp_dir):
        """Test VAL-010: No crashes on any failure mode"""
        test_cases = [
            ("corrupt", b"not a nifti"),
            ("empty", b""),
        ]
        
        for name, content in test_cases:
            filepath = temp_dir / f"{name}.nii.gz"
            with gzip.open(filepath, 'wb') as f:
                f.write(content)
            
            # Should not crash, just return error
            result, metadata = validator.validate_single_file(filepath, ModalityType.T1)
            assert not result.is_valid
            assert result.error_message is not None
            assert metadata is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

