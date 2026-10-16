"""
Environment Verification Script
Checks all dependencies and GPU availability
"""
import sys

def check_python():
    print(f"Python: {sys.version}")
    return True

def check_pytorch():
    try:
        import torch
        print(f"PyTorch: {torch.__version__}")
        print(f"  CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        return True
    except ImportError as e:
        print(f"❌ PyTorch not installed: {e}")
        return False

def check_monai():
    try:
        import monai
        print(f"MONAI: {monai.__version__}")
        return True
    except ImportError as e:
        print(f"❌ MONAI not installed: {e}")
        return False

def check_nibabel():
    try:
        import nibabel as nib
        print(f"NiBabel: {nib.__version__}")
        return True
    except ImportError as e:
        print(f"❌ NiBabel not installed: {e}")
        return False

def check_model():
    import os
    model_path = "../models/brats_mri_segmentation/models/model.pt"
    if os.path.exists(model_path):
        size_mb = os.path.getsize(model_path) / 1024 / 1024
        print(f"Model checkpoint: {model_path} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"❌ Model not found: {model_path}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("NeuroScope 3D - Environment Verification")
    print("="*60)
    
    checks = [
        ("Python", check_python),
        ("PyTorch", check_pytorch),
        ("MONAI", check_monai),
        ("NiBabel", check_nibabel),
        ("Model", check_model),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20} {status}")
    
    all_passed = all(r for _, r in results)
    print("="*60)
    if all_passed:
        print("✅ All checks passed! Environment ready for inference.")
        sys.exit(0)
    else:
        print("❌ Some checks failed. Please install missing dependencies.")
        sys.exit(1)
