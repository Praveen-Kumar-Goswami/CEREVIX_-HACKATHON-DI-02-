"""
Evaluation Metrics for Brain Tumor Segmentation
Implements Dice coefficient and sensitivity with proper edge case handling.

References:
- Dice coefficient: 2*|A∩B| / (|A| + |B|)
- Sensitivity (Recall): |A∩B| / |B|  (true positives / all positives in ground truth)
"""

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class Region(Enum):
    """BraTS tumor regions"""
    WT = "whole_tumor"  # Labels 1, 2, 4
    TC = "tumor_core"   # Labels 1, 4
    ET = "enhancing_tumor"  # Label 4


@dataclass
class RegionMetrics:
    """Metrics for a single region"""
    dice: float
    sensitivity: float
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    
    # Metadata
    prediction_volume_voxels: int
    ground_truth_volume_voxels: int
    is_empty_ground_truth: bool
    is_empty_prediction: bool


def extract_region_mask(segmentation: np.ndarray, region: Region) -> np.ndarray:
    """
    Extract binary mask for a specific region from BraTS label map.
    
    Args:
        segmentation: 3D array with BraTS labels (0, 1, 2, 4)
        region: Region to extract
        
    Returns:
        Binary mask (bool array)
    """
    if region == Region.WT:
        # Whole tumor: all tumor labels (1, 2, 4)
        mask = np.isin(segmentation, [1, 2, 4])
    elif region == Region.TC:
        # Tumor core: NCR (1) + ET (4)
        mask = np.isin(segmentation, [1, 4])
    elif region == Region.ET:
        # Enhancing tumor: only label 4
        mask = (segmentation == 4)
    else:
        raise ValueError(f"Unknown region: {region}")
    
    return mask.astype(bool)


def compute_dice_coefficient(
    prediction: np.ndarray,
    ground_truth: np.ndarray,
    handle_empty: str = "nan"
) -> float:
    """
    Compute Dice coefficient between binary masks.
    
    Formula: Dice = 2 * |A ∩ B| / (|A| + |B|)
    
    Args:
        prediction: Binary prediction mask
        ground_truth: Binary ground truth mask
        handle_empty: How to handle empty masks
            - "nan": Return NaN if both empty (undefined)
            - "one": Return 1.0 if both empty (perfect agreement)
            - "zero": Return 0.0 if both empty (no overlap)
            
    Returns:
        Dice coefficient in [0, 1] or NaN
        
    Edge cases:
    - Both empty: Depends on handle_empty parameter
    - Only GT empty: 0.0 (no true positives possible)
    - Only pred empty: 0.0 (no true positives found)
    """
    prediction = prediction.astype(bool)
    ground_truth = ground_truth.astype(bool)
    
    pred_sum = prediction.sum()
    gt_sum = ground_truth.sum()
    
    # Handle empty masks
    if gt_sum == 0 and pred_sum == 0:
        # Both empty
        if handle_empty == "nan":
            return np.nan
        elif handle_empty == "one":
            return 1.0
        else:  # "zero"
            return 0.0
    
    if gt_sum == 0 or pred_sum == 0:
        # One empty, one not - no overlap possible
        return 0.0
    
    # Compute intersection
    intersection = (prediction & ground_truth).sum()
    
    # Dice = 2*|A∩B| / (|A| + |B|)
    dice = (2.0 * intersection) / (pred_sum + gt_sum)
    
    return float(dice)


def compute_sensitivity(
    prediction: np.ndarray,
    ground_truth: np.ndarray,
    handle_empty: str = "nan"
) -> float:
    """
    Compute sensitivity (recall, true positive rate).
    
    Formula: Sensitivity = TP / (TP + FN) = |A ∩ B| / |B|
    
    Args:
        prediction: Binary prediction mask
        ground_truth: Binary ground truth mask
        handle_empty: How to handle empty ground truth
            - "nan": Return NaN if GT empty (undefined)
            - "one": Return 1.0 if GT empty and pred empty
            - "zero": Return 0.0 if GT empty
            
    Returns:
        Sensitivity in [0, 1] or NaN
        
    Edge cases:
    - GT empty: Depends on handle_empty parameter
    - Pred empty but GT not: 0.0 (no true positives found)
    """
    prediction = prediction.astype(bool)
    ground_truth = ground_truth.astype(bool)
    
    gt_sum = ground_truth.sum()
    
    # Handle empty ground truth
    if gt_sum == 0:
        if handle_empty == "nan":
            return np.nan
        elif handle_empty == "one":
            return 1.0 if prediction.sum() == 0 else 0.0
        else:  # "zero"
            return 0.0
    
    # Compute true positives
    true_positives = (prediction & ground_truth).sum()
    
    # Sensitivity = TP / P
    sensitivity = float(true_positives) / float(gt_sum)
    
    return sensitivity


