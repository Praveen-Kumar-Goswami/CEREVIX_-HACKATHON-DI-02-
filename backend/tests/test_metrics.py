"""
Tests for evaluation metrics
Covers edge cases and validates Dice/Sensitivity computations.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.metrics import (
    compute_dice_coefficient,
    compute_sensitivity,
    compute_confusion_matrix,
    extract_region_mask,
    evaluate_region,
    evaluate_case,
    Region
)


class TestDiceCoefficient:
    """Test Dice coefficient edge cases"""
    
    def test_perfect_overlap(self):
        """Dice = 1.0 for identical masks"""
        mask = np.ones((10, 10, 10), dtype=bool)
        dice = compute_dice_coefficient(mask, mask)
        assert dice == 1.0
    
    def test_no_overlap(self):
        """Dice = 0.0 for disjoint masks"""
        pred = np.zeros((10, 10, 10), dtype=bool)
        pred[:5, :, :] = True
        
        gt = np.zeros((10, 10, 10), dtype=bool)
        gt[5:, :, :] = True
        
        dice = compute_dice_coefficient(pred, gt)
        assert dice == 0.0
    
    def test_partial_overlap(self):
        """Dice for known partial overlap"""
        pred = np.zeros((10, 10, 10), dtype=bool)
        pred[:6, :, :] = True  # 600 voxels
        
        gt = np.zeros((10, 10, 10), dtype=bool)
        gt[4:, :, :] = True  # 600 voxels
        
        # Intersection: [4:6] = 200 voxels
        # Dice = 2*200 / (600 + 600) = 400/1200 = 1/3
        dice = compute_dice_coefficient(pred, gt)
        assert abs(dice - (1/3)) < 1e-10
    
    def test_both_empty_nan(self):
        """Both empty → NaN (default)"""
        empty = np.zeros((10, 10, 10), dtype=bool)
        dice = compute_dice_coefficient(empty, empty, handle_empty="nan")
        assert np.isnan(dice)
    
    def test_both_empty_one(self):
        """Both empty → 1.0 (perfect agreement option)"""
        empty = np.zeros((10, 10, 10), dtype=bool)
        dice = compute_dice_coefficient(empty, empty, handle_empty="one")
        assert dice == 1.0
    
    def test_both_empty_zero(self):
        """Both empty → 0.0 (no overlap option)"""
        empty = np.zeros((10, 10, 10), dtype=bool)
        dice = compute_dice_coefficient(empty, empty, handle_empty="zero")
        assert dice == 0.0
    
    def test_only_pred_empty(self):
        """Only prediction empty → 0.0"""
        pred = np.zeros((10, 10, 10), dtype=bool)
        gt = np.ones((10, 10, 10), dtype=bool)
        dice = compute_dice_coefficient(pred, gt)
        assert dice == 0.0
    
    def test_only_gt_empty(self):
        """Only ground truth empty → 0.0"""
        pred = np.ones((10, 10, 10), dtype=bool)
        gt = np.zeros((10, 10, 10), dtype=bool)
        dice = compute_dice_coefficient(pred, gt)
        assert dice == 0.0


class TestSensitivity:
    """Test sensitivity (recall) edge cases"""
    
    def test_perfect_sensitivity(self):
        """Sensitivity = 1.0 when all GT voxels found"""
        gt = np.ones((10, 10, 10), dtype=bool)
        pred = np.ones((10, 10, 10), dtype=bool)
        sens = compute_sensitivity(pred, gt)
        assert sens == 1.0
    
    def test_zero_sensitivity(self):
        """Sensitivity = 0.0 when no GT voxels found"""
        gt = np.ones((10, 10, 10), dtype=bool)
        pred = np.zeros((10, 10, 10), dtype=bool)
        sens = compute_sensitivity(pred, gt)
        assert sens == 0.0
    
    def test_partial_sensitivity(self):
        """Sensitivity for partial detection"""
        gt = np.zeros((10, 10, 10), dtype=bool)
        gt[:5, :, :] = True  # 500 voxels
        
        pred = np.zeros((10, 10, 10), dtype=bool)
        pred[:3, :, :] = True  # 300 voxels, all in GT
        
        # Sensitivity = 300 / 500 = 0.6
        sens = compute_sensitivity(pred, gt)
        assert abs(sens - 0.6) < 1e-10
    
    def test_gt_empty_nan(self):
        """GT empty → NaN (default)"""
        gt = np.zeros((10, 10, 10), dtype=bool)
        pred = np.zeros((10, 10, 10), dtype=bool)
        sens = compute_sensitivity(pred, gt, handle_empty="nan")
        assert np.isnan(sens)
    
    def test_gt_empty_both_empty_one(self):
        """GT empty, pred empty → 1.0"""
        gt = np.zeros((10, 10, 10), dtype=bool)
        pred = np.zeros((10, 10, 10), dtype=bool)
        sens = compute_sensitivity(pred, gt, handle_empty="one")
        assert sens == 1.0
    
    def test_gt_empty_pred_not_zero(self):
        """GT empty, pred not empty → 0.0"""
        gt = np.zeros((10, 10, 10), dtype=bool)
        pred = np.ones((10, 10, 10), dtype=bool)
        sens = compute_sensitivity(pred, gt, handle_empty="one")
        assert sens == 0.0


class TestConfusionMatrix:
    """Test confusion matrix computation"""
    
    def test_perfect_prediction(self):
        """All correct predictions"""
        gt = np.zeros((10, 10, 10), dtype=bool)
        gt[:5, :, :] = True
        pred = gt.copy()
        
        tp, fp, fn, tn = compute_confusion_matrix(pred, gt)
        
        assert tp == 500  # 5*10*10
        assert fp == 0
        assert fn == 0
        assert tn == 500  # 5*10*10
    
    def test_all_false_positives(self):
        """Predict positive where GT is negative"""
        gt = np.zeros((10, 10, 10), dtype=bool)
        pred = np.ones((10, 10, 10), dtype=bool)
        
        tp, fp, fn, tn = compute_confusion_matrix(pred, gt)
        
        assert tp == 0
        assert fp == 1000  # All predictions wrong
        assert fn == 0
        assert tn == 0
    
    def test_all_false_negatives(self):
        """Predict negative where GT is positive"""
        gt = np.ones((10, 10, 10), dtype=bool)
        pred = np.zeros((10, 10, 10), dtype=bool)
        
        tp, fp, fn, tn = compute_confusion_matrix(pred, gt)
        
        assert tp == 0
        assert fp == 0
        assert fn == 1000  # Missed all positives
        assert tn == 0


class TestRegionExtraction:
    """Test region mask extraction from BraTS labels"""
    
    def test_extract_wt(self):
        """Whole tumor = labels 1, 2, 4"""
        seg = np.zeros((10, 10, 10), dtype=np.uint8)
        seg[0:3, :, :] = 1  # NCR
        seg[3:6, :, :] = 2  # ED
        seg[6:9, :, :] = 4  # ET
        
        wt_mask = extract_region_mask(seg, Region.WT)
        
        assert wt_mask.sum() == 900  # 9*10*10
        assert wt_mask.dtype == bool
    
    def test_extract_tc(self):
        """Tumor core = labels 1, 4"""
        seg = np.zeros((10, 10, 10), dtype=np.uint8)
        seg[0:3, :, :] = 1  # NCR
        seg[3:6, :, :] = 2  # ED (not in TC)
        seg[6:9, :, :] = 4  # ET
        
        tc_mask = extract_region_mask(seg, Region.TC)
        
        assert tc_mask.sum() == 600  # (3+3)*10*10
    
    def test_extract_et(self):
        """Enhancing tumor = label 4 only"""
        seg = np.zeros((10, 10, 10), dtype=np.uint8)
        seg[0:3, :, :] = 1  # NCR (not ET)
        seg[3:6, :, :] = 2  # ED (not ET)
        seg[6:9, :, :] = 4  # ET
        
        et_mask = extract_region_mask(seg, Region.ET)
        
        assert et_mask.sum() == 300  # 3*10*10


class TestEvaluateRegion:
    """Test full region evaluation"""
    
    def test_evaluate_perfect_match(self):
        """Perfect prediction for a region"""
        seg = np.zeros((10, 10, 10), dtype=np.uint8)
        seg[0:5, :, :] = 4  # ET
        
        metrics = evaluate_region(seg, seg, Region.ET)
        
        assert metrics.dice == 1.0
        assert metrics.sensitivity == 1.0
        assert metrics.true_positive == 500
        assert metrics.false_positive == 0
        assert metrics.false_negative == 0
        assert not metrics.is_empty_ground_truth
        assert not metrics.is_empty_prediction
    
    def test_evaluate_empty_region(self):
        """Both empty (e.g., no ET in either)"""
        seg = np.zeros((10, 10, 10), dtype=np.uint8)
        seg[:, :, :] = 2  # Only edema, no ET
        
        metrics = evaluate_region(seg, seg, Region.ET, handle_empty="one")
        
        assert metrics.dice == 1.0  # Both empty = perfect agreement
        assert metrics.sensitivity == 1.0
        assert metrics.is_empty_ground_truth
        assert metrics.is_empty_prediction


class TestEvaluateCase:
    """Test full case evaluation"""
    
    def test_evaluate_complete_case(self):
        """Evaluate all regions for a case"""
        seg = np.zeros((10, 10, 10), dtype=np.uint8)
        seg[0:3, :, :] = 1  # NCR
        seg[3:6, :, :] = 2  # ED
        seg[6:9, :, :] = 4  # ET
        
        results = evaluate_case(seg, seg, handle_empty="one")
        
        # All regions should have perfect scores
        assert results[Region.WT].dice == 1.0
        assert results[Region.TC].dice == 1.0
        assert results[Region.ET].dice == 1.0
        
        assert results[Region.WT].sensitivity == 1.0
        assert results[Region.TC].sensitivity == 1.0
        assert results[Region.ET].sensitivity == 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])