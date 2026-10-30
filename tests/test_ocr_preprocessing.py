"""
Tests for OCR preprocessing and accuracy metrics.
"""
import pytest
import numpy as np
import cv2
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from benchmark_ocr_preprocessing import (
    calculate_levenshtein_distance,
    calculate_character_accuracy,
    normalize_text,
    downsample_image,
    upsample_cubic,
    upsample_lanczos,
    enhance_contrast
)


class TestLevenshteinDistance:
    """Test edit distance calculation."""
    
    def test_identical(self):
        """Test with identical strings."""
        assert calculate_levenshtein_distance("hello", "hello") == 0
        assert calculate_levenshtein_distance("MH12AB1234", "MH12AB1234") == 0
    
    def test_empty(self):
        """Test with empty strings."""
        assert calculate_levenshtein_distance("", "") == 0
        assert calculate_levenshtein_distance("hello", "") == 5
        assert calculate_levenshtein_distance("", "hello") == 5
    
    def test_single_edit(self):
        """Test with single character edits."""
        assert calculate_levenshtein_distance("hello", "hallo") == 1  # substitution
        assert calculate_levenshtein_distance("hello", "helo") == 1   # deletion
        assert calculate_levenshtein_distance("helo", "hello") == 1   # insertion
    
    def test_plate_numbers(self):
        """Test with registration plates."""
        assert calculate_levenshtein_distance("MH12AB1234", "MH12AB1235") == 1
        assert calculate_levenshtein_distance("MH12AB1234", "NH12AB1234") == 1
        assert calculate_levenshtein_distance("MH12AB1234", "MH12AC1234") == 1


class TestCharacterAccuracy:
    """Test character accuracy calculation."""
    
    def test_exact_match(self):
        """Exact match should return 100%."""
        assert calculate_character_accuracy("MH12AB1234", "MH12AB1234") == 100.0
        assert calculate_character_accuracy("", "") == 100.0
    
    def test_empty_strings(self):
        """Test with empty strings."""
        assert calculate_character_accuracy("hello", "") == 0.0
        assert calculate_character_accuracy("", "hello") == 0.0
    
    def test_single_error(self):
        """Test with single character error."""
        # 1 error in 10 chars = 90% accuracy
        assert calculate_character_accuracy("MH12AB1235", "MH12AB1234") == 90.0
    
    def test_multiple_errors(self):
        """Test with multiple errors."""
        # 3 errors in 10 chars = 70% accuracy
        assert calculate_character_accuracy("NH12AC1235", "MH12AB1234") == 70.0
    
    def test_completely_different(self):
        """Completely different strings should return 0%."""
        assert calculate_character_accuracy("AAAAAAAAAA", "BBBBBBBBBB") == 0.0
    
    def test_bounds(self):
        """Accuracy should be bounded between 0 and 100."""
        acc = calculate_character_accuracy("abc", "xyz")
        assert 0.0 <= acc <= 100.0


class TestTextNormalization:
    """Test text normalization."""
    
    def test_uppercase(self):
        """Should convert to uppercase."""
        assert normalize_text("mh12ab1234") == "MH12AB1234"
        assert normalize_text("Mh12Ab1234") == "MH12AB1234"
    
    def test_whitespace(self):
        """Should normalize whitespace."""
        assert normalize_text("MH  12  AB  1234") == "MH 12 AB 1234"
        assert normalize_text("  MH 12 AB 1234  ") == "MH 12 AB 1234"
        assert normalize_text("MH\t12\nAB\r1234") == "MH 12 AB 1234"
    
    def test_combined(self):
        """Should handle case and whitespace together."""
        assert normalize_text("  mh  12  ab  1234  ") == "MH 12 AB 1234"


