# Ground Truth Annotation Report - EagleVision ANPR

**Date:** 2026-10-28  
**Status:** **READY FOR MANUAL ANNOTATION**  
**Phase:** Ground Truth Creation

---

## Executive Summary

The EagleVision ANPR pipeline has been successfully validated on three real CCTV videos with **279 frames processed**, **544 vehicles detected**, and **222 license plates detected**. However, **actual accuracy cannot be measured** without ground truth annotations.

This report documents the annotation workflow preparation, including:
- ✅ Video identity verification complete
- ✅ Annotation frame selection complete (74 representative frames)
- ✅ Frame extraction complete (74 frames saved with detector overlays)
- ✅ Annotation schema and template created
- ✅ Validation script implemented
- ⚠️ **Manual annotation required** (8-11 hours estimated)

**Critical Blocker:** Production deployment requires verified accuracy metrics, which can only be calculated after ground truth annotation is complete.

---

## 📊 Video Identity Verification - COMPLETE

### Video Mapping

| Original Filename | Validation ID | Resolution | FPS | Duration | Scenario |
|-------------------|---------------|------------|-----|----------|----------|
| WhatsApp Video 2026-10-30 at 6.25.41 AM.mp4 | video_1 | 848×478 | 20 | 14.85s | **Rear-plate stationary** |
| WhatsApp Video 2026-10-30 at 6.26.23 AM.mp4 | video_2 | 1152×720 | 30 | 16.77s | **Front-plate moving** |
| WhatsApp Video 2026-10-30 at 6.26.04 AM.mp4 | video_3 | 1280×720 | 15 | 24.04s | **Empty scene negative test** |

### Video 1: Rear-Plate Stationary Vehicle
- **Frames Processed:** 75 (at 5 FPS)
- **Vehicles Detected:** 177 (2.36 per frame)
- **Plates Detected:** 149 (84.2% detection rate) ✅
- **Readable OCR:** 82.6% (non-empty output)
- **Mean Plate Size:** 56×22 pixels (very small!)
- **Processing Time:** 68.7 seconds

**Key Characteristic:** High plate detection rate confirms rear-facing camera is optimal. Small plate sizes will challenge OCR accuracy measurement.

### Video 2: Front-Plate Moving Vehicles
- **Frames Processed:** 84 (at 5 FPS)
- **Vehicles Detected:** 363 (4.32 per frame)
- **Plates Detected:** 71 (19.6% detection rate) ⚠️
- **Readable OCR:** 88.7% (non-empty output)
- **Mean Plate Size:** 69×33 pixels (better resolution)
- **Processing Time:** 85.5 seconds

**Key Characteristic:** Front-facing cameras show 64.6 percentage point drop in plate detection. Higher resolution improves OCR output quality.

### Video 3: Empty Scene (Negative Test)
- **Frames Processed:** 120 (at 5 FPS)
- **Vehicles Detected:** 4 (0.033 per frame)
- **Plates Detected:** 2 (50% of vehicles)
- **Readable OCR:** 0% (all failed)
- **Empty Frames:** 116/120 (96.7%) ✅
- **Processing Time:** 18.5 seconds

**Key Characteristic:** Excellent empty scene handling. 4 vehicle detections require manual verification to determine if true or false positives.

---

## 🎯 Annotation Frame Selection - COMPLETE

### Selection Strategy

**Total Frames Selected:** 74 representative frames

| Video | Frames | Strategy | With Plates | Without Plates |
|-------|--------|----------|-------------|----------------|
| **Video 1** | 30 | Diverse timeline | 23 | 7 |
| **Video 2** | 40 | Plate-focused | 30 | 10 |
| **Video 3** | 4 | All detections | 2 | 2 |
| **Total** | **74** | — | **55** | **19** |

### Video 1 Selection (30 frames)
- **Strategy:** Diverse timeline sampling
- **Target:** Representative frames across 14.85-second video
- **Sampling:** Every 2.5 frames (step size 2-3)
- **Rationale:** Stationary vehicle, so temporal diversity captures different lighting/angle variations

### Video 2 Selection (40 frames)
- **Strategy:** Plate-focused sampling
- **Plate Frames:** 30 (to measure detection/OCR accuracy)
- **Non-Plate Frames:** 10 (to measure false negative rate)
- **Rationale:** Moving vehicles create diverse plate positions/angles, need both positive and negative samples

