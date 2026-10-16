# Prompt 8: Reporting, Provenance, Export & Privacy Controls

**Status**: ✅ COMPLETE  
**Date**: 2026-10-16  
**Tests**: 93/93 passing (15 new report tests)

## Summary

Implemented comprehensive reporting system with full provenance tracking, SHA-256 input hashing, BraTS-compliant NIfTI export, automatic 24-hour cleanup with TTL enforcement, and privacy controls. All outputs include required disclaimers and honest "not available" markers for missing data.

## Implementation

### 1. Report Generation Service (`backend/services/report_service.py`)

**Features**:
- SHA-256 hashing of all input files for reproducibility
- Model provenance: name, version, architecture, license, training dataset
- Git commit hash (or "unavailable" if not in repo)
- ISO 8601 timestamps
- Volume estimates in mL with 2 decimal precision
- Inference timing rounded to 3 decimals
- Required disclaimer text
- Handles missing metrics explicitly (None, not 0)
- JSON serialization

**Report Structure**:
```json
{
  "case_id": "uuid",
  "input_provenance": {
    "t1ce_sha256": "64-char-hex",
    "t1_sha256": "64-char-hex",
    "t2_sha256": "64-char-hex",
    "flair_sha256": "64-char-hex",
    "upload_timestamp": "ISO-8601"
  },
  "model_provenance": {
    "name": "MONAI brats_mri_segmentation",
    "version": "BraTS 2018 pretrained",
    "architecture": "SegResNet",
    "license": "Apache 2.0",
    "training_data": "BraTS 2018 Training Dataset",
    "git_commit": "SHA-1 or unavailable"
  },
  "inference_metrics": {
    "inference_time_sec": 1.234,
    "device": "cuda",
    "timestamp": "ISO-8601"
  },
  "volume_estimates": {
    "whole_tumor_ml": 123.45,
    "tumor_core_ml": 78.90,
    "enhancing_tumor_ml": 45.60,
    "notes": "Estimated volumes from suspected tumour regions predicted by the model"
  },
  "expert_metrics": null,
  "disclaimer": "RESEARCH USE ONLY - NOT FOR CLINICAL DIAGNOSIS..."
}
```

### 2. NIfTI Export Service (`backend/services/export_service.py`)

**Features**:
- Validates BraTS labels (0, 1, 2, 4) before export
- Preserves original affine transformation
- Uint8 data type for compatibility
- Post-export verification
- Proper NIfTI headers

### 3. Cleanup Service (`backend/services/cleanup_service.py`)

**Features**:
- **TTL-based**: Default 24-hour lifetime for temporary files
- **Startup cleanup**: Runs on app start to handle process restarts
- **Protected assets**: Never deletes:
  - Model weights (`models/`)
  - Source code (`backend/`, `frontend/`)
  - Documentation (`docs/`)
  - Git repository (`.git/`)
  - Development test data (`data/synthetic_evaluation/`)
- **Cleanup targets**:
  - `data/uploads/` - Uploaded MRI files
  - `data/predictions/` - Inference outputs
  - `data/reports/` - Generated reports
- **Dry-run support** for testing
- **Empty directory removal**

**Safety**:
- Filesystem timestamp-based (survives restarts)
- Whitelist protection
- Explicit pattern matching
- Logs all deletions

### 4. API Endpoints (`backend/api/main.py`)

**New Endpoints**:
```
GET /api/report/{case_id}      - Generate JSON report with full provenance
GET /api/export/{case_id}      - Export BraTS-compliant NIfTI prediction
GET /api/disclaimer             - Get required disclaimer text
```

**Startup Event**:
```python
@app.on_event("startup")
async def startup_event():
    run_cleanup_on_startup(workspace_root, ttl_hours=24)
```

### 5. Frontend Updates (`frontend/index.html`)

**Disclaimer**: Updated to match required wording:
```
⚠️ RESEARCH USE ONLY - NOT FOR CLINICAL DIAGNOSIS

This system predicts suspected tumour regions using an AI model trained on 
historical research data. All outputs represent estimated volumes and should 
be interpreted by qualified medical professionals only. This tool is not 
FDA-approved and must not be used for clinical decision-making.
```

**Export Buttons**:
- 📄 Download JSON Report
- 💾 Export NIfTI Prediction

Both appear only after successful inference.

### 6. Privacy & Security

**Implemented**:
✅ No external MRI file transmission  
✅ SHA-256 hashes computed on uploaded bytes  
✅ No raw voxel logging  
✅ Secrets excluded from repo (`.gitignore`)  
✅ Error messages sanitized (no server paths)  
✅ 24-hour automatic cleanup  
✅ Case-ID based access control  

