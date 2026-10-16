"""
Batch Evaluation Script
Evaluates model on held-out labeled cases.

Usage:
    python evaluate_batch.py --cases cases_manifest.json --output results.json

LIMITATION: Currently no real held-out BraTS data available.
This script provides the infrastructure for evaluation when data becomes available.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.inference_service import BraTSInferenceService
from evaluation.metrics import evaluate_case, aggregate_metrics, Region, RegionMetrics
import nibabel as nib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_cases_manifest(manifest_path: Path) -> Dict:
    """
    Load cases manifest specifying evaluation cases.
    
    Manifest format:
    {
        "split": "held_out_test",
        "created": "2026-10-16",
        "num_cases": 10,
        "cases": [
            {
                "case_id": "BraTS20_001",
                "patient_id": "001",
                "t1ce": "path/to/t1ce.nii.gz",
                "t1": "path/to/t1.nii.gz",
                "t2": "path/to/t2.nii.gz",
                "flair": "path/to/flair.nii.gz",
                "ground_truth": "path/to/seg.nii.gz"
            },
            ...
        ]
    }
    """
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    logger.info(f"Loaded manifest: {manifest['split']}")
    logger.info(f"Number of cases: {manifest['num_cases']}")
    
    return manifest


def evaluate_batch(
    manifest_path: Path,
    model_path: Path,
    output_path: Path,
    handle_empty: str = "nan"
):
    """
    Run batch evaluation on cases from manifest.
    
    Args:
        manifest_path: Path to cases manifest JSON
        model_path: Path to model weights
        output_path: Where to save evaluation results
        handle_empty: How to handle empty masks
    """
    # Load manifest
    manifest = load_cases_manifest(manifest_path)
    
    # Resolve all file paths relative to manifest directory
    manifest_dir = manifest_path.parent
    for case_info in manifest['cases']:
        for key in ['t1ce', 't1', 't2', 'flair', 'ground_truth']:
            if key in case_info:
                case_info[key] = str((manifest_dir / case_info[key]).resolve())
    
    # Initialize inference service
    logger.info(f"Loading model from {model_path}")
    inference_service = BraTSInferenceService(model_path)
    
    # Evaluate each case
    case_results = {}
    start_time = datetime.now()
    
    for case_info in manifest['cases']:
        case_id = case_info['case_id']
        logger.info(f"Evaluating case: {case_id}")
        
        try:
            # Run inference
            result = inference_service.run_inference(
                t1ce_path=Path(case_info['t1ce']),
                t1_path=Path(case_info['t1']),
                t2_path=Path(case_info['t2']),
                flair_path=Path(case_info['flair'])
            )
            
            # Load ground truth
            gt_nii = nib.load(case_info['ground_truth'])
            gt_seg = gt_nii.get_fdata().astype(int)
            
            # Compute metrics
            metrics = evaluate_case(result.segmentation, gt_seg, handle_empty)
            
            # Store results
            case_results[case_id] = {
                'metrics': {
                    region.value: {
                        'dice': m.dice,
                        'sensitivity': m.sensitivity,
                        'true_positive': m.true_positive,
                        'false_positive': m.false_positive,
                        'false_negative': m.false_negative,
                        'prediction_volume_voxels': m.prediction_volume_voxels,
                        'ground_truth_volume_voxels': m.ground_truth_volume_voxels,
                        'true_negative': m.true_negative,
                        'is_empty_ground_truth': bool(m.is_empty_ground_truth),
                        'is_empty_prediction': bool(m.is_empty_prediction)
                    }
                    for region, m in metrics.items()
                },
                'inference_time_sec': result.inference_time_sec,
                'device': result.device_used
            }
            
            logger.info(f"  WT Dice: {metrics[Region.WT].dice:.4f}")
            logger.info(f"  TC Dice: {metrics[Region.TC].dice:.4f}")
            logger.info(f"  ET Dice: {metrics[Region.ET].dice:.4f}")
        except Exception as e:
            logger.error(f"Error evaluating {case_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            case_results[case_id] = {'error': str(e)}
    
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    # Aggregate metrics
    successful_cases = {k: v for k, v in case_results.items() if 'error' not in v}
    
    # Reconstruct Region enum objects and RegionMetrics from stored dicts
    metrics_only = {}
    for case_id, case_data in successful_cases.items():
        metrics_only[case_id] = {}
        for region_str, metric_dict in case_data['metrics'].items():
            # Find Region enum by value
            region_enum = next(r for r in Region if r.value == region_str)
            # Create metrics object
            metrics_obj = RegionMetrics(**{k: v for k, v in metric_dict.items() 
                                         if k in ['dice', 'sensitivity', 'true_positive', 
                                                 'false_positive', 'false_negative', 'true_negative',
                                                 'prediction_volume_voxels', 'ground_truth_volume_voxels',
                                                 'is_empty_ground_truth', 'is_empty_prediction']})
            metrics_only[case_id][region_enum] = metrics_obj
    
    aggregated = aggregate_metrics(metrics_only)
    
    # Compile results
    results = {
        'evaluation': {
            'split': manifest['split'],
            'num_cases': len(manifest['cases']),
            'num_successful': len(successful_cases),
            'timestamp': datetime.now().isoformat(),
            'total_time_sec': elapsed
        },
        'model': {
            'path': str(model_path),
            'version': 'MONAI brats_mri_segmentation (BraTS 2018)',
            'architecture': 'SegResNet'
        },
        'aggregate_metrics': {
            region.value: metrics 
            for region, metrics in aggregated.items()
        },
        'per_case_results': case_results
    }
    
    # Save results
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info("EVALUATION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Cases evaluated: {len(successful_cases)}/{len(manifest['cases'])}")
    logger.info(f"Total time: {elapsed:.1f}s")
    logger.info(f"\nAggregate Metrics:")
    for region, metrics in aggregated.items():
        logger.info(f"\n{region.value.upper()}:")
        logger.info(f"  Mean Dice: {metrics['mean_dice']:.4f} ± {metrics['std_dice']:.4f}")
        logger.info(f"  Median Dice: {metrics['median_dice']:.4f}")
        logger.info(f"  Mean Sensitivity: {metrics['mean_sensitivity']:.4f}")
    logger.info(f"\nResults saved to: {output_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Batch evaluation on held-out cases')
    parser.add_argument('--cases', type=str, required=True, help='Cases manifest JSON')
    parser.add_argument('--model', type=str, default='../models/brats_mri_segmentation/models/model.pt')
    parser.add_argument('--output', type=str, required=True, help='Output results JSON')
    parser.add_argument('--handle-empty', type=str, default='nan', choices=['nan', 'one', 'zero'])
    
    args = parser.parse_args()
    
    evaluate_batch(
        manifest_path=Path(args.cases),
        model_path=Path(args.model),
        output_path=Path(args.output),
        handle_empty=args.handle_empty
    )


if __name__ == '__main__':
    main()