### Video 3 Selection (4 frames)
- **Strategy:** All frames with detections
- **Why All 4:** Negative test requires verification of every detection (true vs false positive)
- **Empty Frames:** Not included (confirmed as true negatives by system)

### Expected Detections to Annotate

Based on detector predictions (not ground truth):
- **Vehicles:** 74 detections across all frames
- **Plates:** 55 detections (will verify which are true positives)

**Note:** Actual ground truth counts may differ after manual verification.

---

## 🖼️ Frame Extraction - COMPLETE

### Output Directory Structure

```
data/annotations/
├── frames/                              # Extracted frames (COMPLETE)
│   ├── video_1_frame_000000.jpg        # 30 frames from video 1
│   ├── video_1_frame_000003.jpg
│   ├── ...
│   ├── video_2_frame_000000.jpg        # 40 frames from video 2
│   ├── video_2_frame_000002.jpg
│   ├── ...
│   ├── video_3_frame_000030.jpg        # 4 frames from video 3
│   └── video_3_frame_000060.jpg
├── annotation_frame_list.json          # Frame metadata (COMPLETE)
├── ground_truth_template.json          # Annotation template (COMPLETE)
└── ground_truth.json                    # TO BE CREATED BY ANNOTATOR
```

### Frame Image Features

Each extracted frame includes:
- ✅ Original frame content
- ✅ **Green boxes:** Vehicle detections (detector predictions)
- ✅ **Blue boxes:** Plate detections (detector predictions)
- ✅ **Red text:** OCR predictions (detector predictions)
- ✅ **Orange watermark:** "DETECTOR PREDICTIONS (NOT GROUND TRUTH)"

**Important:** Detector predictions shown are for **reference only**. Annotators must:
- Verify all detections independently
- Correct bounding boxes if detector missed/misplaced them
- Read plate text independently (DO NOT copy OCR predictions)

### Frame Quality

All 74 frames successfully extracted:
- ✅ No extraction errors
- ✅ All coordinates validated
- ✅ Detector overlays properly rendered
- ✅ Files saved as high-quality JPEG

---

## 📝 Annotation Schema - COMPLETE

### Ground Truth Format

Schema documented in `GROUND_TRUTH_ANNOTATION_GUIDE.md` with:
- ✅ Bounding box convention: `[x_min, y_min, x_max, y_max]`
- ✅ Required fields for vehicles (bbox, class, ID)
- ✅ Required fields for plates (bbox, text, visibility, orientation, status)
- ✅ Quality flags (blur, occlusion, small_size, poor_lighting, extreme_angle)
- ✅ Annotation status (verified, uncertain, unreadable, review_needed)
- ✅ Complete JSON schema with examples

### Template Created

`data/annotations/ground_truth_template.json` includes:
- Annotation set metadata
- Video reference information
- Empty frames array ready for annotations
- Proper JSON structure with all required fields

---

## ✅ Validation Script - COMPLETE

`scripts/validate_ground_truth.py` implements comprehensive checks:

### Validation Coverage
- ✅ Required field presence
- ✅ Bounding box coordinate validation (within image boundaries, proper ordering)
- ✅ Enum value validation (visibility, orientation, annotation_status, vehicle_class)
- ✅ Vehicle-plate association validation
- ✅ Duplicate ID detection
- ✅ Format consistency checks
- ✅ Size sanity checks (warnings for very small bboxes)

### Output
- Error count (blocking issues)
- Warning count (review recommended)
- Annotation statistics
- Pass/fail verdict

**Usage:**
```bash
python scripts/validate_ground_truth.py
```

---

## ⏱️ Annotation Time Estimate

### Per-Frame Estimates
- **Simple frames** (0-1 vehicles): 2-3 minutes
- **Medium frames** (2-4 vehicles): 5-8 minutes
- **Complex frames** (5+ vehicles): 10-15 minutes

### Total Estimate by Video

| Video | Frames | Avg Complexity | Estimated Time |
|-------|--------|----------------|----------------|
| Video 1 | 30 | Medium (2-3 vehicles/frame) | 3-4 hours |
| Video 2 | 40 | Medium-High (3-5 vehicles/frame) | 4-6 hours |
| Video 3 | 4 | Simple (0-1 vehicles/frame) | 15-20 minutes |
| **Total** | **74** | — | **8-11 hours** |

**Breakdown:**
- Initial annotation: 6-8 hours
- Quality control review: 1-2 hours
- Validation and fixes: 1 hour

**Recommendations:**
- Split work across multiple sessions to avoid fatigue
- Batch similar frames together
- Use breaks to maintain accuracy
- Consider second annotator review for critical frames

