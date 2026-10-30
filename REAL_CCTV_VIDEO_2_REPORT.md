# EagleVision ANPR - Real CCTV Video 2 Validation Report

**Video**: `WhatsApp Video 2026-10-30 at 6.26.23 AM.mp4`  
**Date**: October 28, 2026  
**Test Scenario**: Vehicle detection, ByteTrack tracking, moving vehicles, front-plate detection and OCR

---

## Executive Summary

Video 2 processing detected **363 vehicles** and **71 license plates** across **84 sampled frames** (5 FPS from 16.77s video). OCR preprocessing was applied to 63/71 plates (88.7%), with **63 plates producing non-empty OCR output (88.7% readable rate)**. However, **actual accuracy cannot be determined without ground truth annotations**.

### Key Findings
- ✅ Vehicle detection highly active (363 detections = 4.32 vehicles/frame)
- ⚠️ **Low plate detection rate: 19.6%** (71 plates from 363 vehicles)
- ✅ OCR preprocessing integration working (88.7% preprocessed)
- ✅ **Better resolution than Video 1** (1152×720 vs 848×478)
- ⚠️ Only 4 frames flagged "unreadable" (4.8%) vs 98.7% in Video 1
- ❌ **No ground truth available - cannot verify OCR correctness**

---

## Video Metadata

| Property | Value |
|----------|-------|
| **Resolution** | 1152×720 pixels |
| **Frame Rate** | 30.00 fps |
| **Duration** | 16.77 seconds |
| **Codec** | h264 |
| **Total Frames** | 503 |
| **Sampled Frames** | 84 (every 6th frame at 5 FPS) |

---

## Detection Results

### Vehicle Detection
- **Total Detections**: 363 vehicles
- **Per-Frame Average**: 4.32 vehicles/frame (83% higher than Video 1)
- **Assessment**: High traffic volume or aggressive detection

### License Plate Detection
- **Total Plates Detected**: 71
- **Plate Detection Rate**: **19.6%** (71/363 vehicles)
- **Per-Frame Average**: 0.85 plates/frame

**⚠️ Critical Finding**: Only 1 in 5 detected vehicles has a visible plate.

### Probable Causes for Low Plate Detection
1. **Front-Facing Vehicles**: Video 2 focuses on moving vehicles approaching camera
   - Front plates may be absent (many regions only require rear plates)
   - Front-angle detection more challenging than rear-angle (Video 1)

2. **Motion Blur**: Moving vehicles at 30 fps may introduce blur
   - Reduces plate detection confidence
   - Degrades OCR input quality

3. **Distance/Scale**: Vehicles may be too far when front-facing
   - Plates smaller in frame when approaching vs passing

4. **Occlusion**: Front plates often partially occluded by bumper design, shadows

---

## OCR Performance

### Preprocessing Statistics
- **Plates Preprocessed**: 63/71 (88.7%)
- **Preprocessing Method**: Lanczos4 upsampling (4× scale)
- **Unreadable Flags**: 4/84 frames flagged (4.8%) - significantly lower than Video 1

### OCR Output
- **Non-Empty OCR Results**: 63/71 plates (88.7% readable output rate)
- **Empty/Failed OCR**: 8/71 plates (11.3%)
- **OCR Engine**: EasyOCR

**⚠️ CRITICAL LIMITATION**: 88.7% represents the rate of non-empty OCR output, NOT accuracy. Without ground truth annotations, we cannot determine how many of these 63 "readable" outputs are correct.

---

## Sample OCR Results

Below are examples of OCR output strings from Video 2. **These have NOT been verified against ground truth**.

```
Frame 0000: "GC-OBL-5I", "AGCOBL5"
Frame 0006: "AN-Y3)T8T", "ANY30R"
Frame 0012: "DPASDLO"
Frame 0018: "OBC 24 C 3004"
Frame 0024: "ANDZODT", "GOAM5"
```

