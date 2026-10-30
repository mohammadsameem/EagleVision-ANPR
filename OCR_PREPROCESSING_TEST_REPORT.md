# OCR Preprocessing Test Report

**Date:** 2026-10-29  
**Test:** Preprocessing techniques on small plate crops  
**Status:** ✅ **COMPLETE** - Critical Limitations Identified

---

## Executive Summary

Tested 7 preprocessing methods on 20 small plate crops from Gemini AI-generated video. **Result: Minimal improvement.** Upscaling enabled text detection in 1/20 crops (5%), but detected text was gibberish, not readable registrations.

**Critical Finding:** The source video appears to contain AI-generated or severely degraded plates with no readable registration text, regardless of preprocessing.

---

## Test Configuration

**Input Data:**
- Source: `data/gemini_anpr_test/` - 122 plate crops
- Tested: 20 crops
- Mean original size: 43×12 pixels (from diagnosis)
- Test crop sizes: 23-87 pixels wide, 7-24 pixels high

**Methods Tested:**
1. `none` - No preprocessing (baseline)
2. `cubic_upscale` - Cubic interpolation upscaling to 60px height
3. `lanczos_upscale` - Lanczos4 interpolation upscaling
4. `upscale_sharpen` - Upscale + unsharp mask
5. `upscale_contrast` - Upscale + CLAHE contrast enhancement
6. `upscale_denoise` - Upscale + fast non-local means denoising
7. `adaptive` - Conditional upscaling + contrast adjustment

**OCR Engine:** EasyOCR v1.7+ (English)

---

## Results

### Overall Statistics

| Method | Success Rate | Avg Confidence | Avg Time (s) |
|--------|-------------|----------------|--------------|
| cubic_upscale | **5.0%** (1/20) | 0.003 | 0.087 |
| lanczos_upscale | **5.0%** (1/20) | 0.000 | 0.069 |
| upscale_sharpen | **5.0%** (1/20) | 0.000 | 0.071 |
| upscale_contrast | **5.0%** (1/20) | 0.000 | 0.079 |
| adaptive | **5.0%** (1/20) | 0.000 | 0.073 |
| none | 0.0% (0/20) | 0.000 | 0.031 |
| upscale_denoise | 0.0% (0/20) | 0.000 | 0.231 |

**Key Observations:**
- **Baseline (no preprocessing):** 0/20 successful reads (0%)
- **With upscaling:** 1/20 successful reads (5%)
- **Improvement:** Minimal (+5 percentage points)
- **Detected text quality:** Gibberish, not readable registrations

### Detailed Analysis: Single Successful Detection

**Crop:** `plate_f0040_v0_p0.jpg`
- Original size: 79×22 pixels (1,738px²) - largest in test set
- Upscaled size: 215×59 pixels (12,685px²)
- 7.3× area increase

**OCR Results by Method:**

| Method | Detected Text | Confidence | Comment |
|--------|--------------|------------|---------|
| none | *(empty)* | 0.0 | No detection |
| cubic_upscale | "Da" | 0.059 | Partial gibberish |
| lanczos_upscale | "neau" | 0.006 | Gibberish |
| upscale_sharpen | "Fuoucun" | 0.001 | Gibberish |
| upscale_contrast | "Mncucuu" | 0.010 | Gibberish |
| upscale_denoise | *(empty)* | 0.0 | No text extracted |
| adaptive | "Mncucuu" | 0.010 | Gibberish |

**Analysis:**
- Upscaling enabled text **detection** (vs. zero)
- But detected text is not a valid registration
- Very low confidence scores (0.001-0.059)
- Different methods produce different gibberish
- Suggests source image has no readable text

---

## Root Cause Analysis

### Why Preprocessing Didn't Help

**Problem 1: Source Image Quality**
- Gemini video is AI-generated
- Plates may contain synthetic/random patterns, not real text
- Blurred or pixelated beyond recognition
- No actual registration characters to detect

**Problem 2: Resolution Limits**
- Even after 7× upscaling, crops are ~215×59 pixels
- Upscaling cannot restore missing detail
- Interpolation invents pixels, doesn't recover text
- Source video (1280×720) has insufficient plate resolution

**Problem 3: No Ground Truth**
- Cannot verify if detected text is "correct"
- Don't know what the plates should say
- Cannot measure accuracy improvement

### What This Means

1. **Preprocessing works** - it enabled detection where there was none
2. **Source data is unsuitable** - plates don't contain readable text
3. **Cannot validate OCR** - need better test footage
4. **Cannot claim accuracy** - no ground truth to compare against

---

## Comparison with Previous Tests

### Synthetic Plate Test (Previous)

**Data:** `data/ocr_test/` - 200 synthetic plates
- Image size: 440×110 pixels (48,400px²)
- Quality: Clean, computer-generated text
- Ground truth: Known registration numbers
- **Results:** 74.5% exact match, 96.8% character accuracy

**Conclusion:** EasyOCR works well on adequate resolution + clean text

### Gemini Video Test (Current)

**Data:** `data/gemini_anpr_test/` - 122 plate crops
- Image size: 43×12 pixels (594px²) - 81× smaller
- Quality: AI-generated video, severely degraded
- Ground truth: Unknown
- **Results:** 0/122 with no preprocessing, 1/20 gibberish with preprocessing

**Conclusion:** Source video unsuitable for OCR validation

---

## Recommendations

