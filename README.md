# NeuroScope 3D - Brain MRI Tumor Segmentation Platform

**RESEARCH USE ONLY - NOT FOR CLINICAL DIAGNOSIS**

NeuroScope 3D is a web-based research platform for brain MRI tumor segmentation visualization. It accepts four co-registered skull-stripped brain MRI modalities (T1, T1ce, T2, FLAIR), applies a pretrained MONAI SegResNet model, and provides comprehensive 2D/3D visualization with volumetric measurements and provenance tracking.

**Disclaimer:** This is a research prototype for educational and research purposes only. All predictions represent suspected tumor regions estimated by the model and require expert radiologist review. Not validated for clinical use.

## Features

✅ 4-modality NIfTI input validation  
✅ MONAI SegResNet inference (BraTS 2018 trained)  
✅ 2D slice viewer with segmentation overlay (NiiVue)  
✅ 3D mesh rendering with region toggles  
✅ Spatial correctness (affine preservation, volume calculation)  
✅ Evaluation metrics (Dice, sensitivity)  
✅ Provenance reports (SHA-256, timestamps, model info)  
✅ Privacy controls (24-hour auto-deletion)  
✅ Comprehensive error handling  

## Prerequisites

- **Python:** 3.11 or higher
- **CUDA:** 12.1 or higher (for GPU acceleration)
- **GPU:** NVIDIA GPU with 6GB+ VRAM recommended (RTX 4050 or better)
- **OS:** Windows 10/11, Linux, macOS (tested on Windows 11)
- **RAM:** 8GB minimum, 16GB recommended

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd Kuru
```

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

**Key dependencies:**
- PyTorch 2.5.1+cu121
- MONAI 1.6.1
- FastAPI
- NiBabel 5.4.2
- scikit-image

### 3. Download Model
The MONAI brats_mri_segmentation model is already included:
```
models/brats_mri_segmentation/models/model.pt (17.97 MB)
```

If missing, run:
```bash
python backend/download_model.py
```

## Configuration

**No configuration files required.** The application auto-configures on startup.

**Data directories** (created automatically):
- `data/uploads/` - Temporary upload storage
- `data/cases/` - Case metadata and results
- `data/predictions/` - Segmentation outputs
- `data/reports/` - Generated reports

## Startup

**Single command to start the application:**
```bash
python backend/api/main.py
```

**Access:**
- Frontend: http://localhost:8000/
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/

**Alternative with uvicorn** (recommended for production):
```bash
cd backend/api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage

### Web Interface

1. **Navigate to** http://localhost:8000/
2. **Upload** four co-registered skull-stripped NIfTI files:
   - T1ce (T1 with contrast)
   - T1 (T1 weighted)
   - T2 (T2 weighted)
   - FLAIR
3. **Click** "Upload and Process"
4. **View results:**
   - 2D slice views with segmentation overlay
   - 3D mesh rendering
   - Estimated volumes in mL
   - Download JSON report or NIfTI prediction

### API Endpoints

**Upload:**
```bash
POST /api/upload
Content-Type: multipart/form-data
Body: t1ce, t1, t2, flair files
```

**Inference:**
```bash
POST /api/inference/{case_id}
```

**Results:**
```bash
GET /api/status/{case_id}
GET /api/nifti/{case_id}/{modality}
GET /api/mesh/{case_id}
```

**Report & Export:**
```bash
GET /api/report/{case_id}  # JSON report with provenance
GET /api/export/{case_id}  # NIfTI prediction (BraTS labels)
```

## Testing

**Run all tests:**
```bash
pytest backend/tests/ -v
```

**Expected:** 93/93 tests passing (~20 seconds)

**Test categories:**
- Validation (14 tests)
- Spatial utilities (27 tests)
- Metrics (23 tests)
- Inference (11 tests)
- API (3 tests)
- Reports (15 tests)

## Evaluation

**Generate synthetic test data:**
```bash
python backend/utils/create_evaluation_dataset.py data/synthetic_evaluation 12
```

**Run evaluation:**
```bash
python backend/evaluation/evaluate_batch.py \
    --cases data/synthetic_evaluation/evaluation_manifest.json \
    --model models/brats_mri_segmentation/models/model.pt \
    --output evaluation_results.json
```

## Report & Export Locations

After successful inference:
- **JSON Report:** `data/cases/{case_id}/report_{case_id}.json`
- **NIfTI Export:** `data/cases/{case_id}/prediction_{case_id}.nii.gz`
- **Segmentation:** `data/cases/{case_id}/segmentation.nii.gz`

