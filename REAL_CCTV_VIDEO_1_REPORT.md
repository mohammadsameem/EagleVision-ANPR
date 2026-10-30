# EagleVision ANPR - Real CCTV Video 1 Validation Report

**Video**: `WhatsApp Video 2026-10-30 at 6.25.41 AM.mp4`  
**Date**: October 28, 2026  
**Test Scenario**: Primary OCR and plate-detection validation on stationary vehicle with visible rear plate

---

## Executive Summary

Video 1 processing detected **177 vehicles** and **149 license plates** across **75 sampled frames** (5 FPS from 14.85s video). OCR preprocessing was applied to 142/149 plates (95.3%), with **123 plates producing non-empty OCR output (82.6% readable rate)**. However, **actual accuracy cannot be determined without ground truth annotations**.

### Key Findings
- ✅ Vehicle detection operational (177 detections)
- ✅ Plate detection functional (149 plates from 177 vehicles = 84.2% plate detection rate)
- ✅ OCR preprocessing integration working (142/149 plates preprocessed)
- ⚠️ **Mean plate size 56×22 pixels** - below optimal threshold
- ⚠️ 74/75 frames flagged as "unreadable_after_preprocessing" - indicates quality issues
- ❌ **No ground truth available - cannot verify OCR correctness**

---

## Video Metadata

| Property | Value |
|----------|-------|
| **Resolution** | 848×478 pixels |
| **Frame Rate** | 20.00 fps |
| **Duration** | 14.85 seconds |
| **Codec** | h264 |
| **Total Frames** | 297 |
| **Sampled Frames** | 75 (every 4th frame at 5 FPS) |

---

## Detection Results

### Vehicle Detection
- **Total Detections**: 177 vehicles
- **Per-Frame Average**: 2.36 vehicles/frame
- **Detection Rate**: Consistent across frames

### License Plate Detection
- **Total Plates Detected**: 149
- **Plate Detection Rate**: 84.2% (149/177 vehicles)
- **Per-Frame Average**: 1.99 plates/frame

### Plate Size Analysis
- **Mean Plate Size**: 56×22 pixels
- **Standard Deviation**: ±18×7 pixels
- **Assessment**: Significantly below optimal 100×30px threshold
- **Impact**: Small plate size likely degrades OCR accuracy

---

## OCR Performance

### Preprocessing Statistics
- **Plates Preprocessed**: 142/149 (95.3%)
- **Preprocessing Method**: Lanczos4 upsampling (4× scale)
- **Target Resolution**: ~224×88 pixels after preprocessing
- **Unreadable Flags**: 74/75 frames flagged (98.7%)

### OCR Output
- **Non-Empty OCR Results**: 123/149 plates (82.6% readable output rate)
- **Empty/Failed OCR**: 26/149 plates (17.4%)
- **OCR Engine**: EasyOCR (PaddleOCR unavailable on Python 3.14)

**⚠️ CRITICAL LIMITATION**: 82.6% represents the rate of non-empty OCR output, NOT accuracy. Without ground truth annotations, we cannot determine how many of these 123 "readable" outputs are correct.

---

## Sample OCR Results

Below are examples of OCR output strings from Video 1. **These have NOT been verified against ground truth**.

```
Frame 0000: "48K", "BB48", "DHZABK", "DABHA48", ...
Frame 0004: "48K", "BBAS", "BB18", "HDAA48", ...
Frame 0008: "AH48K", "BBAO", "48", "DAB4A4B", ...
```

### Observations
- Multiple detections per frame (as expected from tracking same vehicle)
- Character consistency varies ("48K" appears frequently, suggests true plate partial)
- Garbled outputs present ("DHZABK", "DABHA48") - unclear if OCR errors or false detections
- Requires manual verification to separate true positives from noise

---

## Annotated Output

All results saved to: `validation_results/cctv_real/video_1/`

### Generated Assets
- **Annotated Frames**: 75 frames with bounding boxes
  - Location: `annotated_frames/frame_XXXX_tYYYYms.jpg`
  - Green boxes: vehicles
  - Blue boxes: license plates
  - Red text: OCR results

- **Plate Crops**: 149 cropped license plate images
  - Location: `plate_crops/frame_XXXX_vXXXX_plate.jpg`
  - Original resolution preserved
  - Enables manual inspection and ground truth creation

- **Results JSON**: Complete detection data
  - Location: `video_1_results.json`
  - Contains: frame indices, bounding boxes, OCR strings, preprocessing metadata

