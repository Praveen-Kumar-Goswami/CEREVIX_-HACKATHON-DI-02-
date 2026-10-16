# 3D Brain Visualization - NeuroScope 3D

## Overview
Added volumetric 3D brain visualization for tumor segmentation results using Three.js.

## Files Added
- **frontend/3d-brain-viewer.html** - Standalone 3D volumetric brain viewer
- Integration button added to main UI

## Features

### 3D Visualization
- **Anatomical cortex** - Simplified brain surface with displacement mapping
- **Three tumor regions**:
  - 🔴 Enhancing Tumor (ET) - Red, innermost
  - 🟢 Tumor Core (TC/NCR) - Green, middle layer
  - 🔵 Edema (ED) - Blue, outermost layer
- **Interactive controls** - Orbit, pan, zoom with mouse
- **Layer toggles** - Show/hide each anatomical region
- **Opacity sliders** - Adjust transparency of cortex and tumors

### Camera Presets
- Front, Back, Left, Right, Top, Bottom views
- Auto-rotate mode
- Reset to default view

### Data Integration
- **Load from API** - Fetches segmentation results using case ID
- **Volume display** - Shows WT, TC, ET volumes in mL
- **Dynamic sizing** - Tumor regions scale based on actual volumes from inference
- **Manual positioning** - X, Y, Z sliders for demonstration purposes

## Usage

### From Main Interface
1. Upload and process MRI scans normally
2. After inference completes, click **"🧠 View in 3D Brain Model"** button
3. Opens in new window with segmentation data pre-loaded

### Direct Access
Open rontend/3d-brain-viewer.html?case_id=YOUR_CASE_ID with a valid case ID

### API Integration
Fetches data from: GET /api/report/{case_id}

Expected JSON structure:
```json
{
  "volumes_ml": {
    "wt_ml": 45.2,
    "tc_ml": 28.1,
    "et_ml": 12.3
  }
}
```

## Technical Details

### Three.js Rendering
- **Engine**: Three.js r128
- **Renderer**: WebGL with antialiasing
- **Lighting**: Ambient + directional lights
- **Materials**: Phong shading with transparency
- **Geometry**: Sphere primitives with displacement noise

### Tumor Size Calculation
Radius calculated from volume using sphere formula:
```javascript
radius = (volume_ml * 3 / (4 * π))^(1/3) * 10  // Scale factor applied
```

### Performance
- 60 FPS rendering
- Low polygon count for real-time interaction
- Responsive design (fullscreen canvas)

## Limitations

### Current Implementation
- **Simplified anatomy** - Uses sphere with noise, not anatomically accurate
- **Approximate positioning** - Tumor position is manually adjustable, not derived from actual NIfTI coordinates
- **No real mesh import** - Does not parse actual segmentation masks for 3D reconstruction

### Future Enhancements
- Import actual segmentation masks as meshes (marching cubes)
- Use anatomically accurate brain models (e.g., from MNI152 templates)
- Calculate tumor centroid from actual voxel data
- Add ventricles, corpus callosum, cerebellum layers
- Surgical probe/planning tools
- Slice plane visualization integrated with 3D model

## Screenshots / Demo

### View Modes
- **Surgical Glass** - High cortex transparency to see internal tumors
- **Standard** - Balanced visibility
- **Isolated Tumor** - Hide cortex to see tumor regions only

### Typical Workflow
1. Process MRI in main interface → Get case ID
2. Click "View in 3D" → Opens volumetric viewer
3. Interact with camera → Examine tumor from all angles
4. Toggle layers → Understand tumor composition
5. Export screenshots or data as needed

## Compliance

**Disclaimer**: Same as main interface
- ⚠️ RESEARCH USE ONLY
- Not for clinical diagnosis
- AI-generated predictions
- Educational purposes

## Browser Support
- Chrome/Edge (recommended)
- Firefox
- Safari (WebGL required)

## Integration Status
✅ Functional proof-of-concept  
⚠️ Not part of core hackathon submission (post-submission enhancement)  
📋 Can be included as "bonus feature" in final presentation

---

**Created**: 2026-10-17 00:00:50
