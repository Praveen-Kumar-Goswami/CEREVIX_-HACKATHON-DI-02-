# NeuroScope 3D – Test Plan

**Version:** 1.0 (Baseline)  
**Last Updated:** 2026-10-16  
**Status:** Planning

---

## Test Strategy Overview

This test plan ensures NeuroScope 3D meets all mandatory requirements, passes judge acceptance tests, and maintains research-grade quality without fabricating results.

**Test Pyramid:**
- **Unit Tests:** Spatial math, validation logic, utilities (~60% of tests)
- **Integration Tests:** API endpoints, inference pipeline, mesh generation (~30%)
- **Acceptance Tests:** Judge geometric tests, failure modes, E2E workflows (~10%)
- **Performance Tests:** Inference timing, memory usage, UI responsiveness

**Test Execution:** Automated (pytest, Vitest) + Manual (UI, crosshair sync, visual inspection)

---

## 1. Unit Tests

### 1.1 Spatial Correctness Tests
**Module:** backend/utils/spatial_utils.py  
**Test File:** backend/tests/test_spatial_correctness.py

| Test ID | Test Name | Input | Expected Output | Requirement |
|---------|-----------|-------|-----------------|-------------|
| SPATIAL-001 | Volume calculation - cubic voxels | 20×20×20 voxels, spacing 1×1×1 mm | 8.0 mL | REQ-8 |
| SPATIAL-002 | Volume calculation - anisotropic | 20×20×20 voxels, spacing 1×1×2 mm | 16.0 mL (±1%) | REQ-8, REQ-17 |
| SPATIAL-003 | Voxel to world transform | Voxel [10,10,10], standard affine | World coords in mm | REQ-7 |
| SPATIAL-004 | World to voxel transform | World [50,50,50] mm, standard affine | Voxel indices | REQ-7 |
| SPATIAL-005 | Orientation detection - RAS | RAS affine | Labels: R/L, A/P, S/I | REQ-7 |
| SPATIAL-006 | Orientation detection - LPS | LPS affine | Labels: L/R, P/A, I/S | REQ-7 |
| SPATIAL-007 | Affine determinant | Various affines | Correct voxel volume mm³ | REQ-8 |

### 1.2 Validation Tests
**Module:** backend/services/validation_service.py  
**Test File:** backend/tests/test_validation.py

| Test ID | Test Name | Input | Expected Outcome | Requirement |
|---------|-----------|-------|------------------|-------------|
| VAL-001 | Accept valid 4 NIfTI files | 4 compatible .nii.gz | case_id returned | REQ-1, REQ-2 |
| VAL-002 | Reject corrupt file | Truncated .nii.gz | Error: "not a valid NIfTI file" | REQ-2, REQ-19 |
| VAL-003 | Reject 2D volume | Shape [256,256,1] | Error: "must be a 3D volume" | REQ-2, REQ-19 |
| VAL-004 | Reject NaN values | Volume with NaN | Error: "non-finite voxel values" | REQ-2, REQ-19 |
| VAL-005 | Reject all-zero volume | All voxels = 0 | Error: "constant or all-zero data" | REQ-2, REQ-19 |
| VAL-006 | Reject >1GB file | 1.1 GB file | Error: "exceeds 1 GB size limit" | REQ-2, REQ-19 |
| VAL-007 | Reject mismatched shapes | [256,256,128] and [240,240,155] | Error: "incompatible shapes" | REQ-2, REQ-19 |
| VAL-008 | Reject mismatched affines | Affines differ >0.01 | Error: "incompatible spatial transforms" | REQ-2, REQ-19 |
| VAL-009 | Accept only 4 files | 3 files uploaded | Error: "4 files required" | REQ-1 |
| VAL-010 | No crash on any failure | All failure modes | Returns error, no stack trace | REQ-2, REQ-10 |

### 1.3 Region Construction Tests
**Module:** backend/services/inference_service.py  
**Test File:** backend/tests/test_regions.py

| Test ID | Test Name | Input Mask | Expected Regions | Requirement |
|---------|-----------|------------|------------------|-------------|
| REG-001 | WT construction | Labels 1,2,4 present | WT = union of all three | REQ-5 |
| REG-002 | TC construction | Labels 1,4 present | TC = union of 1 and 4 | REQ-5 |
| REG-003 | ET construction | Label 4 present | ET = label 4 only | REQ-5 |
| REG-004 | Subset verification | WT, TC, ET constructed | ET ⊆ TC ⊆ WT | REQ-5 |
| REG-005 | Edge case - only NCR | Label 1 only | WT=TC={1}, ET=empty | REQ-5 |
| REG-006 | Edge case - only ED | Label 2 only | WT={2}, TC=ET=empty | REQ-5 |

