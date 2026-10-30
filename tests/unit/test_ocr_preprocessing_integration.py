"""
Unit tests for OCR Engine preprocessing integration.

Tests preprocessing functionality integrated into HybridOCREngine.
"""
import pytest
import numpy as np
import cv2
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ocr_engine import HybridOCREngine


class TestOCRPreprocessingIntegration:
    """Test preprocessing integration in OCR engine"""
    
    def test_preprocessing_disabled(self):
        """Test OCR with preprocessing disabled"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=False)
            
            # Small crop that would trigger preprocessing if enabled
            small_crop = np.zeros((20, 80, 3), dtype=np.uint8)
            result = engine.recognize(small_crop)
            
            assert result["preprocessing"]["enabled"] is False
            assert result["preprocessing"]["applied"] is False
            assert "method" not in result["preprocessing"] or result["preprocessing"]["method"] is None
    
    def test_preprocessing_enabled_small_crop(self):
        """Test preprocessing triggers for small crops"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # Small crop that should trigger preprocessing
            small_crop = np.zeros((20, 80, 3), dtype=np.uint8)
            result = engine.recognize(small_crop)
            
            assert result["preprocessing"]["enabled"] is True
            assert result["preprocessing"]["preprocessed"] is True
            assert result["preprocessing"]["method"] in ['lanczos4', 'cubic']
            assert result["preprocessing"]["original_width"] == 80
            assert result["preprocessing"]["original_height"] == 20
            assert result["preprocessing"]["upscaled_height"] == 60  # Default target
    
    def test_preprocessing_skipped_large_crop(self):
        """Test preprocessing skipped for already large crops"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # Large crop that doesn't need preprocessing
            large_crop = np.zeros((110, 440, 3), dtype=np.uint8)
            result = engine.recognize(large_crop)
            
            assert result["preprocessing"]["enabled"] is True
            assert result["preprocessing"]["preprocessed"] is False
    
    def test_preprocessing_lanczos_method(self):
        """Test Lanczos4 upscaling method"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            engine.upscale_method = 'lanczos'
            
            small_crop = np.zeros((20, 80, 3), dtype=np.uint8)
            result = engine.recognize(small_crop)
            
            assert result["preprocessing"]["method"] == 'lanczos4'
    
    def test_preprocessing_cubic_method(self):
        """Test cubic upscaling method"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            engine.upscale_method = 'cubic'
            
            small_crop = np.zeros((20, 80, 3), dtype=np.uint8)
            result = engine.recognize(small_crop)
            
            assert result["preprocessing"]["method"] == 'cubic'
    
    def test_preprocessing_very_small_crop_flagged(self):
        """Test very small crops flagged as likely unreadable"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "gibberish", 0.5)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # Very small crop (below minimum threshold)
            tiny_crop = np.zeros((8, 30, 3), dtype=np.uint8)
            result = engine.recognize(tiny_crop)
            
            assert result["preprocessing"]["likely_unreadable"] is True
            assert result["needs_review"] is True
    
    def test_preprocessing_preserves_original_crop(self):
        """Test original crop is preserved when requested"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # Create recognizable crop pattern
            small_crop = np.random.randint(0, 255, (20, 80, 3), dtype=np.uint8)
            result = engine.recognize(small_crop, preserve_original=True)
            
            assert "original_crop" in result
            assert isinstance(result["original_crop"], np.ndarray)
            assert result["original_crop"].shape == (20, 80, 3)
            # Verify it's actually the original
            assert np.array_equal(result["original_crop"], small_crop)
    
    def test_preprocessing_correct_dimensions(self):
        """Test upscaling produces correct dimensions"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            engine.target_height = 60
            
            # 80x20 crop should scale to maintain aspect ratio at height 60
            small_crop = np.zeros((20, 80, 3), dtype=np.uint8)
            result = engine.recognize(small_crop)
            
            assert result["preprocessing"]["upscaled_height"] == 60
            expected_width = int(80 * (60 / 20))  # 240
            assert result["preprocessing"]["upscaled_width"] == expected_width
    
    def test_preprocessing_grayscale_support(self):
        """Test preprocessing works with grayscale images"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # Grayscale crop
            gray_crop = np.zeros((20, 80), dtype=np.uint8)
            result = engine.recognize(gray_crop)
            
            # Should process without error
            assert result["preprocessing"]["enabled"] is True
    
    def test_preprocessing_color_crop_support(self):
        """Test preprocessing works with color images"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # BGR color crop
            color_crop = np.zeros((20, 80, 3), dtype=np.uint8)
            result = engine.recognize(color_crop)
            
            # Should process without error
            assert result["preprocessing"]["enabled"] is True
            assert result["preprocessing"]["preprocessed"] is True
    
    def test_preprocessing_empty_crop_handling(self):
        """Test preprocessing handles empty/invalid crops gracefully"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = []
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # Minimal size crop (edge case)
            minimal_crop = np.zeros((5, 10, 3), dtype=np.uint8)
            result = engine.recognize(minimal_crop)
            
            # Should not crash
            assert result["preprocessing"]["enabled"] is True
    
    def test_preprocessing_maintains_ocr_confidence(self):
        """Test preprocessing doesn't affect OCR confidence reporting"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            expected_conf = 0.87
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", expected_conf)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            small_crop = np.zeros((20, 80, 3), dtype=np.uint8)
            result = engine.recognize(small_crop)
            
            # Confidence should be preserved
            assert result["easyocr_conf"] == expected_conf
    
    def test_preprocessing_maintains_review_flags(self):
        """Test preprocessing doesn't interfere with review flag logic"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', True), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.PaddleOCR') as mock_paddle, \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock disagreement between engines
            mock_paddle_inst = Mock()
            mock_paddle_inst.ocr.return_value = [[(None, ("MH 12 AB 1234", 0.65))]]
            mock_paddle.return_value = mock_paddle_inst
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1235", 0.90)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            small_crop = np.zeros((20, 80, 3), dtype=np.uint8)
            
            result = engine.recognize(small_crop)
            
            # Disagreement should still trigger review
            assert result["agreement"] is False
            assert result["needs_review"] is True
    
    def test_preprocessing_integration_with_format_validation(self):
        """Test preprocessing integrates correctly with format validation"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "INVALID", 0.95)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            small_crop = np.zeros((20, 80, 3), dtype=np.uint8)
            result = engine.recognize(small_crop)
            
            # Invalid format should still be flagged for review
            assert result["format_valid"] is False
            assert result["needs_review"] is True


class TestPreprocessingConfiguration:
    """Test preprocessing configuration from environment"""
    
    def test_custom_min_dimensions(self):
        """Test custom minimum dimensions"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', False):
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # Set custom values
            engine.min_width = 100
            engine.min_height = 25
            
            assert engine.min_width == 100
            assert engine.min_height == 25
    
    def test_custom_target_height(self):
        """Test custom target height configuration"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', False):
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # Set custom target height
            engine.target_height = 80
            
            assert engine.target_height == 80
    
    def test_preprocessing_respects_max_dimensions(self):
        """Test preprocessing respects maximum dimension limits"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [(None, "MH 12 AB 1234", 0.85)]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine(enable_preprocessing=True)
            
            # Set max dimensions
            engine.max_width = 200
            engine.max_height = 50
            
            # Crop larger than max should not be upscaled
            large_crop = np.zeros((55, 210, 3), dtype=np.uint8)
            result = engine.recognize(large_crop)
            
            assert result["preprocessing"]["preprocessed"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

