"""
MONAI BraTS Segmentation - Simple Inference CLI
Loads model and performs inference on 4-modality MRI case.

Model details (verified from bundle config):
- Architecture: SegResNet
- Input: 4 channels (order: T1c/T1Gd, T1, T2, FLAIR)
- Output: 3 channels (probabilities for TC, WT, ET regions)
- Trained on: BraTS 2018
- License: Apache 2.0 (MONAI)
"""

import os
import sys
import time
import torch
import nibabel as nib
import numpy as np
from pathlib import Path

# Add bundle to path
bundle_root = Path(__file__).parent.parent / "models" / "brats_mri_segmentation"
sys.path.insert(0, str(bundle_root / "scripts"))

from monai.networks.nets import SegResNet
from monai.inferers import sliding_window_inference
from monai.transforms import (
    Compose, LoadImaged, NormalizeIntensityd, ToTensord, 
    Activationsd, AsDiscreted
)

def load_model(device='cuda'):
    """Load pretrained SegResNet model"""
    print("Loading SegResNet model...")
    model = SegResNet(
        blocks_down=[1, 2, 2, 4],
        blocks_up=[1, 1, 1],
        init_filters=16,
        in_channels=4,
        out_channels=3,
        dropout_prob=0.2
    )
    
    model_path = bundle_root / "models" / "model.pt"
    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint)
    model = model.to(device)
    model.eval()
    print(f"✅ Model loaded from {model_path}")
    return model

def preprocess(t1c_path, t1_path, t2_path, flair_path):
    """
    Load and preprocess 4 modality images.
    Input order matches model training: T1c, T1, T2, FLAIR
    """
    print("\nPreprocessing inputs...")
    print(f"  T1c: {t1c_path}")
    print(f"  T1: {t1_path}")
    print(f"  T2: {t2_path}")
    print(f"  FLAIR: {flair_path}")
    
    # Load images
    transforms = Compose([
        LoadImaged(keys="image"),
        NormalizeIntensityd(keys="image", nonzero=True, channel_wise=True),
        ToTensord(keys="image")
    ])
    
    # Stack in correct order
    data = {"image": [t1c_path, t1_path, t2_path, flair_path]}
    processed = transforms(data)
    
    # Get original affine from first modality for later
    img_nib = nib.load(t1c_path)
    original_affine = img_nib.affine
    original_shape = img_nib.shape
    
    print(f"✅ Loaded images - shape: {processed['image'].shape}")
    print(f"  Original affine shape: {original_affine.shape}")
    
    return processed['image'].unsqueeze(0), original_affine, original_shape

def run_inference(model, input_tensor, device='cuda'):
    """Run sliding window inference"""
    print("\nRunning inference...")
    start_time = time.time()
    
    input_tensor = input_tensor.to(device)
    
    with torch.no_grad():
        # Sliding window inference with same ROI size as training
        output = sliding_window_inference(
            inputs=input_tensor,
            roi_size=(240, 240, 160),
            sw_batch_size=1,
            predictor=model,
            overlap=0.5
        )
    
    elapsed = time.time() - start_time
    print(f"✅ Inference complete in {elapsed:.2f} seconds")
    
    return output, elapsed

def postprocess_output(output):
    """
    Convert model output to binary masks.
    Output channels: 0=TC, 1=WT, 2=ET (as probabilities)
    """
    print("\nPost-processing...")
    
    # Apply sigmoid and threshold
    probs = torch.sigmoid(output)
    masks = (probs > 0.5).cpu().numpy()[0]  # Shape: (3, H, W, D)
    
    print(f"  Output shape: {masks.shape}")
    print(f"  TC voxels: {masks[0].sum()}")
    print(f"  WT voxels: {masks[1].sum()}")
    print(f"  ET voxels: {masks[2].sum()}")
    
    return masks

def save_prediction(masks, original_affine, output_path):
    """
    Save segmentation mask as NIfTI.
    Note: This saves the 3-channel probability output, NOT BraTS label codes yet.
    """
    print(f"\nSaving prediction to {output_path}...")
    
    # For now, save as 3-channel output
    # TODO: Convert to BraTS 2021 labels (1=NCR, 2=ED, 4=ET) in later stage
    nii = nib.Nifti1Image(masks.astype(np.uint8), original_affine)
    nib.save(nii, output_path)
    print(f"✅ Saved: {output_path}")

def main():
    if len(sys.argv) < 6:
        print("Usage: python inference.py <t1c> <t1> <t2> <flair> <output>")
        print("\nExample:")
        print("  python inference.py case001_t1ce.nii.gz case001_t1.nii.gz case001_t2.nii.gz case001_flair.nii.gz output.nii.gz")
        sys.exit(1)
    
    t1c_path = sys.argv[1]
    t1_path = sys.argv[2]
    t2_path = sys.argv[3]
    flair_path = sys.argv[4]
    output_path = sys.argv[5]
    
    # Check files exist
    for p in [t1c_path, t1_path, t2_path, flair_path]:
        if not os.path.exists(p):
            print(f"❌ Error: File not found: {p}")
            sys.exit(1)
    
    # Check GPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if device == 'cuda':
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        print("WARNING: Running on CPU (will be slow)")
    
    # Load model
    model = load_model(device)
    
    # Preprocess
    input_tensor, original_affine, original_shape = preprocess(
        t1c_path, t1_path, t2_path, flair_path
    )
    
    # Inference
    output, elapsed_time = run_inference(model, input_tensor, device)
    
    # Postprocess
    masks = postprocess_output(output)
    
    # Save
    save_prediction(masks, original_affine, output_path)
    
    print(f"\n{'='*60}")
    print("INFERENCE SUMMARY")
    print(f"{'='*60}")
    print(f"Inference time: {elapsed_time:.2f} seconds")
    print(f"Device: {device}")
    print(f"Output shape: {masks.shape}")
    print(f"Output affine: {original_affine.shape}")
    print(f"\n⚠️  NOTE: Output is 3-channel (TC/WT/ET regions)")
    print(f"    Conversion to BraTS 2021 labels (1/2/4) needed in next stage")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
