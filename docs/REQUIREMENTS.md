# Requirements Document

## Introduction

NeuroScope 3D is a research and teaching web platform for brain MRI tumor segmentation visualization. The system accepts four co-registered 3D brain MRI NIfTI volumes (T1, T1Gd, T2, FLAIR), applies a pretrained deep learning segmentation model, and presents comprehensive visualization with axial/coronal/sagittal slice views, spatially correct 3D rendering, volumetric measurements, evaluation metrics, and provenance-rich downloadable reports. This is a research prototype for a 24-hour hackathon (track DI-02) designed to demonstrate accurate spatial computation, robust failure handling, and honest scientific reporting.

## Glossary

- **System**: NeuroScope 3D platform (web application with frontend and backend components)
- **User**: Researcher, educator, or student using the platform for brain MRI tumor segmentation visualization
- **NIfTI**: Neuroimaging Informatics Technology Initiative file format for medical imaging data (.nii or .nii.gz)
- **Modality**: Type of MRI scan (T1, T1Gd, T2, FLAIR)
- **Segmentation_Model**: Pretrained 3D deep learning model (MONAI SegResNet trained on BraTS 2018)
- **BraTS**: Brain Tumor Segmentation challenge dataset and label convention
- **NCR**: Necrotic tumor core (BraTS label 1)
- **ED**: Peritumoral edema (BraTS label 2)
- **ET**: Enhancing tumor (BraTS label 4)
- **WT**: Whole tumor region (NCR + ED + ET)
- **TC**: Tumor core region (NCR + ET)
- **Affine**: 4×4 transformation matrix mapping voxel indices to millimetre world coordinates
- **Voxel**: 3D pixel in medical imaging volume
- **Crosshair**: Spatial cursor synchronized across all visualization views
- **Dice_Score**: Overlap metric for segmentation evaluation (range 0-1, higher is better)
- **Sensitivity**: True positive rate for segmentation evaluation
- **Frontend**: React + TypeScript + Vite web client
- **Backend**: Python + FastAPI inference server
- **Inference**: Process of applying the trained model to new input data
- **Judge**: Hackathon evaluator conducting acceptance tests
- **Held_Out_Cases**: Test cases not used during model training
- **Report**: Generated document containing volumes, metrics, model provenance, and disclaimers
- **Model_Card**: One-page document describing model architecture, training, and limitations

## Requirements

### Requirement 1: Accept Four-Modality NIfTI Input

**User Story:** As a User, I want to upload four co-registered brain MRI NIfTI files with modality identification, so that the System can perform tumor segmentation.

#### Acceptance Criteria

1. THE System SHALL accept four NIfTI files in .nii or .nii.gz format
2. THE System SHALL provide modality selection for each uploaded file (T1, T1Gd, T2, FLAIR)
3. THE System SHALL require exactly one file per modality (T1, T1Gd, T2, FLAIR)
4. WHEN all four modalities are uploaded and identified, THE System SHALL enable the inference submission
5. THE System SHALL compute and store SHA-256 hash for each uploaded file

### Requirement 2: Validate Input Files

**User Story:** As a User, I want the System to validate my uploaded files, so that I receive clear error messages for invalid inputs rather than crashes or incorrect results.

#### Acceptance Criteria

1. WHEN a file cannot be read as valid NIfTI, THE System SHALL reject the file with message "File [name] is not a valid NIfTI file"
2. WHEN a file contains fewer than three spatial dimensions, THE System SHALL reject the file with message "File [name] must be a 3D volume (found [N] dimensions)"
3. WHEN a file contains non-finite voxel values (NaN or Inf), THE System SHALL reject the file with message "File [name] contains non-finite voxel values"
4. WHEN a file contains only constant or all-zero voxel values, THE System SHALL reject the file with message "File [name] contains constant or all-zero data"
5. WHEN a file exceeds 1 GB in size, THE System SHALL reject the file with message "File [name] exceeds 1 GB size limit"
6. WHEN the four modality files have incompatible spatial shapes, THE System SHALL reject the set with message "Modality files have incompatible shapes: T1=[shape], T1Gd=[shape], T2=[shape], FLAIR=[shape]"
7. WHEN the four modality files have incompatible affine matrices (differ by more than 0.01 in any element), THE System SHALL reject the set with message "Modality files have incompatible spatial transforms"
8. WHEN validation fails, THE System SHALL not proceed to inference
9. WHEN validation fails, THE System SHALL not crash or show stack traces to the User

