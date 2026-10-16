# NeuroScope 3D - Running the Application

## Quick Start

### 1. Start the Backend Server

```bash
cd backend/api
python -m uvicorn main:app --reload --port 8000
```

### 2. Open Frontend

Navigate to: http://localhost:8000

The frontend will be served automatically by FastAPI.

## Testing

Run all tests:
```bash
cd backend
pytest tests/ -v
```

Current status: 55/55 tests passing

## API Endpoints

- `POST /api/upload` - Upload 4-modality NIfTI files
- `POST /api/inference/{case_id}` - Run segmentation
- `GET /api/status/{case_id}` - Get case status  
- `GET /api/nifti/{case_id}/{modality}` - Download NIfTI file
- `GET /api/mesh/{case_id}` - Get 3D mesh data

## System Requirements

- Python 3.11+
- NVIDIA GPU with CUDA 12.1
- 8GB RAM minimum
- Windows/Linux/Mac
