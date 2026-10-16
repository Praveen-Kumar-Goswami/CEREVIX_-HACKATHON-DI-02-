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

### Command-Line Interface (CLI)

NeuroScope 3D includes a standalone, fully verified command-line interface for offline and scripted processing:

```bash
python backend/cli.py \
    --t1ce data/test_cases/case001/case001_t1ce.nii.gz \
    --t1   data/test_cases/case001/case001_t1.nii.gz \
    --t2   data/test_cases/case001/case001_t2.nii.gz \
    --flair data/test_cases/case001/case001_flair.nii.gz \
    --output ./prediction.nii.gz \
    --report ./report.json \
    --expert data/test_cases/case001/case001_expert_seg.nii.gz
```

**CLI Output:**
- Standalone multi-label BraTS 2021 NIfTI segmentation file (Labels: 1=NCR, 2=ED, 4=ET, 0=Background).
- Preserves the original image grid shape and affine matrix.
- Structured JSON provenance report with SHA-256 hashes, timestamps, calculated volumes, and optional comparison metrics (Dice, Sensitivity).

### API Endpoints

**Upload:**
```bash
POST /api/upload
Content-Type: multipart/form-data
Body: t1ce, t1, t2, flair files (and optional expert_mask)
```

**Inference:**
```bash
POST /api/inference/{case_id}
```

**Results:**
```bash
GET /api/status/{case_id}
GET /api/nifti/{case_id}/{modality}
GET /api/mesh/{case_id}   # Marching cubes 3D surface geometry (WT, TC, ET)
```

**Report & Export:**
```bash
GET /api/report/{case_id}  # JSON report with provenance and expert metrics
GET /api/export/{case_id}  # NIfTI prediction (BraTS labels 1, 2, 4)
```

## Testing & Quality Assurance

**Run complete automated test suite:**
```bash
pytest backend/tests/ -v
```

**Actual Verified Count:** **108/108 tests PASSING** (~39 seconds on Python 3.11)

**Test modules:**
- `test_validation.py`: 14 tests (NIfTI headers, orientation, shape matching, affine consistency)
- `test_spatial_utils.py`: 27 tests (coordinate mapping, voxel indexing, volume calculation)
- `test_metrics.py`: 23 tests (Dice score, sensitivity, confusion matrix, edge cases)
- `test_inference.py`: 11 tests (MONAI SegResNet pipeline, sliding window, CPU/GPU)
- `test_api.py`: 3 tests (FastAPI endpoints, health checks, error responses)
- `test_reports.py`: 15 tests (provenance metadata, SHA-256 hashing, JSON serialization)
- `test_expert_mask.py`: 4 tests (expert mask validation, Dice/Sensitivity comparison)
- `test_mesh_generation.py`: 6 tests (Marching Cubes surfaces, RAS+ affine coordinate mapping)
- `test_cleanup_service.py`: 5 tests (24-hour TTL expiration, protected file rules)

**Run full end-to-end browser verification (Playwright):**
```bash
python backend/tests/verify_browser_full.py
```
*Verifies all 17 browser workflow steps: upload, validation, GPU inference, 2D NiiVue viewer, 3D Marching Cubes viewer, layer toggles, expert mask metrics, downloads, and case switching.*

## Performance Benchmarks

Benchmark script: `python backend/benchmark_performance.py`  
**Test Hardware:** NVIDIA GeForce RTX 4050 Laptop GPU (6.0 GB VRAM), AMD64 12-core CPU, Windows 11, PyTorch 2.5.1+cu121, Python 3.11.9.  
**Evaluated on:** Genuine BraTS research volume (240 × 240 × 155 voxels, 1.0 mm³ isotropic).

| Pipeline Stage | Mean Duration (s) | Notes |
|----------------|-------------------|-------|
| 1. Upload & File Validation | 0.888 s | Modality headers, shapes, and affines verified |
| 2. MRI Load & Preprocessing | 0.912 s | 4-channel tensor assembly & intensity normalization |
| 3. Model Initialization (Cold) | 0.158 s | SegResNet weights loaded to GPU |
| 4. GPU Inference | 0.620 s | Sliding window (roi_size 240×240×160, sw_batch_size 1) |
| 5. Postprocessing & Mapping | 0.079 s | Probabilities to BraTS labels (1, 2, 4) |
| 6. Volume Calculation | 0.076 s | WT: 21.90 mL, TC: 3.19 mL, ET: 2.61 mL |
| 7. Marching Cubes Mesh Gen | 0.343 s | WT: 14,496 faces, TC: 4,008 faces, ET: 2,752 faces |
| 8. Report & NIfTI Export | 0.282 s | JSON report + multi-label NIfTI file generation |
| **Total Upload-to-Report** | **3.200 s** | **Official Target: < 120s (Passes with 116.80s margin)** |

> [!NOTE]
> **T4-Class GPU Status:** **NOT TESTED** (the hackathon host environment with T4 GPUs was not locally accessible; benchmarks were recorded on the local RTX 4050 Laptop GPU).

## Known Issues & Limitations

### Limitations
- **Research use only** - not validated for clinical diagnosis.
- **Requires skull-stripped input** - brain tissue only, no skull.
- **BraTS 2018 training** - performance depends on data similarity to BraTS distribution.
- **GPU recommended** - CPU inference is significantly slower.
- **No concurrent requests** - designed as a single-user prototype.
- **Held-out real evaluation blocked** - the organizer's 40-case development dataset and official scorer were not provided in the workspace. Evaluation infrastructure is fully tested on synthetic cases and user-supplied expert masks.

### Resolved Capabilities
- **Standalone CLI** - Fully implemented and verified (`backend/cli.py`).
- **3D Real Geometry** - Marching Cubes isosurface extraction replaces placeholder spheres.
- **Expert Mask Comparison** - Users can provide ground truth masks for real-time Dice and Sensitivity metrics.

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

**Version:** 2.1  
**Last Updated:** 2026-10-17  
**Status:** Delivery Ready (Research Use with Documented Limitations)  
**Tests:** 108/108 Passing  