Reports include:
- SHA-256 hashes of all inputs
- Model provenance (name, version, license, training data)
- Git commit hash
- ISO 8601 timestamps
- Estimated volumes in mL
- Research-only disclaimer

## Cleanup Behavior

**Automatic 24-hour deletion:**
- Uploaded files deleted after 24 hours
- Predictions deleted after 24 hours
- Reports deleted after 24 hours
- Cleanup runs on application startup
- Protected assets (models, code, docs) never deleted

**Manual cleanup:**
```python
from services.cleanup_service import cleanup_expired_files
from pathlib import Path
cleanup_expired_files(Path.cwd(), ttl_hours=24, dry_run=False)
```

## Known Issues & Limitations

### Limitations
- **Research use only** - not validated for clinical diagnosis
- **Requires skull-stripped input** - brain tissue only, no skull
- **BraTS 2018 training** - performance depends on data similarity
- **GPU recommended** - CPU inference is significantly slower
- **No concurrent requests** - single-user prototype
- **Synthetic evaluation** - no real BraTS held-out data available

### Known Issues
- **Low Dice scores on synthetic data** - expected, synthetic ≠ real distribution
- **No PDF reports** - JSON only (PDF requires additional dependencies)
- **No standalone CLI** - use API endpoints instead
- **CrosshairSync** - relies on NiiVue, not separately tested for 2-voxel accuracy

### Not Available (External Dependencies)
- Official BraTS scorer (not provided by organizers)
- Real BraTS held-out test data (not accessible)
- Organizer baseline for comparison (not provided)

## Model Information

**Model:** MONAI SegResNet  
**Source:** MONAI Model Zoo brats_mri_segmentation bundle  
**Training Data:** BraTS 2018 Training Dataset  
**License:** Apache 2.0  
**Architecture:** SegResNet (3D residual U-Net)  
**Input:** 4 modalities (T1ce, T1, T2, FLAIR) - 240×240×155 expected  
**Output:** 3 region masks (TC, WT, ET) → converted to BraTS labels 1, 2, 4  

See `docs/MODEL_CARD.md` for complete details.

## Data Sources

**Approved datasets:**
- BraTS 2018 Training (public, de-identified)
- BraTS 2021 Training (public, de-identified)
- Synthetic test data (generated for testing)

**Do not use:**
- Patient-identifiable data
- Clinical scans without IRB approval
- Non-skull-stripped MRI

## Citations & Licenses

### Model
- MONAI: Apache 2.0 License
- SegResNet: Apache 2.0 License
- BraTS 2018 Dataset: CC BY-NC-SA 4.0

### Dependencies
- PyTorch: BSD-3-Clause
- FastAPI: MIT
- NiBabel: MIT
- scikit-image: BSD-3-Clause
- NiiVue: MIT

### Dataset Citation
Menze BH, et al. "The Multimodal Brain Tumor Image Segmentation Benchmark (BRATS)". IEEE Trans Med Imaging. 2015.

## Performance

**Hardware tested:** RTX 4050 Laptop GPU (6GB VRAM), CUDA 12.1

| Metric | Performance |
|--------|-------------|
| Inference time | ~2.5s per case |
| Preprocessing | ~0.3s |
| Postprocessing | ~0.2s |
| Total pipeline | ~3.0s |
| Target | <120s (40x under) |

## Development

**Repository structure:**
```
Kuru/
├── backend/
│   ├── api/          # FastAPI application
│   ├── services/     # Core services
│   ├── utils/        # Utilities
│   ├── evaluation/   # Metrics & evaluation
│   └── tests/        # 93 comprehensive tests
├── frontend/
│   └── index.html    # NiiVue-based viewer
├── models/           # MONAI model weights
├── docs/             # Documentation
└── data/             # Temporary data (auto-created)
```

**Running tests:**
```bash
# All tests
pytest backend/tests/ -v

# Specific module
pytest backend/tests/test_validation.py -v

# With coverage
pytest backend/tests/ --cov=backend/services
```

## Security & Privacy

✅ **All processing local** - no external API calls  
✅ **SHA-256 input hashing** - for reproducibility  
✅ **24-hour auto-deletion** - temporary data removed  
✅ **No PHI in logs** - patient info excluded  
✅ **Sanitized errors** - no stack traces to users  
✅ **Protected assets** - models/code never deleted  

## Support

**Issues:** File issues in the repository  
**Documentation:** See `docs/` directory  
**Questions:** Contact repository maintainers  

## License

This project is released under Apache 2.0 License.

---

**Version:** 2.0  
**Last Updated:** 2026-10-16  
**Status:** Production Ready (Research Use)  
**Tests:** 93/93 Passing  
