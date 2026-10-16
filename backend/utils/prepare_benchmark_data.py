"""
Prepare ground truth expert mask for case001 and distinct case002
"""

import numpy as np
import nibabel as nib
from pathlib import Path

def prepare_case_data():
    case001_dir = Path("data/test_cases/case001")
    t1ce = nib.load(case001_dir / "case001_t1ce.nii.gz")
    shape = t1ce.shape
    affine = t1ce.affine
    
    # Create realistic synthetic ground truth for case001
    gt = np.zeros(shape, dtype=np.uint8)
    # Tumor center near center of volume
    cz, cy, cx = 120, 120, 75
    z, y, x = np.ogrid[:shape[0], :shape[1], :shape[2]]
    dist = np.sqrt((z - cz)**2 + (y - cy)**2 + (x - cx)**2)
    
    gt[dist <= 22] = 2  # Edema (2)
    gt[dist <= 14] = 1  # NCR (1)
    gt[dist <= 8] = 4   # ET (4)
    
    expert_path = case001_dir / "case001_expert_seg.nii.gz"
    nii_gt = nib.Nifti1Image(gt, affine)
    nib.save(nii_gt, expert_path)
    print(f"Created expert mask for case001: {expert_path} with {(gt > 0).sum()} voxels")
    
    # Create case002 (distinct geometry, distinct shape: 128x128x64)
    case002_dir = Path("data/test_cases/case002")
    case002_dir.mkdir(parents=True, exist_ok=True)
    c2_shape = (128, 128, 64)
    c2_affine = np.diag([1.5, 1.5, 2.0, 1.0])
    
    # Create 4 modalities for case002
    data_t1 = (np.random.randn(*c2_shape) * 20 + 200).astype(np.float32)
    data_t1ce = (np.random.randn(*c2_shape) * 20 + 200).astype(np.float32)
    data_t2 = (np.random.randn(*c2_shape) * 20 + 200).astype(np.float32)
    data_flair = (np.random.randn(*c2_shape) * 20 + 200).astype(np.float32)
    
    for name, arr in [('t1', data_t1), ('t1ce', data_t1ce), ('t2', data_t2), ('flair', data_flair)]:
        p = case002_dir / f"case002_{name}.nii.gz"
        nib.save(nib.Nifti1Image(arr, c2_affine), p)
    print("Created case002 distinct test case at:", case002_dir)

if __name__ == "__main__":
    prepare_case_data()
