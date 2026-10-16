"""
Report Generation Service
Generates provenance reports for successful inference cases with full traceability.

Requirements:
- Input SHA-256 hashes for reproducibility
- Model version and license information
- Inference runtime metrics
- Volumes with correct units (mL)
- Git commit hash (if available)
- Timestamp
- Required disclaimers
- Handle missing metrics gracefully
"""

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

# Required disclaimer text
DISCLAIMER_TEXT = """
RESEARCH USE ONLY - NOT FOR CLINICAL DIAGNOSIS

This system predicts suspected tumour regions using an AI model trained on 
historical research data. All outputs represent estimated volumes and should 
be interpreted by qualified medical professionals only. This tool is not 
FDA-approved and must not be used for clinical decision-making.
"""


@dataclass
class InputProvenance:
    """Provenance tracking for input files"""
    t1ce_sha256: str
    t1_sha256: str
    t2_sha256: str
    flair_sha256: str
    upload_timestamp: str
    
    
@dataclass
class ModelProvenance:
    """Model version and license information"""
    name: str
    version: str
    architecture: str
    license: str
    training_data: str
    git_commit: Optional[str]
    

@dataclass
class InferenceMetrics:
    """Inference timing and device information"""
    inference_time_sec: float
    device: str
    timestamp: str
    

@dataclass
class VolumeEstimates:
    """Estimated tumor volumes (terminology compliant)"""
    whole_tumor_ml: Optional[float]
    tumor_core_ml: Optional[float]
    enhancing_tumor_ml: Optional[float]
    notes: str = "Estimated volumes from suspected tumour regions predicted by the model"
    

@dataclass
class CaseReport:
    """Complete case report with full provenance"""
    case_id: str
    input_provenance: InputProvenance
    model_provenance: ModelProvenance
    inference_metrics: InferenceMetrics
    volume_estimates: VolumeEstimates
    expert_metrics: Optional[Dict[str, Any]]  # Dice, sensitivity if available
    disclaimer: str
    report_version: str = "1.0"
    

def compute_file_sha256(filepath: Path) -> str:
    """
    Compute SHA-256 hash of file contents.
    
    Args:
        filepath: Path to file
        
    Returns:
        Hexadecimal SHA-256 hash string
    """
    sha256_hash = hashlib.sha256()
    
    with open(filepath, "rb") as f:
        # Read in 64kb chunks for memory efficiency
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def get_git_commit() -> Optional[str]:
    """
    Get current git commit hash if available.
    
    Returns:
        Commit hash or None if not available
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def generate_case_report(
    case_id: str,
    input_files: Dict[str, Path],
    volumes_ml: Dict[str, float],
    inference_time_sec: float,
    device: str,
    upload_timestamp: str,
    expert_metrics: Optional[Dict[str, Any]] = None
) -> CaseReport:
    """
    Generate complete case report with provenance.
    
    Args:
        case_id: Case identifier
        input_files: Dict mapping modality -> file path
        volumes_ml: Estimated volumes in mL
        inference_time_sec: Inference runtime
        device: Device used (cuda/cpu)
        upload_timestamp: When files were uploaded
        expert_metrics: Optional ground truth metrics
        
    Returns:
        Complete case report
    """
    # Compute input hashes
    logger.info(f"Computing SHA-256 hashes for case {case_id}")
    input_prov = InputProvenance(
        t1ce_sha256=compute_file_sha256(input_files['t1ce']),
        t1_sha256=compute_file_sha256(input_files['t1']),
        t2_sha256=compute_file_sha256(input_files['t2']),
        flair_sha256=compute_file_sha256(input_files['flair']),
        upload_timestamp=upload_timestamp
    )
    
    # Model provenance
    git_commit = get_git_commit()
    model_prov = ModelProvenance(
        name="MONAI brats_mri_segmentation",
        version="BraTS 2018 pretrained",
        architecture="SegResNet",
        license="Apache 2.0",
        training_data="BraTS 2018 Training Dataset",
        git_commit=git_commit if git_commit else "unavailable"
    )
    
    # Inference metrics
    inference_met = InferenceMetrics(
        inference_time_sec=round(inference_time_sec, 3),
        device=device,
        timestamp=datetime.now().isoformat()
    )
    
    # Volume estimates
    volume_est = VolumeEstimates(
        whole_tumor_ml=round(volumes_ml.get('WT', 0), 2) if volumes_ml.get('WT') else None,
        tumor_core_ml=round(volumes_ml.get('TC', 0), 2) if volumes_ml.get('TC') else None,
        enhancing_tumor_ml=round(volumes_ml.get('ET', 0), 2) if volumes_ml.get('ET') else None
    )
    
    return CaseReport(
        case_id=case_id,
        input_provenance=input_prov,
        model_provenance=model_prov,
        inference_metrics=inference_met,
        volume_estimates=volume_est,
        expert_metrics=expert_metrics,
        disclaimer=DISCLAIMER_TEXT.strip()
    )


def save_report_json(report: CaseReport, output_path: Path) -> None:
    """Save report as JSON"""
    with open(output_path, 'w') as f:
        json.dump(asdict(report), f, indent=2)
    logger.info(f"Report saved to {output_path}")