### 1.4 Metrics Calculation Tests
**Module:** backend/services/metrics_service.py  
**Test File:** backend/tests/test_metrics.py

| Test ID | Test Name | Ground Truth | Prediction | Expected Dice | Requirement |
|---------|-----------|--------------|------------|---------------|-------------|
| MET-001 | Dice - perfect match | Label 4: 100 voxels | Label 4: 100 voxels | 1.0 | REQ-9 |
| MET-002 | Dice - 50% overlap | Label 4: [0:100] | Label 4: [50:150] | 0.667 | REQ-9 |
| MET-003 | Dice - no overlap | Label 4: [0:100] | Label 4: [200:300] | 0.0 | REQ-9 |
| MET-004 | Sensitivity calculation | TP=80, FN=20 | N/A | 0.80 | REQ-9 |

---

## 2. Integration Tests

### 2.1 API Endpoint Tests
**Test File:** backend/tests/test_api_integration.py

| Test ID | Endpoint | Method | Test Case | Expected Status | Requirement |
|---------|----------|--------|-----------|-----------------|-------------|
| API-001 | /health | GET | Health check | 200 OK | Baseline |
| API-002 | /upload | POST | Valid 4 files | 201, case_id | REQ-1 |
| API-003 | /upload | POST | Invalid file | 400, error msg | REQ-2 |
| API-004 | /predict/{id} | POST | Valid case_id | 202, job started | REQ-4 |
| API-005 | /predict/{id} | POST | Invalid case_id | 404 | REQ-10 |
| API-006 | /results/{id} | GET | After inference | 200, meshes+metrics | REQ-6, REQ-8 |
| API-007 | /report/{id} | GET | After inference | 200, HTML/PDF | REQ-12 |
| API-008 | /evaluate | POST | Judge scorer call | 200, prediction path | REQ-22 |

### 2.2 Inference Pipeline Tests
**Test File:** backend/tests/test_inference_pipeline.py

| Test ID | Test Name | Input | Expected Output | Requirement |
|---------|-----------|-------|-----------------|-------------|
| INF-001 | End-to-end inference | 4 synthetic volumes | Prediction on original grid | REQ-4 |
| INF-002 | Output label codes | 4 volumes | Labels 1, 2, 4 only | REQ-4 |
| INF-003 | Output affine preserved | Input affine | Output affine matches | REQ-4 |
| INF-004 | Reproducibility | Same input, 2 runs | Dice ≥0.99 between outputs | REQ-20 |
| INF-005 | Timing measurement | Real case | Time logged, <2 min on T4 | REQ-14 |

### 2.3 Mesh Generation Tests
**Test File:** backend/tests/test_mesh_generation.py

| Test ID | Test Name | Input Mask | Expected Output | Requirement |
|---------|-----------|------------|-----------------|-------------|
| MESH-001 | Brain surface mesh | Full brain mask | Vertices in mm world space | REQ-6 |
| MESH-002 | WT region mesh | WT mask | Mesh with correct transform | REQ-6 |
| MESH-003 | TC region mesh | TC mask | Mesh subset of WT | REQ-6 |
| MESH-004 | ET region mesh | ET mask | Mesh subset of TC | REQ-6 |
| MESH-005 | Timing | All 4 meshes | <30 seconds total | REQ-6 |

---

## 3. Judge Acceptance Tests

### 3.1 Geometric Accuracy Tests
**Test File:** backend/tests/test_judge_geometric.py

| Test ID | Test Name | Input | Expected Result | Pass Criteria | Requirement |
|---------|-----------|-------|-----------------|---------------|-------------|
| JUDGE-001 | Cube volume test | 20×20×20, label 2, 1×1×2 mm | WT=16.0 mL, TC=0, ET=0 | WT: 15.84-16.16 mL | REQ-8, REQ-17 |
| JUDGE-002 | Anisotropic volume | Original + downsampled | WT volumes | Differ by ≤10% | REQ-17 |
| JUDGE-003 | L/R flip with affine | Flipped voxels + flipped affine | Same side label, same volume | Volume within 2% | REQ-17 |
| JUDGE-004 | Mirrored anatomy | Mirrored voxels, same affine | Opposite side label | Tumor on opposite side | REQ-17 |

### 3.2 Crosshair Synchronization Test
**Test File:** Manual inspection + frontend/tests/test_crosshair_sync.spec.ts