### Requirement 3: Accept Optional Expert Segmentation Mask

**User Story:** As a User, I want to optionally upload an expert segmentation mask, so that the System can evaluate prediction accuracy against ground truth.

#### Acceptance Criteria

1. THE System SHALL accept an optional fifth NIfTI file as expert segmentation mask
2. THE System SHALL interpret expert mask labels as 1=NCR, 2=ED, 4=ET following BraTS 2021 convention
3. WHEN an expert mask is provided with incompatible shape or affine, THE System SHALL reject the mask with message "Expert mask has incompatible shape or spatial transform"
4. WHEN an expert mask is provided, THE System SHALL compute Dice_Score and Sensitivity for WT, TC, and ET regions
5. WHEN no expert mask is provided, THE System SHALL skip case-specific evaluation and proceed with inference

### Requirement 4: Execute 3D Segmentation Inference

**User Story:** As a User, I want the System to apply a pretrained deep learning model to my MRI scans, so that I can visualize suspected tumor regions.

#### Acceptance Criteria

1. THE System SHALL use MONAI Model Zoo brats_mri_segmentation SegResNet model
2. THE System SHALL preprocess inputs in the order required by the model (T1Gd, T1, T2, FLAIR)
3. THE System SHALL execute inference on GPU if available
4. THE System SHALL produce a segmentation mask on the original input grid and affine
5. THE System SHALL output segmentation labels using BraTS 2021 convention (1=NCR, 2=ED, 4=ET)
6. THE System SHALL provide a CLI command or API endpoint that accepts four input file paths and one output path for Judge scoring
7. WHEN inference completes, THE System SHALL store the prediction mask with timestamp
8. THE System SHALL complete inference within 2 minutes on T4-class GPU hardware

### Requirement 5: Construct Hierarchical Tumor Regions

**User Story:** As a User, I want the System to construct whole tumor, tumor core, and enhancing tumor regions, so that I can visualize and measure each region separately.

#### Acceptance Criteria

1. THE System SHALL construct WT region as the union of all voxels with labels 1, 2, or 4
2. THE System SHALL construct TC region as the union of all voxels with labels 1 or 4
3. THE System SHALL construct ET region as all voxels with label 4
4. THE System SHALL preserve the subset relationship ET ⊆ TC ⊆ WT in the output masks
5. WHEN constructing regions, THE System SHALL verify that every voxel in ET appears in TC
6. WHEN constructing regions, THE System SHALL verify that every voxel in TC appears in WT

### Requirement 6: Render 3D Brain and Region Meshes

**User Story:** As a User, I want to see 3D surface renderings of the brain and tumor regions in millimetre world space, so that I can understand spatial relationships and anatomical context.

#### Acceptance Criteria

1. THE System SHALL display the brain surface as a 3D mesh in millimetre world coordinates
2. THE System SHALL display WT, TC, and ET regions as separate 3D meshes in millimetre world coordinates
3. THE System SHALL apply the NIfTI affine transformation to position all meshes in the same world coordinate system
4. THE System SHALL enable rotation of the 3D view with mouse drag
5. THE System SHALL enable zoom of the 3D view with mouse wheel
6. THE System SHALL provide toggle controls to show or hide each region mesh (WT, TC, ET)
7. THE System SHALL provide opacity sliders to adjust transparency of each region mesh
8. THE System SHALL use distinct colors for WT (green), TC (blue), and ET (yellow) regions

### Requirement 7: Display Linked Orthogonal Slice Views