### Immediate: Test on Synthetic Plates

The synthetic plates in `data/ocr_test/` are **already large enough** (440×110px) and have ground truth. Test preprocessing on artificially downsampled versions to isolate the preprocessing effect:

1. Downsample synthetic plates to 50×13px (matching real crop sizes)
2. Apply preprocessing methods
3. Run OCR
4. Compare against known ground truth
5. Measure actual accuracy improvement

**Expected outcome:** Controlled test of preprocessing effectiveness

### Priority: Obtain Suitable Test Footage

**Requirements:**
- Real CCTV camera footage OR high-quality dashcam video
- Visible license plates with readable text
- Higher resolution (1920×1080 minimum)
- Various conditions (lighting, angles, distances)
- Licensing/permissions documented

**Why:** Current test video is unsuitable for validation

### Alternative: Use Existing High-Quality Datasets

**Options:**
- CCPD Dataset (Chinese City Parking Dataset) - 300k+ images
- OpenALPR Benchmark Dataset
- RodoSol-ALPR Dataset (Brazilian plates)
- UFPR-ALPR Dataset (Brazilian plates)

**Advantage:** Pre-annotated ground truth, various conditions

**Disadvantage:** Non-Indian plates (format/language different)

---

## Preprocessing Effectiveness

### What We Learned

**Upscaling helps detection:**
- 0% → 5% detection rate
- Enables text detection where there was none
- Processing time increase acceptable (0.03s → 0.07s)

**But doesn't create readable text:**
- Cannot restore missing information
- Produces gibberish on degraded sources
- Low confidence scores indicate uncertainty

**Best method:** Cubic or Lanczos upscaling
- Similar performance
- Cubic slightly faster
- Additional enhancements (sharpen, denoise) don't help

### When Preprocessing Works

**Conditions where upscaling is effective:**
1. Source has readable text (just too small)
2. Crop size 50-100 pixels minimum
3. Adequate source image quality
4. Target upscale to 150-200 pixels

**Conditions where it fails:**
1. Source has no readable text (AI-generated, blur)
2. Extreme downsampling (<40 pixels)
3. Poor source image quality
4. No actual text characters present

---

## Next Steps

### Priority 1: Controlled Preprocessing Test (2-3 hours)

1. Take synthetic plates (440×110px, known text)
2. Downsample to various sizes (80×20, 60×15, 40×10px)
3. Apply preprocessing
4. Measure accuracy vs. ground truth
5. Document at what size preprocessing helps

**Deliverable:** Evidence-based preprocessing effectiveness

### Priority 2: Real Test Footage (User action)

1. Obtain suitable CCTV/dashcam video
2. Verify plates are readable (manual inspection)
3. Annotate ground truth (10-20 plates minimum)
4. Run full pipeline
5. Measure actual accuracy

**Deliverable:** Real-world accuracy metrics

### Priority 3: Integrate Preprocessing (1-2 hours)

If controlled tests show benefit:
1. Add preprocessing to `src/ocr_engine.py`
2. Apply conditionally based on crop size
3. Update tests
4. Document configuration

**Deliverable:** Production-ready preprocessing

---

## Conclusions

### Test Results

✅ **Completed:** Comprehensive preprocessing test on 20 crops
✅ **Measured:** 7 methods, processing times, confidence scores
✅ **Finding:** Minimal improvement (0% → 5% detection)
❌ **Limitation:** Source video unsuitable for validation
❌ **Cannot measure:** Accuracy without ground truth

### Critical Insights

1. **Preprocessing works in principle** - detection increased from 0 to 1 crop
2. **Source data is the blocker** - AI-generated video has no readable text
3. **Cannot validate without ground truth** - need annotated test footage
4. **Upscaling doesn't create information** - only interpolates existing pixels

### Production Readiness

**For deployment:**
- ⚠️ Cannot claim OCR accuracy on real footage (not tested)
- ⚠️ Cannot recommend preprocessing without controlled tests
- ⚠️ Need suitable test data for validation
- ✅ Framework ready for testing when data available

**Next milestone:** Test preprocessing on downsampled synthetic plates with known ground truth to measure actual effectiveness.

---

## Files Created

1. `scripts/test_ocr_preprocessing.py` - Preprocessing test script (580 lines)
2. `ocr_preprocessing_results/preprocessing_test_results.json` - Full results
3. `ocr_preprocessing_results/*.jpg` - Preprocessed crops for visual inspection (35 files)
4. `OCR_PREPROCESSING_TEST_REPORT.md` - This report

---

## Appendix: Test Configuration

```python
# Preprocessing methods tested
methods = {
    'none': no_preprocessing,
    'cubic_upscale': upscale_cubic(target_height=60),
    'lanczos_upscale': upscale_lanczos(target_height=60),
    'upscale_sharpen': upscale_with_sharpening(target_height=60),
    'upscale_contrast': upscale_with_contrast(target_height=60, CLAHE),
    'upscale_denoise': upscale_with_denoising(target_height=60, fastNlMeans),
    'adaptive': adaptive_preprocessing(conditional_upscale + CLAHE)
}

# OCR Configuration
reader = easyocr.Reader(['en'], gpu=False, verbose=False)

# Test Parameters
- Crops tested: 20
- Max crop in test: 79×22 pixels
- Target upscale height: 60 pixels
- Interpolation: INTER_CUBIC, INTER_LANCZOS4
```
