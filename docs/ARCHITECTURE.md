# NeuroScope 3D – Architecture

**Version:** 1.0  
**Last Updated:** 2026-10-16  
**Status:** Planning

## System Overview

NeuroScope 3D is a web-based scientific platform for brain MRI tumor segmentation visualization. It processes four co-registered NIfTI volumes through a pretrained 3D deep learning model and presents results through interactive 2D slice views, 3D mesh visualization, volumetric analysis, and provenance-rich reporting.

**Design Principles:**
- Privacy-first: All processing local, no external API uploads
- Safety-first: Clear limitations, no clinical claims
- Accuracy-first: Honest metrics, spatial correctness, reproducibility
- Research-grade: Full provenance, evaluation transparency

## Technology Stack

### Frontend
- **Framework:** React 18.2 + TypeScript 5.x
- **Build Tool:** Vite 5.x
- **Styling:** Tailwind CSS 3.x (dark scientific theme)
- **Medical Imaging:** NiiVue 0.45+ for linked 2D slice views
- **3D Visualization:** Three.js r160+ with React Three Fiber
- **State Management:** React Query v5 + Zustand
- **HTTP Client:** Axios
- **Validation:** Zod for runtime types

### Backend
- **Framework:** FastAPI 0.109+
- **Runtime:** Python 3.10+
- **Deep Learning:** PyTorch 2.1+ with CUDA 11.8+
- **Medical Imaging:** MONAI 1.3+
- **NIfTI I/O:** NiBabel 5.x
- **Mesh Generation:** scikit-image marching_cubes
- **Validation:** Pydantic v2
- **Testing:** pytest + pytest-asyncio

### Model
- **Base Model:** MONAI Model Zoo brats_mri_segmentation
- **Architecture:** SegResNet 3D
- **Training Data:** BraTS 2018
- **License:** Apache-2.0
- **Input Order:** T1Gd, T1, T2, FLAIR (to be verified in bundle config)
- **Output:** 3-channel probability maps → BraTS 2021 labels (1=NCR, 2=ED, 4=ET)

### Infrastructure
- **Containerization:** Docker + docker-compose
- **Web Server:** Uvicorn (ASGI) + Nginx (reverse proxy, optional)
- **Storage:** Local filesystem with 24h TTL cleanup
- **GPU:** NVIDIA CUDA-capable (T4-class minimum)

## System Architecture Diagram

\\\
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (Client)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  React + TypeScript UI                                    │  │
│  │  ├─ Upload Component (modality selection, validation)     │  │
│  │  ├─ NiiVue Viewer (linked axial/coronal/sagittal slices) │  │
│  │  ├─ Three.js 3D Viewer (brain + region meshes)           │  │
│  │  ├─ Metrics Panel (volumes, Dice, sensitivity)           │  │
│  │  └─ Report Generator (PDF/HTML export)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│                              │ REST API (JSON)                   │
│                              ▼                                   │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Routes                                               │  │
│  │  ├─ POST /upload (4 NIfTI + optional mask)               │  │
│  │  ├─ POST /predict/{case_id} (trigger inference)          │  │
│  │  ├─ GET /results/{case_id} (meshes, metrics, metadata)   │  │
│  │  ├─ GET /report/{case_id} (generate report)              │  │
│  │  └─ POST /evaluate (judge scorer endpoint)               │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Core Services                                            │  │
│  │  ├─ ValidationService (shape, affine, data integrity)    │  │
│  │  ├─ InferenceService (MONAI model, preprocessing)        │  │
│  │  ├─ MeshService (marching cubes, decimation)             │  │
│  │  ├─ MetricsService (volume calculation, Dice, sens.)     │  │
│  │  └─ ReportService (provenance, SHA-256, disclaimers)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MONAI Model                                              │  │
│  │  └─ SegResNet (pretrained, BraTS 2018, Apache-2.0)       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Storage (Local Filesystem)                               │  │
│  │  ├─ /data/uploads/{case_id}/ (input NIfTI files)         │  │
│  │  ├─ /data/predictions/{case_id}/ (output segmentation)   │  │
│  │  └─ /data/evaluation/ (held-out labeled cases)           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
\\\

## Data Flow

1. **Upload Phase:**
   - User selects 4 NIfTI files + assigns modalities (T1, T1Gd, T2, FLAIR)
   - Frontend: Basic file type check
   - Backend: Deep validation (header parsing, shape/affine compatibility, data integrity, size limits)
   - Case ID generated, files stored in \/data/uploads/{case_id}/\

