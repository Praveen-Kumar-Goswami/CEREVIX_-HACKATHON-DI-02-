# NeuroScope 3D – Implementation Plan (10 Prompts)

**Version:** 1.0 (Baseline)  
**Last Updated:** 2026-10-16  
**Status:** Planning - Prompt 1 Complete

---

## Overview

This plan structures NeuroScope 3D implementation into 10 sequential prompts aligned with the 24-hour hackathon constraint. Each prompt has explicit acceptance criteria and must be verified before proceeding.

**Principles:**
- Each prompt establishes a checkpoint before continuing
- No fabricated results or placeholder predictions
- Incremental testing with evidence collection
- Blockers resolved before advancing

---

## PROMPT 1: Repository Audit & Baseline ✅ COMPLETE

**Status:** ✅ VERIFIED  
**Duration:** ~1 hour  
**Priority:** CRITICAL

### Goal
Establish project baseline without building anything.

### Tasks
- ✅ Inspect directory tree, environment, GPU, dependencies
- ✅ Finalize ARCHITECTURE.md with verified stack
- ✅ Create REQUIREMENTS_TRACEABILITY.md mapping all 28 requirements
- ✅ Create detailed IMPLEMENTATION_PLAN.md (this file)
- ✅ Create PROJECT_PROGRESS.md with baseline facts
- ✅ Create TEST_PLAN.md with all test specifications
- ✅ Identify missing resources (MONAI bundle, datasets, starter kit)

### Acceptance Criteria
- ✅ Existing repository fully inspected
- ✅ Architecture documented with tech stack rationale
- ✅ Every requirement mapped to implementation stage
- ✅ Baseline test commands recorded with actual outcomes
- ✅ Zero fabricated metrics or model results
- ✅ Official requirements verified (labels, modalities, affine, timing)

### Deliverables
- ✅ docs/ARCHITECTURE.md
- ✅ docs/REQUIREMENTS_TRACEABILITY.md
- ✅ docs/IMPLEMENTATION_PLAN.md
- ✅ docs/PROJECT_PROGRESS.md
- ✅ docs/TEST_PLAN.md

### Blockers Identified
- ⚠️ Docker not installed (USER ACTION REQUIRED)
- ⚠️ GPU verification blocked by permissions (needs admin)
- ⚠️ PyTorch not installed
- ⚠️ MONAI bundle not downloaded
- ⚠️ No sample BraTS data present

---

## PROMPT 2: Foundation & Environment Setup

**Status:** ⬜ NOT STARTED (Blocked by Docker install)  
**Duration:** ~2 hours  
**Priority:** CRITICAL  
**Prerequisites:** Docker installed, GPU verified

### Goal
Create working development environment with health checks.

### Tasks
1. Create .gitignore (Python, Node, Docker, data/, models/)
2. Create docker-compose.yml with:
   - Backend service (FastAPI, Python 3.10)
   - Frontend service (React + Vite)
   - Shared volumes for data/ and models/
   - GPU passthrough configuration
3. Create ackend/ structure:
   - Dockerfile (Python 3.10, CUDA 11.8)
   - equirements.txt (FastAPI, uvicorn, PyTorch, MONAI, NiBabel, pydantic)
   - main.py with health endpoint
   - pi/, services/, utils/, 	ests/ directories
4. Create rontend/ structure:
   - Dockerfile (Node 20)
   - package.json (React 18, TypeScript, Vite, Tailwind)
   - src/App.tsx with "NeuroScope 3D" title
   - Basic dark theme
5. Create README.md with:
   - Project description
   - Prerequisites (Docker, NVIDIA Container Toolkit)
   - One-command startup: docker-compose up
   - Organizer resources section (TBD)
6. Initialize git with first commit