class TestImageResampling:
    """Test image downsampling and upsampling."""
    
    def test_downsample_dimensions(self):
        """Downsampled image should match target size."""
        image = np.random.randint(0, 255, (110, 440, 3), dtype=np.uint8)
        downsampled = downsample_image(image, (80, 20))
        
        assert downsampled.shape == (20, 80, 3)
    
    def test_upsample_cubic_dimensions(self):
        """Upsampled image should match target size."""
        image = np.random.randint(0, 255, (20, 80, 3), dtype=np.uint8)
        upsampled = upsample_cubic(image, (440, 110))
        
        assert upsampled.shape == (110, 440, 3)
    
    def test_upsample_lanczos_dimensions(self):
        """Lanczos upsampling should match target size."""
        image = np.random.randint(0, 255, (20, 80, 3), dtype=np.uint8)
        upsampled = upsample_lanczos(image, (440, 110))
        
        assert upsampled.shape == (110, 440, 3)
    
    def test_downup_cycle_shape(self):
        """Downsample then upsample should restore shape."""
        original = np.random.randint(0, 255, (110, 440, 3), dtype=np.uint8)
        downsampled = downsample_image(original, (80, 20))
        upsampled = upsample_cubic(downsampled, (440, 110))
        
        assert upsampled.shape == original.shape
    
    def test_downup_cycle_degrades(self):
        """Downsample then upsample should degrade quality."""
        # Create a test pattern with sharp edges
        original = np.zeros((110, 440, 3), dtype=np.uint8)
        original[:, :220] = 255  # Half white, half black
        
        downsampled = downsample_image(original, (80, 20))
        upsampled = upsample_cubic(downsampled, (440, 110))
        
        # Upsampled should not be identical to original
        assert not np.array_equal(upsampled, original)
        
        # But should be similar (high correlation)
        correlation = np.corrcoef(original.flatten(), upsampled.flatten())[0, 1]
        assert correlation > 0.7


class TestContrastEnhancement:
    """Test contrast enhancement."""
    
    def test_enhance_preserves_shape(self):
        """Enhancement should preserve image shape."""
        image = np.random.randint(0, 255, (110, 440, 3), dtype=np.uint8)
        enhanced = enhance_contrast(image)
        
        assert enhanced.shape == image.shape
    
    def test_enhance_preserves_dtype(self):
        """Enhancement should preserve data type."""
        image = np.random.randint(0, 255, (110, 440, 3), dtype=np.uint8)
        enhanced = enhance_contrast(image)
        
        assert enhanced.dtype == np.uint8
    
    def test_enhance_grayscale(self):
        """Enhancement should work on grayscale images."""
        image = np.random.randint(0, 255, (110, 440), dtype=np.uint8)
        enhanced = enhance_contrast(image)
        
        assert enhanced.shape == image.shape
        assert enhanced.dtype == np.uint8


class TestAccuracyMetrics:
    """Test accuracy metric calculations."""
    
    def test_exact_match_counted(self):
        """Exact matches should be counted correctly."""
        gt = "MH 12 AB 1234"
        pred = "MH 12 AB 1234"
        
        gt_norm = normalize_text(gt)
        pred_norm = normalize_text(pred)
        
        assert gt_norm == pred_norm  # Should match
    
    def test_case_insensitive_match(self):
        """Matching should be case-insensitive."""
        gt = "MH 12 AB 1234"
        pred = "mh 12 ab 1234"
        
        gt_norm = normalize_text(gt)
        pred_norm = normalize_text(pred)
        
        assert gt_norm == pred_norm  # Should match
    
    def test_whitespace_normalized(self):
        """Matching should normalize whitespace."""
        gt = "MH 12 AB 1234"
        pred = "MH  12  AB  1234"
        
        gt_norm = normalize_text(gt)
        pred_norm = normalize_text(pred)
        
        assert gt_norm == pred_norm  # Should match
    
    def test_empty_output_detection(self):
        """Empty outputs should be detected."""
        assert normalize_text("") == ""
        assert normalize_text("   ") == ""
        assert normalize_text("\t\n") == ""
    
    def test_character_accuracy_range(self):
        """Character accuracy should be between 0 and 100."""
        test_cases = [
            ("MH12AB1234", "MH12AB1234"),  # Perfect
            ("MH12AB1234", "NH12AB1234"),  # 1 error
            ("MH12AB1234", "XXXXXXXXXX"),  # All errors
            ("MH12AB1234", ""),            # Empty prediction
        ]
        
        for pred, gt in test_cases:
            acc = calculate_character_accuracy(pred, gt)
            assert 0.0 <= acc <= 100.0, f"Accuracy out of range for ({pred}, {gt})"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