2. **Inference Phase:**
   - User triggers prediction
   - Backend loads all 4 volumes using NiBabel (preserves affine)
   - Preprocessing: Intensity normalization, resampling if needed (document exact steps)
   - Stack into 4-channel tensor in correct order (T1Gd, T1, T2, FLAIR)
   - MONAI model inference on GPU
   - Post-processing: Argmax → BraTS 2021 labels (1, 2, 4), resample to original grid/affine
   - Construct regions: WT=(1|2|4), TC=(1|4), ET=(4) with proper nesting
   - Save prediction NIfTI to \/data/predictions/{case_id}/segmentation.nii.gz\

3. **Visualization Phase:**
   - Backend generates meshes for brain surface + 3 regions using marching cubes
   - Meshes in millimetre world space (apply affine transforms)
   - Frontend receives: meshes (STL/JSON), slice data URLs, metadata
   - NiiVue loads original NIfTI + segmentation overlay
   - Three.js renders meshes with shared camera/crosshair sync

4. **Evaluation Phase:**
   - Load held-out labeled cases from \/data/evaluation/\
   - Run inference on each, compute Dice & sensitivity per region
   - Store results with patient split documentation

5. **Report Phase:**
   - Aggregate: volumes (mL), metrics, model card, preprocessing steps
   - Compute SHA-256 of input files
   - Add git commit hash, timestamp, disclaimers
   - Generate HTML/PDF report

## Coordinate System Handling

**Critical for spatial correctness:**

- All NIfTI files carry a 4×4 affine matrix mapping voxel indices (i,j,k) → world coordinates (x,y,z) in mm
- **Single Source of Truth:** NiBabel affines
- **Voxel → World Transform:** \world_coords = affine @ [i, j, k, 1]\
- **Volume Calculation:** \olume_ml = voxel_count × det(affine[:3,:3]) / 1000\
- **Mesh Generation:** Apply affine to vertex coordinates before export
- **L/R, A/P, S/I Labels:** Derived from affine orientation (RAS/LPS handling)
- **Crosshair Sync:** Convert crosshair voxel index → world → back to voxel in each view

**Tests:**
- L/R flip with matching affine → same volume, correct labeling
- Mirrored anatomy with unchanged affine → opposite side labeling
- Anisotropic spacing → volume calculation within 10% tolerance

## Security & Privacy

- No external API calls with patient data
- No model inference via cloud services
- Input validation prevents path traversal, code injection
- File size limits (1 GB) prevent DoS
- Temporary storage cleared after 24h
- No logging of PHI (even in research context, maintain best practices)

## Performance Requirements

- **Inference Time:** <2 minutes on T4-class GPU (must measure, not assume)
- **Mesh Generation:** <30 seconds for all regions
- **UI Responsiveness:** Slice navigation <100ms, 3D rotation 60fps
- **Memory:** Handle 256×256×256 volumes without OOM
- **Concurrent Users:** Not required (single-user research prototype acceptable)

## Limitations & Disclaimers

**On every screen:**
> ⚠️ **Research Prototype Only**  
> This system is for research and teaching purposes. Predictions are not validated for clinical use and must not be used for diagnosis or treatment decisions.

**In report:**
- Model trained on BraTS 2018, not validated on other populations
- Possible training/evaluation data overlap (disclose if known)
- Spatial accuracy depends on correct skull-stripping
- No guarantees for non-brain, artifact-heavy, or unusual inputs

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Channel order mismatch | Inspect MONAI bundle config; unit test with known cases |
| Spatial transform errors | Unit tests for affine math; judge geometric tests |
| Inference timeout | Profile early; TorchScript compilation; GPU monitoring |
| Out-of-memory | Reject large files; lazy loading; mesh decimation |
| Skull-strip detection false alarms | Conservative heuristics; allow override with warning |
| Stale predictions | Tie results to input hashes; clear on new upload |
| Fabricated metrics | Compute on real held-out data; document split; never mock |

## Development Phases (High-Level)

1. **Foundation:** Repo setup, Docker, backend skeleton, frontend skeleton
2. **Model Integration:** MONAI bundle download, inference pipeline, verification
3. **NIfTI Validation:** Shape/affine checks, data integrity, error handling
4. **Spatial Correctness:** Volume calculation, coordinate transforms, unit tests
5. **2D Visualization:** NiiVue integration, linked views, crosshair sync
6. **3D Visualization:** Three.js meshes, world-space rendering, toggles
7. **Evaluation System:** Held-out cases, Dice/sensitivity, honest reporting
8. **Report Generation:** Provenance, SHA-256, model card, disclaimers
9. **Judge Test Suite:** All 12+ required tests, evidence collection
10. **Polish & Deployment:** UI refinement, performance tuning, documentation, demo materials

---

**Next Steps:**
- Obtain organizer starter kit & 40-case dev subset
- Inspect MONAI bundle configuration
- Verify GPU availability & CUDA environment
- Set up development environment
- Begin Stage 1 implementation