**User Story:** As a User, I want to see axial, coronal, and sagittal slice views with segmentation overlays and anatomical orientation labels, so that I can inspect the segmentation in detail across all three planes.

#### Acceptance Criteria

1. THE System SHALL display axial, coronal, and sagittal slice views side by side
2. THE System SHALL overlay segmentation masks on each slice view with color-coded regions
3. THE System SHALL display anatomical orientation labels: Left/Right, Anterior/Posterior, Superior/Inferior
4. THE System SHALL display a crosshair on all three slice views
5. WHEN the User clicks on any slice view, THE System SHALL update the crosshair position in all three slice views
6. WHEN the User clicks on any slice view, THE System SHALL update the 3D view camera focus to the crosshair position
7. THE System SHALL display voxel indices (i, j, k) at the crosshair position
8. THE System SHALL display world coordinates in millimetres (x, y, z) at the crosshair position
9. THE System SHALL synchronize crosshair positions across all views within 2 voxels
10. THE System SHALL enable slice scrolling with mouse wheel or slider controls

### Requirement 8: Calculate and Display Region Volumes

**User Story:** As a User, I want the System to calculate and display tumor region volumes in millilitres using correct spatial metadata, so that I can quantify tumor burden accurately.

#### Acceptance Criteria

1. THE System SHALL calculate volume in mL using the formula: (voxel_count × voxel_volume_mm³) / 1000
2. THE System SHALL compute voxel_volume_mm³ from the determinant of the affine matrix 3×3 spatial component
3. THE System SHALL display the volume calculation formula on the interface
4. THE System SHALL display voxel_count for each region (WT, TC, ET)
5. THE System SHALL display voxel_volume_mm³ used in the calculation
6. THE System SHALL display the final volume in mL for each region (WT, TC, ET)
7. THE System SHALL round displayed volumes to one decimal place
8. WHEN the User views the 20×20×20 synthetic test cube labelled 2 at 1×1×2 mm spacing, THE System SHALL report WT volume between 15.84 and 16.16 mL

### Requirement 9: Evaluate Segmentation Accuracy

**User Story:** As a User, I want the System to evaluate segmentation accuracy on held-out labelled cases, so that I can assess model performance honestly.

#### Acceptance Criteria

1. THE System SHALL evaluate Dice_Score per region (WT, TC, ET) on at least ten held-out labelled cases
2. THE System SHALL evaluate Sensitivity per region (WT, TC, ET) on at least ten held-out labelled cases
3. THE System SHALL split held-out cases by patient to prevent data leakage
4. THE System SHALL document the held-out case patient IDs in the Report
5. THE System SHALL disclose any possible overlap between held-out cases and Segmentation_Model training data
6. THE System SHALL display mean Dice_Score and Sensitivity with standard deviation for each region
7. THE System SHALL never display fabricated or placeholder evaluation scores

### Requirement 10: Handle Invalid Inputs Safely

**User Story:** As a User, I want the System to fail safely for invalid, broken, or unsupported inputs, so that I do not receive misleading results or experience crashes.

#### Acceptance Criteria

1. WHEN the User uploads a corrupted NIfTI file, THE System SHALL display error message "File [name] is corrupted or unreadable"
2. WHEN the User uploads a 2D or 4D volume, THE System SHALL display error message "File [name] must be a 3D volume"
3. WHEN the User uploads files with mismatched spatial dimensions, THE System SHALL display error message "Input files have incompatible shapes"
4. WHEN the User uploads a file containing NaN values, THE System SHALL display error message "File [name] contains invalid voxel values"
5. WHEN the User uploads an all-zero volume, THE System SHALL display error message "File [name] contains no signal"
6. WHEN the User uploads a file larger than 1 GB, THE System SHALL display error message "File [name] exceeds size limit"
7. WHEN the User uploads files with mismatched affine matrices, THE System SHALL display error message "Input files have incompatible spatial transforms"
8. WHEN the User uploads a clearly non-skull-stripped brain MRI, THE System SHALL display warning message "Warning: Input appears to contain skull tissue; segmentation is designed for skull-stripped brain MRI only"
9. WHEN any validation error occurs, THE System SHALL not proceed to inference
10. WHEN any error occurs, THE System SHALL not crash or display stack traces to the User

