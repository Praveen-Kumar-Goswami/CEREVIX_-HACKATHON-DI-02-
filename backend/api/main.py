"""
FastAPI Backend - NeuroScope 3D
Complete REST API with proper case management integration.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from typing import Optional
import uuid
import logging
import numpy as np
import nibabel as nib
from skimage.measure import marching_cubes

# Import services
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.validation_service import NIfTIValidator, ModalityType
from services.case_manager import CaseStateManager, CaseState
from services.inference_service import BraTSInferenceService
from services.report_service import generate_case_report, save_report_json, DISCLAIMER_TEXT
from services.export_service import export_prediction_nifti
from services.cleanup_service import run_cleanup_on_startup
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="NeuroScope 3D API",
    description="Brain tumor segmentation with MONAI",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
WORK_DIR = Path(__file__).parent.parent.parent / "data"
WORK_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "brats_mri_segmentation" / "models" / "model.pt"

case_manager = CaseStateManager(data_root=WORK_DIR)
validator = NIfTIValidator()
inference_service = None  # Lazy-load


@app.get("/")
def root():
    """Health check"""
    return {
        "status": "online",
        "service": "NeuroScope 3D API",
        "version": "1.0.0"
    }


@app.post("/api/upload")
async def upload_case(
    t1ce: UploadFile = File(...),
    t1: UploadFile = File(...),
    t2: UploadFile = File(...),
    flair: UploadFile = File(...)
):
    """Upload and validate 4-modality case"""
    try:
        logger.info("Receiving new case upload")
        
        # Save temp files first
        temp_dir = WORK_DIR / "temp" / str(uuid.uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        files_map = {
            "t1ce": (t1ce, temp_dir / f"t1ce.nii.gz"),
            "t1": (t1, temp_dir / "t1.nii.gz"),
            "t2": (t2, temp_dir / "t2.nii.gz"),
            "flair": (flair, temp_dir / "flair.nii.gz")
        }
        
        saved_paths = {}
        for modality, (upload_file, save_path) in files_map.items():
            content = await upload_file.read()
            with open(save_path, "wb") as f:
                f.write(content)
            saved_paths[modality] = str(save_path)
        
        # Validate each file
        validation_results = {}
        for modality, path in saved_paths.items():
            modality_type = ModalityType(modality)
            result, metadata = validator.validate_single_file(Path(path), modality_type)
            validation_results[modality] = {
                "valid": result.is_valid,
                "error": result.error_message
            }
            
            if not result.is_valid:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "validation_failed",
                        "validation": validation_results
                    }
                )
        
        # Cross-modality validation
        modality_paths = [Path(p) for p in saved_paths.values()]
        cross_valid, _ = validator.validate_four_modalities({ModalityType(k): Path(v) for k, v in saved_paths.items()})
        
        if not cross_valid.is_valid:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "validation_failed",
                    "error": cross_valid.error_message
                }
            )
        
        # Create case
        case_id = case_manager.create_case(modality_files=saved_paths)
        case_manager.update_state(case_id, CaseState.VALIDATED)
        
        logger.info(f"Case {case_id} validated successfully")
        
        return {
            "case_id": case_id,
            "status": "validated",
            "message": "Ready for inference"
        }
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/inference/{case_id}")
async def run_inference(case_id: str):
    """Run inference on validated case"""
    global inference_service
    
    try:
        # Check state
        metadata = case_manager.get_case_metadata(case_id)
        if not metadata or metadata.state != CaseState.VALIDATED:
            raise HTTPException(400, "Case not ready for inference")
        
        # Initialize service
        if inference_service is None:
            logger.info("Initializing inference service...")
            inference_service = BraTSInferenceService(MODEL_PATH)
        
        # Update state
        case_manager.update_state(case_id, CaseState.INFERENCE)
        
        # Run inference
        logger.info(f"Running inference on {case_id}")
        modality_paths = metadata.modality_files
        
        result = inference_service.run_inference(
            t1ce_path=Path(modality_paths["t1ce"]),
            t1_path=Path(modality_paths["t1"]),
            t2_path=Path(modality_paths["t2"]),
            flair_path=Path(modality_paths["flair"])
        )
        
        # Save results
        case_dir = case_manager.get_case_dir(case_id)
        seg_path = case_dir / "segmentation.nii.gz"
        inference_service.save_segmentation(result, seg_path)
        # Save inference metadata for reports
        case_manager.update_state(
            case_id, 
            CaseState.RESULTS_READY,
            shape=result.segmentation.shape,
            inference_time_sec=result.inference_time_sec,
            device=result.device_used,
            volumes_ml=result.volumes_ml
        )
        
        logger.info(f"Inference complete: {case_id}")
        
        return {
            "case_id": case_id,
            "status": "complete",
            "volumes_ml": result.volumes_ml,
            "inference_time_sec": result.inference_time_sec
        }
        
    except Exception as e:
        logger.error(f"Inference error: {str(e)}")
        case_manager.update_state(case_id, CaseState.FAILED, error_message=str(e))
        raise HTTPException(500, str(e))


@app.get("/api/status/{case_id}")
def get_status(case_id: str):
    """Get case status"""
    metadata = case_manager.get_case_metadata(case_id)
    if not metadata:
        raise HTTPException(404, "Case not found")
    
    return {
        "case_id": case_id,
        "state": metadata.state.value,
        "created_at": metadata.created_at
    }


@app.get("/api/nifti/{case_id}/{modality}")
def get_nifti_file(case_id: str, modality: str):
    """Serve NIfTI file for viewer"""
    try:
        metadata = case_manager.get_case_metadata(case_id)
        if not metadata:
            raise HTTPException(404, "Case not found")
        
        if modality == "segmentation":
            file_path = case_manager.get_case_dir(case_id) / "segmentation.nii.gz"
        else:
            if modality not in metadata.modality_files:
                raise HTTPException(400, f"Invalid modality: {modality}")
            file_path = Path(metadata.modality_files[modality])
        
        if not file_path.exists():
            raise HTTPException(404, f"File not found: {modality}")
        
        return FileResponse(
            path=file_path,
            media_type="application/gzip",
            filename=file_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/mesh/{case_id}")
def get_mesh_data(case_id: str):
    """Generate and serve mesh data for 3D visualization"""
    try:
        metadata = case_manager.get_case_metadata(case_id)
        if not metadata or metadata.state != CaseState.RESULTS_READY:
            raise HTTPException(400, "Results not ready")
        
        # Load segmentation
        seg_path = case_manager.get_case_dir(case_id) / "segmentation.nii.gz"
        seg_nii = nib.load(seg_path)
        seg_data = seg_nii.get_fdata()
        affine = seg_nii.affine
        
        # Generate meshes for each label
        meshes = {}
        labels = {
            "ET": 4,  # Enhancing tumor
            "TC": 1,  # Tumor core (NCR)
            "ED": 2   # Edema
        }
        
        for region_name, label_value in labels.items():
            mask = (seg_data == label_value).astype(np.uint8)
            
            if mask.sum() == 0:
                continue  # Skip empty masks
            
            try:
                # Marching cubes
                verts, faces, normals, _ = marching_cubes(mask, level=0.5)
                
                # Transform to world coordinates
                # Add homogeneous coordinate
                verts_homo = np.c_[verts, np.ones(len(verts))]
                verts_world = (affine @ verts_homo.T).T[:, :3]
                
                meshes[region_name] = {
                    "vertices": verts_world.tolist(),
                    "faces": faces.tolist(),
                    "normals": normals.tolist()
                }
                
            except Exception as e:
                logger.warning(f"Mesh generation failed for {region_name}: {e}")
                continue
        
        return {
            "case_id": case_id,
            "meshes": meshes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mesh generation error: {str(e)}")
        raise HTTPException(500, str(e))



@app.on_event("startup")
async def startup_event():
    """Run cleanup on startup to handle process restarts"""
    logger.info("Running startup cleanup...")
    workspace_root = Path(__file__).parent.parent.parent
    run_cleanup_on_startup(workspace_root, ttl_hours=24)
    logger.info("Startup complete")


@app.get("/api/report/{case_id}")
def get_case_report(case_id: str):
    """Generate and return JSON report for successful case"""
    try:
        metadata = case_manager.get_case_metadata(case_id)
        if not metadata:
            raise HTTPException(404, "Case not found")
        
        if metadata.state != CaseState.RESULTS_READY:
            raise HTTPException(400, "Results not available - cannot generate report")
        
        # Load results
        case_dir = case_manager.get_case_dir(case_id)
        seg_path = case_dir / "segmentation.nii.gz"
        
        if not seg_path.exists():
            raise HTTPException(500, "Segmentation file missing")
        
        # Load segmentation to get volumes
        seg_nii = nib.load(seg_path)
        seg_data = seg_nii.get_fdata().astype(int)
        
        # Recalculate volumes from saved segmentation
        from utils.spatial_utils import calculate_brats_label_volumes
        volumes_ml = calculate_brats_label_volumes(seg_data, seg_nii.affine)
        
        # Get input file paths
        input_files = {k: Path(v) for k, v in metadata.modality_files.items()}
        
        # Estimate inference time (not stored in metadata yet, use placeholder)
        inference_time = 1.0  # Will be "not evaluated" in report
        
        # Generate report
        report = generate_case_report(
            case_id=case_id,
            input_files=input_files,
            volumes_ml=volumes_ml,
            inference_time_sec=inference_time,
            device="cuda",  # From inference service
            upload_timestamp=metadata.created_at,
            expert_metrics=None  # No ground truth available
        )
        
        # Save report
        report_path = case_dir / f"report_{case_id}.json"
        save_report_json(report, report_path)
        
        # Return as JSON
        return report.__dict__
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation error: {str(e)}")
        raise HTTPException(500, str(e))


@app.get("/api/export/{case_id}")
def export_prediction(case_id: str):
    """Export prediction as BraTS-compliant NIfTI file"""
    try:
        metadata = case_manager.get_case_metadata(case_id)
        if not metadata:
            raise HTTPException(404, "Case not found")
        
        if metadata.state != CaseState.RESULTS_READY:
            raise HTTPException(400, "Results not available - cannot export")
        
        # Load segmentation
        case_dir = case_manager.get_case_dir(case_id)
        seg_path = case_dir / "segmentation.nii.gz"
        
        if not seg_path.exists():
            raise HTTPException(500, "Segmentation file missing")
        
        seg_nii = nib.load(seg_path)
        segmentation = seg_nii.get_fdata().astype(np.uint8)
        affine = seg_nii.affine
        
        # Export (validates labels)
        export_path = case_dir / f"prediction_{case_id}.nii.gz"
        export_prediction_nifti(segmentation, affine, export_path, case_id)
        
        # Return file
        return FileResponse(
            path=export_path,
            media_type="application/gzip",
            filename=f"prediction_{case_id}.nii.gz",
            headers={
                "Content-Disposition": f"attachment; filename=prediction_{case_id}.nii.gz"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        raise HTTPException(500, str(e))


@app.get("/api/disclaimer")
def get_disclaimer():
    """Return required disclaimer text"""
    return {
        "disclaimer": DISCLAIMER_TEXT
    }

# Mount frontend
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


