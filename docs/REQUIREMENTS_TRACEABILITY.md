# NeuroScope 3D – Requirements Traceability Matrix

**Version:** 1.0  
**Last Updated:** 2026-10-16  
**Status:** Planning

This document maps each requirement to its acceptance criteria, verification method, and planned test evidence.

## Judge Test Requirements

| Req ID | Requirement | Acceptance Criteria | Verification Method | Evidence Location | Status |
|--------|-------------|---------------------|---------------------|-------------------|--------|
| REQ-8 | Volume Calculation | Synthetic cube 20×20×20 at 1×1×2mm → 16.0 mL ±1% | Automated test with synthetic data | docs/JUDGE_TEST_EVIDENCE/cube_test.md | NOT STARTED |
| REQ-17 | Geometric Accuracy | All spatial transform tests pass | Automated test suite | docs/JUDGE_TEST_EVIDENCE/geometric_tests.md | NOT STARTED |
| REQ-18 | Crosshair Sync | Crosshair syncs within 2 voxels across views | Manual inspection + screenshot | docs/JUDGE_TEST_EVIDENCE/crosshair_sync.png | NOT STARTED |
| REQ-19 | Failure Handling | All 8 failure modes return clear errors without crash | Automated test suite | backend/tests/test_validation.py | NOT STARTED |
| REQ-20 | Repeatability | Same input → Dice ≥0.99 between runs | Automated test | docs/JUDGE_TEST_EVIDENCE/repeatability_test.md | NOT STARTED |
| REQ-21 | Unseen Case | Blind case returns plausible non-empty mask | Manual inspection | docs/JUDGE_TEST_EVIDENCE/blind_case.md | NOT STARTED |
| REQ-14 | Performance | Upload → report in <2 min on T4 GPU | Timed execution | docs/JUDGE_TEST_EVIDENCE/performance_log.txt | NOT STARTED |

## Functional Requirements

| Req ID | Requirement | Implementation Files | Test Files | Status |
|--------|-------------|---------------------|------------|--------|
| REQ-1 | Accept 4 NIfTI Files | backend/api/routes/upload.py | backend/tests/test_upload.py | NOT STARTED |
| REQ-2 | Validate Inputs | backend/services/validation_service.py | backend/tests/test_validation.py | NOT STARTED |
| REQ-3 | Optional Expert Mask | backend/services/evaluation_service.py | backend/tests/test_evaluation.py | NOT STARTED |
| REQ-4 | 3D Inference | backend/services/inference_service.py | backend/tests/test_inference.py | NOT STARTED |
| REQ-5 | Region Construction | backend/services/inference_service.py | backend/tests/test_regions.py | NOT STARTED |
| REQ-6 | 3D Mesh Rendering | backend/services/mesh_service.py, frontend/src/components/ThreeDViewer.tsx | backend/tests/test_mesh.py | NOT STARTED |
| REQ-7 | 2D Slice Views | frontend/src/components/NiiVueViewer.tsx | Manual inspection | NOT STARTED |
| REQ-8 | Volume Calculation | backend/utils/spatial_utils.py | backend/tests/test_spatial.py | NOT STARTED |
| REQ-9 | Evaluation | backend/services/evaluation_service.py | backend/tests/test_evaluation.py | NOT STARTED |
| REQ-11 | Prevent Stale Results | frontend/src/store/resultsStore.ts | Manual inspection | NOT STARTED |
| REQ-12 | Generate Report | backend/services/report_service.py | docs/sample_report.html | NOT STARTED |
| REQ-15 | Auto-Delete Uploads | backend/services/cleanup_service.py | Manual inspection | NOT STARTED |
| REQ-22 | CLI Interface | backend/cli.py | backend/tests/test_cli.py | NOT STARTED |

## Non-Functional Requirements

| Req ID | Requirement | Verification Method | Evidence | Status |
|--------|-------------|---------------------|----------|--------|
| REQ-13 | Disclaimers | Visual inspection of all screens | Screenshots | NOT STARTED |
| REQ-14 | Performance | Timed execution on T4 GPU | Log file | NOT STARTED |
| REQ-16 | Deployment Package | Checklist completion | README.md, sample_report.html, MODEL_CARD.md | NOT STARTED |
| REQ-25 | No External APIs | Code review | Architecture diagram | NOT STARTED |
| REQ-26 | De-identified Data | Documentation review | README.md | NOT STARTED |

## Implementation Stages → Requirements Mapping

| Stage | Requirements Addressed |
|-------|------------------------|
| Stage 1: Foundation | REQ-16 (partial: README, structure) |
| Stage 2: Model Integration | REQ-4 (partial: model loading), REQ-23, REQ-24 |
| Stage 3: Upload & Validation | REQ-1, REQ-2, REQ-19 |
| Stage 4: Spatial Correctness | REQ-8, REQ-17 |
| Stage 5: Inference Pipeline | REQ-4, REQ-5, REQ-20, REQ-22 |
| Stage 6: 2D Visualization | REQ-7, REQ-18 |
| Stage 7: 3D Visualization | REQ-6, REQ-18 |
| Stage 8: Evaluation | REQ-3, REQ-9, REQ-21 |
| Stage 9: Report Generation | REQ-12, REQ-13 |
| Stage 10: Judge Tests | All REQ-17 through REQ-21, verification of all requirements |
| Stage 11: UI Polish | REQ-13 |
| Stage 12: Documentation | REQ-16, REQ-26 |

## Traceability Notes

- All 28 requirements from requirements.md are traced to implementation and test files
- Each judge acceptance test maps to specific automated or manual verification
- Evidence collection planned for Stage 10
- All requirements will be marked VERIFIED only after acceptance criteria pass

---

**Last Updated:** 2026-10-16  
**Review Status:** Planning Phase
