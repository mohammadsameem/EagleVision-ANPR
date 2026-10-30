"""
Download and verify license plate detection model.

This script should be updated once a specific model is selected.
"""
import os
import sys
from pathlib import Path

def download_plate_model():
    """Download plate detection model weights"""
    
    print("="*60)
    print("License Plate Detection Model Download")
    print("="*60)
    
    print("\n⚠️  Model selection not yet finalized")
    print("\nPlease:")
    print("1. Research available license plate detection models")
    print("2. Verify licensing (GPL, MIT, Apache, etc.)")
    print("3. Update this script with download URL and checksum")
    print("4. Download and place in models/ directory")
    
    print("\nRecommended sources:")
    print("- Ultralytics Hub: https://hub.ultralytics.com/")
    print("- HuggingFace: https://huggingface.co/models?search=license+plate")
    print("- RoboFlow: https://universe.roboflow.com/")
    
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # Check if any .pt files already exist
    existing_models = list(models_dir.glob("*.pt"))
    if existing_models:
        print(f"\n✓ Found existing models:")
        for model in existing_models:
            size_mb = model.stat().st_size / (1024*1024)
            print(f"  - {model.name} ({size_mb:.1f} MB)")
    
    print("\n" + "="*60)
    return False

if __name__ == "__main__":
    success = download_plate_model()
    sys.exit(0 if success else 1)