---

## 🚀 Annotation Workflow - READY

### Step 1: Setup ✅
- [x] Extract frames to `data/annotations/frames/`
- [x] Copy template to `data/annotations/ground_truth.json`
- [x] Review annotation guide

### Step 2: Annotate (MANUAL WORK REQUIRED)
For each of 74 frames:
1. **Open frame image** in `data/annotations/frames/`
2. **Verify vehicles:**
   - Are all visible vehicles detected? (check false negatives)
   - Are detector boxes accurate? (adjust if needed)
   - Are detections true vehicles? (check false positives)
3. **Verify plates:**
   - Are all visible plates detected? (check false negatives)
   - Are detector boxes accurate? (adjust if needed)
   - Are detections true plates? (check false positives)
4. **Read plate text:**
   - **Zoom in** on plate crop
   - **Read independently** (DO NOT copy OCR)
   - If ANY character unreadable: mark as `null`
   - Record exact text with spacing
5. **Record metadata:**
   - Visibility (clear/partial/occluded/blurry/small/absent)
   - Orientation (front/rear/side)
   - Quality flags (blur, occlusion, etc.)
   - Vehicle-plate association
   - Annotation status (verified/uncertain/unreadable/review_needed)

### Step 3: Quality Control
- [ ] Review all 74 annotations
- [ ] Check bounding boxes within boundaries
- [ ] Verify plate_text not copied from OCR
- [ ] Ensure vehicle-plate associations valid
- [ ] Mark uncertain cases explicitly

### Step 4: Validation
```bash
python scripts/validate_ground_truth.py
```
- Fix any errors reported
- Review warnings
- Re-run until validation passes

### Step 5: Calculate Metrics
```bash
python scripts/validate_anpr_accuracy.py \
  --ground-truth data/annotations/ground_truth.json \
  --validation-results validation_results/cctv_real/
```
- Generates precision, recall, F1, accuracy metrics
- Produces detailed accuracy report
- Compares against 83.8% "readable rate" baseline

---

## 📋 Critical Annotation Rules

### ❌ DO NOT:
1. **Copy OCR predictions as ground truth** - Read plate text independently from image
2. **Guess unreadable characters** - Mark as `unreadable` if uncertain
3. **Annotate off-frame vehicles** - Only annotate what's visible
4. **Use inconsistent plate text format** - Preserve spacing: "MH 12 AB 1234"
5. **Skip quality control** - Always validate before submitting

### ✅ DO:
1. **Zoom in on small plates** - Use image viewer zoom for accuracy
2. **Mark uncertain cases explicitly** - Use `"uncertain": true` flag
3. **Track vehicles consistently** - Use same `vehicle_id` across frames if confident
4. **Document ambiguous cases** - Use `notes` field
5. **Request second opinion** - For difficult frames

---

## 📊 Expected Outcomes After Annotation

### Metrics to Calculate

1. **Vehicle Detection Metrics:**
   - Precision: True Positives / (True Positives + False Positives)
   - Recall: True Positives / (True Positives + False Negatives)
   - F1-Score: Harmonic mean of precision and recall
   - Mean IoU: Average intersection-over-union for matched detections

2. **Plate Detection Metrics:**
   - Precision, Recall, F1-Score (same formulas)
   - Detection rate by plate size category
   - Detection rate by visibility category

3. **OCR Metrics:**
   - **Exact-match accuracy:** Plates with 100% correct text / Total readable plates
   - **Character accuracy:** Correct characters / Total characters (using Levenshtein)
   - **Character Error Rate (CER):** Edit distance / True text length
   - Empty output rate
   - Unreadable plate identification accuracy

4. **End-to-End Metrics:**
   - Correct ANPR rate: Perfect vehicle + plate + OCR / Total vehicles
   - Vehicle-to-plate association accuracy

### Comparison Points

- **Current "readable rate":** 83.8% (non-empty OCR output)
- **True accuracy:** To be measured with ground truth
- **Gap analysis:** Readable vs correct rate difference

### Report Updates

After annotation completion, update:
- `GROUND_TRUTH_VALIDATION.json` - Validated annotations
- `GROUND_TRUTH_ANNOTATION_REPORT.md` - This file (results section)
- `REAL_CCTV_COMBINED_REPORT.md` - Add true accuracy metrics
- `PROJECT_STATUS.md` - Mark annotation phase complete
- `IMPLEMENTATION_LOG.md` - Add annotation session
- `TEST_REPORT.md` - Add Test 10: Ground Truth Validation
- `NEXT_STEPS.md` - Update with post-annotation priorities

