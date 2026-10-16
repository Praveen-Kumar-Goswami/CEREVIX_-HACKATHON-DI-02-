"""
API Integration Tests
Tests FastAPI endpoints with real backend services.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from utils.synthetic_data import create_synthetic_case

client = TestClient(app)


def test_root_endpoint():
    """Test health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "NeuroScope 3D" in data["service"]


def test_upload_missing_files():
    """Test upload with missing files"""
    response = client.post("/api/upload", files={})
    assert response.status_code == 422  # FastAPI validation error


@pytest.fixture(scope="module")
def synthetic_case_files(tmp_path_factory):
    """Create synthetic test case"""
    test_dir = tmp_path_factory.mktemp("api_test")
    case_dir = test_dir / "case001"
    
    files = create_synthetic_case(
        output_dir=case_dir,
        case_id="case001",
        shape=(64, 64, 32),  # Small for fast testing
        voxel_spacing=(1.0, 1.0, 1.0),
        has_tumor=True
    )
    
    return files


def test_upload_and_inference_flow(synthetic_case_files):
    """Test complete upload → inference flow"""
    # Upload files
    with open(synthetic_case_files['t1ce'], 'rb') as f1ce, \
         open(synthetic_case_files['t1'], 'rb') as f1, \
         open(synthetic_case_files['t2'], 'rb') as f2, \
         open(synthetic_case_files['flair'], 'rb') as f_flair:
        
        response = client.post("/api/upload", files={
            "t1ce": ("t1ce.nii.gz", f1ce, "application/gzip"),
            "t1": ("t1.nii.gz", f1, "application/gzip"),
            "t2": ("t2.nii.gz", f2, "application/gzip"),
            "flair": ("flair.nii.gz", f_flair, "application/gzip")
        })
    
    assert response.status_code == 200
    upload_data = response.json()
    assert upload_data["status"] == "validated"
    assert "case_id" in upload_data
    
    case_id = upload_data["case_id"]
    
    # Check status
    status_response = client.get(f"/api/status/{case_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["state"] == "validated"
    
    # Run inference
    inference_response = client.post(f"/api/inference/{case_id}")
    assert inference_response.status_code == 200
    inference_data = inference_response.json()
    
    assert inference_data["status"] == "complete"
    assert "volumes_ml" in inference_data
    assert "inference_time_sec" in inference_data
    
    # Verify volumes exist
    volumes = inference_data["volumes_ml"]
    assert "wt_ml" in volumes
    assert "tc_ml" in volumes
    assert "et_ml" in volumes
    
    # Check final status
    final_status = client.get(f"/api/status/{case_id}")
    assert final_status.status_code == 200
    assert final_status.json()["state"] == "results_ready"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])