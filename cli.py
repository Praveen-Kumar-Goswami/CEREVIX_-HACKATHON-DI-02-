"""
Command-Line Interface for NeuroScope 3D
Standalone inference for automated evaluation/scoring.

Usage:
    python cli.py --t1 path/to/t1.nii.gz \
                  --t1ce path/to/t1ce.nii.gz \
                  --t2 path/to/t2.nii.gz \
                  --flair path/to/flair.nii.gz \
                  --output path/to/prediction.nii.gz

Output:
    NIfTI file with BraTS 2021 labels (1=NCR, 2=ED, 4=ET)
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.inference_service import BraTSInferenceService
import nibabel as nib
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='NeuroScope 3D - CLI Inference for BraTS Segmentation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic inference
    python cli.py --t1 t1.nii.gz --t1ce t1ce.nii.gz --t2 t2.nii.gz --flair flair.nii.gz --output pred.nii.gz
    
    # Specify model path
    python cli.py --t1 t1.nii.gz --t1ce t1ce.nii.gz --t2 t2.nii.gz --flair flair.nii.gz --output pred.nii.gz --model models/model.pt

Output Format:
    NIfTI file with BraTS 2021 labels:
    - 0: Background
    - 1: NCR (necrotic tumor core)
    - 2: ED (peritumoral edema)
    - 4: ET (enhancing tumor)
        """
    )
    
    # Required arguments
    parser.add_argument('--t1', type=str, required=True, help='Path to T1 weighted NIfTI file')
    parser.add_argument('--t1ce', type=str, required=True, help='Path to T1 contrast-enhanced NIfTI file')
    parser.add_argument('--t2', type=str, required=True, help='Path to T2 weighted NIfTI file')
    parser.add_argument('--flair', type=str, required=True, help='Path to FLAIR NIfTI file')
    parser.add_argument('--output', type=str, required=True, help='Path for output prediction NIfTI file')
    
    # Optional arguments
    parser.add_argument('--model', type=str, 
                        default='models/brats_mri_segmentation/models/model.pt',
                        help='Path to model weights (default: models/brats_mri_segmentation/models/model.pt)')
    parser.add_argument('--device', type=str, choices=['cuda', 'cpu', 'auto'], default='auto',
                        help='Device to use for inference (default: auto)')
    
    args = parser.parse_args()
    
    # Validate input files exist
    for modality, path_str in [('T1', args.t1), ('T1ce', args.t1ce), ('T2', args.t2), ('FLAIR', args.flair)]:
        path = Path(path_str)
        if not path.exists():
            logger.error(f"{modality} file not found: {path}")
            return 1
    
    # Validate model exists
    model_path = Path(args.model)
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return 1
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize inference service
        logger.info(f"Loading model from {model_path}")
        inference_service = BraTSInferenceService(model_path)
        logger.info(f"Using device: {inference_service.device}")
        
        # Run inference
        logger.info("Running inference...")
        result = inference_service.run_inference(
            t1ce_path=Path(args.t1ce),
            t1_path=Path(args.t1),
            t2_path=Path(args.t2),
            flair_path=Path(args.flair)
        )
        
        # Save prediction
        logger.info(f"Saving prediction to {output_path}")
        nii = nib.Nifti1Image(result.segmentation.astype('uint8'), result.affine)
        nib.save(nii, output_path)
        
        # Report results
        logger.info(f"Inference complete in {result.inference_time_sec:.2f}s")
        logger.info(f"Volumes: WT={result.volumes_ml.get('WT', 0):.2f}mL, "
                   f"TC={result.volumes_ml.get('TC', 0):.2f}mL, "
                   f"ET={result.volumes_ml.get('ET', 0):.2f}mL")
        logger.info(f"Output saved: {output_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Inference failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
