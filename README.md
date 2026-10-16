# NeuroScope 3D

**Brain MRI Tumor Segmentation Platform** for Research & Teaching  
Hackathon Track DI-02

> ⚠️ **Research Prototype Only**  
> This system is for research and teaching purposes. Predictions are not validated for clinical use and must not be used for diagnosis or treatment decisions.

---

## Quick Start

### Prerequisites

- **Python:** 3.11.x
- **GPU:** NVIDIA with 6GB+ VRAM and CUDA 12.1+
- **Disk Space:** 2 GB (model + dependencies)

### Installation

1. **Clone repository:**
\\\powershell
git clone <repo-url>
cd NeuroScope3D
\\\

2. **Install Python dependencies:**
\\\powershell
cd backend
pip install -r requirements.txt
\\\

3. **Download MONAI model bundle:**
\\\powershell
python download_model.py
\\\

4. **Verify environment:**
\\\powershell
python verify_environment.py
\\\

You should see:
\\\
✅ All checks passed! Environment ready for inference.
\\\

---

## Usage

### Run Inference

\\\powershell
python inference.py <t1ce> <t1> <t2> <flair> <output>
\\\

**Example:**
\\\powershell
python inference.py 
  case001_t1ce.nii.gz 
  case001_t1.nii.gz 
  case001_t2.nii.gz 
  case001_flair.nii.gz 
  prediction.nii.gz
\\\

**Input Requirements:**
- 4 co-registered NIfTI files (.nii or .nii.gz)
- Order: T1ce (T1 with contrast/Gd), T1, T2, FLAIR
- Skull-stripped brain MRI (as per BraTS standard)
- Isotropic 1mm spacing preferred

**Output:**
- 3-channel NIfTI (TC, WT, ET region masks)
- ⚠️ Note: Conversion to BraTS 2021 labels (1/2/4) in progress

---

## Model Details

**Architecture:** SegResNet (3D)  
**Training Data:** BraTS 2018 (285 volumes)  
**License:** Apache 2.0  
**Validation Dice:** TC=0.86, WT=0.90, ET=0.79 (avg 0.85)

**Input Channels:** 4 (T1ce, T1, T2, FLAIR)  
**Output Channels:** 3 (TC, WT, ET regions)

See docs/MODEL_VERIFICATION.md for complete specifications.

---

## Project Structure

\\\
NeuroScope3D/
├── backend/
│   ├── inference.py              # Inference CLI
│   ├── download_model.py         # Model download script
│   ├── verify_environment.py     # Environment check
│   └── requirements.txt          # Python dependencies
├── models/
│   └── brats_mri_segmentation/   # MONAI bundle (17.97 MB)
├── data/                         # Input/output data (gitignored)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── MODEL_VERIFICATION.md
│   ├── PROJECT_PROGRESS.md
│   └── ...
└── README.md                     # This file
\\\

---

## Development Status

**Current Prompt:** 2 of 10 ✅ COMPLETE  
**Status:** Environment verified, model ready, inference CLI implemented  
**Next:** Test on real BraTS case (Prompt 3)

See docs/PROJECT_PROGRESS.md for detailed progress tracking.

---

## Environment

**Verified Configuration:**
- Python 3.11.9
- PyTorch 2.5.1+cu121
- CUDA 12.1
- MONAI 1.6.1
- NiBabel 5.4.2
- GPU: NVIDIA GeForce RTX 4050 (6 GB)

---

## Data Sources

**Training Data:** BraTS 2018  
**Test Data:** Public BraTS datasets (for evaluation)  
**License:** Data usage follows BraTS challenge terms

**Public BraTS Access:**
- BraTS 2021: https://www.synapse.org/#!Synapse:syn25829067
- BraTS 2018: https://www.med.upenn.edu/sbia/brats2018/data.html

---

## Citation

If you use this code, please cite:

\\\ibtex
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

## License

**Code:** TBD (will be specified)  
**Model:** Apache 2.0 (MONAI)  
**Data:** BraTS challenge terms

---

## Disclaimer

This is a research prototype developed for a hackathon. It is NOT:
- ❌ A clinical diagnostic tool
- ❌ FDA approved or clinically validated
- ❌ Suitable for patient care decisions

All predictions must be reviewed by qualified medical professionals.

---

**Last Updated:** 2026-10-16  
**Contact:** [To be added]
