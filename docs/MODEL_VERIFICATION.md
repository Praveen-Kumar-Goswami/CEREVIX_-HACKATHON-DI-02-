# MONAI BraTS Segmentation Bundle - Verified Details

**Version:** 0.1.0  
**Date Verified:** 2026-10-16  
**Verified By:** Repository inspection and config parsing

---

## Model Overview

**Name:** brats_mri_segmentation  
**Source:** MONAI Model Zoo  
**Architecture:** SegResNet (3D)  
**Training Data:** BraTS 2018 (285 volumes, 200 train / 42 val / 43 test)  
**License:** Apache 2.0 (MONAI Project)  
**Model File:** model.pt (17.97 MB)  
**TorchScript:** model.ts (18.04 MB) - available but not used

---

## Input Specification (VERIFIED)

**Number of Channels:** 4  
**Channel Order:** T1c (T1Gd), T1, T2, FLAIR  
**Expected Resolution:** 1×1×1 mm (isotropic)  
**Input Size (Training):** 224×224×144 (cropped from full volume)  
**Input Size (Inference):** Variable (sliding window with ROI 240×240×160)

### Preprocessing (from configs/inference.json):
1. LoadImaged - Load NIfTI files
2. NormalizeIntensityd - Normalize to zero mean, unit std (nonzero=true, channel_wise=true)
3. ToTensord - Convert to PyTorch tensor

**CRITICAL:** Input order is **T1c/T1Gd, T1, T2, FLAIR** (verified in bundle README)

---

## Output Specification (VERIFIED)

**Number of Channels:** 3  
**Output Type:** Probabilities (before sigmoid/threshold)  
**Channel Semantics (from docs/README.md):**
- **Channel 0:** TC (Tumor Core) = NCR + ET
- **Channel 1:** WT (Whole Tumor) = NCR + ED + ET
- **Channel 2:** ET (Enhancing Tumor)

### Postprocessing (from configs/inference.json):
1. Activationsd - Sigmoid activation
2. AsDiscreted - Threshold at 0.5 to get binary masks
3. Invertd - Resample to original input grid/affine

**⚠️ IMPORTANT FINDING:**  
The model outputs **region masks** (TC, WT, ET), NOT the BraTS component labels.  
**Required conversion to BraTS 2021 labels:**
- Label 1 (NCR): WT AND TC AND NOT ET
- Label 2 (ED): WT AND NOT TC
- Label 4 (ET): ET channel

This conversion must be implemented in the next stage to meet judge requirements.

---

## Network Architecture

\\\python
SegResNet(
    blocks_down=[1, 2, 2, 4],
    blocks_up=[1, 1, 1],
    init_filters=16,
    in_channels=4,
    out_channels=3,
    dropout_prob=0.2
)
\\\

**Parameters:** ~18 MB  
**Inference Mode:** eval() with torch.no_grad()  
**AMP Support:** Yes (automatic mixed precision)

---

## Performance (from bundle docs)

**Validation Dice Scores (BraTS 2018 val set):**
- Tumor Core (TC): 0.8559
- Whole Tumor (WT): 0.9026
- Enhancing Tumor (ET): 0.7905
- **Average: 0.8518**

**Training Configuration:**
- GPU Memory Required: 16GB minimum (training)
- Optimizer: Adam
- Learning Rate: 1e-4
- Loss: DiceLoss
- Augmentation: Random crop, flip, intensity scaling/shifting

---

## Inference Configuration

**Sliding Window Parameters:**
- ROI Size: (240, 240, 160)
- Batch Size: 1
- Overlap: 0.5
- Mode: Gaussian importance weighting

**Device:** CUDA preferred (verified working on RTX 4050 6GB)  
**Determinism:** Set torch.backends.cudnn.benchmark=True in original config (may affect reproducibility)

---

## License & Attribution

**MONAI Framework:** Apache License 2.0  
**Model:** Apache License 2.0  
**Training Data:** BraTS 2018 (publicly available for research)  
**Reference Paper:** Myronenko, A. "3D MRI brain tumor segmentation using autoencoder regularization." MICCAI Brainlesion Workshop 2018.

**Citation:**
\\\
@article{myronenko20183d,
  title={3D MRI brain tumor segmentation using autoencoder regularization},
  author={Myronenko, Andriy},
  journal={International MICCAI Brainlesion Workshop},
  pages={311--320},
  year={2018},
  publisher={Springer}
}
\\\

---

## Verified Facts

✅ Bundle downloaded and extracted successfully  
✅ Model checkpoint loaded (model.pt - 17.97 MB)  
✅ Configuration files parsed and semantics documented  
✅ Input channel order verified: T1c, T1, T2, FLAIR  
✅ Output channel semantics documented: TC, WT, ET regions  
✅ Preprocessing pipeline documented  
✅ License verified: Apache 2.0  
✅ Training data source: BraTS 2018

---

## Known Limitations & TODOs

⚠️ **Output Format Issue:**  
Model outputs 3-channel region masks, not BraTS 2021 label codes.  
**Required:** Implement region-to-label conversion in next stage:
- Derive NCR (label 1) from WT ∩ TC ∩ ¬ET
- Derive ED (label 2) from WT ∩ ¬TC
- Map ET channel directly to label 4

⚠️ **Skull-Stripping:**  
Model assumes skull-stripped input (trained on BraTS which is skull-stripped).  
Must validate or warn users about non-skull-stripped inputs.

⚠️ **Determinism:**  
Original config sets cudnn.benchmark=True which may cause slight variations.  
For reproducibility testing, should set benchmark=False and fix all seeds.

---

**Status:** Model bundle verified and ready for integration  
**Next Steps:** Create label conversion logic, test on sample case, implement deterministic inference
