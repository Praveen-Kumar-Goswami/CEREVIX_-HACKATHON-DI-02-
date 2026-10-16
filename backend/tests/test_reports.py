"""
Report Service Tests
Tests for report generation, provenance tracking, and export functionality.

Tests:
- Correct units (mL)
- Input SHA-256 hashing
- Model provenance (name, version, license, git commit)
- Timestamp format
- Disclaimer presence
- Missing metrics handling
- Failed case behavior
- NIfTI export validation
"""

import pytest
import tempfile
import numpy as np
import nibabel as nib
from pathlib import Path
from datetime import datetime
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.report_service import (
    generate_case_report, compute_file_sha256, get_git_commit,
    save_report_json, DISCLAIMER_TEXT
)
from services.export_service import export_prediction_nifti, validate_exported_prediction
from services.cleanup_service import cleanup_expired_files, is_protected


class TestReportGeneration:
    """Test report generation with full provenance"""
    
    def setup_method(self):
        """Create temp directory with test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create fake NIfTI files
        self.input_files = {}
        for modality in ['t1ce', 't1', 't2', 'flair']:
            data = np.random.rand(10, 10, 10).astype(np.float32)
            affine = np.eye(4)
            nii = nib.Nifti1Image(data, affine)
            filepath = self.temp_path / f"{modality}.nii.gz"
            nib.save(nii, filepath)
            self.input_files[modality] = filepath
    
    def test_units_are_milliliters(self):
        """Volume units must be mL"""
        volumes = {'WT': 123.456, 'TC': 78.9, 'ET': 45.6}
        
        report = generate_case_report(
            case_id="test_001",
            input_files=self.input_files,
            volumes_ml=volumes,
            inference_time_sec=1.5,
            device="cuda",
            upload_timestamp=datetime.now().isoformat()
        )
        
        # Check units in field names
        assert hasattr(report.volume_estimates, 'whole_tumor_ml')
        assert hasattr(report.volume_estimates, 'tumor_core_ml')
        assert hasattr(report.volume_estimates, 'enhancing_tumor_ml')
        
        # Check values are rounded to 2 decimals
        assert report.volume_estimates.whole_tumor_ml == 123.46
        assert report.volume_estimates.tumor_core_ml == 78.90
    
    def test_input_sha256_hashes(self):
        """SHA-256 hashes must be computed for all inputs"""
        report = generate_case_report(
            case_id="test_002",
            input_files=self.input_files,
            volumes_ml={'WT': 100, 'TC': 50, 'ET': 25},
            inference_time_sec=1.0,
            device="cuda",
            upload_timestamp=datetime.now().isoformat()
        )
        
        # All hashes present
        assert report.input_provenance.t1ce_sha256
        assert report.input_provenance.t1_sha256
        assert report.input_provenance.t2_sha256
        assert report.input_provenance.flair_sha256
        
        # Valid SHA-256 format (64 hex characters)
        assert len(report.input_provenance.t1ce_sha256) == 64
        assert all(c in '0123456789abcdef' for c in report.input_provenance.t1ce_sha256)
        
        # Hashes are deterministic
        hash1 = compute_file_sha256(self.input_files['t1ce'])
        hash2 = compute_file_sha256(self.input_files['t1ce'])
        assert hash1 == hash2
    
    def test_model_provenance(self):
        """Model provenance must include name, version, license"""
        report = generate_case_report(
            case_id="test_003",
            input_files=self.input_files,
            volumes_ml={'WT': 100, 'TC': 50, 'ET': 25},
            inference_time_sec=1.0,
            device="cuda",
            upload_timestamp=datetime.now().isoformat()
        )
        
        # Required fields
        assert report.model_provenance.name == "MONAI brats_mri_segmentation"
        assert report.model_provenance.version == "BraTS 2018 pretrained"
        assert report.model_provenance.architecture == "SegResNet"
        assert report.model_provenance.license == "Apache 2.0"
        assert report.model_provenance.training_data == "BraTS 2018 Training Dataset"
        
        # Git commit (may be unavailable or actual hash)
        assert report.model_provenance.git_commit is not None
        assert isinstance(report.model_provenance.git_commit, str)
    
    def test_git_commit_handling(self):
        """Git commit should be 'unavailable' if not in repo"""
        commit = get_git_commit()
        
        # Either valid SHA-1 (40 chars) or unavailable
        if commit != "unavailable":
            assert len(commit) == 40
            assert all(c in '0123456789abcdef' for c in commit)
    
    def test_timestamp_format(self):
        """Timestamps must be ISO 8601 format"""
        upload_time = datetime.now().isoformat()
        
        report = generate_case_report(
            case_id="test_004",
            input_files=self.input_files,
            volumes_ml={'WT': 100, 'TC': 50, 'ET': 25},
            inference_time_sec=1.0,
            device="cuda",
            upload_timestamp=upload_time
        )
        
        # Upload timestamp preserved
        assert report.input_provenance.upload_timestamp == upload_time
        
        # Inference timestamp is ISO format
        inference_ts = report.inference_metrics.timestamp
        # Should parse without error
        datetime.fromisoformat(inference_ts)
    
    def test_disclaimer_presence(self):
        """Disclaimer must be present in every report"""
        report = generate_case_report(
            case_id="test_005",
            input_files=self.input_files,
            volumes_ml={'WT': 100, 'TC': 50, 'ET': 25},
            inference_time_sec=1.0,
            device="cuda",
            upload_timestamp=datetime.now().isoformat()
        )
        
        assert report.disclaimer
        assert "RESEARCH USE ONLY" in report.disclaimer
        assert "NOT FOR CLINICAL DIAGNOSIS" in report.disclaimer
        assert "suspected tumour region" in report.disclaimer
        assert "estimated volume" in report.disclaimer
    
    def test_missing_metrics_explicit(self):
        """Missing metrics should be None, not zero"""
        # No expert metrics provided
        report = generate_case_report(
            case_id="test_006",
            input_files=self.input_files,
            volumes_ml={'WT': 100, 'TC': 50, 'ET': 25},
            inference_time_sec=1.0,
            device="cuda",
            upload_timestamp=datetime.now().isoformat(),
            expert_metrics=None
        )
        
        # Expert metrics should be None
        assert report.expert_metrics is None
        
        # If a volume is missing, it should be None
        report2 = generate_case_report(
            case_id="test_007",
            input_files=self.input_files,
            volumes_ml={},  # No volumes
            inference_time_sec=1.0,
            device="cuda",
            upload_timestamp=datetime.now().isoformat()
        )
        
        assert report2.volume_estimates.whole_tumor_ml is None
        assert report2.volume_estimates.tumor_core_ml is None
        assert report2.volume_estimates.enhancing_tumor_ml is None
    
    def test_inference_runtime_precision(self):
        """Inference time should be rounded to 3 decimals"""
        report = generate_case_report(
            case_id="test_008",
            input_files=self.input_files,
            volumes_ml={'WT': 100, 'TC': 50, 'ET': 25},
            inference_time_sec=1.23456789,
            device="cuda",
            upload_timestamp=datetime.now().isoformat()
        )
        
        assert report.inference_metrics.inference_time_sec == 1.235
    
    def test_json_serialization(self):
        """Report must be serializable to JSON"""
        report = generate_case_report(
            case_id="test_009",
            input_files=self.input_files,
            volumes_ml={'WT': 100, 'TC': 50, 'ET': 25},
            inference_time_sec=1.0,
            device="cuda",
            upload_timestamp=datetime.now().isoformat()
        )
        
        output_path = self.temp_path / "report.json"
        save_report_json(report, output_path)
        
        # Load and verify
        with open(output_path) as f:
            data = json.load(f)
        
        assert data['case_id'] == "test_009"
        assert 'input_provenance' in data
        assert 'model_provenance' in data
        assert 'disclaimer' in data


class TestNIfTIExport:
    """Test NIfTI export functionality"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def test_brats_label_validation(self):
        """Export must validate BraTS labels"""
        affine = np.eye(4)
        
        # Valid labels
        seg_valid = np.array([[[0, 1, 2, 4]]], dtype=np.uint8)
        output_path = self.temp_path / "valid.nii.gz"
        
        result = export_prediction_nifti(seg_valid, affine, output_path, "test_case")
        assert result.exists()
        
        # Invalid labels
        seg_invalid = np.array([[[0, 1, 2, 3]]], dtype=np.uint8)  # 3 is invalid
        output_path2 = self.temp_path / "invalid.nii.gz"
        
        with pytest.raises(ValueError, match="Invalid BraTS labels"):
            export_prediction_nifti(seg_invalid, affine, output_path2, "test_case")
    
    def test_affine_preservation(self):
        """Export must preserve affine transformation"""
        affine = np.array([
            [1.5, 0, 0, 10],
            [0, 1.5, 0, 20],
            [0, 0, 2.0, 30],
            [0, 0, 0, 1]
        ])
        
        seg = np.zeros((10, 10, 10), dtype=np.uint8)
        output_path = self.temp_path / "affine_test.nii.gz"
        
        export_prediction_nifti(seg, affine, output_path, "test_case")
        
        # Verify
        nii = nib.load(output_path)
        assert np.allclose(nii.affine, affine, atol=1e-5)
    
    def test_export_validation(self):
        """Validation helper should catch mismatches"""
        affine = np.eye(4)
        seg = np.zeros((10, 10, 10), dtype=np.uint8)
        output_path = self.temp_path / "validate_test.nii.gz"
        
        export_prediction_nifti(seg, affine, output_path, "test_case")
        
        # Valid check
        assert validate_exported_prediction(output_path, (10, 10, 10), affine)
        
        # Invalid shape check
        assert not validate_exported_prediction(output_path, (20, 20, 20), affine)


