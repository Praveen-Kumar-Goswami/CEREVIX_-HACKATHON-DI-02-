"""
Generate synthetic evaluation dataset with ground truth
Creates realistic test cases with known tumor regions for evaluation testing.
"""

import numpy as np
import nibabel as nib
from pathlib import Path
import json
from typing import Dict, List


def create_synthetic_evaluation_case(
    output_dir: Path,
    case_id: str,
    shape: tuple = (128, 128, 64),
    voxel_spacing: tuple = (1.0, 1.0, 1.0),
    tumor_center: tuple = None,
    tumor_size: str = "medium"
) -> Dict:
    """
    Create a synthetic case with ground truth segmentation.
    
    Returns paths to modality files and ground truth.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    np.random.seed(hash(case_id) % 2**32)  # Reproducible per case
    
    H, W, D = shape
    
    # Create affine
    affine = np.diag([*voxel_spacing, 1.0])
    
    # Base brain structure
    z, y, x = np.ogrid[:H, :W, :D]
    brain_mask = (
        ((x - W//2) / (W//2.5))**2 +
        ((y - H//2) / (H//2.5))**2 +
        ((z - D//2) / (D//2.8))**2
    ) < 1.0
    
    # Create ground truth segmentation with realistic tumor
    ground_truth = np.zeros(shape, dtype=np.uint8)
    
    if tumor_center is None:
        tumor_center = (H//2 + 15, W//2 + 10, D//2 + 5)
    
    # Size parameters
    if tumor_size == "small":
        et_radius, ncr_radius, ed_radius = 5, 8, 12
    elif tumor_size == "large":
        et_radius, ncr_radius, ed_radius = 10, 15, 22
    else:  # medium
        et_radius, ncr_radius, ed_radius = 7, 11, 18
    
    # Create tumor regions
    cz, cy, cx = tumor_center
    
    # Edema (label 2) - outer ring
    ed_dist = np.sqrt((x - cx)**2 + (y - cy)**2 + (z - cz)**2)
    ground_truth[ed_dist <= ed_radius] = 2
    
    # NCR (label 1) - inner core
    ncr_dist = np.sqrt((x - cx)**2 + (y - cy)**2 + (z - cz)**2)
    ground_truth[ncr_dist <= ncr_radius] = 1
    
    # ET (label 4) - enhancing rim
    et_dist = np.sqrt((x - cx)**2 + (y - cy)**2 + (z - cz)**2)
    ground_truth[(et_dist <= et_radius)] = 4
    
    # Only keep tumor in brain region
    ground_truth = ground_truth * brain_mask.astype(np.uint8)
    
    # Create modality images with tumor characteristics
    structure_noise = np.random.randn(H, W, D) * 0.2
    
    t1_base = brain_mask.astype(float) * (0.3 + structure_noise * 0.1)
    t1ce_base = brain_mask.astype(float) * (0.35 + structure_noise * 0.1)
    t2_base = brain_mask.astype(float) * (0.4 + structure_noise * 0.15)
    flair_base = brain_mask.astype(float) * (0.45 + structure_noise * 0.12)
    
    # Add tumor signal
    et_mask = (ground_truth == 4)
    ncr_mask = (ground_truth == 1)
    ed_mask = (ground_truth == 2)
    
    # ET: bright on T1ce
    t1ce_base[et_mask] = 0.9
    t1_base[et_mask] = 0.7
    
    # NCR: dark on all
    t1ce_base[ncr_mask] = 0.2
    t1_base[ncr_mask] = 0.15
    
    # Edema: bright on T2/FLAIR
    t2_base[ed_mask] = 0.85
    flair_base[ed_mask] = 0.9
    
    # Add noise
    t1 = np.clip(t1_base + np.random.randn(H, W, D) * 0.05, 0, 1)
    t1ce = np.clip(t1ce_base + np.random.randn(H, W, D) * 0.05, 0, 1)
    t2 = np.clip(t2_base + np.random.randn(H, W, D) * 0.05, 0, 1)
    flair = np.clip(flair_base + np.random.randn(H, W, D) * 0.05, 0, 1)
    
    # Save files
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
        files[name] = str(filepath)
    
    # Save ground truth
    gt_filename = f"{case_id}_seg.nii.gz"
    gt_filepath = output_dir / gt_filename
    nii_gt = nib.Nifti1Image(ground_truth, affine)
    nib.save(nii_gt, gt_filepath)
    files['ground_truth'] = str(gt_filepath)
    
    # Compute ground truth statistics
    gt_stats = {
        'wt_voxels': int((ground_truth > 0).sum()),
        'tc_voxels': int(np.isin(ground_truth, [1, 4]).sum()),
        'et_voxels': int((ground_truth == 4).sum()),
        'ncr_voxels': int((ground_truth == 1).sum()),
        'ed_voxels': int((ground_truth == 2).sum())
    }
    
    print(f"Created: {case_id}")
    print(f"  WT: {gt_stats['wt_voxels']} voxels")
    print(f"  TC: {gt_stats['tc_voxels']} voxels")
    print(f"  ET: {gt_stats['et_voxels']} voxels")
    
    return {
        'case_id': case_id,
        'files': files,
        'ground_truth_stats': gt_stats
    }


def create_evaluation_dataset(
    output_base: Path,
    num_cases: int = 12
) -> Dict:
    """
    Create a complete synthetic evaluation dataset.
    
    Creates cases with varying characteristics:
    - Different tumor sizes
    - Different locations
    - Different voxel spacings
    """
    output_base = Path(output_base)
    
    cases = []
    
    # Vary tumor characteristics
    sizes = ['small', 'medium', 'large']
    spacings = [(1.0, 1.0, 1.0), (1.0, 1.0, 2.0), (0.9, 0.9, 0.9)]
    
    for i in range(num_cases):
        case_id = f"SYNTHETIC_EVAL_{i+1:03d}"
        case_dir = output_base / case_id
        
        # Vary parameters
        tumor_size = sizes[i % len(sizes)]
        spacing = spacings[i % len(spacings)]
        
        # Vary tumor location
        if i % 3 == 0:
            center = (64 + 10, 64 + 5, 32)  # Right side
        elif i % 3 == 1:
            center = (64 - 10, 64 + 5, 32)  # Left side
        else:
            center = (64, 64 + 15, 32 + 5)  # Central
        
        case_info = create_synthetic_evaluation_case(
            output_dir=case_dir,
            case_id=case_id,
            shape=(128, 128, 64),
            voxel_spacing=spacing,
            tumor_center=center,
            tumor_size=tumor_size
        )
        
        # Convert absolute paths to relative (relative to manifest location)
        
        for key in ['t1ce', 't1', 't2', 'flair', 'ground_truth']:
        
            case_info['files'][key] = str(Path(case_info['files'][key]).relative_to(output_base))
        
        
        
        cases.append({
            'case_id': case_info['case_id'],
            'patient_id': f"SYNTH_PT_{(i//2)+1:03d}",  # 2 scans per patient
            't1ce': case_info['files']['t1ce'],
            't1': case_info['files']['t1'],
            't2': case_info['files']['t2'],
            'flair': case_info['files']['flair'],
            'ground_truth': case_info['files']['ground_truth'],
            'metadata': {
                'voxel_spacing': spacing,
                'tumor_size': tumor_size,
                'ground_truth_stats': case_info['ground_truth_stats']
            }
        })
    
    # Create manifest
    manifest = {
        'split': 'synthetic_held_out_evaluation',
        'created': '2026-10-16',
        'num_cases': len(cases),
        'description': 'Synthetic evaluation dataset for testing infrastructure',
        'note': 'NOT REAL PATIENT DATA - For system validation only',
        'cases': cases
    }
    
    # Save manifest
    manifest_path = output_base / 'evaluation_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Created {num_cases} synthetic evaluation cases")
    print(f"Manifest saved to: {manifest_path}")
    print(f"{'='*60}")
    
    return manifest


if __name__ == '__main__':
    import sys
    
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('data/synthetic_evaluation')
    num_cases = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    
    manifest = create_evaluation_dataset(output_dir, num_cases)
    
    print(f"\nTo run evaluation:")
    print(f"python backend/evaluation/evaluate_batch.py \\")
    print(f"    --cases {output_dir}/evaluation_manifest.json \\")
    print(f"    --output evaluation_results.json")