### Observations
- **Higher character counts** than Video 1 (e.g., "OBC 24 C 3004" = 12 chars vs Video 1's 3-6 chars)
- **Format patterns visible**: "XX-XXX-XX" suggests plate format detection working
- **Special characters present**: Hyphens, parentheses indicate OCR detecting structure
- **Garbled outputs still present**: "DPASDLO", "AN-Y3)T8T" unclear if real or errors
- Better resolution (1152×720) may improve OCR quality vs Video 1

---

## Comparison with Video 1

| Metric | Video 1 | Video 2 | Delta |
|--------|---------|---------|-------|
| **Resolution** | 848×478 | 1152×720 | +50% |
| **Vehicles Detected** | 177 | 363 | +105% |
| **Plates Detected** | 149 | 71 | -52% |
| **Plate Detection Rate** | 84.2% | 19.6% | **-64.6%** |
| **Readable OCR Rate** | 82.6% | 88.7% | +6.1% |
| **Unreadable Flags** | 98.7% | 4.8% | -93.9% |

### Key Insights
1. **Better resolution improves OCR quality**:
   - Video 2 has 6.1% higher readable output rate
   - 93.9% fewer "unreadable" flags suggests better input quality

2. **Front-facing detection significantly harder**:
   - 64.6 percentage point drop in plate detection rate
   - Confirms rear-plate scenario (Video 1) more favorable

3. **Motion impacts detection volume**:
   - Moving vehicles generate more detections per frame (4.32 vs 2.36)
   - Likely tracking same vehicles across multiple frames

---

## Annotated Output

All results saved to: `validation_results/cctv_real/video_2/`

### Generated Assets
- **Annotated Frames**: 84 frames with bounding boxes
  - Location: `annotated_frames/frame_XXXX_tYYYYms.jpg`
  - Green boxes: vehicles
  - Blue boxes: license plates
  - Red text: OCR results

- **Plate Crops**: 71 cropped license plate images
  - Location: `plate_crops/frame_XXXX_vXXXX_plate.jpg`
  - Enables manual inspection and ground truth creation

- **Results JSON**: Complete detection data
  - Location: `video_2_results.json`
  - Contains: frame indices, bounding boxes, OCR strings, preprocessing metadata

---

## Issues and Limitations

### 1. No Ground Truth Annotations
**Impact**: Cannot calculate precision, recall, F1-score, accuracy, or character error rate.  
**Resolution Required**: Manual annotation of visible plates in annotated frames.

### 2. Low Plate Detection Rate (19.6%)
**Cause**: Front-facing vehicles combined with motion blur.  
**Impact**: System may miss majority of vehicles in front-camera deployments.  
**Mitigation Options**:
- Deploy cameras at rear-capture angles
- Lower plate detection confidence threshold (risks false positives)
- Train specialized front-plate detection model

### 3. ByteTrack Consolidation Not Tested
**Impact**: Moving vehicles generate multiple detections across frames.  
**Without ByteTrack ID merging**:
- Cannot determine if 363 vehicles = unique vehicles or repeated detections
- Cannot apply confidence voting across multiple OCR readings of same plate
- Inflates detection count artificially

**Requirement**: Implement track ID consolidation to merge detections from same vehicle.

### 4. Motion Blur Not Quantified
**Observation**: Video 2 has moving vehicles at 30 fps.  
**Unknown**: How motion blur impacts OCR accuracy (requires ground truth).  
**Hypothesis**: Lower unreadable flag rate (4.8%) suggests motion blur manageable at 30 fps.

---

## Preprocessing Validation

Video 2 demonstrates improved preprocessing performance compared to Video 1:
- ✅ 88.7% of plates preprocessed successfully
- ✅ Only 4.8% flagged as "unreadable" (vs 98.7% in Video 1)
- ✅ Higher readable output rate (88.7% vs 82.6%)
- ✅ Better resolution (1152×720) provides better preprocessing input

**Assessment**: Higher source resolution significantly improves preprocessing effectiveness.

---

## Production Readiness Assessment

| Component | Status | Confidence |
|-----------|--------|------------|
| Vehicle Detection | ✅ Operational | High |
| Plate Detection (Rear) | ✅ Good (84.2% Video 1) | High |
| Plate Detection (Front) | ⚠️ Poor (19.6% Video 2) | **Low** |
| OCR Preprocessing | ✅ Integrated | Medium |
| OCR Accuracy | ❌ Unverified | **Unknown** |
| ByteTrack Consolidation | ❌ Not Implemented | N/A |

**Overall Assessment**: System performs better on rear-facing scenarios. **Front-plate detection requires optimization** before multi-angle deployment.

---

## Next Steps

### Immediate (Required for Validation)
1. **Create Ground Truth Annotations**
   - Manually inspect annotated frames in `annotated_frames/`
   - Record visible license plate strings
   - Document which vehicles have NO visible plate (expected for front-facing)
   - Suggested sample size: 20-30 frames

2. **Calculate True Accuracy Metrics**
   - Exact-match accuracy (full plate string)
   - Character-level accuracy (Levenshtein distance)
   - Precision and recall for plate detection
   - Separate metrics for front vs rear plates (if distinguishable)

3. **Implement ByteTrack Consolidation**
   - Merge detections from same tracked vehicle across frames
   - Apply confidence voting for final OCR result
   - Measure impact on detection count (363 vehicles → X unique vehicles)

### Optimization (After Ground Truth Available)
4. **Tune Front-Plate Detection**
   - Analyze why 80.4% of vehicles have no plate detected
   - Consider separate model for front-angle plates
   - Evaluate trade-off: lower confidence threshold vs false positive rate

5. **Motion Blur Mitigation**
   - Evaluate frame selection strategies (skip blurred frames)
   - Test higher shutter speed recommendations for camera deployment

6. **Multi-Angle Deployment Strategy**
   - Document optimal camera angles (rear-capture recommended)
   - Define fallback behavior for front-only scenarios

---

## Conclusion

Video 2 validation demonstrates that EagleVision ANPR performs **significantly better on higher-resolution footage** (1152×720) with an **88.7% readable output rate** and **93.9% fewer unreadable flags** compared to Video 1.

However, **front-plate detection is a critical weakness**, with only **19.6% of vehicles** having detectable plates. This confirms that **rear-capture camera angles are strongly preferred** for production deployment.

**Deployment is blocked** until:
1. Ground truth annotations enable true accuracy measurement
2. ByteTrack consolidation merges repeated detections from tracked vehicles
3. Front-plate detection optimization (if multi-angle deployment required)

**Recommendation**: Prioritize ground truth annotation of Video 2 to measure OCR accuracy on moving vehicles, then compare with Video 1 (stationary) to understand motion impact.
