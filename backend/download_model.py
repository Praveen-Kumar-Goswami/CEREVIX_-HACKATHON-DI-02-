"""
Download MONAI BraTS MRI Segmentation Bundle
"""
import os
from monai.bundle import download

# Create models directory
os.makedirs("../models", exist_ok=True)

# Download the bundle
bundle_name = "brats_mri_segmentation"
download_path = "../models"

print(f"Downloading MONAI bundle: {bundle_name}")
print(f"Target directory: {download_path}")

try:
    download(
        name=bundle_name,
        bundle_dir=download_path,
        source="monaihosting",
        progress=True
    )
    print(f"\n✅ Successfully downloaded {bundle_name}")
    print(f"Location: {os.path.abspath(download_path)}/{bundle_name}")
except Exception as e:
    print(f"\n❌ Error downloading bundle: {e}")
    print("\nTrying alternative download method...")
    try:
        from monai.apps import download_url
        url = "https://github.com/Project-MONAI/model-zoo/releases/download/hosting_storage_v1/brats_mri_segmentation_v0.1.0.zip"
        download_url(url=url, filepath=f"{download_path}/brats_mri_segmentation.zip")
        print("Downloaded from GitHub releases")
    except Exception as e2:
        print(f"Alternative download also failed: {e2}")
        raise
