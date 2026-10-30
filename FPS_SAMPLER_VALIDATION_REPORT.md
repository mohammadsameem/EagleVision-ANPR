# FPS Sampler Validation Report

**Date:** 2026-10-28  
**Component:** Video Frame Sampling (`src/video_processor.py`)  
**Status:** ✅ VALIDATED & CORRECTED

---

## Executive Summary

The FPS sampler has been **validated and corrected** to properly sample frames at the target frame rate based on video timeline, rather than using a simple frame-skip interval approach. All 13 validation tests pass.

### Key Changes

**Before (Frame Interval Approach):**
- Calculated `frame_interval = source_fps / target_fps`
- Processed every Nth frame (modulo approach)
- **Problem:** Incorrect for non-divisible FPS combinations
- **Example:** 24 FPS → 5 FPS produced 60 frames (should be 50)

**After (Time-Based Sampling):**
- Calculates sample interval: `1000ms / target_fps`
- Samples frames at regular time points (0ms, 200ms, 400ms for 5 FPS)
- **Correct for all FPS combinations**
- **Example:** 24 FPS → 5 FPS now produces 50 frames ✅

---

## Test Results

### Test Suite: `tests/test_fps_sampler.py`

**Total Tests:** 13  
**Passed:** 13 ✅  
**Failed:** 0  
**Duration:** 21.66 seconds

### Detailed Results

#### 1. Basic FPS Sampling Tests

| Test | Source Video | Target FPS | Expected Frames | Actual Frames | Status |
|------|--------------|------------|-----------------|---------------|--------|
| 30 FPS → 1 FPS | traffic_park_720p.mp4 (30 FPS, 5.7s) | 1 | 5-6 | 6 | ✅ PASS |
| 30 FPS → 5 FPS | traffic_park_720p.mp4 (30 FPS, 5.7s) | 5 | 27-29 | 29 | ✅ PASS |
| 30 FPS → 10 FPS | traffic_park_720p.mp4 (30 FPS, 5.7s) | 10 | 56-58 | 57 | ✅ PASS |
| 24 FPS → 1 FPS | gemini_video.mp4 (24 FPS, 10.0s) | 1 | 9-11 | 10 | ✅ PASS |
| 24 FPS → 5 FPS | gemini_video.mp4 (24 FPS, 10.0s) | 5 | 49-51 | 50 | ✅ PASS |

**Tolerance:** ±1 frame (accounts for rounding at video boundaries)

#### 2. Non-Divisible FPS Combinations

**Test:** 24 FPS source → 5 FPS target (24 ÷ 5 = 4.8, non-integer)

- **Expected:** 50 frames (10.0s × 5 FPS)
- **Actual:** 50 frames ✅
- **Previous Implementation:** 60 frames ❌ (incorrect)

This was the **critical fix** - the frame-interval approach failed for non-divisible combinations.

#### 3. Timestamp Validation

| Test | Validation | Status |
|------|------------|--------|
| Timestamps ordered | All timestamps monotonically increasing | ✅ PASS |
| Timestamps within duration | All timestamps ≤ video duration | ✅ PASS |
| Timestamp correspondence | Timestamps match original video timeline | ✅ PASS |

**Example:** 30 FPS @ 5 FPS sampling: 0ms → 5600ms (29 frames)

#### 4. Frame Index Validation

| Test | Validation | Status |
|------|------------|--------|
| Sequential indices | frame_index: 0, 1, 2, ... N-1 | ✅ PASS |
| Valid source frames | All source_frame values within [0, total_frames) | ✅ PASS |
| Increasing source frames | source_frame values strictly increasing | ✅ PASS |

#### 5. Edge Cases

| Test | Scenario | Status |
|------|----------|--------|
| Invalid video file | Raises ValueError | ✅ PASS |
| High target FPS (60 FPS on 30 FPS video) | Processes all source frames | ✅ PASS |
| Repeated sampling | Consistent results across multiple runs | ✅ PASS |

---

## Technical Implementation

### Sampling Algorithm

```python
# Calculate time interval between samples (milliseconds)
sample_interval_ms = 1000.0 / target_fps

# Initialize
next_sample_time_ms = 0

# For each frame in video:
while frame available:
    timestamp_ms = get_frame_timestamp()
    
    # Check if frame is at or past next sample time
    if timestamp_ms >= next_sample_time_ms:
        yield frame
        next_sample_time_ms += sample_interval_ms
```

### Key Properties

1. **Time-based:** Samples based on video timeline, not frame numbers
2. **FPS-agnostic:** Works correctly for any source/target FPS combination
3. **Timestamp-preserving:** Original video timestamps maintained
4. **Deterministic:** Same input produces same output

### Formula

```
Expected frames = ⌊duration_seconds × target_fps⌋
```

**Examples:**
- 5.7s @ 5 FPS = 28.5 → 28-29 frames
- 10.0s @ 5 FPS = 50.0 → 50 frames
- 5.7s @ 1 FPS = 5.7 → 5-6 frames

---

## Validation Coverage

### FPS Combinations Tested