### Acceptance Criteria
- [ ] docker-compose up starts both containers without errors
- [ ] Backend accessible at http://localhost:8000/health returns {"status": "healthy"}
- [ ] Frontend accessible at http://localhost:3000 shows "NeuroScope 3D"
- [ ] Git repository has initial commit with all scaffolding
- [ ] README has clear startup instructions
- [ ] No application logic yet (just scaffolding)

### Verification Commands
\\\powershell
# Start services
docker-compose up -d

# Test backend health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000

# Check git
git log --oneline
\\\

### Deliverables
- .gitignore
- docker-compose.yml
- ackend/Dockerfile, ackend/requirements.txt, ackend/main.py
- rontend/Dockerfile, rontend/package.json, rontend/src/App.tsx
- README.md
- Git commit: "Initial scaffolding - backend + frontend + Docker"

### Requirements Addressed
- REQ-16 (partial): README with startup command

---

## PROMPT 3: MONAI Model Integration & Verification

**Status:** ⬜ NOT STARTED  
**Duration:** ~2 hours  
**Priority:** CRITICAL  
**Prerequisites:** Prompt 2 complete, GPU verified, internet access

### Goal
Download MONAI bundle, verify semantics, run test inference.

### Tasks
1. Create ackend/scripts/download_model.py:
   - Use MONAI bundle API to download rats_mri_segmentation
   - Save to models/brats_mri_segmentation/
   - Verify download integrity
2. Create ackend/services/inference_service.py:
   - Load MONAI bundle
   - Parse bundle config to verify:
     - Input channel order (T1Gd, T1, T2, FLAIR - **must verify**)
     - Output channel semantics (**must map to BraTS 2021 labels**)
   - Implement predict() method (stub)
3. Create synthetic 4-channel test input (128×128×128)
4. Run test inference on GPU
5. Document findings in docs/MODEL_CARD.md:
   - Architecture (SegResNet)
   - Training data (BraTS 2018)
   - License (Apache-2.0)
   - Input order (verified)
   - Output semantics (verified)
   - Preprocessing requirements
6. Create ackend/tests/test_inference.py:
   - Test model loads successfully
   - Test inference produces correct output shape
   - Test GPU utilization

### Acceptance Criteria
- [ ] MONAI bundle downloaded to models/brats_mri_segmentation/
- [ ] Bundle config inspected, input order documented
- [ ] Test inference on synthetic data completes in <30s on GPU
- [ ] Output shape verified: (1, 3, H, W, D) for 3-channel probabilities
- [ ] 
vidia-smi shows GPU utilization during inference
- [ ] MODEL_CARD.md documents actual bundle semantics (not assumptions)
- [ ] Unit test 	est_inference.py passes

### Verification Commands
\\\powershell
# Download model
docker-compose exec backend python scripts/download_model.py

# Verify bundle
ls models/brats_mri_segmentation/

# Run test inference
docker-compose exec backend pytest tests/test_inference.py -v

# Monitor GPU
nvidia-smi dmon -s u
\\\

### Deliverables
- models/brats_mri_segmentation/ (bundle files)
- ackend/scripts/download_model.py
- ackend/services/inference_service.py (stub with model loading)
- ackend/tests/test_inference.py
- docs/MODEL_CARD.md

### Requirements Addressed
- REQ-4 (partial): Model loading and basic inference
- REQ-23: Input modality order verification
- REQ-24: Output label semantics verification

### Blockers
- If bundle config differs from docs, document actual semantics
- If GPU OOM, reduce test input size and document

---

## PROMPT 4: NIfTI Upload & Deep Validation

**Status:** ⬜ NOT STARTED  
**Duration:** ~2 hours  
**Priority:** CRITICAL  
**Prerequisites:** Prompt 3 complete, sample BraTS case available

### Goal
Implement robust upload endpoint with all 8 failure modes tested.

### Tasks
1. Add NiBabel to equirements.txt
2. Create ackend/services/validation_service.py:
   - alidate_nifti_file(): Format, 3D check, data integrity
   - alidate_nifti_set(): Shape/affine compatibility
   - Clear error messages for each failure mode
