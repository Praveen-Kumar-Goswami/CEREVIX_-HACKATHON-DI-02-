"""
Inference Service - Brain Tumor Segmentation
Integrates MONAI model with spatial utilities for production inference.

Key features:
- MONAI SegResNet model inference
- Region mask to BraTS label conversion (TC/WT/ET → 1/2/4)
- Affine preservation through pipeline
- Volume calculation integration
- GPU/CPU support with automatic fallback
"""

import torch
import numpy as np
import nibabel as nib
from pathlib import Path
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import logging

from monai.networks.nets import SegResNet
from monai.inferers import sliding_window_inference
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd,
    ScaleIntensityRanged, EnsureTyped
)

from utils.spatial_utils import calculate_brats_label_volumes

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """Result of model inference"""
    segmentation: np.ndarray  # 3D label map with BraTS labels (0, 1, 2, 4)
    affine: np.ndarray  # 4x4 affine matrix
    volumes_ml: Dict[str, float]  # Volumes for each region
    inference_time_sec: float
    device_used: str


class BraTSInferenceService:
    """
    Production inference service for BraTS segmentation.
    
    Handles:
    1. Model loading and caching
    2. MONAI preprocessing pipeline
    3. Sliding window inference
    4. Region mask → BraTS label conversion
    5. Volume calculation
    """
    
    def __init__(self, model_path: Path, device: Optional[str] = None):
        """
        Initialize inference service.
        
        Args:
            model_path: Path to model.pt checkpoint
            device: 'cuda', 'cpu', or None (auto-detect)
        """
        self.model_path = model_path
        
        # Auto-detect device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        logger.info(f"Initializing inference service on device: {self.device}")
        
        # Load model
        self.model = self._load_model()
        
        # Create preprocessing pipeline
        self.preprocess = self._create_preprocessing_pipeline()
    
    def _load_model(self) -> torch.nn.Module:
        """Load pretrained SegResNet model"""
        logger.info(f"Loading model from {self.model_path}")
        
        model = SegResNet(
            blocks_down=[1, 2, 2, 4],
            blocks_up=[1, 1, 1],
            init_filters=16,
            in_channels=4,
            out_channels=3,  # TC, WT, ET regions
            dropout_prob=0.2
        )
        
        checkpoint = torch.load(
            self.model_path,
            map_location=self.device,
            weights_only=True  # Security: only load weights
        )
        
        model.load_state_dict(checkpoint)
        model = model.to(self.device)
        model.eval()
        
        logger.info("Model loaded successfully")
        return model
    
    def _create_preprocessing_pipeline(self):
        """
        Create MONAI preprocessing transforms.
        
        Matches training pipeline:
        - Load 4 modalities
        - Ensure channel-first format
        - Intensity normalization (0-1 range, clip outliers)
        - Convert to tensor
        """
        return Compose([
            LoadImaged(keys="image", image_only=False),
            EnsureChannelFirstd(keys="image"),
            ScaleIntensityRanged(
                keys="image",
                a_min=0.0,
                a_max=1.0,
                b_min=0.0,
                b_max=1.0,
                clip=True
            ),
            EnsureTyped(keys="image", dtype=torch.float32)
        ])
    
    def run_inference(
        self,
        t1ce_path: Path,
        t1_path: Path,
        t2_path: Path,
        flair_path: Path
    ) -> InferenceResult:
        """
        Run complete inference pipeline on 4-modality case.
        
        Args:
            t1ce_path: T1 with contrast enhancement
            t1_path: T1 weighted
            t2_path: T2 weighted
            flair_path: FLAIR
            
        Returns:
            InferenceResult with segmentation, affine, volumes, timing
        """
        import time
        start_time = time.time()
        
        # 1. Load and preprocess
        logger.info("Preprocessing 4 modalities...")
        input_tensor, affine = self._preprocess_case(
            t1ce_path, t1_path, t2_path, flair_path
        )
        
        # 2. Run model inference
        logger.info("Running model inference...")
        region_masks = self._run_model_inference(input_tensor)
        
        # 3. Convert region masks to BraTS labels
        logger.info("Converting region masks to BraTS labels...")
        label_map = self._convert_regions_to_labels(region_masks)
        
        # 4. Calculate volumes
        logger.info("Calculating tumor volumes...")
        volumes = calculate_brats_label_volumes(label_map, affine)
        
        inference_time = time.time() - start_time
        
        logger.info(f"Inference complete in {inference_time:.2f}s")
        logger.info(f"Volumes: WT={volumes['wt_ml']:.2f}mL, "
                   f"TC={volumes['tc_ml']:.2f}mL, ET={volumes['et_ml']:.2f}mL")
        
        return InferenceResult(
            segmentation=label_map,
            affine=affine,
            volumes_ml=volumes,
            inference_time_sec=inference_time,
            device_used=self.device
        )
    
    def _preprocess_case(
        self,
        t1ce_path: Path,
        t1_path: Path,
        t2_path: Path,
        flair_path: Path
    ) -> Tuple[torch.Tensor, np.ndarray]:
        """
        Load and preprocess 4 modality images.
        
        Returns:
            (input_tensor, affine) where tensor is (1, 4, H, W, D)
        """
        # Stack in model's expected order: T1ce, T1, T2, FLAIR
        modality_paths = [str(t1ce_path), str(t1_path), str(t2_path), str(flair_path)]
        
        data = {"image": modality_paths}
        processed = self.preprocess(data)
        
        # Get affine from first modality
        img_nib = nib.load(t1ce_path)
        affine = img_nib.affine
        
        # Add batch dimension: (4, H, W, D) -> (1, 4, H, W, D)
        input_tensor = processed["image"].unsqueeze(0)
        
        logger.info(f"Input shape: {input_tensor.shape}, affine: {affine.shape}")
        
        return input_tensor, affine
    
    def _run_model_inference(self, input_tensor: torch.Tensor) -> np.ndarray:
        """
        Run sliding window inference.
        
        Args:
            input_tensor: (1, 4, H, W, D) tensor
            
        Returns:
            region_masks: (3, H, W, D) binary masks for TC, WT, ET
        """
        input_tensor = input_tensor.to(self.device)
        
        with torch.no_grad():
            # Sliding window with same ROI as training
            output = sliding_window_inference(
                inputs=input_tensor,
                roi_size=(240, 240, 160),
                sw_batch_size=1,
                predictor=self.model,
                overlap=0.5
            )
        
        # Convert to binary masks: sigmoid + threshold
        probs = torch.sigmoid(output)
        region_masks = (probs > 0.5).cpu().numpy()[0]  # (3, H, W, D)
        
        logger.info(f"Region mask shape: {region_masks.shape}")
        logger.info(f"TC voxels: {region_masks[0].sum()}, "
                   f"WT voxels: {region_masks[1].sum()}, "
                   f"ET voxels: {region_masks[2].sum()}")
        
        return region_masks
    
    def _convert_regions_to_labels(self, region_masks: np.ndarray) -> np.ndarray:
        """
        Convert MONAI region masks to BraTS 2021 label codes.
        
        Input channels:
        - channel 0: TC (Tumor Core)
        - channel 1: WT (Whole Tumor)
        - channel 2: ET (Enhancing Tumor)
        
        Output labels:
        - Label 0: Background
        - Label 1: NCR (Necrotic Core) = WT ∩ TC ∩ ¬ET
        - Label 2: ED (Edema) = WT ∩ ¬TC
        - Label 4: ET (Enhancing Tumor) = ET channel
        
        Args:
            region_masks: (3, H, W, D) binary region masks
            
        Returns:
            label_map: (H, W, D) with BraTS labels
        """
        tc_mask = region_masks[0].astype(bool)
        wt_mask = region_masks[1].astype(bool)
        et_mask = region_masks[2].astype(bool)
        
        # Initialize with background
        label_map = np.zeros(tc_mask.shape, dtype=np.uint8)
        
        # Label 4: ET (highest priority)
        label_map[et_mask] = 4
        
        # Label 1: NCR = WT ∩ TC ∩ ¬ET
        ncr_mask = wt_mask & tc_mask & ~et_mask
        label_map[ncr_mask] = 1
        
        # Label 2: ED = WT ∩ ¬TC
        ed_mask = wt_mask & ~tc_mask
        label_map[ed_mask] = 2
        
        # Verify no overlaps
        unique_labels = np.unique(label_map)
        logger.info(f"Label map contains: {unique_labels}")
        logger.info(f"Label 1 (NCR) voxels: {(label_map == 1).sum()}")
        logger.info(f"Label 2 (ED) voxels: {(label_map == 2).sum()}")
        logger.info(f"Label 4 (ET) voxels: {(label_map == 4).sum()}")
        
        return label_map
    
    def save_segmentation(
        self,
        result: InferenceResult,
        output_path: Path
    ):
        """
        Save segmentation to NIfTI file.
        
        Args:
            result: InferenceResult with segmentation and affine
            output_path: Where to save .nii.gz file
        """
        nii = nib.Nifti1Image(result.segmentation, result.affine)
        nib.save(nii, output_path)
        logger.info(f"Saved segmentation to {output_path}")