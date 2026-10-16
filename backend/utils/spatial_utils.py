"""
Spatial Utilities for BraTS Segmentation
Handles coordinate transformations and volume calculations with proper
affine matrix handling for clinical accuracy.

Key functions:
- voxel_to_world: Transform voxel indices to RAS+ physical coordinates
- world_to_voxel: Inverse transformation from physical to voxel space
- calculate_volume_ml: Accurate volume calculation accounting for anisotropic voxels
- validate_affine: Check affine matrix validity
"""

import numpy as np
from typing import Tuple, Union, Dict
import nibabel as nib


def validate_affine(affine: np.ndarray) -> Tuple[bool, str]:
    """
    Validate affine transformation matrix.
    
    Args:
        affine: 4x4 affine matrix
        
    Returns:
        (is_valid, error_message)
    """
    if affine.shape != (4, 4):
        return False, f"Affine must be 4x4, got shape {affine.shape}"
    
    # Check if matrix contains valid numbers
    if not np.all(np.isfinite(affine)):
        return False, "Affine contains non-finite values (NaN or Inf)"
    
    # Extract 3x3 rotation/scale component
    M = affine[:3, :3]
    
    # Check determinant (must be non-zero for invertibility)
    det = np.linalg.det(M)
    if np.abs(det) < 1e-10:
        return False, f"Affine has near-zero determinant ({det}), matrix is singular"
    
    # Check for reasonable voxel sizes (0.1mm to 10mm typical for MRI)
    voxel_sizes = np.sqrt(np.sum(M**2, axis=0))
    if np.any(voxel_sizes < 0.01) or np.any(voxel_sizes > 20.0):
        return False, f"Unusual voxel sizes detected: {voxel_sizes} mm"
    
    # Check bottom row is [0, 0, 0, 1]
    if not np.allclose(affine[3, :], [0, 0, 0, 1]):
        return False, f"Affine bottom row must be [0, 0, 0, 1], got {affine[3, :]}"
    
    return True, ""


