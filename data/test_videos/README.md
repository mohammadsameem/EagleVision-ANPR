# Test Videos Directory

This directory contains test video files for validating the EagleVision ANPR system.

## Files

### Downloaded Test Videos

*Videos downloaded from public sources for testing purposes only. Not to be committed to Git.*

#### traffic_park_720p.mp4
- **Source:** [SampleLib.com](https://samplelib.com/sample-mp4.html)
- **Original URL:** https://samplelib.com/lib/preview/mp4/sample-5s.mp4
- **License:** No license restrictions (per SampleLib website)
- **Description:** Stream of vehicles passing by a park
- **Downloaded:** 2026-10-28
- **Specifications:**
  - Resolution: 1920x1080 (Full HD)
  - Duration: 5.70 seconds
  - Frame count: 171 frames
  - FPS: 30
  - File size: 2.72 MB
- **Content validation:**
  - Avg pixel mean: 83.56 (good visibility)
  - Avg pixel std: 81.68 (good contrast)
  - YOLOv8 detections: 19 vehicles across 5 sampled frames (16 cars, 2 trucks, 1 bus)
  - Detection confidence: 0.252-0.840 (mean 0.489)

---

## Video Sources and Licenses

### SampleLib
- Website: https://samplelib.com/sample-mp4.html
- License: "Sample videos available for download with no license restrictions"
- Content: Various test video clips including traffic footage
- Compliance: Rephrased for licensing compliance - original states videos have no license restrictions

## Usage Guidelines

1. Test videos are for validation only and should not be committed to the repository
2. Add `data/test_videos/*.mp4` to `.gitignore`
3. Document all downloaded videos with source URL and license information
4. Validate each video before use (resolution, FPS, content quality)
5. Run YOLOv8 detection tests to verify vehicle visibility

## Validation Results

All videos in this directory have been validated using `scripts/validate_test_video.py` and tested with YOLOv8 detection via `scripts/test_yolo_detection.py`.