def compute_confusion_matrix(
    prediction: np.ndarray,
    ground_truth: np.ndarray
) -> Tuple[int, int, int, int]:
    """
    Compute confusion matrix for binary masks.
    
    Returns:
        (TP, FP, FN, TN)
    """
    prediction = prediction.astype(bool)
    ground_truth = ground_truth.astype(bool)
    
    tp = (prediction & ground_truth).sum()
    fp = (prediction & ~ground_truth).sum()
    fn = (~prediction & ground_truth).sum()
    tn = (~prediction & ~ground_truth).sum()
    
    return int(tp), int(fp), int(fn), int(tn)


def evaluate_region(
    prediction_seg: np.ndarray,
    ground_truth_seg: np.ndarray,
    region: Region,
    handle_empty: str = "nan"
) -> RegionMetrics:
    """
    Evaluate metrics for a specific tumor region.
    
    Args:
        prediction_seg: Predicted segmentation (BraTS labels)
        ground_truth_seg: Ground truth segmentation (BraTS labels)
        region: Region to evaluate
        handle_empty: How to handle empty masks
        
    Returns:
        RegionMetrics with dice, sensitivity, and confusion matrix
    """
    # Extract binary masks for this region
    pred_mask = extract_region_mask(prediction_seg, region)
    gt_mask = extract_region_mask(ground_truth_seg, region)
    
    # Compute metrics
    dice = compute_dice_coefficient(pred_mask, gt_mask, handle_empty)
    sensitivity = compute_sensitivity(pred_mask, gt_mask, handle_empty)
    tp, fp, fn, tn = compute_confusion_matrix(pred_mask, gt_mask)
    
    return RegionMetrics(
        dice=dice,
        sensitivity=sensitivity,
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        true_negative=tn,
        prediction_volume_voxels=int(pred_mask.sum()),
        ground_truth_volume_voxels=int(gt_mask.sum()),
        is_empty_ground_truth=(gt_mask.sum() == 0),
        is_empty_prediction=(pred_mask.sum() == 0)
    )


def evaluate_case(
    prediction_seg: np.ndarray,
    ground_truth_seg: np.ndarray,
    handle_empty: str = "nan"
) -> Dict[Region, RegionMetrics]:
    """
    Evaluate all regions for a case.
    
    Args:
        prediction_seg: Predicted segmentation (BraTS labels)
        ground_truth_seg: Ground truth segmentation (BraTS labels)
        handle_empty: How to handle empty masks
        
    Returns:
        Dictionary mapping Region to RegionMetrics
    """
    results = {}
    
    for region in Region:
        results[region] = evaluate_region(
            prediction_seg,
            ground_truth_seg,
            region,
            handle_empty
        )
    
    return results


def aggregate_metrics(
    case_results: Dict[str, Dict[Region, RegionMetrics]]
) -> Dict[Region, Dict[str, float]]:
    """
    Aggregate metrics across multiple cases.
    
    Args:
        case_results: Dict mapping case_id -> region -> metrics
        
    Returns:
        Dict mapping region -> {mean_dice, mean_sensitivity, etc.}
    """
    aggregated = {}
    
    for region in Region:
        dice_scores = []
        sensitivity_scores = []
        
        for case_id, region_metrics in case_results.items():
            metrics = region_metrics[region]
            
            # Only include non-NaN scores
            if not np.isnan(metrics.dice):
                dice_scores.append(metrics.dice)
            if not np.isnan(metrics.sensitivity):
                sensitivity_scores.append(metrics.sensitivity)
        
        aggregated[region] = {
            "mean_dice": np.mean(dice_scores) if dice_scores else np.nan,
            "std_dice": np.std(dice_scores) if dice_scores else np.nan,
            "median_dice": np.median(dice_scores) if dice_scores else np.nan,
            "mean_sensitivity": np.mean(sensitivity_scores) if sensitivity_scores else np.nan,
            "std_sensitivity": np.std(sensitivity_scores) if sensitivity_scores else np.nan,
            "median_sensitivity": np.median(sensitivity_scores) if sensitivity_scores else np.nan,
            "num_cases": len(dice_scores)
        }
    
    return aggregated