class TestCleanupService:
    """Test automatic cleanup with TTL"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def test_protected_assets(self):
        """Model weights and code must never be deleted"""
        workspace = self.temp_path
        
        # Create protected files
        (workspace / "models" / "test").mkdir(parents=True)
        model_file = workspace / "models" / "test" / "model.pt"
        model_file.write_text("fake model")
        
        assert is_protected(model_file, workspace)
        
        # Backend code protected
        (workspace / "backend").mkdir()
        code_file = workspace / "backend" / "test.py"
        code_file.write_text("# code")
        
        assert is_protected(code_file, workspace)
    
    def test_cleanup_targets_only_temp_data(self):
        """Cleanup should only target upload/prediction/report directories"""
        workspace = self.temp_path
        
        # Create cleanup directories
        upload_dir = workspace / "data" / "uploads"
        upload_dir.mkdir(parents=True)
        
        old_file = upload_dir / "old_case.nii.gz"
        old_file.write_text("old data")
        
        # Make file old (simulate with modified time)
        import time
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        import os
        os.utime(old_file, (old_time, old_time))
        
        # Run cleanup
        deleted, protected = cleanup_expired_files(workspace, ttl_hours=24, dry_run=False)
        
        assert deleted == 1
        assert not old_file.exists()
    
    def test_dry_run_does_not_delete(self):
        """Dry run should report but not delete"""
        workspace = self.temp_path
        
        upload_dir = workspace / "data" / "uploads"
        upload_dir.mkdir(parents=True)
        
        old_file = upload_dir / "test.nii.gz"
        old_file.write_text("data")
        
        # Make old
        import time, os
        old_time = time.time() - (25 * 3600)
        os.utime(old_file, (old_time, old_time))
        
        # Dry run
        deleted, _ = cleanup_expired_files(workspace, ttl_hours=24, dry_run=True)
        
        assert deleted == 1
        assert old_file.exists()  # Still there


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