**File Storage**:
- Uploads: `data/uploads/{case_id}/`
- Predictions: `data/cases/{case_id}/segmentation.nii.gz`
- Reports: `data/cases/{case_id}/report_{case_id}.json`

## Test Coverage (15 new tests)

### Report Generation Tests (9 tests)
1. ✅ `test_units_are_milliliters` - Volumes in mL, 2 decimal precision
2. ✅ `test_input_sha256_hashes` - All inputs hashed, deterministic, 64 hex chars
3. ✅ `test_model_provenance` - Name, version, arch, license, training data
4. ✅ `test_git_commit_handling` - Returns commit or "unavailable"
5. ✅ `test_timestamp_format` - ISO 8601 timestamps
6. ✅ `test_disclaimer_presence` - Required text present
7. ✅ `test_missing_metrics_explicit` - None not 0 for missing data
8. ✅ `test_inference_runtime_precision` - 3 decimal places
9. ✅ `test_json_serialization` - Full report serializes correctly

### NIfTI Export Tests (3 tests)
10. ✅ `test_brats_label_validation` - Rejects invalid labels
11. ✅ `test_affine_preservation` - Affine matrix preserved exactly
12. ✅ `test_export_validation` - Validation helper catches mismatches

### Cleanup Service Tests (3 tests)
13. ✅ `test_protected_assets` - Model weights and code never deleted
14. ✅ `test_cleanup_targets_only_temp_data` - Only targets temp directories
15. ✅ `test_dry_run_does_not_delete` - Dry run reports without deletion

## Verification

### Manual Verification Steps

**From evaluation results**:
```bash
# Generate report from synthetic case
curl http://localhost:8000/api/report/SYNTHETIC_EVAL_001
```

**Expected**:
- All SHA-256 hashes present (64 hex chars)
- Volumes in mL with 2 decimals
- Git commit hash or "unavailable"
- ISO timestamps
- Full disclaimer text
- expert_metrics: null (not available)

**Export prediction**:
```bash
# Download NIfTI
curl http://localhost:8000/api/export/SYNTHETIC_EVAL_001 -o prediction.nii.gz

# Verify labels
python -c "import nibabel as nib; import numpy as np; nii = nib.load('prediction.nii.gz'); print(f'Labels: {np.unique(nii.get_fdata())}')"
```

**Expected**: Labels: [0 1 2 4]

### Cleanup Verification

```python
from pathlib import Path
from services.cleanup_service import cleanup_expired_files

workspace = Path.cwd()
deleted, protected = cleanup_expired_files(workspace, ttl_hours=24, dry_run=True)
print(f"Would delete: {deleted}, Protected: {protected}")
```

**Expected**:
- Files in `data/uploads/` older than 24h flagged
- Model files, code, docs protected

## Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Valid case can generate report | ✅ | `/api/report/{case_id}` endpoint, test_json_serialization |
| Report provenance reflects runtime | ✅ | SHA-256, git commit, timestamps, device |
| Missing fields marked unavailable | ✅ | expert_metrics: null, test_missing_metrics_explicit |
| Disclaimer across app | ✅ | Frontend header, API endpoint, report field |
| Failed case yields no report | ✅ | API returns 400 if state != RESULTS_READY |
| Cleanup deletes 24h+ uploads | ✅ | test_cleanup_targets_only_temp_data |
| Model assets preserved | ✅ | test_protected_assets |
| No external MRI transfer | ✅ | No external HTTP calls in code |

## Git Commit

```bash
git add -A
git commit -m "Prompt 8: Reports, provenance, export & privacy (93/93 tests pass)

- Report generation with SHA-256 hashes, model provenance, timestamps
- NIfTI export with BraTS label validation and affine preservation
- Automatic 24-hour cleanup with TTL enforcement and asset protection
- Privacy controls: no external transfer, sanitized errors, case-based access
- Frontend: updated disclaimer, download buttons for reports & predictions
- 15 new tests covering reports, export, and cleanup
- All acceptance criteria met"
```

## Files Created/Modified

### New Files
- `backend/services/report_service.py` - Report generation
- `backend/services/export_service.py` - NIfTI export
- `backend/services/cleanup_service.py` - TTL-based cleanup
- `backend/tests/test_reports.py` - 15 comprehensive tests

### Modified Files
- `backend/api/main.py` - New endpoints, startup cleanup
- `backend/services/case_manager.py` - Added metadata fields
- `frontend/index.html` - Disclaimer update, export buttons

## Known Limitations

1. **No PDF reports**: Only JSON (PDF generation requires additional dependencies)
2. **Cleanup scheduling**: Manual trigger or startup-only (no background scheduler)
3. **Git commit**: May show "unavailable" if not in repo or git not installed
4. **Expert metrics**: Always null (no ground truth in production)

## Next Steps

Prompt 9: Ready for integration testing, performance optimization, and final documentation.