### Requirement 11: Prevent Stale or Fabricated Predictions

**User Story:** As a User, I want the System to ensure I never see stale or fabricated segmentation results, so that I can trust the predictions correspond to my uploaded inputs.

#### Acceptance Criteria

1. WHEN new inputs are uploaded, THE System SHALL clear any previous prediction results from the display
2. WHEN inference is in progress, THE System SHALL display a loading indicator and disable result viewing
3. WHEN inference completes, THE System SHALL display only the current prediction corresponding to the uploaded inputs
4. THE System SHALL never display cached predictions from different inputs
5. THE System SHALL never display synthetic or placeholder segmentation masks as real predictions
6. WHEN inputs are modified or replaced, THE System SHALL re-run inference before displaying results

### Requirement 12: Generate Provenance-Rich Report

**User Story:** As a User, I want the System to generate a comprehensive report with volumes, metrics, model provenance, and disclaimers, so that I can document and share results with full transparency.

#### Acceptance Criteria

1. THE System SHALL generate a Report page or PDF for each completed case
2. THE Report SHALL include calculated volumes in mL for WT, TC, and ET regions
3. THE Report SHALL include evaluation metrics (Dice_Score, Sensitivity) if an expert mask was provided
4. THE Report SHALL include Segmentation_Model name, version, and license (SegResNet, BraTS 2018, Apache-2.0)
5. THE Report SHALL include preprocessing steps applied (skull stripping requirement, intensity normalization)
6. THE Report SHALL include SHA-256 hash for each input file
7. THE Report SHALL include code repository commit hash if available
8. THE Report SHALL include timestamp of inference execution
9. THE Report SHALL include limitations section stating "Research prototype only; not validated for clinical use"
10. THE Report SHALL include disclaimer stating "Predictions represent suspected tumor regions estimated by the model and require expert radiologist review"
11. THE Report SHALL be downloadable in PDF format

### Requirement 13: Display Disclaimer on Every Screen

**User Story:** As a User, I want to see a clear disclaimer on every screen, so that I understand this is a research tool and not a clinical diagnostic system.

#### Acceptance Criteria

1. THE System SHALL display the disclaimer "Research prototype only - not for clinical use" on every page
2. THE System SHALL display the disclaimer "Suspected tumor regions predicted by model - requires expert review" on result pages
3. THE System SHALL not use the term "tumor detected" in the interface
4. THE System SHALL not use the term "diagnostic system" in the interface
5. THE System SHALL not claim to "replace the radiologist" in the interface
6. THE System SHALL use the term "suspected tumor region" when referring to predictions
7. THE System SHALL use the term "estimated volume" when referring to volumetric measurements

### Requirement 14: Meet Performance Requirements

**User Story:** As a User, I want the System to complete segmentation quickly, so that I can iterate efficiently during research and teaching sessions.

#### Acceptance Criteria

1. THE System SHALL complete a case from upload to Report generation within 2 minutes on T4-class GPU
2. THE System SHALL measure actual inference time and display it in the Report
3. WHEN inference exceeds 2 minutes, THE System SHALL log a warning
4. THE System SHALL execute inference on GPU if available
5. THE System SHALL fall back to CPU inference if GPU is unavailable

### Requirement 15: Automatically Delete Uploads

**User Story:** As a User, I want the System to automatically delete my uploaded files after 24 hours, so that my data does not persist indefinitely on the server.

#### Acceptance Criteria

1. THE System SHALL store uploaded files in a temporary directory
2. THE System SHALL tag each uploaded file with a creation timestamp
3. THE System SHALL run a background cleanup process every hour
4. WHEN a file has existed for more than 24 hours, THE System SHALL delete it automatically
5. THE System SHALL delete both input files and prediction outputs after 24 hours

