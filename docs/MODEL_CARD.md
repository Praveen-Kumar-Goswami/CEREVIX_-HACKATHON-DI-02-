# Model Card: NeuroScope 3D - Brain Tumor Segmentation

## Model Identity

**Model Name:** MONAI BraTS MRI Segmentation (SegResNet)  
**Version:** Pre-trained weights from MONAI Model Zoo  
**Model Hash (SHA-256):** `computed from model.pt file`  
**Source:** [MONAI Model Zoo - brats_mri_segmentation](https://github.com/Project-MONAI/model-zoo/tree/dev/models/brats_mri_segmentation)  
**License:** Apache License 2.0  
**Architecture:** SegResNet (Residual Encoder-Decoder)

---

## Training Data

**Dataset:** BraTS 2018 (Brain Tumor Segmentation Challenge 2018)  
**Training Set Size:** 285 cases  
**Data Source:** Multi institutional collaboration  
**Modalities Used:** 4-channel input (T1ce, T1, T2, FLAIR)  
**Ground Truth:** Expert annotations of tumor regions

**⚠️ DATA PROVENANCE RISK:**  
This model was trained on BraTS 2018. Available evaluation datasets (BraTS 2019, 2020, 2021) may contain:
- Overlapping patients from BraTS 2018 training set
- Related scans from the same patients
- Data from the same institutions

**Implication:** Reported evaluation metrics may be optimistically biased due to data leakage. True generalization performance on completely independent data is UNKNOWN.

---

## Model Inputs

**Format:** NIfTI (.nii, .nii.gz)  
**Dimensions:** 3D volumes (H × W × D)  
**Channels:** 4 modalities in specific order:
1. **T1ce** (T1-weighted with gadolinium contrast enhancement)
2. **T1** (T1-weighted)
3. **T2** (T2-weighted)
4. **FLAIR** (Fluid-attenuated inversion recovery)

**Preprocessing (Applied by Inference Pipeline):**
- Load with NiBabel
- Ensure channel-first format
- Intensity normalization (0-1 range)
- Convert to PyTorch tensor (float32)

**Expected Voxel Spacing:** Typically 1mm isotropic, but model handles anisotropic voxels  
**Coordinate System:** RAS+ (Right-Anterior-Superior with millimeter units)

---

## Model Outputs

**Format:** 3-channel probability maps (internally), converted to BraTS 2021 labels  
**Output Channels (Model):**
- Channel 0: TC (Tumor Core) probability
- Channel 1: WT (Whole Tumor) probability
- Channel 2: ET (Enhancing Tumor) probability

**Output Labels (Post-processed):**
- **Label 0:** Background
- **Label 1:** NCR (Necrotic/Non-enhancing Tumor Core)
- **Label 2:** ED (Peritumoral Edema)
- **Label 4:** ET (GD-Enhancing Tumor)

**Conversion Logic:**
```
Label 4 (ET) = ET channel (threshold > 0.5)
Label 1 (NCR) = WT ∩ TC ∩ ¬ET
Label 2 (ED) = WT ∩ ¬TC
Label 0 (Background) = everything else
```

**Spatial Information:** Output inherits input affine matrix (preserves orientation and spacing)

---

## Inference Configuration

**Inference Method:** Sliding window with overlap  
**Window Size:** 240 × 240 × 160 voxels  
**Overlap:** 50%  
**Batch Size:** 1 (per window)  
**Post-processing:**
- Sigmoid activation
- Threshold at 0.5 for binary masks
- Hierarchical label conversion (TC/WT/ET → 1/2/4)

**Device:** CUDA (GPU) preferred, CPU fallback available  
**Inference Time:** ~16-20 seconds per case (128³ volume on RTX 4050 6GB)

---

## Evaluation Results

### Test Set Composition

**Source:** Synthetic test data generated for development  
**Number of Cases:** INSUFFICIENT (<10 cases)  
**Patient Diversity:** NOT APPLICABLE (synthetic data)

⚠️ **EVALUATION LIMITATION:**  
No evaluation on real held-out BraTS data has been performed. Metrics reported below are on **synthetic test cases only** and do **NOT** reflect real-world performance.

### Metrics (Synthetic Data Only - NOT CLINICALLY VALIDATED)

**Regions Evaluated:**
- **WT (Whole Tumor):** All tumor labels combined
- **TC (Tumor Core):** NCR + Enhancing tumor
- **ET (Enhancing Tumor):** Gadolinium enhancement only

**Metrics Computed:**
- **Dice Coefficient:** 2|A∩B| / (|A| + |B|)
- **Sensitivity (Recall):** |A∩B| / |B|

**Results:** NOT REPORTED - Insufficient real evaluation data

---

## Known Limitations

### Technical Limitations

1. **Training Data Age:** Model trained on BraTS 2018 (2018 dataset)
2. **Single Architecture:** No ensemble, single model only
3. **No Uncertainty Quantification:** Model provides point predictions without confidence scores
4. **Fixed Window Size:** 240×240×160 may not be optimal for all anatomies
5. **Binary Thresholding:** Simple 0.5 threshold, no adaptive thresholding

### Clinical Limitations

1. **NOT FOR CLINICAL USE:** This is a research tool only
2. **No FDA Approval:** Not cleared for diagnostic use
3. **No Clinical Validation:** Performance on clinical cohorts UNKNOWN
4. **Expert Review Required:** All segmentations must be reviewed by qualified radiologists
5. **Population Bias:** Training data may not represent all demographics/scanners/protocols

### Data Limitations

1. **Scanner Variability:** Performance on different MRI scanners UNKNOWN
2. **Protocol Sensitivity:** Assumes standard BraTS acquisition protocols
3. **Artifact Handling:** Behavior on motion artifacts, metal artifacts, etc. NOT CHARACTERIZED
4. **Rare Tumor Types:** Performance on atypical presentations UNKNOWN

### Evaluation Limitations

1. **NO REAL EVALUATION DATA:** System tested only on synthetic data
2. **Data Leakage Risk:** Cannot verify independence from BraTS 2018 training set
3. **Generalization Unknown:** Performance on new patients/institutions NOT MEASURED

---

## Intended Use

**Primary Use Case:** Research and educational tool for brain tumor segmentation  
**User Audience:** Researchers, students, healthcare professionals in research settings  
**Appropriate Context:**
- Algorithm development and comparison
- Educational demonstrations
- Research studies with proper oversight
- Proof-of-concept applications

**Decision Support Level:** NONE - Not intended for diagnostic decisions

---

## Prohibited Uses

❌ **Clinical diagnosis or treatment planning**  
❌ **Unsupervised automated reporting**  
❌ **Regulatory submissions without validation**  
❌ **Commercial diagnostic products**  
❌ **Any use without expert radiologist review**  
❌ **Populations not represented in BraTS 2018**  
❌ **Life-critical applications**

---

## Ethical Considerations

### Bias and Fairness

**Training Data Demographics:** NOT DISCLOSED in BraTS 2018 documentation  
**Potential Biases:**
- Geographic bias (multi-institutional but limited)
- Scanner manufacturer bias
- Acquisition protocol bias
- Socioeconomic bias (if present in original data)

**Mitigation:** Unknown - no fairness analysis performed

### Privacy and Security

**Patient Data:** Model does not store patient data  
**Inference Privacy:** Cases processed locally, no external transmission  
**De-identification:** Users responsible for proper de-identification of inputs

---

## Model Maintenance

**Updates:** None planned - using pre-trained weights as-is  
**Retraining:** Not performed  
**Fine-tuning:** Not performed  
**Version Control:** Tracked via git commit hash

---

## Contact and Feedback

**Project:** NeuroScope 3D (24-hour hackathon project)  
**Purpose:** Educational demonstration of ML deployment  
**Feedback:** Not applicable (hackathon demonstration)

---

## References

1. MONAI Model Zoo: https://github.com/Project-MONAI/model-zoo
2. BraTS 2018: https://www.med.upenn.edu/sbia/brats2018.html
3. SegResNet: Myronenko, A. (2018). "3D MRI brain tumor segmentation using autoencoder regularization."

---

**Last Updated:** 2026-10-16  
**Model Card Version:** 1.0  
**Compliance:** Research use only - NOT FOR CLINICAL DIAGNOSIS

---

## Appendix: Metric Definitions

### Dice Coefficient
```
Dice = 2 × |Prediction ∩ Ground Truth| / (|Prediction| + |Ground Truth|)
```
**Range:** [0, 1], higher is better  
**Interpretation:** Overlap agreement between prediction and expert annotation

### Sensitivity (Recall)
```
Sensitivity = |Prediction ∩ Ground Truth| / |Ground Truth|
```
**Range:** [0, 1], higher is better  
**Interpretation:** Proportion of ground truth voxels correctly identified

### Edge Cases
- **Both empty:** Dice and Sensitivity reported as NaN (undefined)
- **Only GT empty:** Dice = 0.0, Sensitivity = NaN
- **Only prediction empty:** Dice = 0.0, Sensitivity = 0.0

---

**⚠️ IMPORTANT:** This model card acknowledges significant gaps in evaluation and clinical validation. The model is provided AS-IS for research purposes only.