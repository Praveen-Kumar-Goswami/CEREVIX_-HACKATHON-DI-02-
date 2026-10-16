"""
Tests for expert mask upload and comparison functionality
"""

import pytest
import numpy as np
import nibabel as nib
from pathlib import Path
from fastapi.testclient import TestClient
import tempfile
import shutil

# Import the app
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.main import app

client = TestClient(app)


@pytest.fixture
def test_data_dir():
    """Create temporary directory for test data"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


def create_test_nifti(filepath, shape=(64, 64, 64), labels=None):
    """Helper to create test NIfTI files"""
    if labels is None:
        # Create random MRI data
        data = np.random.randn(*shape).astype(np.float32) * 100 + 500
    else:
        # Create label map with specified labels
        data = np.zeros(shape, dtype=np.uint8)
        if 1 in labels:
            data[20:30, 20:30, 20:30] = 1
        if 2 in labels:
            data[15:25, 15:25, 15:25] = 2
        if 4 in labels:
            data[25:35, 25:35, 25:35] = 4
    
    affine = np.eye(4)
    img = nib.Nifti1Image(data, affine)
    nib.save(img, filepath)


class TestExpertMaskUpload:
    """Test expert mask upload functionality"""
    
    def test_upload_without_expert_mask(self, test_data_dir):
        """Test: Upload works without expert mask (backward compatibility)"""
        # Create test files
        t1ce_path = test_data_dir / "t1ce.nii.gz"
        t1_path = test_data_dir / "t1.nii.gz"
        t2_path = test_data_dir / "t2.nii.gz"
        flair_path = test_data_dir / "flair.nii.gz"
        
        for path in [t1ce_path, t1_path, t2_path, flair_path]:
            create_test_nifti(path)
        
        # Upload without expert mask
        with open(t1ce_path, 'rb') as t1ce, \
             open(t1_path, 'rb') as t1, \
             open(t2_path, 'rb') as t2, \
             open(flair_path, 'rb') as flair:
            
            response = client.post('/api/upload', files={
                't1ce': ('t1ce.nii.gz', t1ce, 'application/gzip'),
                't1': ('t1.nii.gz', t1, 'application/gzip'),
                't2': ('t2.nii.gz', t2, 'application/gzip'),
                'flair': ('flair.nii.gz', flair, 'application/gzip'),
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'validated'
        assert 'case_id' in data
    
    def test_upload_with_valid_expert_mask(self, test_data_dir):
        """Test: Upload with valid expert mask"""
        # Create test files
        t1ce_path = test_data_dir / "t1ce.nii.gz"
        t1_path = test_data_dir / "t1.nii.gz"
        t2_path = test_data_dir / "t2.nii.gz"
        flair_path = test_data_dir / "flair.nii.gz"
        expert_path = test_data_dir / "expert.nii.gz"
        
        for path in [t1ce_path, t1_path, t2_path, flair_path]:
            create_test_nifti(path)
        
        # Create expert mask with valid BraTS labels
        create_test_nifti(expert_path, labels=[0, 1, 2, 4])
        
        # Upload with expert mask
        with open(t1ce_path, 'rb') as t1ce, \
             open(t1_path, 'rb') as t1, \
             open(t2_path, 'rb') as t2, \
             open(flair_path, 'rb') as flair, \
             open(expert_path, 'rb') as expert:
            
            response = client.post('/api/upload', files={
                't1ce': ('t1ce.nii.gz', t1ce, 'application/gzip'),
                't1': ('t1.nii.gz', t1, 'application/gzip'),
                't2': ('t2.nii.gz', t2, 'application/gzip'),
                'flair': ('flair.nii.gz', flair, 'application/gzip'),
                'expert_mask': ('expert.nii.gz', expert, 'application/gzip'),
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'validated'
        assert 'case_id' in data
    
    def test_upload_with_invalid_labels(self, test_data_dir):
        """Test: Expert mask with invalid labels is rejected"""
        # Create test files
        t1ce_path = test_data_dir / "t1ce.nii.gz"
        t1_path = test_data_dir / "t1.nii.gz"
        t2_path = test_data_dir / "t2.nii.gz"
        flair_path = test_data_dir / "flair.nii.gz"
        expert_path = test_data_dir / "expert.nii.gz"
        
        for path in [t1ce_path, t1_path, t2_path, flair_path]:
            create_test_nifti(path)
        
        # Create expert mask with INVALID labels (3 and 5 are not allowed)
        data = np.zeros((64, 64, 64), dtype=np.uint8)
        data[20:30, 20:30, 20:30] = 3  # Invalid label
        data[30:40, 30:40, 30:40] = 5  # Invalid label
        img = nib.Nifti1Image(data, np.eye(4))
        nib.save(img, expert_path)
        
        # Upload with invalid expert mask
        with open(t1ce_path, 'rb') as t1ce, \
             open(t1_path, 'rb') as t1, \
             open(t2_path, 'rb') as t2, \
             open(flair_path, 'rb') as flair, \
             open(expert_path, 'rb') as expert:
            
            response = client.post('/api/upload', files={
                't1ce': ('t1ce.nii.gz', t1ce, 'application/gzip'),
                't1': ('t1.nii.gz', t1, 'application/gzip'),
                't2': ('t2.nii.gz', t2, 'application/gzip'),
                'flair': ('flair.nii.gz', flair, 'application/gzip'),
                'expert_mask': ('expert.nii.gz', expert, 'application/gzip'),
            })
        
        assert response.status_code == 400
        data = response.json()
        assert 'Expert mask validation failed' in data['error']
    
    def test_upload_with_mismatched_shape(self, test_data_dir):
        """Test: Expert mask with incompatible shape is rejected"""
        # Create test files
        t1ce_path = test_data_dir / "t1ce.nii.gz"
        t1_path = test_data_dir / "t1.nii.gz"
        t2_path = test_data_dir / "t2.nii.gz"
        flair_path = test_data_dir / "flair.nii.gz"
        expert_path = test_data_dir / "expert.nii.gz"
        
        for path in [t1ce_path, t1_path, t2_path, flair_path]:
            create_test_nifti(path, shape=(64, 64, 64))
        
        # Create expert mask with DIFFERENT shape
        create_test_nifti(expert_path, shape=(32, 32, 32), labels=[0, 1, 2, 4])
        
        # Upload with mismatched expert mask
        with open(t1ce_path, 'rb') as t1ce, \
             open(t1_path, 'rb') as t1, \
             open(t2_path, 'rb') as t2, \
             open(flair_path, 'rb') as flair, \
             open(expert_path, 'rb') as expert:
            
            response = client.post('/api/upload', files={
                't1ce': ('t1ce.nii.gz', t1ce, 'application/gzip'),
                't1': ('t1.nii.gz', t1, 'application/gzip'),
                't2': ('t2.nii.gz', t2, 'application/gzip'),
                'flair': ('flair.nii.gz', flair, 'application/gzip'),
                'expert_mask': ('expert.nii.gz', expert, 'application/gzip'),
            })
        
        assert response.status_code == 400
        data = response.json()
        assert 'shape' in data['error'].lower() or 'Expert mask validation failed' in data['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