### Requirement 16: Provide Complete Deployment Package

**User Story:** As a Judge, I want to receive a complete deployment package with documentation and sample outputs, so that I can evaluate the submission efficiently.

#### Acceptance Criteria

1. THE System SHALL provide a README file with installation and startup instructions
2. THE System SHALL provide exactly one startup command to launch the application
3. THE System SHALL provide one real sample Report generated from actual inference
4. THE System SHALL provide a one-page Model_Card describing the Segmentation_Model
5. THE System SHALL provide five-minute demo and viva presentation materials

### Requirement 17: Pass Geometric Accuracy Tests

**User Story:** As a Judge, I want to verify the System calculates volumes and coordinates correctly, so that I can confirm spatial accuracy.

#### Acceptance Criteria

1. WHEN the Judge provides a 20×20×20 cube labelled 2 at 1×1×2 mm spacing, THE System SHALL report WT volume within 1% of 16.0 mL (15.84-16.16 mL)
2. WHEN the Judge provides a 20×20×20 cube, THE System SHALL report TC volume as 0.0 mL
3. WHEN the Judge provides a 20×20×20 cube, THE System SHALL report ET volume as 0.0 mL
4. WHEN the Judge provides an anisotropic case and a downsampled version, THE System SHALL report WT volumes differing by 10% or less
5. WHEN the Judge flips voxel data left-right with matching affine update, THE System SHALL report the same anatomical side label and WT volume within 2%
6. WHEN the Judge mirrors anatomical data without changing the affine, THE System SHALL show the tumor on the opposite labelled side

### Requirement 18: Pass Crosshair Synchronization Test

**User Story:** As a Judge, I want to verify that the crosshair synchronizes correctly across all views, so that I can confirm spatial consistency.

#### Acceptance Criteria

1. WHEN the Judge clicks on the axial slice view, THE System SHALL update the coronal and sagittal crosshairs within 2 voxels
2. WHEN the Judge clicks on the coronal slice view, THE System SHALL update the axial and sagittal crosshairs within 2 voxels
3. WHEN the Judge clicks on the sagittal slice view, THE System SHALL update the axial and coronal crosshairs within 2 voxels
4. WHEN the Judge clicks on any slice view, THE System SHALL update the 3D view camera focus to the crosshair position

### Requirement 19: Pass Failure Handling Tests

**User Story:** As a Judge, I want to verify that the System handles all failure cases gracefully, so that I can confirm robust error handling.

#### Acceptance Criteria

1. WHEN the Judge uploads a corrupted NIfTI file, THE System SHALL display a clear error message without crashing
2. WHEN the Judge uploads a 2D image, THE System SHALL display a clear error message without crashing
3. WHEN the Judge uploads files with mismatched shapes, THE System SHALL display a clear error message without crashing
4. WHEN the Judge uploads a file with NaN values, THE System SHALL display a clear error message without crashing
5. WHEN the Judge uploads an all-zero volume, THE System SHALL display a clear error message without crashing
6. WHEN the Judge uploads a file over 1 GB, THE System SHALL display a clear error message without crashing
7. WHEN the Judge uploads files with mismatched affines, THE System SHALL display a clear error message without crashing
8. WHEN the Judge uploads a non-skull-stripped brain, THE System SHALL display a warning message

### Requirement 20: Pass Repeatability Test

**User Story:** As a Judge, I want to verify that repeated inference on the same input produces consistent results, so that I can confirm deterministic behavior.

#### Acceptance Criteria

1. WHEN the Judge runs inference twice on identical inputs, THE System SHALL produce prediction masks with Dice_Score of 0.99 or higher
2. WHEN the Judge runs inference twice on identical inputs, THE System SHALL report identical volume measurements

### Requirement 21: Pass Unseen Case Test

**User Story:** As a Judge, I want to verify that the System produces plausible predictions on unseen cases, so that I can confirm the model generalizes.