3. Create ackend/api/routes/upload.py:
   - POST /api/upload accepting multipart form (4 files + modality labels)
   - Generate case_id (UUID)
   - Save files to data/uploads/{case_id}/
   - Return case_id or validation errors
4. Create ackend/utils/nifti_utils.py:
   - File I/O helpers
   - SHA-256 computation
5. Create ackend/tests/test_validation.py:
   - All 8 judge failure test cases
   - Valid upload test
6. Create synthetic test data:
   - Corrupt .nii.gz
   - 2D image
   - All-zero volume
   - Volume with NaN
   - Mismatched shapes
   - Files >1GB (or mock size check)

### Acceptance Criteria
- [ ] Valid 4-file upload succeeds, returns case_id
- [ ] Corrupt file → Error: "File [name] is corrupted or unreadable"
- [ ] 2D input → Error: "File [name] must be a 3D volume"
- [ ] NaN values → Error: "File [name] contains invalid voxel values"
- [ ] All-zero → Error: "File [name] contains no signal"
- [ ] >1GB → Error: "File [name] exceeds size limit"
- [ ] Mismatched shapes → Error: "incompatible shapes" with dimensions
- [ ] Mismatched affines → Error: "incompatible spatial transforms"
- [ ] All tests in 	est_validation.py pass (VAL-001 to VAL-010)
- [ ] No crashes, no stack traces shown to user

### Verification Commands
\\\powershell
# Run validation tests
docker-compose exec backend pytest tests/test_validation.py -v

# Manual API test
curl -X POST http://localhost:8000/api/upload -F "t1=@test_t1.nii.gz" -F "t1gd=@test_t1gd.nii.gz" -F "t2=@test_t2.nii.gz" -F "flair=@test_flair.nii.gz"
\\\

### Deliverables
- ackend/services/validation_service.py
- ackend/api/routes/upload.py
- ackend/utils/nifti_utils.py
- ackend/tests/test_validation.py
- ackend/tests/fixtures/ (synthetic invalid test files)

### Requirements Addressed
- REQ-1: Accept 4 NIfTI files with modality identification
- REQ-2: All validation rules
- REQ-10: Safe failure handling
- REQ-19: All 8 judge failure tests (JUDGE-009 to JUDGE-016)

---

## PROMPT 5: Spatial Correctness & Volume Calculation

**Status:** ⬜ NOT STARTED  
**Duration:** ~2 hours  
**Priority:** CRITICAL (judge geometric tests)  
**Prerequisites:** Prompt 4 complete, synthetic geometric test cases

### Goal
Implement correct spatial math and pass all geometric judge tests.

### Tasks
1. Create ackend/utils/spatial_utils.py:
   - oxel_to_world(voxel_coords, affine) → mm coords
   - world_to_voxel(world_coords, affine) → voxel indices
   - calculate_volume_ml(voxel_count, affine) → volume in mL
   - detect_orientation(affine) → L/R, A/P, S/I labels
   - erify_affine_compatibility(affines, tolerance=0.01) → bool
2. Create ackend/services/metrics_service.py:
   - calculate_region_volumes(mask, affine) → dict of volumes per region
   - compute_dice(pred, gt, labels) → Dice scores
   - compute_sensitivity(pred, gt, labels) → sensitivity scores
3. Create synthetic test cases:
   - 20×20×20 cube with label 2, spacing 1×1×2 mm
   - Anisotropic case + downsampled version
   - L/R flipped case with matching affine
   - Mirrored anatomy case
4. Create ackend/tests/test_spatial_correctness.py:
   - SPATIAL-001 to SPATIAL-007 (unit tests)
   - JUDGE-001 to JUDGE-004 (geometric accuracy)

