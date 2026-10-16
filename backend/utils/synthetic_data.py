"""
Synthetic BraTS Test Data Generator
Creates realistic-looking 4-modality MRI cases for testing.

Generates:
- 4 modality NIfTI files (T1ce, T1, T2, FLAIR)
- Matching shapes and affines
- Realistic intensity distributions
- Optional synthetic tumor regions
"""

import numpy as np
import nibabel as nib
from pathlib import Path
from typing import Tuple, Optional


def create_synthetic_brain_volume(
    shape: Tuple[int, int, int] = (240, 240, 155),
    has_tumor: bool = True,
    tumor_center: Optional[Tuple[int, int, int]] = None,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate synthetic 4-modality MRI volumes.
    
    Args:
        shape: Volume dimensions (H, W, D)
        has_tumor: Whether to add synthetic tumor
        tumor_center: Tumor center voxel coordinates
        seed: Random seed for reproducibility
        
    Returns:
        (t1ce, t1, t2, flair) as numpy arrays
    """
    np.random.seed(seed)
    
    H, W, D = shape
    
    # Create base brain tissue with realistic structure
    # Ellipsoid mask for brain region
    z, y, x = np.ogrid[:H, :W, :D]
    brain_mask = (
        ((x - W//2) / (W//2.5))**2 +
        ((y - H//2) / (H//2.5))**2 +
        ((z - D//2) / (D//2.8))**2
    ) < 1.0
    
    # Add some anatomical structure (ventricles, sulci)
    structure_noise = np.random.randn(H, W, D) * 0.3
    
    # Base intensities for each modality (normalized range)
    t1_base = brain_mask.astype(float) * (0.3 + structure_noise * 0.1)
    t1ce_base = brain_mask.astype(float) * (0.35 + structure_noise * 0.1)
    t2_base = brain_mask.astype(float) * (0.4 + structure_noise * 0.15)
    flair_base = brain_mask.astype(float) * (0.45 + structure_noise * 0.12)
    
    # Add noise
    t1 = np.clip(t1_base + np.random.randn(H, W, D) * 0.05, 0, 1)
    t1ce = np.clip(t1ce_base + np.random.randn(H, W, D) * 0.05, 0, 1)
    t2 = np.clip(t2_base + np.random.randn(H, W, D) * 0.05, 0, 1)
    flair = np.clip(flair_base + np.random.randn(H, W, D) * 0.05, 0, 1)
    
    if has_tumor:
        # Add synthetic tumor with multiple regions
        if tumor_center is None:
            tumor_center = (H//2 + 20, W//2 + 10, D//2)
        
        # Create tumor regions with different characteristics
        # ET (enhancing tumor) - bright on T1ce
        et_mask = create_spherical_region(shape, tumor_center, radius=8)
        
        # Necrotic core - dark center
        ncr_center = tumor_center
        ncr_mask = create_spherical_region(shape, ncr_center, radius=5)
        ncr_mask = ncr_mask & ~et_mask  # Don't overlap with ET
        
        # Edema - extended region, bright on T2/FLAIR
        ed_center = tumor_center
        ed_mask = create_spherical_region(shape, ed_center, radius=15)
        ed_mask = ed_mask & ~et_mask & ~ncr_mask  # Surrounding regions
        
        # Apply tumor characteristics to modalities
        t1ce[et_mask] = 0.9  # Bright enhancement
        t1[et_mask] = 0.7
        t2[et_mask] = 0.6
        flair[et_mask] = 0.65
        
        t1ce[ncr_mask] = 0.2  # Dark necrotic core
        t1[ncr_mask] = 0.15
        t2[ncr_mask] = 0.25
        flair[ncr_mask] = 0.2
        
        t1ce[ed_mask] = 0.4  # Edema
        t1[ed_mask] = 0.35
        t2[ed_mask] = 0.8  # Bright on T2
        flair[ed_mask] = 0.85  # Very bright on FLAIR
    
    return t1ce, t1, t2, flair


def create_spherical_region(
    shape: Tuple[int, int, int],
    center: Tuple[int, int, int],
    radius: float
) -> np.ndarray:
    """Create binary spherical mask"""
    H, W, D = shape
    z, y, x = np.ogrid[:H, :W, :D]
    cz, cy, cx = center
    
    dist_sq = (x - cx)**2 + (y - cy)**2 + (z - cz)**2
    return dist_sq <= radius**2


def create_synthetic_case(
    output_dir: Path,
    case_id: str = "synthetic_001",
    shape: Tuple[int, int, int] = (240, 240, 155),
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    has_tumor: bool = True
) -> dict:
    """
    Generate complete synthetic BraTS case with 4 modalities.
    
    Args:
        output_dir: Where to save NIfTI files
        case_id: Case identifier
        shape: Volume dimensions
        voxel_spacing: Voxel spacing in mm (x, y, z)
        has_tumor: Include synthetic tumor
        
    Returns:
        Dictionary with paths to created files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create affine matrix (simple diagonal with spacing)
    affine = np.diag([*voxel_spacing, 1.0])
    
    # Generate volumes
    t1ce, t1, t2, flair = create_synthetic_brain_volume(
        shape=shape,
        has_tumor=has_tumor
    )
    
    # Save as NIfTI
    files = {}
    modalities = {
        't1ce': t1ce,
        't1': t1,
        't2': t2,
        'flair': flair
    }
    
    for name, volume in modalities.items():
        filename = f"{case_id}_{name}.nii.gz"
        filepath = output_dir / filename
        
        nii = nib.Nifti1Image(volume.astype(np.float32), affine)
        nib.save(nii, filepath)
        
        files[name] = filepath
        print(f"Created: {filepath}")
    
    return files


def create_test_cases(
    output_dir: Path,
    num_cases: int = 3
):
    """
    Generate multiple synthetic test cases.
    
    Cases include:
    1. Standard case with tumor
    2. Anisotropic voxels (1x1x2mm) with tumor
    3. Isotropic high-res (0.5mm) without tumor (negative case)
    """
    output_dir = Path(output_dir)
    
    cases = []
    
    # Case 1: Standard
    print("\n=== Creating Case 1: Standard ===")
    case1 = create_synthetic_case(
        output_dir / "case001",
        case_id="case001",
        shape=(240, 240, 155),
        voxel_spacing=(1.0, 1.0, 1.0),
        has_tumor=True
    )
    cases.append(("case001", case1))
    
    if num_cases > 1:
        # Case 2: Anisotropic
        print("\n=== Creating Case 2: Anisotropic ===")
        case2 = create_synthetic_case(
            output_dir / "case002",
            case_id="case002",
            shape=(240, 240, 77),  # Half z-resolution
            voxel_spacing=(1.0, 1.0, 2.0),
            has_tumor=True
        )
        cases.append(("case002", case2))
    
    if num_cases > 2:
        # Case 3: High-res negative
        print("\n=== Creating Case 3: High-res Negative ===")
        case3 = create_synthetic_case(
            output_dir / "case003",
            case_id="case003",
            shape=(480, 480, 310),  # Double resolution
            voxel_spacing=(0.5, 0.5, 0.5),
            has_tumor=False
        )
        cases.append(("case003", case3))
    
    return cases


if __name__ == "__main__":
    import sys
    
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/test_cases")
    num_cases = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    print(f"Generating {num_cases} synthetic test cases in {output_dir}")
    cases = create_test_cases(output_dir, num_cases)
    
    print(f"\n✅ Created {len(cases)} test cases")
    for case_id, files in cases:
        print(f"\n{case_id}:")
        for modality, path in files.items():
            print(f"  {modality}: {path}")