| Source FPS | Target FPS | Divisible? | Status |
|------------|------------|------------|--------|
| 30 | 1 | Yes (30÷1=30) | ✅ |
| 30 | 5 | Yes (30÷5=6) | ✅ |
| 30 | 10 | Yes (30÷10=3) | ✅ |
| 24 | 1 | Yes (24÷1=24) | ✅ |
| 24 | 5 | **No** (24÷5=4.8) | ✅ |
| 30 | 60 | No (target > source) | ✅ |

### Video Durations Tested

- **Short video:** 5.7 seconds (171 frames @ 30 FPS)
- **Medium video:** 10.0 seconds (240 frames @ 24 FPS)

### Edge Cases Tested

1. ✅ Invalid video file path
2. ✅ Target FPS higher than source FPS
3. ✅ Non-divisible FPS combinations
4. ✅ Repeated sampling consistency
5. ✅ Timestamp ordering and validity
6. ✅ Frame index sequencing

---

## Performance Characteristics

### Processing Speed

**Test:** 30 FPS video, 171 frames, 5.7s duration

| Target FPS | Frames Processed | Processing Time | FPS Ratio |
|------------|------------------|-----------------|-----------|
| 1 FPS | 6 | ~1.5s | 35% of source |
| 5 FPS | 29 | ~1.8s | 17% of source |
| 10 FPS | 57 | ~2.1s | 33% of source |

**Note:** Processing time includes frame reading, not inference. Actual ANPR pipeline speed depends on detection and OCR operations.

---

## Important Clarifications

### What This Validates ✅

- Frame sampling accuracy at various FPS rates
- Correct handling of non-divisible FPS combinations
- Timestamp preservation from original video
- Deterministic and consistent sampling behavior

### What This Does NOT Validate ❌

- **OCR accuracy** - unchanged by FPS sampling
- **Plate detection accuracy** - unchanged by FPS sampling
- **Vehicle detection accuracy** - unchanged by FPS sampling
- **End-to-end pipeline performance** - requires separate testing

### Critical Distinction

**Sampling FPS ≠ Processing Speed**

- **Sampling FPS:** How many frames we extract from video (e.g., 5 FPS = 5 frames per second of video)
- **Processing Speed:** How fast we run inference on those frames (e.g., 10 FPS = 10 frames per second of wall time)

These are **independent metrics**.

---

## Comparison: Before vs After

### Before Fix (Frame Interval)

```python
frame_interval = int(source_fps / target_fps)  # e.g., 24/5 = 4
# Process every 4th frame
if frame_number % frame_interval == 0:
    yield frame
# Result: 240 frames / 4 = 60 frames ❌ INCORRECT
```

### After Fix (Time-Based)

```python
sample_interval_ms = 1000 / target_fps  # e.g., 1000/5 = 200ms
# Process frames at 0ms, 200ms, 400ms, ...
if timestamp >= next_sample_time:
    yield frame
    next_sample_time += sample_interval_ms
# Result: 10s × 5 FPS = 50 frames ✅ CORRECT
```

---

## Integration Test Results

**Existing Tests:** `tests/integration/test_video_processor.py`

All 4 existing integration tests continue to pass after the fix:

1. ✅ `test_video_processor_initialization`
2. ✅ `test_video_processor_opens_valid_video`
3. ✅ `test_video_processor_extracts_frames`
4. ✅ `test_video_processor_timestamp_preservation`

**Backward Compatibility:** ✅ Maintained

---

## Recommendations

### For Production Use

1. **Target FPS Selection:**
   - 1 FPS: Very light processing, may miss quick events
   - 5 FPS: Good balance for ANPR (recommended)
   - 10 FPS: More frames, higher processing cost

2. **Expected Frame Counts:**
   - Always calculate: `duration_sec × target_fps`
   - Allow ±1 frame tolerance for rounding

3. **Timestamp Usage:**
   - Use `timestamp_ms` for correlating detections with video timeline
   - Do not confuse sampling rate with inference speed

### Next Steps

1. ✅ **FPS sampler validated** - this task complete
2. **Next:** Validate OCR with suitable test plates
3. **Then:** Complete PaddleOCR vs EasyOCR comparison
4. **After:** End-to-end pipeline validation with ground truth

---

## Files Modified

1. **`src/video_processor.py`**
   - Changed from frame-interval to time-based sampling
   - Updated `extract_frames()` method
   - Updated `get_metadata()` to include sample interval

2. **`tests/test_fps_sampler.py`** (NEW)
   - 13 comprehensive validation tests
   - Tests divisible and non-divisible FPS combinations
   - Edge case coverage

---

## Conclusion

The FPS sampler has been **thoroughly validated and corrected**. The time-based sampling approach now correctly handles all FPS combinations, including non-divisible cases that previously failed.

**Key Achievement:** 24 FPS → 5 FPS now produces the correct 50 frames instead of 60 frames.

**Test Coverage:** 13/13 tests passing, including edge cases and backward compatibility.

**Ready for Production:** Yes, with documented sampling behavior and tolerances.

---

## Test Execution Commands

```bash
# Run FPS sampler validation tests
python -m pytest tests/test_fps_sampler.py -v -s

# Run existing integration tests
python -m pytest tests/integration/test_video_processor.py -v

# Run all tests
python -m pytest tests/ -v
```

**Last Validated:** 2026-10-28  
**All Tests Passing:** ✅ Yes (17/17 total)