### Acceptance Criteria
- [ ] Cube test: 20×20×20 voxels, 1×1×2 mm → 16.0 mL ±1% (15.84-16.16)
- [ ] Anisotropic test: volumes differ by ≤10%
- [ ] L/R flip test: same side label, volume within 2%
- [ ] Mirrored anatomy: tumor on opposite side
- [ ] All unit tests pass (SPATIAL-001 to SPATIAL-007)
- [ ] All geometric tests pass (JUDGE-001 to JUDGE-004)
- [ ] Volume formula displayed correctly in future UI

### Verification Commands
\\\powershell
# Run spatial tests
docker-compose exec backend pytest tests/test_spatial_correctness.py -v

# Run judge geometric tests
docker-compose exec backend pytest tests/test_judge_geometric.py -v
\\\

### Deliverables
- ackend/utils/spatial_utils.py
- ackend/services/metrics_service.py
- ackend/tests/test_spatial_correctness.py
- ackend/tests/test_judge_geometric.py
- ackend/tests/fixtures/synthetic_test_cases.py

### Requirements Addressed
- REQ-8: Volume calculation with correct formula
- REQ-17: Geometric accuracy tests
- REQ-7 (partial): Coordinate transforms for future crosshair

---

## PROMPT 6: End-to-End Inference Pipeline

**Status:** ⬜ NOT STARTED  
**Duration:** ~2-3 hours  
**Priority:** HIGH  
**Prerequisites:** Prompts 3-5 complete

### Goal
Full predict endpoint: upload → inference → save prediction on original grid.

### Tasks
1. Extend ackend/services/inference_service.py:
   - preprocess(nifti_files): Load, normalize, stack in correct order
   - un_inference(input_tensor): MONAI model forward pass
   - postprocess(output, original_affine): Argmax, map labels, resample to original grid
   - construct_regions(mask): Build WT, TC, ET from labels 1, 2, 4
   - Verify ET ⊆ TC ⊆ WT
2. Create ackend/api/routes/predict.py:
   - POST /api/predict/{case_id}: Trigger inference
   - Load uploaded files from data/uploads/{case_id}/
   - Run full pipeline
   - Save prediction to data/predictions/{case_id}/segmentation.nii.gz
   - Calculate volumes using MetricsService
   - Return status + volumes
3. Profile inference timing
4. Create ackend/tests/test_inference_pipeline.py:
   - INF-001 to INF-005 (integration tests)
   - JUDGE-017 to JUDGE-018 (repeatability)

### Acceptance Criteria
- [ ] Full pipeline completes on synthetic 4-volume case
- [ ] Output NIfTI has same shape and affine as input
- [ ] Output uses only BraTS 2021 labels (1, 2, 4)
- [ ] Regions satisfy ET ⊆ TC ⊆ WT
- [ ] Same input run twice → Dice ≥0.99 between outputs
- [ ] Inference time measured and logged
- [ ] Volumes calculated and returned in API response
- [ ] Integration tests pass (INF-001 to INF-005)
- [ ] Repeatability tests pass (JUDGE-017, JUDGE-018)

### Verification Commands
\\\powershell
# Upload test case
curl -X POST http://localhost:8000/api/upload -F "t1=@case001_t1.nii.gz" ...

# Run inference
curl -X POST http://localhost:8000/api/predict/{case_id}

# Check output
ls data/predictions/{case_id}/

# Run tests
docker-compose exec backend pytest tests/test_inference_pipeline.py -v
\\\

### Deliverables
- ackend/services/inference_service.py (complete)
- ackend/api/routes/predict.py
- ackend/tests/test_inference_pipeline.py

### Requirements Addressed
- REQ-4: 3D inference with correct preprocessing/postprocessing
- REQ-5: Region construction with subset verification
- REQ-14: Performance timing
- REQ-20: Repeatability (JUDGE-017, JUDGE-018)

### Performance Target
- <2 minutes on T4 GPU (measure actual time, log warning if exceeded)

---

## PROMPT 7: 2D Visualization with NiiVue

