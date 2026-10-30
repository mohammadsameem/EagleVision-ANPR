# Ground Truth Annotation Guide - EagleVision ANPR

**Purpose:** Create verified ground truth annotations for measuring actual ANPR accuracy  
**Annotation Set:** `cctv_real_set_1`  
**Total Frames:** 74 representative frames across 3 videos  
**Status:** Ready for manual annotation

---

## 📋 Overview

This guide explains how to create ground truth annotations for the EagleVision ANPR system. These annotations will enable calculation of true accuracy metrics including:

- Vehicle detection precision, recall, and F1-score
- License plate detection precision, recall, and F1-score  
- OCR exact-match accuracy and character error rate
- End-to-end correct ANPR recognition rate

**Critical Rule:** Ground truth must be created by human observation only. Never copy OCR predictions as ground truth.

---

## 🎯 Annotation Set Details

### Video 1: Rear-Plate Stationary Vehicle
- **File:** `WhatsApp Video 2026-10-30 at 6.25.41 AM.mp4`
- **Resolution:** 848×478 @ 20fps
- **Frames Selected:** 30 frames
- **Scenario:** Stationary vehicle with rear plate visible
- **Detection Results:** 177 vehicles, 149 plates detected (84.2% rate)
- **Mean Plate Size:** 56×22 pixels (small!)
- **Challenge:** Very small plate sizes, may be unreadable

### Video 2: Front-Plate Moving Vehicles
- **File:** `WhatsApp Video 2026-10-30 at 6.26.23 AM.mp4`
- **Resolution:** 1152×720 @ 30fps
- **Frames Selected:** 40 frames (30 with plates, 10 without)
- **Scenario:** Moving vehicles approaching camera
- **Detection Results:** 363 vehicles, 71 plates detected (19.6% rate)
- **Mean Plate Size:** 69×33 pixels (better resolution)
- **Challenge:** Front-facing plates harder to detect, motion blur

### Video 3: Empty Scene (Negative Test)
- **File:** `WhatsApp Video 2026-10-30 at 6.26.04 AM.mp4`
- **Resolution:** 1280×720 @ 15fps
- **Frames Selected:** 4 frames (all frames with detections)
- **Scenario:** Mostly empty scene for false positive testing
- **Detection Results:** 4 vehicles, 2 plates detected
- **Challenge:** Verify if detections are true or false positives

---

## 📐 Bounding Box Convention

**Format:** `[x_min, y_min, x_max, y_max]` (absolute pixel coordinates)

- `x_min`: Leftmost edge of bounding box
- `y_min`: Top edge of bounding box  
- `x_max`: Rightmost edge of bounding box
- `y_max`: Bottom edge of bounding box

**Example:** `[100, 200, 250, 300]` represents a box from pixel (100,200) at top-left to (250,300) at bottom-right.

**Validation:**
- All coordinates must be ≥ 0
- `x_max > x_min`
- `y_max > y_min`
- Coordinates must be within image dimensions

---

## 🚗 Vehicle Annotation

For each visible vehicle in the frame:

### Required Fields

1. **`vehicle_bbox`** (required): `[x_min, y_min, x_max, y_max]`
   - Draw tight box around entire visible vehicle
   - Include bumpers, mirrors, visible parts
   - Exclude shadows unless part of vehicle body

2. **`vehicle_class`** (required): Integer class ID
   - `2` = car (sedan, hatchback, SUV)
   - `3` = motorcycle (bike, scooter)
   - `5` = bus
   - `7` = truck
   - Use YOLOv8 COCO class IDs

3. **`vehicle_id`** (optional): String identifier
   - Assign same ID if you can confidently track vehicle across frames
   - Format: `v1`, `v2`, `v3`, etc.
   - Leave `null` if uncertain about identity

### Annotation Rules

- **Partial Occlusion:** Annotate if ≥50% of vehicle visible
- **Edge Cases:** Annotate if ≥75% of vehicle in frame
- **Distant Vehicles:** Annotate if vehicle clearly identifiable as a vehicle
- **Doubt:** If uncertain if object is a vehicle, mark with `"uncertain": true`

---

## 🔖 License Plate Annotation

For each visible license plate in the frame:

### Required Fields

1. **`plate_bbox`** (required): `[x_min, y_min, x_max, y_max]`
   - Draw tight box around plate border
   - Include mounting screws/frame if part of plate
   - Exclude bumper, vehicle body

