"""
NIfTI Validation Service
Robust validation of uploaded brain MRI NIfTI files for BraTS segmentation.

Safety features:
- Size limits (1 GB per file)
- Header integrity checks
- 3D volume verification
- Finite value checks
- Shape/affine compatibility
- Clear error messages
- No external service calls
"""

import os
import hashlib
import nibabel as nib
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class ModalityType(Enum):
    """Required MRI modalities for BraTS"""
    T1 = "t1"
    T1CE = "t1ce"  # T1 with Gadolinium contrast
    T2 = "t2"
    FLAIR = "flair"

@dataclass
class ValidationResult:
    """Result of NIfTI validation"""
    is_valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

@dataclass
class NIfTIMetadata:
    """Metadata extracted from validated NIfTI"""
    filename: str
    modality: ModalityType
    shape: Tuple[int, int, int]
    affine: np.ndarray
    voxel_spacing: Tuple[float, float, float]
    data_dtype: str
    sha256: str
    file_size_bytes: int

class NIfTIValidator:
    """Validates NIfTI files for BraTS segmentation pipeline"""
    
    MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB
    AFFINE_TOLERANCE = 0.01  # Tolerance for affine matrix comparison
    
    def __init__(self):
        self.validated_files: Dict[ModalityType, NIfTIMetadata] = {}
    
    def validate_file_size(self, filepath: Path) -> ValidationResult:
        """Check file size before attempting to load"""
        try:
            size = os.path.getsize(filepath)
            if size > self.MAX_FILE_SIZE_BYTES:
                size_gb = size / (1024**3)
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File exceeds 1 GB size limit ({size_gb:.2f} GB)"
                )
            return ValidationResult(is_valid=True)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Cannot access file: {str(e)}"
            )
    
    def validate_nifti_format(self, filepath: Path) -> Tuple[ValidationResult, Optional[nib.Nifti1Image]]:
        """Validate NIfTI file can be loaded and has valid header"""
        try:
            # Attempt to load
            img = nib.load(str(filepath))
            
            # Verify it's actually a NIfTI format we support
            if not isinstance(img, (nib.Nifti1Image, nib.Nifti2Image)):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File is not a valid NIfTI format (got {type(img).__name__})"
                ), None
            
            return ValidationResult(is_valid=True), img
            
        except nib.filebasedimages.ImageFileError as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"File is corrupted or unreadable: {str(e)}"
            ), None
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Cannot read NIfTI file: {str(e)}"
            ), None
    
    def validate_3d_volume(self, img: nib.Nifti1Image) -> ValidationResult:
        """Ensure image is 3D (not 2D or 4D)"""
        shape = img.shape
        
        if len(shape) < 3:
            return ValidationResult(
                is_valid=False,
                error_message=f"File must be a 3D volume (found {len(shape)}D with shape {shape})"
            )
        
        if len(shape) > 3:
            # Check if extra dimensions are singleton
            if len(shape) == 4 and shape[3] == 1:
                # 4D with singleton time dimension is acceptable
                warnings = ["File has singleton 4th dimension (will be squeezed)"]
                return ValidationResult(is_valid=True, warnings=warnings)
            else:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File must be a 3D volume (found {len(shape)}D with shape {shape})"
                )
        
        # Check for degenerate dimensions
        if any(d <= 1 for d in shape[:3]):
            return ValidationResult(
                is_valid=False,
                error_message=f"Volume has degenerate dimensions: {shape}"
            )
        
        return ValidationResult(is_valid=True)
    
    def validate_data_integrity(self, img: nib.Nifti1Image) -> ValidationResult:
        """Check for NaN, Inf, constant, and all-zero data"""
        try:
            # Load data (this is memory-intensive, so we do it carefully)
            data = img.get_fdata(dtype=np.float32)
            
            # Check for non-finite values
            if not np.all(np.isfinite(data)):
                nan_count = np.sum(np.isnan(data))
                inf_count = np.sum(np.isinf(data))
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File contains non-finite voxel values (NaN: {nan_count}, Inf: {inf_count})"
                )
            
            # Check for all-zero
            if np.all(data == 0):
                return ValidationResult(
                    is_valid=False,
                    error_message="File contains only zero values (no signal)"
                )
            
            # Check for constant values
            if np.min(data) == np.max(data):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File contains only constant values ({np.min(data)})"
                )
            
            # Warn if mostly zero (possible skull-stripping issue)
            zero_fraction = np.sum(data == 0) / data.size
            warnings = []
            if zero_fraction > 0.95:
                warnings.append(f"Warning: {zero_fraction*100:.1f}% of voxels are zero (check skull-stripping)")
            
            return ValidationResult(is_valid=True, warnings=warnings)
            
        except MemoryError:
            return ValidationResult(
                is_valid=False,
                error_message="Insufficient memory to load volume (file may be too large)"
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Error reading voxel data: {str(e)}"
            )
    
    def compute_sha256(self, filepath: Path) -> str:
        """Compute SHA-256 hash of file for provenance"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def validate_single_file(
        self, 
        filepath: Path, 
        modality: ModalityType
    ) -> Tuple[ValidationResult, Optional[NIfTIMetadata]]:
        """Complete validation pipeline for a single NIfTI file"""
        
        # 1. Check file size
        result = self.validate_file_size(filepath)
        if not result.is_valid:
            return result, None
        
        # 2. Check NIfTI format
        result, img = self.validate_nifti_format(filepath)
        if not result.is_valid or img is None:
            return result, None
        
        # 3. Check 3D volume
        result = self.validate_3d_volume(img)
        if not result.is_valid:
            return result, None
        all_warnings = result.warnings.copy()
        
        # 4. Check data integrity
        result = self.validate_data_integrity(img)
        if not result.is_valid:
            return result, None
        all_warnings.extend(result.warnings)
        
        # 5. Extract metadata
        shape = img.shape[:3]  # Take only first 3 dimensions
        affine = img.affine
        header = img.header
        voxel_spacing = tuple(header.get_zooms()[:3])
        
        # 6. Compute SHA-256
        sha256 = self.compute_sha256(filepath)
        
        metadata = NIfTIMetadata(
            filename=filepath.name,
            modality=modality,
            shape=shape,
            affine=affine,
            voxel_spacing=voxel_spacing,
            data_dtype=str(img.get_data_dtype()),
            sha256=sha256,
            file_size_bytes=os.path.getsize(filepath)
        )
        
        return ValidationResult(is_valid=True, warnings=all_warnings), metadata
    
    def validate_shape_compatibility(self) -> ValidationResult:
        """Ensure all four modalities have the same shape"""
        if len(self.validated_files) < 4:
            return ValidationResult(
                is_valid=False,
                error_message=f"Need 4 modalities, got {len(self.validated_files)}"
            )
        
        shapes = [meta.shape for meta in self.validated_files.values()]
        reference_shape = shapes[0]
        
        for modality, meta in self.validated_files.items():
            if meta.shape != reference_shape:
                return ValidationResult(
                    is_valid=False,
                    error_message=(
                        f"Modality files have incompatible shapes:\\n"
                        f"  Reference (T1): {reference_shape}\\n"
                        f"  {modality.value}: {meta.shape}"
                    )
                )
        
        return ValidationResult(is_valid=True)
    
    def validate_affine_compatibility(self) -> ValidationResult:
        """Ensure all four modalities have compatible affine matrices"""
        if len(self.validated_files) < 4:
            return ValidationResult(
                is_valid=False,
                error_message=f"Need 4 modalities, got {len(self.validated_files)}"
            )
        
        affines = {mod: meta.affine for mod, meta in self.validated_files.items()}
        reference_modality = ModalityType.T1
        reference_affine = affines[reference_modality]
        
        for modality, affine in affines.items():
            if modality == reference_modality:
                continue
            
            # Check if affines are close (within tolerance)
            max_diff = np.max(np.abs(affine - reference_affine))
            if max_diff > self.AFFINE_TOLERANCE:
                return ValidationResult(
                    is_valid=False,
                    error_message=(
                        f"Modality files have incompatible spatial transforms:\\n"
                        f"  Maximum affine difference: {max_diff:.6f} (tolerance: {self.AFFINE_TOLERANCE})\\n"
                        f"  Mismatch between {reference_modality.value} and {modality.value}"
                    )
                )
        
        return ValidationResult(is_valid=True)
    
    def validate_four_modalities(
        self,
        file_paths: Dict[ModalityType, Path]
    ) -> Tuple[ValidationResult, Dict[ModalityType, NIfTIMetadata]]:
        """
        Validate all four required modalities.
        
        Args:
            file_paths: Dictionary mapping modality type to file path
            
        Returns:
            Tuple of (ValidationResult, metadata dict if valid)
        """
        # Check we have exactly 4 modalities
        required = set(ModalityType)
        provided = set(file_paths.keys())
        
        if provided != required:
            missing = required - provided
            extra = provided - required
            error_parts = []
            if missing:
                error_parts.append(f"Missing modalities: {', '.join(m.value for m in missing)}")
            if extra:
                error_parts.append(f"Extra modalities: {', '.join(m.value for m in extra)}")
            return ValidationResult(
                is_valid=False,
                error_message=f"Incorrect modalities provided. {' '.join(error_parts)}"
            ), {}
        
        # Validate each file individually
        self.validated_files = {}
        all_warnings = []
        
        for modality, filepath in file_paths.items():
            if not filepath.exists():
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File not found: {filepath}"
                ), {}
            
            result, metadata = self.validate_single_file(filepath, modality)
            
            if not result.is_valid:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"[{modality.value}] {result.error_message}"
                ), {}
            
            self.validated_files[modality] = metadata
            all_warnings.extend([f"[{modality.value}] {w}" for w in result.warnings])
        
        # Cross-validate: check shape compatibility
        result = self.validate_shape_compatibility()
        if not result.is_valid:
            return result, {}
        
        # Cross-validate: check affine compatibility
        result = self.validate_affine_compatibility()
        if not result.is_valid:
            return result, {}
        
        return ValidationResult(is_valid=True, warnings=all_warnings), self.validated_files
    
    def validate_expert_mask(
        self,
        mask_path: Path,
        reference_metadata: NIfTIMetadata
    ) -> Tuple[ValidationResult, Optional[NIfTIMetadata]]:
        """
        Validate optional expert segmentation mask.
        
        Expected labels: 1 (NCR), 2 (ED), 4 (ET) per BraTS 2021
        """
        # File size check
        result = self.validate_file_size(mask_path)
        if not result.is_valid:
            return result, None
        
        # NIfTI format check
        result, img = self.validate_nifti_format(mask_path)
        if not result.is_valid or img is None:
            return result, None
        
        # 3D volume check
        result = self.validate_3d_volume(img)
        if not result.is_valid:
            return result, None
        
        # Shape compatibility with input modalities
        shape = img.shape[:3]
        if shape != reference_metadata.shape:
            return ValidationResult(
                is_valid=False,
                error_message=f"Expert mask shape {shape} does not match input shape {reference_metadata.shape}"
            ), None
        
        # Affine compatibility
        max_diff = np.max(np.abs(img.affine - reference_metadata.affine))
        if max_diff > self.AFFINE_TOLERANCE:
            return ValidationResult(
                is_valid=False,
                error_message=f"Expert mask has incompatible spatial transform (max diff: {max_diff:.6f})"
            ), None
        
        # Check labels are valid BraTS 2021 codes
        data = img.get_fdata(dtype=np.float32)
        unique_labels = np.unique(data)
        allowed_labels = {0, 1, 2, 4}  # Background + NCR + ED + ET
        
        invalid_labels = set(unique_labels) - allowed_labels
        if invalid_labels:
            return ValidationResult(
                is_valid=False,
                error_message=f"Expert mask contains invalid labels: {invalid_labels}. Allowed: {allowed_labels}"
            ), None
        
        # Create metadata
        sha256 = self.compute_sha256(mask_path)
        metadata = NIfTIMetadata(
            filename=mask_path.name,
            modality=ModalityType.T1,  # Placeholder, not actually a modality
            shape=shape,
            affine=img.affine,
            voxel_spacing=tuple(img.header.get_zooms()[:3]),
            data_dtype=str(img.get_data_dtype()),
            sha256=sha256,
            file_size_bytes=os.path.getsize(mask_path)
        )
        
        return ValidationResult(is_valid=True), metadata

def check_skull_stripped(img: nib.Nifti1Image) -> Tuple[bool, str]:
    """
    Heuristic check if brain appears skull-stripped.
    
    Returns:
        (is_likely_skull_stripped, warning_message)
    
    Note: This is a HEURISTIC, not clinically validated.
    """
    data = img.get_fdata(dtype=np.float32)
    
    # Check 1: Edge voxels should be mostly zero in skull-stripped images
    edge_thickness = 5
    edges = np.concatenate([
        data[:edge_thickness, :, :].flatten(),
        data[-edge_thickness:, :, :].flatten(),
        data[:, :edge_thickness, :].flatten(),
        data[:, -edge_thickness:, :].flatten(),
        data[:, :, :edge_thickness].flatten(),
        data[:, :, -edge_thickness:].flatten()
    ])
    
    edge_nonzero_fraction = np.count_nonzero(edges) / len(edges)
    
    # Skull-stripped images typically have <5% nonzero edge voxels
    if edge_nonzero_fraction > 0.20:
        return False, (
            f"Warning: Input may not be skull-stripped ({edge_nonzero_fraction*100:.1f}% nonzero edge voxels). "
            "Model trained on skull-stripped BraTS data; results may be unreliable."
        )
    
    return True, ""