**Status:** ⬜ NOT STARTED  
**Duration:** ~2-3 hours  
**Priority:** HIGH  
**Prerequisites:** Prompt 6 complete, sample prediction available

### Goal
Linked 2D slice views with crosshair sync and coordinate display.

### Tasks
1. Add NiiVue to rontend/package.json
2. Create rontend/src/components/NiiVueViewer.tsx:
   - Load 4 modalities + segmentation overlay
   - 3-panel layout (axial, coronal, sagittal)
   - Crosshair synchronization
   - Hover: display voxel indices + world coords
   - L/R, A/P, S/I orientation labels
   - Segmentation colormap (NCR=red, ED=green, ET=yellow)
3. Create rontend/src/utils/niftiLoader.ts:
   - Fetch NIfTI from backend
   - Load into NiiVue
4. Create backend endpoint GET /api/results/{case_id}/nifti:
   - Serve original NIfTI + segmentation for frontend
5. Manual testing + screenshots

### Acceptance Criteria
- [ ] NiiVue loads 4 modalities + segmentation overlay
- [ ] Three orthogonal views displayed side-by-side
- [ ] Crosshair synchronized across all views (within 2 voxels)
- [ ] Hover shows voxel index (i, j, k) and world coords (x, y, z) in mm
- [ ] L/R, A/P, S/I labels displayed correctly
- [ ] Segmentation visible with adjustable opacity
- [ ] Slice navigation responsive (<100ms)
- [ ] Manual test of JUDGE-005 to JUDGE-008 (crosshair sync)

### Verification
- Manual testing with real case
- Screenshot evidence in docs/JUDGE_TEST_EVIDENCE/crosshair_sync.png

### Deliverables
- rontend/src/components/NiiVueViewer.tsx
- rontend/src/utils/niftiLoader.ts
- ackend/api/routes/results.py (partial)
- Screenshots for judge evidence

### Requirements Addressed
- REQ-7: Linked 2D slice views
- REQ-18: Crosshair sync (JUDGE-005 to JUDGE-008)

---

## PROMPT 8: 3D Visualization with Three.js

**Status:** ⬜ NOT STARTED  
**Duration:** ~2-3 hours  
**Priority:** HIGH  
**Prerequisites:** Prompt 6 complete

### Goal
3D brain + region meshes in mm world space with controls.

### Tasks
1. Create ackend/services/mesh_service.py:
   - Use scikit-image marching_cubes on segmentation
   - Apply affine transform to vertices → mm world space
   - Decimate if vertex count >100k
   - Export as JSON (vertices, faces)
2. Create backend endpoint GET /api/results/{case_id}/meshes:
   - Generate meshes for brain + WT + TC + ET
   - Return JSON mesh data
3. Add Three.js, React Three Fiber to rontend/package.json
4. Create rontend/src/components/ThreeDViewer.tsx:
   - Load meshes from backend
   - Render with distinct colors (WT=green, TC=blue, ET=yellow)
   - Camera controls (orbit, zoom, pan)
   - Toggle visibility per region
   - Opacity sliders per region
5. Sync 3D crosshair with 2D views (world coords)

### Acceptance Criteria
- [ ] Brain surface mesh rendered
- [ ] WT, TC, ET meshes rendered in distinct colors
- [ ] Meshes in mm world space (verified with coordinate check)
- [ ] Camera orbit, zoom, pan work smoothly (target 60fps)
- [ ] Toggle buttons show/hide each region
- [ ] Opacity sliders adjust transparency (0-100%)
- [ ] 3D view camera focuses on crosshair when 2D view clicked
- [ ] Mesh generation completes in <30 seconds

### Verification
- Manual testing with real case
- Performance profiling (fps counter)

### Deliverables
- ackend/services/mesh_service.py
- ackend/api/routes/results.py (complete)
- rontend/src/components/ThreeDViewer.tsx

### Requirements Addressed
- REQ-6: 3D meshes in mm world space with controls

---

## PROMPT 9: Evaluation System & Honest Reporting