---

## 🔄 Current Status

### Completed ✅
- [x] Video identity verification (3 videos mapped)
- [x] Annotation frame selection (74 frames selected)
- [x] Frame extraction (74 images with detector overlays)
- [x] Annotation guide created (`GROUND_TRUTH_ANNOTATION_GUIDE.md`)
- [x] Annotation schema defined
- [x] Ground truth template created
- [x] Validation script implemented
- [x] Workflow documentation complete

### In Progress ⏳
- [ ] **Manual annotation** (0/74 frames completed)
  - [ ] Video 1: 0/30 frames
  - [ ] Video 2: 0/40 frames
  - [ ] Video 3: 0/4 frames

### Blocked 🚫
- [ ] Ground truth validation (requires annotations)
- [ ] Accuracy metric calculation (requires annotations)
- [ ] Production deployment (requires verified accuracy)

---

## 📁 Files Created

### Documentation
- `GROUND_TRUTH_ANNOTATION_GUIDE.md` - Complete annotation instructions
- `GROUND_TRUTH_ANNOTATION_REPORT.md` - This file (status and workflow)

### Data Files
- `data/annotations/annotation_frame_list.json` - Selected frames metadata
- `data/annotations/ground_truth_template.json` - Annotation template
- `data/annotations/frames/` - 74 extracted frame images
- `validation_results/cctv_real/video_identity_mapping.json` - Video verification

### Scripts
- `scripts/verify_video_identity.py` - Video verification script
- `scripts/select_annotation_frames.py` - Frame selection script
- `scripts/extract_annotation_frames.py` - Frame extraction script
- `scripts/validate_ground_truth.py` - Annotation validation script

---

## 🎯 Next Steps

### Immediate (Required for Metrics)
1. **Perform Manual Annotation** (8-11 hours)
   - Annotate all 74 frames following guide
   - Create `data/annotations/ground_truth.json`
   - Run validation script after each batch

2. **Calculate True Accuracy Metrics**
   ```bash
   python scripts/validate_anpr_accuracy.py \
     --ground-truth data/annotations/ground_truth.json \
     --validation-results validation_results/cctv_real/
   ```

3. **Update All Documentation**
   - Add accuracy results to reports
   - Compare 83.8% readable rate vs true accuracy
   - Document preprocessing effectiveness

### Medium-Term (After Metrics Available)
4. Implement ByteTrack consolidation
5. Optimize front-plate detection (currently 19.6%)
6. Test preprocessing on/off comparison
7. Expand annotation set if sample size insufficient

### Long-Term (Production Preparation)
8. Annotate additional videos (diverse conditions)
9. Measure false positive rate with statistical confidence
10. Deploy to staging environment with monitoring

---

## ⚠️ Critical Reminders

**Production Deployment BLOCKED Until:**
- Ground truth annotation complete (0/74 frames done)
- True accuracy metrics calculated
- Accuracy verified as acceptable for use case
- False positive rate measured and deemed acceptable

**DO NOT CLAIM:**
- "83.8% accuracy" - This is readable rate, not accuracy
- "Production-ready" - Accuracy unmeasured
- "Validated on real CCTV" - Detection validated, accuracy not

**CAN CLAIM:**
- "Pipeline functional on real CCTV footage"
- "83.8% non-empty OCR output rate"
- "Rear-camera optimal (84.2% plate detection rate)"
- "Ready for ground truth annotation"

---

## 📞 Support

**Questions During Annotation:**
- Unclear plate visibility → Mark as `"uncertain": true`
- Vehicle class ambiguous → Use best judgment, note in comments
- Unsure about vehicle tracking → Leave `vehicle_id` as `null`
- Frame quality poor → Set appropriate quality flags

**Technical Issues:**
- Frame extraction failed → Check video paths in `annotation_frame_list.json`
- Validation errors → Read error messages carefully, fix schema issues
- Bounding box tool problems → Verify coordinate format `[x_min, y_min, x_max, y_max]`

**Annotation Quality:**
- When in doubt, mark as uncertain rather than guessing
- Second annotator review recommended for critical frames
- Aim for 100% accuracy on ground truth (it's the gold standard!)

---

**Report Status:** COMPLETE - Ready for manual annotation  
**Last Updated:** 2026-10-28  
**Next Update:** After annotation completion
