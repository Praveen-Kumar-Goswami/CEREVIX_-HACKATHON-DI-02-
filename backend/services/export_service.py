"""
Export Service
Export predictions in BraTS-compliant NIfTI format on original input grid.

Requirements:
- Preserve original affine transformation
- Use BraTS 2021 label codes (0, 1, 2, 4)
- Validate output before saving
"""

import nibabel as nib
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# BraTS label codes
BRATS_LABELS = {0, 1, 2, 4}


def export_prediction_nifti(
    segmentation: np.ndarray,
    affine: np.ndarray,
    output_path: Path,
    case_id: str
) -> Path:
    """
    Export prediction as NIfTI file with BraTS labels.
    
    Args:
        segmentation: 3D label map (0, 1, 2, 4)
        affine: 4x4 affine transformation matrix
        output_path: Where to save the file
        case_id: Case identifier for logging
        
    Returns:
        Path to saved file
        
    Raises:
        ValueError: If segmentation contains invalid labels
    """
    # Validate labels
    unique_labels = set(np.unique(segmentation))
    if not unique_labels.issubset(BRATS_LABELS):
        invalid = unique_labels - BRATS_LABELS
        raise ValueError(f"Invalid BraTS labels in segmentation: {invalid}")
    
    # Ensure integer type
    segmentation_int = segmentation.astype(np.uint8)
    
    # Create NIfTI image
    nii = nib.Nifti1Image(segmentation_int, affine)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save
    nib.save(nii, output_path)
    logger.info(f"Exported prediction for case {case_id} to {output_path}")
    
    # Verify file was written
    if not output_path.exists():
        raise IOError(f"Failed to write prediction file: {output_path}")
    
    # Verify file can be loaded
    try:
        test_load = nib.load(output_path)
        logger.debug(f"Verified exported file: shape={test_load.shape}, labels={np.unique(test_load.get_fdata())}")
    except Exception as e:
        raise IOError(f"Exported file verification failed: {e}")
    
    return output_path


def validate_exported_prediction(filepath: Path, expected_shape: tuple, expected_affine: np.ndarray) -> bool:
    """
    Validate exported prediction file.
    
    Args:
        filepath: Path to exported file
        expected_shape: Expected 3D shape
        expected_affine: Expected affine matrix
        
    Returns:
        True if valid
    """
    try:
        nii = nib.load(filepath)
        data = nii.get_fdata()
        
        # Check shape
        if data.shape != expected_shape:
            logger.error(f"Shape mismatch: {data.shape} != {expected_shape}")
            return False
        
        # Check affine
        if not np.allclose(nii.affine, expected_affine, atol=1e-5):
            logger.error("Affine mismatch")
            return False
        
        # Check labels
        unique_labels = set(np.unique(data.astype(int)))
        if not unique_labels.issubset(BRATS_LABELS):
            logger.error(f"Invalid labels: {unique_labels}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return False