**Status:** ⬜ NOT STARTED  
**Duration:** ~2 hours  
**Priority:** MEDIUM  
**Prerequisites:** Prompt 6 complete, 10+ labeled BraTS cases available

### Goal
Evaluate on held-out cases with patient-level split and honest metrics.

### Tasks
1. Acquire 10+ labeled BraTS cases (preferably BraTS 2021 validation set)
2. Store in data/evaluation/ with manifest
3. Create data/evaluation/manifest.json:
   - Patient IDs
   - File paths
   - Patient-level split documentation
4. Create ackend/services/evaluation_service.py:
   - Load evaluation cases
   - Run inference on each
   - Compute Dice & sensitivity per region (WT, TC, ET)
   - Aggregate statistics (mean, std)
5. Create ackend/api/routes/evaluate.py:
   - POST /api/evaluate: Judge scorer endpoint
   - Accepts input paths, returns prediction path
6. Create docs/EVALUATION_RESULTS.md:
   - Case IDs
   - Dice & sensitivity per region
   - Training data overlap disclosure
7. Add evaluation metrics to UI

### Acceptance Criteria
- [ ] ≥10 held-out cases with ground truth available
- [ ] Patient-level split documented (no patient in both train and test)
- [ ] Dice and sensitivity computed per WT, TC, ET
- [ ] Results stored in EVALUATION_RESULTS.md with actual scores
- [ ] Evaluation manifest lists all case IDs
- [ ] Training overlap disclosed (BraTS 2018 train vs. our eval set)
- [ ] Judge endpoint /api/evaluate accepts paths, returns prediction
- [ ] No fabricated scores (all computed from real inference)

### Verification Commands
\\\powershell
# Run evaluation
docker-compose exec backend python -m services.evaluation_service

# Test judge endpoint
curl -X POST http://localhost:8000/api/evaluate -d '{"input_paths": [...], "output_path": "..."}'
\\\

### Deliverables
- data/evaluation/manifest.json
- ackend/services/evaluation_service.py
- ackend/api/routes/evaluate.py
- docs/EVALUATION_RESULTS.md

### Requirements Addressed
- REQ-9: Evaluation on ≥10 held-out cases
- REQ-22: Judge scorer CLI/endpoint
- REQ-21: Blind case test (JUDGE-019)

---

## PROMPT 10: Report Generation, Judge Tests & Final Polish

**Status:** ⬜ NOT STARTED  
**Duration:** ~3-4 hours  
**Priority:** HIGH (final verification)  
**Prerequisites:** All previous prompts complete

### Goal
Complete report generation, verify all judge tests, collect evidence, polish UI.

### Tasks
1. Create ackend/services/report_service.py:
   - Aggregate volumes, formulas, metrics
   - Model card info
   - Preprocessing steps
   - SHA-256 of inputs
   - Git commit hash
   - Timestamp
   - Limitations & disclaimers
2. Create ackend/api/routes/report.py:
   - GET /api/report/{case_id}: Generate report
3. Create HTML report template
4. Generate sample report and save to docs/sample_report.html
5. Add disclaimer banner to all frontend pages
6. Create ackend/services/cleanup_service.py:
   - Background task: delete uploads >24h old
7. Run all judge tests and collect evidence:
   - Screenshots of UI
   - Test output logs
   - Timing measurements
8. Update PROJECT_PROGRESS.md with VERIFIED status for all stages
9. Create docs/DEMO_SCRIPT.md (5-minute demo)
10. Finalize README.md

### Acceptance Criteria
- [ ] Report includes all required elements (REQ-12):
  - Volumes in mL with formula
  - Metrics (if expert mask provided)
  - Model name, version, license, training data
  - Preprocessing description
  - SHA-256 of 4 inputs
  - Git commit hash
  - Timestamp
  - Limitations & disclaimers
