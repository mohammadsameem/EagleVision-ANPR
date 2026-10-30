# EagleVision ANPR - Real CCTV Combined Validation Report

**Date**: October 28, 2026  
**Videos Tested**: 3 (WhatsApp Video 2026-10-30 at 6.25.41/6.26.23/6.26.04 AM)  
**Total Processing Time**: ~172 seconds  
**Total Frames Analyzed**: 279 (sampled at 5 FPS)

---

## Executive Summary

EagleVision ANPR pipeline was validated on three real-world CCTV videos representing different deployment scenarios. The system processed **279 frames**, detected **544 vehicles** and **222 license plates**, achieving an **83.8% readable OCR output rate**. However, **actual accuracy cannot be determined without ground truth annotations**.

### Key Findings Across All Videos
- ✅ **Vehicle detection operational** across all scenarios (544 detections)
- ✅ **Plate detection functional** (222 plates detected)
- ✅ **OCR preprocessing integrated successfully** (142/222 plates preprocessed = 64%)
- ✅ **Empty scene handling effective** (Video 3: 96.7% empty frames)
- ⚠️ **Plate detection highly scenario-dependent** (84.2% rear vs 19.6% front)
- ⚠️ **OCR quality varies significantly** (0% to 88.7% by video)
- ❌ **No ground truth available - accuracy unmeasured**

---

## Test Scenarios

### Video 1: Stationary Vehicle with Rear Plate
**Purpose**: Validate OCR and plate detection on prominently visible rear plate.  
**Scene**: Parked vehicle, rear-facing camera angle.  
**Results**: 177 vehicles, 149 plates (84.2% detection rate), 82.6% readable OCR.

### Video 2: Moving Vehicles with Front Plates
**Purpose**: Test detection on moving vehicles, front-angle capture, ByteTrack tracking.  
**Scene**: Traffic with vehicles approaching camera.  
**Results**: 363 vehicles, 71 plates (19.6% detection rate), 88.7% readable OCR.

### Video 3: Negative Test (Low/No Activity)
**Purpose**: Measure false positive rate in empty or low-activity scenes.  
**Scene**: Minimal traffic, possibly empty lot.  
**Results**: 4 vehicles, 2 plates (50% detection rate), 0% readable OCR.

---

## Combined Detection Results

| Metric | Video 1 | Video 2 | Video 3 | **Total/Avg** |
|--------|---------|---------|---------|---------------|
| **Resolution** | 848×478 | 1152×720 | 1280×720 | — |
| **Duration** | 14.85s | 16.77s | 24.04s | 55.66s |
| **Frames Sampled** | 75 | 84 | 120 | **279** |
| **Vehicles Detected** | 177 | 363 | 4 | **544** |
| **Plates Detected** | 149 | 71 | 2 | **222** |
| **Plate Detection Rate** | 84.2% | 19.6% | 50% | **40.8%** |
| **Readable OCR Rate** | 82.6% | 88.7% | 0% | **83.8%** |

### Aggregated Statistics
- **Total Processing Time**: ~172 seconds (~0.62 seconds/frame)
- **Vehicle Detection Density**: 1.95 vehicles/frame (avg)
- **Plate Detection Density**: 0.80 plates/frame (avg)
- **Plates with Non-Empty OCR**: 186/222 (83.8%)

**⚠️ CRITICAL**: 83.8% readable rate means **non-empty OCR output**, NOT accuracy. Without ground truth, we cannot verify correctness.

---

## OCR Preprocessing Validation

### Preprocessing Coverage
- **Plates Preprocessed**: 142/222 (64%)
- **Method**: Lanczos4 upsampling (4× scale)
- **Target Resolution**: ~224×88 pixels after preprocessing

### Preprocessing by Video

| Video | Preprocessed | % Preprocessed | Unreadable Flags |
|-------|--------------|----------------|------------------|
| **Video 1** | 142/149 | 95.3% | 74/75 frames (98.7%) |
| **Video 2** | 63/71 | 88.7% | 4/84 frames (4.8%) |
| **Video 3** | 0/2 | 0% | 0/120 frames (0%) |
| **Total** | **205/222** | **92.3%** | **78/279 frames (28%)** |

### Key Findings
1. **Preprocessing integration functional**: 92.3% of plates attempted preprocessing
2. **Unreadable flag rate inversely correlates with resolution**:
   - Video 1 (848×478): 98.7% flagged unreadable
   - Video 2 (1152×720): 4.8% flagged unreadable
   - **Conclusion**: Higher source resolution improves preprocessing effectiveness

3. **Flagged "unreadable" plates still produce OCR output**:
   - Video 1: 98.7% flagged unreadable, yet 82.6% readable output
   - **Gap suggests conservative quality thresholds or false flags**

---

## Scenario-Specific Insights

### Rear-Plate Scenario (Video 1)
- ✅ **High plate detection rate (84.2%)**
- ✅ Stationary vehicle simplifies detection
- ⚠️ Small plate sizes (mean 56×22px) limit OCR quality
- ⚠️ 98.7% flagged as unreadable despite 82.6% producing output