2. **`plate_text`** (required if readable): String
   - **Only record if you can independently read the text**
   - Do NOT copy from OCR predictions
   - Use exact characters visible: letters, numbers, spaces, dashes
   - Preserve spacing: "MH 12 AB 1234" not "MH12AB1234"
   - If ANY characters unreadable: set to `null`

3. **`plate_visibility`** (required): Enum
   - `"clear"`: All characters readable with high confidence
   - `"partial"`: 50-90% of characters readable
   - `"occluded"`: Plate present but <50% readable (by object, shadow, angle)
   - `"blurry"`: Plate present but motion/focus blur prevents reading
   - `"small"`: Plate too small to read individual characters
   - `"absent"`: No plate visible on vehicle

4. **`plate_orientation`** (required if visible): Enum
   - `"front"`: Front-facing plate
   - `"rear"`: Rear-facing plate
   - `"side"`: Side-mounted plate (rare)
   - `null`: Orientation unclear

5. **`associated_vehicle`** (required): String
   - Reference to `vehicle_id` this plate belongs to
   - Must match a vehicle annotation in same frame
   - Set to `null` if plate detected but vehicle not visible

### Quality Flags (Optional)

Mark applicable issues:

- **`blur`**: `true` if motion blur or focus issues
- **`occlusion`**: `true` if partially blocked (dirt, object, shadow)
- **`small_size`**: `true` if plate <60px width
- **`poor_lighting`**: `true` if overexposed, underexposed, or shadows
- **`extreme_angle`**: `true` if plate at >45° angle from camera
- **`damaged_plate`**: `true` if plate physically damaged or faded

### Annotation Status

1. **`annotation_status`** (required): Enum
   - `"verified"`: You are confident in all annotations
   - `"uncertain"`: Some uncertainty about vehicle/plate presence or text
   - `"unreadable"`: Plate present but text cannot be read
   - `"review_needed"`: Requires second opinion

---

## 🛠️ Annotation Workflow

### Step 1: Setup

1. Open `data/annotations/annotation_frame_list.json`
2. Create `data/annotations/ground_truth.json` (or use annotation tool output)
3. Extract frames: `python scripts/extract_annotation_frames.py`
   - Frames saved to `data/annotations/frames/`
   - Detector predictions overlaid for reference (green=vehicle, blue=plate)

### Step 2: Annotate Each Frame

For each frame in the annotation set:

1. **Open Frame Image**
   - File: `data/annotations/frames/{video_id}_frame_{frame_index:06d}.jpg`
   - View detector predictions (reference only, not ground truth!)

2. **Verify Vehicles**
   - Are all visible vehicles detected? (check for false negatives)
   - Are detections correct vehicles? (check for false positives)
   - Draw/adjust vehicle bounding boxes as needed

3. **Verify Plates**
   - Are all visible plates detected? (check for false negatives)
   - Are detections actual plates? (check for false positives)
   - Draw/adjust plate bounding boxes as needed

4. **Read Plate Text**
   - **DO NOT copy OCR predictions**
   - Zoom in on plate crop image
   - Read characters independently
   - If ANY character unreadable: mark as unreadable, don't guess
   - Record exact visible text with spacing

5. **Record Metadata**
   - Mark visibility, orientation, quality flags
   - Associate plates with vehicles
   - Set annotation status

### Step 3: Quality Control

Before submitting annotations:

- [ ] All bounding boxes within image boundaries
- [ ] All `plate_text` fields verified independently (not copied from OCR)
- [ ] No missing required fields
- [ ] Vehicle-plate associations valid
- [ ] Uncertain cases marked with `"uncertain": true`
- [ ] Annotation status set for every frame

---

## 📊 Ground Truth Schema