- [ ] Report downloadable as HTML
- [ ] Sample report in docs/sample_report.html
- [ ] Disclaimer visible on every screen (REQ-13)
- [ ] Upload cleanup runs every hour, deletes files >24h (REQ-15)
- [ ] All judge tests pass:
  - JUDGE-001 to JUDGE-004 (geometric) ✅
  - JUDGE-005 to JUDGE-008 (crosshair sync) ✅
  - JUDGE-009 to JUDGE-016 (failure handling) ✅
  - JUDGE-017 to JUDGE-018 (repeatability) ✅
  - JUDGE-019 (blind case) ✅
- [ ] Evidence collected in docs/JUDGE_TEST_EVIDENCE/
- [ ] Performance verified: <2 min on T4 GPU
- [ ] Demo script complete
- [ ] README complete with all sections

### Verification
- Run full judge test suite
- Collect screenshots, logs, timing data
- Verify all acceptance criteria in PROJECT_PROGRESS.md

### Deliverables
- ackend/services/report_service.py
- ackend/api/routes/report.py
- ackend/templates/report_template.html
- ackend/services/cleanup_service.py
- docs/sample_report.html
- docs/DEMO_SCRIPT.md
- docs/JUDGE_TEST_EVIDENCE/ (all evidence)
- README.md (complete)
- rontend/src/components/DisclaimerBanner.tsx

### Requirements Addressed
- REQ-12: Report generation
- REQ-13: Disclaimers on every screen
- REQ-15: 24h upload deletion
- REQ-16: Complete deployment package
- All remaining judge tests

---

## 24-Hour Priority Order

If time-constrained, implement in this order:

### CRITICAL PATH (Must Have - Hours 1-16)
1. ✅ Prompt 1: Baseline (1h)
2. Prompt 2: Foundation (2h)
3. Prompt 3: Model Integration (2h)
4. Prompt 4: Validation (2h)
5. Prompt 5: Spatial Correctness (2h)
6. Prompt 6: Inference Pipeline (3h)
7. Prompt 9 (partial): Basic evaluation (2h)
8. Prompt 10 (partial): Essential judge tests (2h)

### HIGH PRIORITY (Should Have - Hours 17-20)
9. Prompt 7: 2D Visualization (2h)
10. Prompt 8: 3D Visualization (2h)

### MEDIUM PRIORITY (Nice to Have - Hours 21-24)
11. Prompt 9 (complete): Full evaluation metrics (1h)
12. Prompt 10 (complete): Report generation, polish (3h)

---

## Risk Management

| Stage | Risk | Impact | Mitigation |
|-------|------|--------|------------|
| 2 | Docker setup fails | HIGH | Pre-verify Docker works |
| 3 | MONAI bundle unavailable | CRITICAL | Have backup download link |
| 3 | GPU OOM | HIGH | Reduce batch size, profile early |
| 5 | Geometric tests fail | CRITICAL | Unit test affine math first |
| 6 | Inference >2 min | HIGH | Profile, optimize, consider TorchScript |
| 9 | Can't get held-out data | MEDIUM | Use public BraTS, disclose overlap |

---

## Dependencies & Prerequisites

### Before Prompt 2:
- Docker Desktop installed
- GPU verified with 
vidia-smi

### Before Prompt 3:
- Internet for MONAI download
- GPU with 16GB+ VRAM

### Before Prompt 4:
- At least one sample 4-modality BraTS case

### Before Prompt 5:
- Synthetic geometric test cases created

### Before Prompt 9:
- 10+ labeled BraTS cases with ground truth

---

## Success Criteria

**Project is complete when:**
- All 10 prompts verified
- All judge tests passing
- Performance <2 min on T4 GPU
- Evidence collected for all requirements
- No fabricated metrics or fake predictions
- Comprehensive documentation ready
- Demo-ready for 5-minute presentation

---

**Status:** Prompt 1 complete, ready for Prompt 2 after blockers resolved  
**Next Action:** User must install Docker and verify GPU, then paste Prompt 2