#### Acceptance Criteria

1. WHEN the Judge provides a blind unseen case, THE System SHALL return a case-specific segmentation mask
2. WHEN the Judge provides a blind unseen case, THE System SHALL not return an empty or all-zero mask
3. WHEN the Judge provides a blind unseen case, THE System SHALL not return a mask identical to previous test cases

### Requirement 22: Provide CLI Inference Interface

**User Story:** As a Judge, I want to run inference from the command line, so that I can score predictions using automated evaluation scripts.

#### Acceptance Criteria

1. THE System SHALL provide a CLI command that accepts paths to four input NIfTI files
2. THE System SHALL accept an output path parameter for the prediction mask
3. WHEN the Judge runs the CLI command, THE System SHALL write the prediction mask to the specified output path
4. THE System SHALL accept modality order as: T1, T1Gd, T2, FLAIR in the CLI command
5. THE System SHALL write the output mask in NIfTI format with BraTS 2021 labels (1, 2, 4)

### Requirement 23: Parse Input Modality Order

**User Story:** As a Developer, I want to verify the Segmentation_Model input modality order, so that preprocessing matches model expectations.

#### Acceptance Criteria

1. THE System SHALL read the MONAI bundle configuration to determine required input modality order
2. THE System SHALL reorder uploaded modalities to match model requirements (T1Gd, T1, T2, FLAIR)
3. WHEN the bundle configuration specifies a different order, THE System SHALL apply that order
4. THE System SHALL log the applied modality order to aid debugging

### Requirement 24: Verify Output Label Semantics

**User Story:** As a Developer, I want to verify the Segmentation_Model output label semantics, so that region construction uses correct labels.

#### Acceptance Criteria

1. THE System SHALL read the MONAI bundle configuration to determine output label meanings
2. THE System SHALL verify that output labels follow BraTS 2021 convention (1=NCR, 2=ED, 4=ET)
3. WHEN the bundle configuration specifies different labels, THE System SHALL map them to BraTS 2021 labels
4. THE System SHALL log the label mapping to aid debugging

### Requirement 25: Prevent External API Upload

**User Story:** As a User, I want assurance that my MRI scans are not uploaded to external APIs, so that patient data privacy is protected.

#### Acceptance Criteria

1. THE System SHALL process all data locally without external API calls
2. THE System SHALL not transmit uploaded files to third-party services
3. THE System SHALL document in the README that all processing is local
4. THE System SHALL use only local GPU or CPU for inference

### Requirement 26: Use De-Identified Research Data Only

**User Story:** As a Developer, I want to ensure only de-identified research data is used for demonstration, so that patient privacy is protected.

#### Acceptance Criteria

1. THE System documentation SHALL state that only public, de-identified research datasets should be used (BraTS 2018, BraTS 2021)
2. THE System SHALL include a sample Report generated from de-identified research data
3. THE System SHALL not include any patient-identifiable information in documentation or sample outputs

### Requirement 27: Pretty Print Configuration and Segmentation Masks

**User Story:** As a Developer, I want to pretty-print MONAI bundle configurations and segmentation masks, so that I can verify model settings and debug predictions.

#### Acceptance Criteria

1. THE System SHALL provide a function to format MONAI bundle configuration as human-readable JSON
2. THE System SHALL provide a function to format segmentation mask statistics (label counts, volumes) as human-readable text
3. WHEN a Developer enables debug mode, THE System SHALL log pretty-printed configuration and mask statistics

### Requirement 28: Round-Trip Parse Configuration

**User Story:** As a Developer, I want to parse MONAI bundle configurations and verify round-trip consistency, so that configuration reading is reliable.

#### Acceptance Criteria

1. THE System SHALL parse the MONAI bundle configuration file into a structured object
2. THE System SHALL serialize the structured object back to JSON format
3. WHEN serialized and re-parsed, THE System SHALL produce an equivalent structured object
4. THE System SHALL validate that critical fields (input order, output labels) are preserved in round-trip

