"""
NeuroScope 3D - Command Line Interface (CLI)
Performs end-to-end inference and report generation from the command line.

Usage:
  python backend/cli.py --t1ce <t1ce.nii.gz> --t1 <t1.nii.gz> --t2 <t2.nii.gz> --flair <flair.nii.gz> --output <pred.nii.gz> [--report <report.json>] [--expert <expert.nii.gz>]
"""

import argparse
import sys
import os
import json
import time
from pathlib import Path

# Enable UTF-8 for console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Setup paths
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from services.validation_service import NIfTIValidator, ModalityType
from services.inference_service import BraTSInferenceService
from services.report_service import generate_case_report, save_report_json
from services.export_service import export_prediction_nifti
from utils.spatial_utils import calculate_brats_label_volumes
from evaluation.metrics import evaluate_case
import nibabel as nib
import numpy as np


def main():
    parser = argparse.ArgumentParser(
        description="NeuroScope 3D - Brain MRI Tumor Segmentation CLI"
    )
    parser.add_argument("--t1ce", required=True, type=Path, help="Path to T1ce (contrast-enhanced) NIfTI")
    parser.add_argument("--t1", required=True, type=Path, help="Path to T1-weighted NIfTI")
    parser.add_argument("--t2", required=True, type=Path, help="Path to T2-weighted NIfTI")
    parser.add_argument("--flair", required=True, type=Path, help="Path to FLAIR NIfTI")
    parser.add_argument("--output", "-o", required=True, type=Path, help="Output path for segmentation NIfTI")
    parser.add_argument("--report", "-r", type=Path, default=None, help="Output path for JSON provenance report")
    parser.add_argument("--expert", "-e", type=Path, default=None, help="Optional expert ground truth mask")
    parser.add_argument("--model", type=Path, default=Path("models/brats_mri_segmentation/models/model.pt"), help="Path to model weights")

    args = parser.parse_args()

    print("=" * 65)
    print("NeuroScope 3D - CLI Brain Tumor Segmentation")
    print("=" * 65)
    print("DISCLAIMER: RESEARCH USE ONLY - NOT FOR CLINICAL DIAGNOSIS")
    print("=" * 65)

    # 1. Validate inputs
    print("\n[1/5] Validating input volumes...")
    validator = NIfTIValidator()
    modality_dict = {
        ModalityType.T1CE: args.t1ce,
        ModalityType.T1: args.t1,
        ModalityType.T2: args.t2,
        ModalityType.FLAIR: args.flair
    }
    
    val_result, val_meta = validator.validate_four_modalities(modality_dict)
    if not val_result.is_valid:
        print(f"[ERROR] Input validation failed: {val_result.error_message}")
        sys.exit(1)
    print(f"[OK] All 4 modalities validated (Shape: {val_meta[ModalityType.T1CE].shape})")

    # Optional expert mask validation
    expert_metrics = None
    if args.expert:
        print("\nValidating expert ground truth mask...")
        exp_valid, exp_meta = validator.validate_expert_mask(args.expert, val_meta[ModalityType.T1CE])
        if not exp_valid.is_valid:
            print(f"[ERROR] Expert mask validation failed: {exp_valid.error_message}")
            sys.exit(1)
        print("[OK] Expert mask validated")

    # 2. Run inference
    print("\n[2/5] Running SegResNet inference pipeline...")
    service = BraTSInferenceService(args.model)
    print(f"  Device: {service.device}")
    
    t_start = time.perf_counter()
    result = service.run_inference(
        t1ce_path=args.t1ce,
        t1_path=args.t1,
        t2_path=args.t2,
        flair_path=args.flair
    )
    t_elapsed = time.perf_counter() - t_start
    print(f"[OK] Inference complete in {t_elapsed:.2f}s")

    # 3. Verify labels and volume measurements
    print("\n[3/5] Computing volumetric measurements...")
    vols = result.volumes_ml
    print(f"  Whole Tumor (WT):      {vols['wt_ml']:>8.2f} mL")
    print(f"  Tumor Core (TC):       {vols['tc_ml']:>8.2f} mL")
    print(f"  Enhancing Tumor (ET):  {vols['et_ml']:>8.2f} mL")

    # 4. Expert mask comparison if supplied
    if args.expert:
        print("\n[4/5] Computing comparison metrics against expert mask...")
        exp_img = nib.load(args.expert)
        exp_seg = exp_img.get_fdata()
        comp_results = evaluate_case(result.segmentation, exp_seg, handle_empty="nan")
        expert_metrics = {}
        for r, rm in comp_results.items():
            rname = r.value
            dice_str = f"{rm.dice:.3f}" if not np.isnan(rm.dice) else "N/A"
            sens_str = f"{rm.sensitivity:.3f}" if not np.isnan(rm.sensitivity) else "N/A"
            print(f"  {rname.upper():16s} Dice: {dice_str} | Sensitivity: {sens_str}")
            expert_metrics[rname] = {
                "dice": float(rm.dice) if not np.isnan(rm.dice) else None,
                "sensitivity": float(rm.sensitivity) if not np.isnan(rm.sensitivity) else None,
                "expert_voxels": int(rm.ground_truth_volume_voxels),
                "pred_voxels": int(rm.prediction_volume_voxels)
            }

    # 5. Export NIfTI and Provenance Report
    print("\n[5/5] Exporting BraTS-compliant NIfTI and Provenance Report...")
    export_prediction_nifti(result.segmentation, result.affine, args.output, "CLI_CASE")
    print(f"[OK] NIfTI segmentation saved to: {args.output}")

    if args.report:
        report = generate_case_report(
            case_id="CLI_EXECUTION",
            input_files={
                "t1ce": args.t1ce,
                "t1": args.t1,
                "t2": args.t2,
                "flair": args.flair
            },
            volumes_ml={
                "WT": vols["wt_ml"],
                "TC": vols["tc_ml"],
                "ET": vols["et_ml"]
            },
            inference_time_sec=t_elapsed,
            device=service.device,
            upload_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            expert_metrics=expert_metrics
        )
        save_report_json(report, args.report)
        print(f"[OK] Provenance report saved to: {args.report}")

    print("\n" + "=" * 65)
    print("SUCCESS: Full pipeline execution verified.")
    print("=" * 65)


if __name__ == "__main__":
    main()
