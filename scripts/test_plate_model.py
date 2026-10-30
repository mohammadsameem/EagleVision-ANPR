"""Test plate detection model loading and basic inference."""
import sys
from pathlib import Path

try:
    from ultralytics import YOLO
    import cv2
    import numpy as np
    print("[OK] Dependencies loaded")
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    sys.exit(1)

def test_model_loading():
    """Test that the plate detection model loads correctly."""
    print("\n" + "="*70)
    print("PLATE DETECTION MODEL TEST")
    print("="*70)
    
    model_path = "models/plate_detector.pt"
    
    # Check file exists
    if not Path(model_path).exists():
        print(f"[ERROR] Model file not found: {model_path}")
        return False
    
    file_size = Path(model_path).stat().st_size / (1024 * 1024)
    print(f"Model file: {model_path}")
    print(f"File size: {file_size:.2f} MB")
    print()
    
    # Load model
    try:
        print("Loading model...")
        model = YOLO(model_path)
        print("[OK] Model loaded successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        return False
    
    # Get model info
    try:
        print()
        print("Model Information:")
        print(f"  Task: {model.task}")
        print(f"  Names: {model.names}")
        print(f"  Model type: {type(model.model).__name__}")
        print()
    except Exception as e:
        print(f"[WARNING] Could not extract model info: {e}")
    
    # Test inference on dummy image
    try:
        print("Testing inference on dummy 640x640 image...")
        dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)
        results = model(dummy_image, verbose=False)
        print(f"[OK] Inference successful")
        print(f"  Results type: {type(results)}")
        print(f"  Number of results: {len(results)}")
        if results and results[0].boxes is not None:
            print(f"  Detections: {len(results[0].boxes)}")
        else:
            print(f"  Detections: 0 (expected for blank image)")
        print()
    except Exception as e:
        print(f"[ERROR] Inference failed: {e}")
        return False
    
    print("="*70)
    print("[SUCCESS] Plate detection model is ready")
    print("="*70)
    return True

if __name__ == "__main__":
    success = test_model_loading()
    sys.exit(0 if success else 1)