| Test ID | Test Name | User Action | Expected Behavior | Pass Criteria | Requirement |
|---------|-----------|-------------|-------------------|---------------|-------------|
| JUDGE-005 | Axial click sync | Click axial view | Coronal & sagittal update | Within 2 voxels | REQ-18 |
| JUDGE-006 | Coronal click sync | Click coronal view | Axial & sagittal update | Within 2 voxels | REQ-18 |
| JUDGE-007 | Sagittal click sync | Click sagittal view | Axial & coronal update | Within 2 voxels | REQ-18 |
| JUDGE-008 | 3D view sync | Click 2D view | 3D camera focuses on crosshair | Visual confirmation | REQ-18 |

### 3.3 Failure Handling Tests
**Test File:** backend/tests/test_judge_failures.py

| Test ID | Failure Mode | Input | Expected Error Message | Pass Criteria | Requirement |
|---------|--------------|-------|------------------------|---------------|-------------|
| JUDGE-009 | Corrupt NIfTI | Invalid .nii.gz | "corrupted or unreadable" | Clear msg, no crash | REQ-19 |
| JUDGE-010 | 2D image | Shape [256,256,1] | "must be a 3D volume" | Clear msg, no crash | REQ-19 |
| JUDGE-011 | Mismatched shapes | Different dimensions | "incompatible shapes" | Clear msg, no crash | REQ-19 |
| JUDGE-012 | NaN values | Volume with NaN | "invalid voxel values" | Clear msg, no crash | REQ-19 |
| JUDGE-013 | All-zero volume | All voxels = 0 | "contains no signal" | Clear msg, no crash | REQ-19 |
| JUDGE-014 | File >1GB | 1.1 GB file | "exceeds size limit" | Clear msg, no crash | REQ-19 |
| JUDGE-015 | Mismatched affines | Incompatible transforms | "incompatible spatial transforms" | Clear msg, no crash | REQ-19 |
| JUDGE-016 | Non-skull-stripped | Brain with skull | Warning displayed | Warning shown | REQ-19 |

### 3.4 Repeatability Test
**Test File:** backend/tests/test_judge_repeatability.py

| Test ID | Test Name | Input | Test Action | Pass Criteria | Requirement |
|---------|-----------|-------|-------------|---------------|-------------|
| JUDGE-017 | Inference repeatability | Same 4 volumes | Run inference twice | Dice ≥0.99 | REQ-20 |
| JUDGE-018 | Volume repeatability | Same 4 volumes | Run inference twice | Identical mL values | REQ-20 |

### 3.5 Unseen Case Test
**Test File:** backend/tests/test_judge_unseen.py

| Test ID | Test Name | Input | Expected Behavior | Pass Criteria | Requirement |
|---------|-----------|-------|-------------------|---------------|-------------|
| JUDGE-019 | Blind case prediction | Unseen 4-modality case | Returns segmentation | Non-empty, case-specific mask | REQ-21 |

---

## 4. Performance Tests

### 4.1 Inference Performance
**Test File:** backend/tests/test_performance.py

| Test ID | Test Name | Hardware | Input Size | Target | Requirement |
|---------|-----------|----------|------------|--------|-------------|
| PERF-001 | Inference timing | T4 GPU | 240×240×155 | <120 seconds | REQ-14 |
| PERF-002 | Memory usage | T4 GPU | 240×240×155 | No OOM | REQ-14 |
| PERF-003 | Mesh generation | T4 GPU | Full brain + 3 regions | <30 seconds | REQ-6 |

### 4.2 UI Performance
**Test File:** Manual testing with Chrome DevTools

| Test ID | Test Name | User Action | Target | Requirement |
|---------|-----------|-------------|--------|-------------|
| PERF-004 | Slice navigation | Scroll through slices | <100ms response | Architecture |
| PERF-005 | 3D rotation | Drag to rotate | 60 fps | REQ-6 |
| PERF-006 | Crosshair update | Click on slice | <100ms sync | REQ-18 |

---

## 5. Evaluation System Tests

### 5.1 Held-Out Case Evaluation
**Test File:** backend/tests/test_evaluation.py

| Test ID | Test Name | Input | Expected Behavior | Requirement |
|---------|-----------|-------|-------------------|-------------|
| EVAL-001 | Load evaluation cases | Manifest with 10+ cases | Cases loaded successfully | REQ-9 |
| EVAL-002 | Compute metrics | Ground truth + prediction | Dice per region (WT, TC, ET) | REQ-9 |
| EVAL-003 | Patient-level split | Evaluation manifest | No patient in train and eval | REQ-9 |
| EVAL-004 | Document overlap | Training data source | Overlap disclosed in report | REQ-9 |
| EVAL-005 | No fabricated scores | Real inference only | All scores computed, not mocked | REQ-9 |

---

## 6. Privacy & Security Tests

### 6.1 Data Privacy
**Test File:** Manual code review + backend/tests/test_privacy.py