```json
{
  "annotation_set_id": "cctv_real_set_1",
  "annotator": "string (your name/ID)",
  "annotation_date": "2026-10-28",
  "annotation_tool": "manual | cvat | labelstudio",
  "bounding_box_format": "[x_min, y_min, x_max, y_max]",
  "frames": [
    {
      "video_id": "video_1",
      "video_filename": "WhatsApp Video 2026-10-30 at 6.25.41 AM.mp4",
      "frame_index": 0,
      "timestamp_ms": 0,
      "image_width": 848,
      "image_height": 478,
      "vehicles": [
        {
          "vehicle_id": "v1",
          "vehicle_bbox": [0, 186, 250, 239],
          "vehicle_class": 2,
          "confidence_human": "high | medium | low",
          "notes": "optional notes"
        }
      ],
      "plates": [
        {
          "plate_id": "p1",
          "plate_bbox": [91, 144, 172, 167],
          "plate_text": "MH 12 AB 1234",
          "plate_visibility": "clear",
          "plate_orientation": "rear",
          "associated_vehicle": "v1",
          "quality_flags": {
            "blur": false,
            "occlusion": false,
            "small_size": true,
            "poor_lighting": false,
            "extreme_angle": false,
            "damaged_plate": false
          },
          "annotation_status": "verified",
          "notes": "small but all characters readable"
        }
      ],
      "annotation_status": "verified",
      "annotation_time_seconds": 120,
      "notes": "frame annotation notes"
    }
  ]
}
```

---

## ⚠️ Common Mistakes to Avoid

### ❌ DO NOT:
1. **Copy OCR predictions as ground truth**
   - OCR predictions are what we're trying to validate!
   - Read plate text independently from the image

2. **Guess unreadable characters**
   - If you can't read it, neither can the system
   - Mark as `unreadable`, don't fabricate text

3. **Annotate vehicles not in frame**
   - Only annotate what's actually visible
   - Don't assume vehicles outside frame bounds

4. **Use inconsistent plate text format**
   - Preserve exact spacing: "DL 3C AB 1234" not "DL3CAB1234"
   - Use uppercase for letters
   - Record exactly what you see, including errors/damage

5. **Skip quality control**
   - Always validate before submitting
   - Check all required fields present
   - Verify bounding box coordinates

### ✅ DO:
1. **Zoom in on small plates** to read characters
2. **Mark uncertain cases** explicitly
3. **Use vehicle_id consistently** when tracking across frames
4. **Document ambiguous cases** in notes field
5. **Request second opinion** for difficult frames

---

## 🧪 Validation Script

After annotation, validate your ground truth:

```bash
python scripts/validate_ground_truth.py
```

Checks:
- ✅ All required fields present
- ✅ Bounding boxes within image boundaries
- ✅ Valid enum values
- ✅ Vehicle-plate associations exist
- ✅ No duplicate IDs
- ✅ Consistent formats

---

## 📈 Expected Annotation Time

**Per Frame:**
- Simple frames (0-1 vehicles): 2-3 minutes
- Medium frames (2-4 vehicles): 5-8 minutes  
- Complex frames (5+ vehicles): 10-15 minutes

**Total Estimate:**
- Video 1 (30 frames): 3-4 hours
- Video 2 (40 frames): 4-6 hours
- Video 3 (4 frames): 15-20 minutes
- **Total: 8-11 hours** for complete annotation

**Tips for Efficiency:**
- Batch similar frames together
- Use keyboard shortcuts in annotation tool
- Take breaks to avoid fatigue errors
- Do quality control in separate session

---

## 📁 File Structure

```
data/annotations/
├── annotation_frame_list.json      # Frame selection (generated)
├── ground_truth.json                # Your annotations (create this)
├── ground_truth_validated.json      # After validation (generated)
├── frames/                          # Extracted frame images (generated)
│   ├── video_1_frame_000000.jpg
│   ├── video_1_frame_000003.jpg
│   └── ...
└── README.md                        # This guide
```

---

## 🚀 Next Steps

1. **Extract Frames:** Run `python scripts/extract_annotation_frames.py`
2. **Choose Annotation Tool:**
   - Manual: Use image viewer + JSON editor
   - CVAT: Import frames and export to JSON
   - Label Studio: Import frames and export to JSON
3. **Annotate:** Follow workflow above
4. **Validate:** Run validation script
5. **Calculate Metrics:** Run `python scripts/validate_anpr_accuracy.py`

---

## 📞 Questions?

**Unclear Cases:**
- If plate visibility is ambiguous, mark as `"uncertain"`
- If vehicle class is ambiguous, use best judgment and note
- If unsure about vehicle-plate association, leave `null`

**Technical Issues:**
- Bounding box tool not working: check coordinate format
- Frame not loading: verify file path in annotation_frame_list.json
- Validation errors: read error message, fix schema issues

**Annotation Quality:**
- Aim for 100% accuracy on ground truth
- When in doubt, mark as uncertain rather than guessing
- Second annotator review recommended for critical frames

---

**Document Version:** 1.0  
**Last Updated:** 2026-10-28  
**Status:** Ready for annotation