**Conclusion**: Rear-capture angle is optimal for plate detection.

### Front-Plate Scenario (Video 2)
- ❌ **Low plate detection rate (19.6%)** - critical weakness
- ✅ Higher resolution (1152×720) improves OCR quality (88.7% readable)
- ✅ Better preprocessing performance (only 4.8% flagged unreadable)
- ⚠️ Moving vehicles generate multiple detections (ByteTrack consolidation needed)

**Conclusion**: Front-facing cameras significantly reduce plate detection success.

### Negative Test (Video 3)
- ✅ **Excellent empty frame handling (96.7% empty)**
- ⚠️ 4 vehicle and 2 plate detections require manual verification
- ❌ 0% readable OCR (all detected plates failed)
- ❌ Cannot calculate false positive rate without ground truth

**Conclusion**: System handles empty scenes well, but FP rate unmeasured.

---

## Critical Limitations

### 1. No Ground Truth Annotations
**Impact**: The most critical blocker for production deployment.

Without ground truth, we **cannot measure**:
- OCR accuracy (exact-match or character-level)
- Precision and recall for plate detection
- False positive rate (especially Video 3)
- Character Error Rate (CER)
- F1-score or other classification metrics

**What we CAN measure**:
- Detection counts (544 vehicles, 222 plates)
- Non-empty output rate (83.8% - but NOT accuracy)
- Preprocessing application rate (92.3%)

**Resolution Required**: Manual annotation of visible license plates in annotated frames. Suggested workflow:
1. Review annotated frames for each video
2. Record ground truth license plate strings
3. Mark unreadable/occluded plates
4. Calculate true accuracy metrics

### 2. ByteTrack Consolidation Not Implemented
**Impact**: Inflated detection counts, no confidence voting.

- **Problem**: Same vehicle tracked across multiple frames generates repeated detections
  - Video 1: 177 vehicle detections ≠ 177 unique vehicles
  - Video 2: 363 vehicle detections ≠ 363 unique vehicles
  
- **Missing Feature**: Merge detections by track ID, apply confidence voting for final OCR result

- **Consequence**: Cannot determine true vehicle count or improve OCR via multi-frame consensus

**Resolution Required**: Implement track ID consolidation in results processing.

### 3. Front-Plate Detection Severely Limited
**Impact**: Only 19.6% of vehicles in Video 2 had detectable plates.

- **Cause**: Front-facing camera angle + possible front-plate absence in region
- **Comparison**: 84.2% detection rate for rear-facing (Video 1) vs 19.6% front-facing (Video 2)
- **Deployment Impact**: Multi-angle camera deployments will have reduced coverage

**Resolution Options**:
- Deploy cameras at rear-capture angles (recommended)
- Train specialized front-plate detection model
- Lower confidence threshold (risks false positives)

### 4. Small Plate Sizes
**Impact**: Degrades OCR quality on low-resolution footage.

- **Video 1 mean plate size**: 56×22 pixels (44% below 100×30px optimal threshold)
- **Mitigation**: Preprocessing upsampling applied, but effectiveness unmeasured
- **Requires**: Ground truth comparison of preprocessed vs raw OCR accuracy

---

## Preprocessing Impact Assessment

### Synthetic vs Real-World Performance

**Synthetic Test Results** (from previous validation):
- Test dataset: 80×20 pixel plates (extreme low resolution)
- Preprocessing: Lanczos4 upsampling
- Result: **100% OCR accuracy** on synthetic images

**Real CCTV Results** (this validation):
- Mean plate size: 56×22 pixels (Video 1) to unknown (Video 2/3)
- Preprocessing: Same Lanczos4 upsampling
- Result: **83.8% readable output rate (accuracy unknown)**

**Conclusion**: Synthetic 100% accuracy does NOT predict real-world performance. Real CCTV footage introduces:
- Motion blur
- Lighting variations
- Perspective distortion
- Compression artifacts
- Environmental noise

**Assessment**: Preprocessing integration is **functionally successful** but **effectiveness on real plates is unproven without ground truth**.

---

## Production Readiness Assessment

| Component | Status | Blocking Issues |
|-----------|--------|-----------------|
| **Vehicle Detection** | ✅ Operational | None |
| **Plate Detection (Rear)** | ✅ Good (84.2%) | None |
| **Plate Detection (Front)** | ❌ Poor (19.6%) | **Deployment angle constraints** |
| **OCR Preprocessing** | ✅ Integrated | Effectiveness unmeasured |
| **OCR Accuracy** | ❌ Unknown | **No ground truth** |
| **ByteTrack Consolidation** | ❌ Not Implemented | **Inflated counts** |
| **False Positive Filtering** | ⚠️ Not Validated | Video 3 inconclusive |
| **Multi-Camera Fusion** | ❌ Not Tested | — |

### Overall Assessment: **NOT PRODUCTION-READY**