---

## Issues and Limitations

### 1. No Ground Truth Annotations
**Impact**: Cannot calculate precision, recall, F1-score, accuracy, or character error rate.  
**Resolution Required**: Manual annotation of visible plates in annotated frames.

### 2. Small Plate Sizes
**Mean plate size 56×22 pixels** is 44% below the 100×30px threshold where OCR performs reliably.  
**Contributing Factors**:
- Low video resolution (848×478)
- Distance from camera to vehicle
- Cropping during plate detection

**Mitigation**: Preprocessing upsampling applied (4× scale via Lanczos4), but effectiveness unmeasured.

### 3. High Unreadable Flag Rate
74/75 frames (98.7%) flagged as `unreadable_after_preprocessing` despite 82.6% producing OCR output.  
**Possible Causes**:
- Conservative quality thresholds
- Blur/motion blur in source footage
- Plate angle/perspective distortion
- Low contrast

**Requires Investigation**: Correlation between "unreadable" flags and actual OCR correctness unknown.

### 4. Multiple Detections Per Plate
Same vehicle tracked across frames generates multiple OCR attempts.  
**Without ByteTrack ID consolidation**, cannot distinguish:
- Multiple readings of same plate (should be merged for confidence voting)
- Separate vehicles with similar detections

**Impact**: Inflates detection count, complicates accuracy calculation.

---

## Preprocessing Validation

Video 1 demonstrates that OCR preprocessing integration is **functionally operational**:
- ✅ Preprocessing applied to 95.3% of detected plates
- ✅ Lanczos4 upsampling executed without errors
- ✅ Preprocessing metadata correctly logged in results
- ✅ 82.6% of plates produced non-empty OCR output

However, **effectiveness on real-world CCTV footage is unproven**:
- Synthetic validation (100% accuracy on 80×20px test images) does not predict CCTV performance
- Small mean plate size (56×22px) may exceed preprocessing recovery capability
- High unreadable flag rate suggests quality issues persist after preprocessing

---

## Production Readiness Assessment

| Component | Status | Confidence |
|-----------|--------|------------|
| Vehicle Detection | ✅ Operational | High |
| Plate Detection | ✅ Operational | High |
| OCR Preprocessing | ✅ Integrated | Medium |
| OCR Accuracy | ❌ Unverified | **Unknown** |
| ByteTrack Consolidation | ⚠️ Not Tested | N/A |
| False Positive Filtering | ⚠️ Not Tested | N/A |

**Overall Assessment**: System produces output but **cannot be deployed to production without ground truth validation**.

---

## Next Steps

### Immediate (Required for Validation)
1. **Create Ground Truth Annotations**
   - Manually inspect annotated frames in `annotated_frames/`
   - Record true license plate strings visible in footage
   - Document unreadable/occluded plates
   - Suggested sample size: 20-30 frames for statistically significant results

2. **Calculate True Accuracy Metrics**
   - Exact-match accuracy (full plate string)
   - Character-level accuracy (Levenshtein distance)
   - Precision and recall for plate detection
   - Correlation between "unreadable" flags and OCR correctness

3. **Analyze False Positives**
   - Identify OCR outputs that do NOT correspond to visible plates
   - Measure false detection rate

### Optimization (After Ground Truth Available)
4. **Tune Confidence Thresholds**
   - Current: 0.70 for vehicle detection
   - Optimize plate detection confidence to reduce false positives

5. **Evaluate Preprocessing Impact**
   - Compare OCR accuracy with vs without preprocessing
   - Validate Lanczos4 vs other upsampling methods
   - Measure impact on small plates (<60px width)

6. **Implement ByteTrack Consolidation**
   - Merge multiple OCR results from same tracked vehicle
   - Apply confidence voting for final plate string

---

## Conclusion

Video 1 validation confirms that EagleVision's ANPR pipeline is **technically functional** but **accuracy is unverified**. The system successfully detected vehicles, located license plates, applied preprocessing, and generated OCR output at an 82.6% non-empty rate.

However, **deployment is blocked** until ground truth annotations enable true accuracy measurement. The reported 82.6% "readable rate" represents the percentage of plates that produced non-empty OCR strings, NOT the percentage of correct readings.

**Recommendation**: Prioritize ground truth annotation of Video 1 (stationary vehicle scenario) before proceeding to Video 2 (moving vehicles) or production deployment.