def voxel_to_world(voxel_coords: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """
    Transform voxel coordinates to world (physical) coordinates.
    
    Uses RAS+ convention (Right-Anterior-Superior with mm units).
    
    Args:
        voxel_coords: Array of shape (N, 3) or (3,) with voxel indices
        affine: 4x4 affine transformation matrix
        
    Returns:
        Array of shape (N, 3) or (3,) with world coordinates in mm
        
    Example:
        >>> affine = np.diag([2.0, 2.0, 2.0, 1.0])  # 2mm isotropic
        >>> voxel = np.array([10, 20, 30])
        >>> world = voxel_to_world(voxel, affine)
        >>> # world = [20.0, 40.0, 60.0]
    """
    voxel_coords = np.asarray(voxel_coords, dtype=float)
    
    # Handle single coordinate
    single_point = False
    if voxel_coords.ndim == 1:
        voxel_coords = voxel_coords.reshape(1, -1)
        single_point = True
    
    if voxel_coords.shape[1] != 3:
        raise ValueError(f"voxel_coords must have 3 columns, got {voxel_coords.shape[1]}")
    
    # Convert to homogeneous coordinates (add column of ones)
    N = voxel_coords.shape[0]
    homogeneous = np.hstack([voxel_coords, np.ones((N, 1))])
    
    # Apply affine transformation: world = affine @ voxel
    world_coords = (affine @ homogeneous.T).T[:, :3]
    
    if single_point:
        return world_coords.ravel()
    
    return world_coords


def world_to_voxel(world_coords: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """
    Transform world (physical) coordinates to voxel coordinates.
    
    Inverse of voxel_to_world.
    
    Args:
        world_coords: Array of shape (N, 3) or (3,) with world coordinates in mm
        affine: 4x4 affine transformation matrix
        
    Returns:
        Array of shape (N, 3) or (3,) with voxel indices (float, may need rounding)
        
    Example:
        >>> affine = np.diag([2.0, 2.0, 2.0, 1.0])
        >>> world = np.array([20.0, 40.0, 60.0])
        >>> voxel = world_to_voxel(world, affine)
        >>> # voxel = [10.0, 20.0, 30.0]
    """
    world_coords = np.asarray(world_coords, dtype=float)
    
    # Handle single coordinate
    single_point = False
    if world_coords.ndim == 1:
        world_coords = world_coords.reshape(1, -1)
        single_point = True
    
    if world_coords.shape[1] != 3:
        raise ValueError(f"world_coords must have 3 columns, got {world_coords.shape[1]}")
    
    # Invert affine matrix
    affine_inv = np.linalg.inv(affine)
    
    # Convert to homogeneous coordinates
    N = world_coords.shape[0]
    homogeneous = np.hstack([world_coords, np.ones((N, 1))])
    
    # Apply inverse transformation: voxel = affine_inv @ world
    voxel_coords = (affine_inv @ homogeneous.T).T[:, :3]
    
    if single_point:
        return voxel_coords.ravel()
    
    return voxel_coords


def calculate_volume_ml(
    mask: np.ndarray,
    affine: np.ndarray,
    label: Union[int, None] = None
) -> float:
    """
    Calculate volume of a segmentation mask in milliliters.
    
    Accounts for anisotropic voxel spacing using affine matrix determinant.
    
    Formula:
        volume_ml = voxel_count * abs(det(affine[:3, :3])) / 1000
        
    Where det(affine[:3, :3]) gives the voxel volume in mm3.
    
    Args:
        mask: 3D binary mask or label map (H, W, D)
        affine: 4x4 affine transformation matrix
        label: If provided, calculate volume only for this label value.
               If None, treat mask as binary (any non-zero = foreground)
               
    Returns:
        Volume in milliliters (mL)
        
    Example:
        >>> # 20x20x20 cube at 1x1x2mm spacing
        >>> mask = np.ones((20, 20, 20), dtype=np.uint8)
        >>> affine = np.diag([1.0, 1.0, 2.0, 1.0])
        >>> volume = calculate_volume_ml(mask, affine)
        >>> # volume = 8000 voxels * 2 mm3/voxel / 1000 = 16.0 mL
    """
    mask = np.asarray(mask)
    
    if mask.ndim != 3:
        raise ValueError(f"Mask must be 3D, got shape {mask.shape}")
    
    # Extract voxel for specific label or count all non-zero
    if label is not None:
        voxel_count = np.sum(mask == label)
    else:
        voxel_count = np.sum(mask > 0)
    
    # Extract 3x3 rotation/scale component
    M = affine[:3, :3]
    
    # Calculate voxel volume in mm3
    # abs(det(M)) gives the volume scale factor
    voxel_volume_mm3 = np.abs(np.linalg.det(M))
    
    # Total volume in mm3
    total_volume_mm3 = voxel_count * voxel_volume_mm3
    
    # Convert to mL (1 mL = 1000 mm3)
    volume_ml = total_volume_mm3 / 1000.0
    
    return volume_ml


def get_voxel_dimensions(affine: np.ndarray) -> Tuple[float, float, float]:
    """
    Extract voxel dimensions from affine matrix.
    
    Args:
        affine: 4x4 affine transformation matrix
        
    Returns:
        (x_spacing, y_spacing, z_spacing) in mm
    """
    M = affine[:3, :3]
    
    # Voxel dimensions are the norms of the column vectors
    voxel_dims = np.sqrt(np.sum(M**2, axis=0))
    
    return tuple(voxel_dims)


def check_orientation_consistency(
    affine1: np.ndarray,
    affine2: np.ndarray,
    tolerance: float = 1e-3
) -> Tuple[bool, str]:
    """
    Check if two affine matrices have consistent orientation.
    
    Used to verify all modalities in a case have the same spatial alignment.
    
    Args:
        affine1: First 4x4 affine matrix
        affine2: Second 4x4 affine matrix
        tolerance: Maximum allowed difference in matrix elements
        
    Returns:
        (is_consistent, message)
    """
    # Extract orientation components (rotation/flip, ignoring scale)
    M1 = affine1[:3, :3]
    M2 = affine2[:3, :3]
    
    # Normalize columns to unit vectors
    M1_norm = M1 / np.linalg.norm(M1, axis=0)
    M2_norm = M2 / np.linalg.norm(M2, axis=0)
    
    # Check if orientations match
    diff = np.abs(M1_norm - M2_norm)
    max_diff = np.max(diff)
    
    if max_diff > tolerance:
        return False, f"Orientation mismatch (max diff: {max_diff:.6f})"
    
    # Check origin alignment (translation component)
    origin_diff = np.abs(affine1[:3, 3] - affine2[:3, 3])
    max_origin_diff = np.max(origin_diff)
    
    if max_origin_diff > tolerance:
        return False, f"Origin mismatch (max diff: {max_origin_diff:.3f} mm)"
    
    return True, ""


def detect_left_right_flip(affine: np.ndarray) -> bool:
    """
    Detect if affine matrix represents a left-right flip.
    
    In RAS+ convention, negative determinant indicates L/R flip.
    
    Args:
        affine: 4x4 affine transformation matrix
        
    Returns:
        True if L/R flip detected, False otherwise
    """
    M = affine[:3, :3]
    det = np.linalg.det(M)
    
    # Negative determinant indicates flip (reflection)
    return det < 0


def calculate_brats_label_volumes(
    segmentation: np.ndarray,
    affine: np.ndarray
) -> Dict[str, float]:
    """
    Calculate volumes for all BraTS tumor regions.
    
    BraTS labels:
    - Label 1: Necrotic and non-enhancing tumor core (NCR)
    - Label 2: Peritumoral edema (ED)  
    - Label 4: GD-enhancing tumor (ET)
    
    Composite regions:
    - WT (Whole Tumor): labels 1, 2, 4
    - TC (Tumor Core): labels 1, 4
    - ET (Enhancing Tumor): label 4
    
    Args:
        segmentation: 3D label map with BraTS labels (1, 2, 4)
        affine: 4x4 affine transformation matrix
        
    Returns:
        Dictionary with volumes in mL for each region
    """
    results = {}
    
    # Individual label volumes
    results['ncr_ml'] = calculate_volume_ml(segmentation, affine, label=1)
    results['ed_ml'] = calculate_volume_ml(segmentation, affine, label=2)
    results['et_ml'] = calculate_volume_ml(segmentation, affine, label=4)
    
    # Composite region volumes
    wt_mask = np.isin(segmentation, [1, 2, 4])
    tc_mask = np.isin(segmentation, [1, 4])
    et_mask = (segmentation == 4)
    
    results['wt_ml'] = calculate_volume_ml(wt_mask.astype(np.uint8), affine)
    results['tc_ml'] = calculate_volume_ml(tc_mask.astype(np.uint8), affine)
    # ET volume same as label 4
    
    return results