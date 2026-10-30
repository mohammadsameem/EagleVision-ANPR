# EagleVision ANPR - Current Blocker Report

**Date:** 2026-10-28  
**Session:** Priority 1 Implementation (Vehicle Detection)  
**Status:** BLOCKED - No Valid Test Data

## Problem

Vehicle detection is now **enabled** (ultralytics 8.3.38 installed, YOLOv8n.pt loaded successfully), but **cannot be verified** due to invalid sample videos.

## Evidence

### Sample Videos Analysis
All three sample videos (`cam-n4.mp4`, `cam-w2.mp4`, `cam-s1.mp4`):
- **File size:** 0.01 MB each (10-11 KB)
- **Format:** Valid MP4 containers (640x360, 24fps, 144 frames, 6s duration)
- **Content issue:** Extremely dark/black frames
  - Mean pixel value: 23-25 (out of 255)
  - Max pixel value: 38-41 (out of 255)
  - Normal outdoor video: mean ~100-150, max 255

### Detection Tests Conducted
1. **Original frames:** 0 detections on first 10 frames of cam-n4.mp4
2. **Brightened frames:** Artificially brightened 5x (mean 24→124), still 0 detections
3. **Synthetic test:** Created test video with white rectangle vehicle, 0 detections (expected - too simple for YOLOv8)

### YOLOv8 Verification
Model loading and inference confirmed working:
```
✓ ultralytics==8.3.38 installed
✓ yolov8n.pt downloaded (6.25 MB)
✓ Model loads without errors
✓ Inference runs on frames (no crashes)
✓ Returns results objects correctly
```

## Conclusion

The sample videos appear to be **placeholder files** - valid MP4 containers with no meaningful visual content. YOLOv8 cannot detect vehicles in near-black frames or synthetic geometric shapes.

## Options to Unblock

### Option 1: Download Real Test Video (RECOMMENDED)
Download CCTV traffic footage from public sources:
- [Vecteezy free traffic CCTV videos](https://www.vecteezy.com/free-videos/traffic-cctv)
- [SampleLib MP4 samples](https://samplelib.com/sample-mp4.html)
- GitHub repos with test footage (requires investigation)

**Pros:** Immediate validation of full pipeline with real vehicles/plates  
**Cons:** May require manual download/selection

### Option 2: Use Public Dataset
Use established ANPR datasets:
- Car Plate Detection dataset (mentioned in GitHub projects)
- TVC dataset (traffic videos, requires access request)
- D2-City dataset (DiDi platform, Chinese traffic)

**Pros:** Ground truth annotations available  
**Cons:** Larger downloads, may require registration

### Option 3: Record/Obtain Real Footage
Record CCTV footage from local traffic camera or dashcam.

**Pros:** Custom test scenarios  
**Cons:** Time-consuming, requires physical access

### Option 4: Continue with Heuristic Testing
Proceed with development using heuristic plate detection (no vehicle detection validation).

**Pros:** No external dependencies  
**Cons:** Cannot verify vehicle detection works; defeats purpose of Priority 1

## Recommendation

**Immediate:** Download a single short (5-10s) traffic video from Vecteezy or similar free source to validate that:
1. YOLOv8 detects vehicles (cars, trucks, motorcycles)
2. Vehicle bboxes are extracted correctly
3. Heuristic plate detection can crop plate regions
4. OCR can read text from plate crops

**Once validated:** Request user guidance on sourcing larger test dataset or proceeding with current capabilities.

## Current Capabilities (Verified)

| Component | Status | Evidence |
|-----------|--------|----------|
| Environment | ✓ Working | Python 3.14.0, pip functional |
| Dependencies | ✓ Installed | ultralytics, easyocr, opencv-python, torch |
| Video Processing | ✓ Working | Extracts frames, preserves timestamps |
| YOLOv8 Loading | ✓ Working | Model loads, inference runs |
| YOLOv8 Detection | ? Unknown | No valid test data |
| Plate Detection | ✓ Working | Heuristic fallback implemented |
| OCR (EasyOCR) | ✓ Working | Tested in isolation |
| Full Pipeline | ? Unknown | No valid test data |

## Files Created This Session

- `scripts/inspect_video.py` - Video file analysis tool
- `scripts/test_vehicle_detection.py` - YOLOv8 detection verification
- `scripts/create_test_video.py` - Synthetic video generator
- `public/videos/test_vehicle.mp4` - Synthetic test video (not suitable for real detection)
- `public/videos/cam-n4_first_frame.jpg` - Extracted dark frame
- `public/videos/cam-n4_brightened.jpg` - Artificially brightened frame

## Next Steps (Pending User Decision)

1. **If user provides video:** Test immediately with full pipeline
2. **If user approves download:** Fetch free sample from Vecteezy
3. **If blocked on test data:** Skip to Priority 2 (plate detection model selection) or Priority 3 (FPS sampler fixes)