**Blockers**:
1. **Ground truth annotations required** - Cannot claim accuracy without verification
2. **ByteTrack consolidation missing** - Vehicle counts unreliable
3. **Front-plate detection inadequate** - Limits multi-angle deployments

---

## Deployment Recommendations

### Camera Placement
- ✅ **Rear-capture angles strongly preferred** (84.2% vs 19.6% plate detection)
- ❌ Avoid front-facing cameras unless specialized model trained
- ✅ Target resolution: **1152×720 minimum** (Video 2 showed 6% better readable rate than Video 1)

### System Configuration
- **Confidence Threshold**: Current 0.70 appears effective (96.7% empty frames in Video 3)
- **Sampling Rate**: 5 FPS adequate for stationary vehicles, may need increase for high-speed traffic
- **Preprocessing**: Enable Lanczos4 upsampling for all plates <100px width

### Workflow Integration
- **Implement ByteTrack consolidation** before calculating vehicle counts
- **Apply confidence voting** across multiple OCR readings of same tracked vehicle
- **Flag low-confidence detections** for manual review

---

## Next Steps

### Phase 1: Ground Truth Creation (CRITICAL)
1. **Create annotation template** with fields:
   - Frame index
   - Vehicle bounding box
   - License plate ground truth string (if visible)
   - Visibility flag (readable/partially occluded/fully occluded)

2. **Manually annotate sample frames**:
   - Video 1: 20-30 frames (stationary vehicle)
   - Video 2: 20-30 frames (moving vehicles)
   - Video 3: All 4 detection frames (false positive verification)

3. **Calculate true accuracy metrics**:
   - Exact-match accuracy
   - Character-level accuracy (Levenshtein distance)
   - Precision, recall, F1-score
   - Character Error Rate (CER)

### Phase 2: System Optimization
4. **Implement ByteTrack consolidation**:
   - Merge detections by track ID
   - Apply confidence voting for final OCR result
   - Measure impact on vehicle count accuracy

5. **Tune detection parameters**:
   - Optimize confidence thresholds per scenario
   - Test impact of preprocessing on accuracy
   - Evaluate alternative upsampling methods

6. **Validate preprocessing effectiveness**:
   - Compare accuracy: raw vs preprocessed plates
   - Measure improvement on small plates (<60px)
   - Identify failure modes

### Phase 3: Extended Testing
7. **Expand test dataset**:
   - Record 10+ additional videos across scenarios
   - Day/night lighting conditions
   - Weather variations (rain, fog)
   - High-speed traffic

8. **Measure false positive rate**:
   - Create verified empty scene dataset (100+ frames)
   - Calculate FP rate with statistical significance
   - Tune to achieve <1% FP rate

9. **Test multi-camera fusion**:
   - Overlapping camera coverage
   - Cross-camera vehicle re-identification
   - Confidence merging from multiple angles

---

## Summary Statistics

### Detection Volume
- **Total Frames Processed**: 279
- **Total Vehicles Detected**: 544
- **Total Plates Detected**: 222
- **Plates with Non-Empty OCR**: 186 (83.8%)

### Preprocessing Metrics
- **Preprocessing Application Rate**: 92.3% (205/222 plates)
- **Unreadable Flags**: 78/279 frames (28%)
- **Preprocessing Method**: Lanczos4 upsampling (4× scale)

### Scenario Performance
- **Best Plate Detection**: Video 1 (84.2% rear-facing)
- **Worst Plate Detection**: Video 2 (19.6% front-facing)
- **Best OCR Output Rate**: Video 2 (88.7% readable)
- **Worst OCR Output Rate**: Video 3 (0% readable)

### System Performance
- **Processing Speed**: ~0.62 seconds/frame (5 FPS sampling)
- **Empty Frame Handling**: 96.7% correct (Video 3)
- **False Positive Rate**: **Unknown** (requires ground truth)

---

## Conclusion

EagleVision ANPR pipeline demonstrates **functional integration** of vehicle detection, license plate detection, and OCR preprocessing across three real-world CCTV scenarios. The system successfully processed 279 frames, detecting 544 vehicles and 222 license plates with an 83.8% non-empty OCR output rate.

However, **the system is NOT production-ready** due to:
1. **Unmeasured accuracy** - 83.8% "readable rate" ≠ 83.8% accuracy
2. **No ground truth annotations** - Cannot verify OCR correctness
3. **Front-plate detection weakness** - Only 19.6% success rate limits deployment flexibility
4. **Missing ByteTrack consolidation** - Vehicle counts and OCR confidence voting unavailable

**Deployment is BLOCKED** until ground truth annotations enable true accuracy measurement and ByteTrack consolidation merges repeated detections from tracked vehicles.

**Immediate Next Step**: Create ground truth annotations for 50-80 sample frames across all three videos to measure actual OCR accuracy and validate preprocessing effectiveness.

**Recommendation**: Prioritize rear-capture camera angles (84.2% plate detection) and minimum 1152×720 resolution (6% better readable rate) for pilot deployments. Do NOT deploy to production until accuracy verified via ground truth.