| Test ID | Test Name | Expected Behavior | Verification Method | Requirement |
|---------|-----------|-------------------|---------------------|-------------|
| PRIV-001 | No external API calls | Code review | Grep for HTTP calls to external domains | REQ-25 |
| PRIV-002 | Local GPU inference | Code review | No cloud inference APIs used | REQ-25 |
| PRIV-003 | 24h deletion | Cleanup service | Files deleted after 24h | REQ-15 |
| PRIV-004 | No PHI logging | Log review | No patient identifiable info in logs | Architecture |

---

## 7. Report Generation Tests

### 7.1 Report Completeness
**Test File:** backend/tests/test_report.py

| Test ID | Report Element | Verification | Requirement |
|---------|----------------|--------------|-------------|
| REP-001 | Volumes in mL | Present with formula | REQ-12 |
| REP-002 | Metrics | Dice/sensitivity if expert mask provided | REQ-12 |
| REP-003 | Model card | Name, version, license, training data | REQ-12 |
| REP-004 | Preprocessing | Steps documented | REQ-12 |
| REP-005 | SHA-256 | All 4 input files | REQ-12 |
| REP-006 | Git commit | Hash included if available | REQ-12 |
| REP-007 | Timestamp | Inference execution time | REQ-12 |
| REP-008 | Limitations | Research-only disclaimer | REQ-12 |
| REP-009 | Disclaimers | Prominent and clear | REQ-13 |

---

## 8. UI/UX Tests

### 8.1 Disclaimer Tests
**Test File:** Manual inspection of all screens

| Test ID | Screen | Expected Behavior | Requirement |
|---------|--------|-------------------|-------------|
| UI-001 | Upload page | Disclaimer visible | REQ-13 |
| UI-002 | Inference page | Disclaimer visible | REQ-13 |
| UI-003 | Results page | Disclaimer visible | REQ-13 |
| UI-004 | Report page | Disclaimer visible | REQ-13 |
| UI-005 | All pages | No "tumor detected" wording | REQ-13 |
| UI-006 | All pages | Use "suspected tumor region" | REQ-13 |
| UI-007 | All pages | Use "estimated volume" | REQ-13 |

---

## 9. CLI Interface Tests

### 9.1 Judge Scorer Endpoint
**Test File:** backend/tests/test_cli.py

| Test ID | Test Name | Command | Expected Output | Requirement |
|---------|-----------|---------|-----------------|-------------|
| CLI-001 | CLI inference | python cli.py --input t1.nii t1gd.nii t2.nii flair.nii --output pred.nii | pred.nii created | REQ-22 |
| CLI-002 | Output format | Check pred.nii | BraTS 2021 labels (1, 2, 4) | REQ-22 |
| CLI-003 | Output grid | Compare to input | Same shape and affine | REQ-22 |

---

## Test Execution Schedule

### Prompt 2 (Foundation): Baseline Tests
- Git initialized
- Docker compose up works
- Health endpoint returns 200

### Prompt 3 (Model Integration): Model Tests
- MONAI bundle downloads
- Test inference runs
- GPU utilization confirmed

### Prompt 4 (Validation): Unit Tests VAL-001 to VAL-010
- All failure modes tested
- Clear error messages verified

### Prompt 5 (Spatial): Unit Tests SPATIAL-001 to SPATIAL-007, JUDGE-001 to JUDGE-004
- Geometric accuracy verified
- Volume calculation correct

### Prompt 6 (Inference): Integration Tests INF-001 to INF-005
- E2E pipeline works
- Reproducibility confirmed

### Prompt 7-8 (Visualization): Manual UI Tests + JUDGE-005 to JUDGE-008
- Crosshair sync verified
- Visuals correct

### Prompt 9 (Evaluation): Tests EVAL-001 to EVAL-005
- Held-out cases evaluated
- Honest metrics computed

### Prompt 10 (Final): All Judge Tests, Performance, CLI
- JUDGE-001 to JUDGE-019 pass
- Performance targets met
- Evidence collected

---

## Pass/Fail Criteria

**PASS:** All acceptance criteria met, no fabricated results, all judge tests pass
**FAIL:** Any judge test fails, fabricated metrics, crashes on invalid input, inference >2 min

---

## Test Evidence Location

- **Unit test results:** backend/tests/reports/
- **Integration test results:** backend/tests/reports/
- **Judge test evidence:** docs/JUDGE_TEST_EVIDENCE/
- **Performance logs:** docs/JUDGE_TEST_EVIDENCE/performance_log.txt
- **Screenshots:** docs/JUDGE_TEST_EVIDENCE/screenshots/

---

**Status:** Test specifications complete, execution pending implementation  
**Next Action:** Execute tests incrementally as each prompt completes
