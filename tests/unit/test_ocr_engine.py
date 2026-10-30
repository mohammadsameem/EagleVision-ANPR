"""
Unit tests for Hybrid OCR Engine.

Tests OCR functionality with mock data and various edge cases.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ocr_engine import HybridOCREngine


class TestHybridOCREngine:
    """Test suite for HybridOCREngine"""
    
    def test_init_no_engines_available(self):
        """Test initialization when no OCR engines are available"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', False):
            engine = HybridOCREngine()
            assert engine.paddle is None
            assert engine.easy is None
    
    def test_init_easyocr_only(self):
        """Test initialization with only EasyOCR available"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            mock_reader.return_value = Mock()
            engine = HybridOCREngine()
            assert engine.paddle is None
            assert engine.easy is not None
    
    def test_recognize_unreadable_no_engines(self):
        """Test recognize returns UNREADABLE when no engines available"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', False):
            engine = HybridOCREngine()
            
            # Create fake plate crop
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop)
            
            assert result["final_text"] == "UNREADABLE"
            assert result["final_engine"] == "unreadable"
            assert result["needs_review"] is True
            assert result["paddleocr_text"] is None
            assert result["easyocr_text"] is None
    
    def test_recognize_exact_match_high_confidence(self):
        """Test exact match with high confidence (no review needed)"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock EasyOCR to return good result
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "MH 12 AB 1234", 0.95)
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop, confidence_threshold=0.70)
            
            assert result["easyocr_text"] == "MH 12 AB 1234"
            assert result["easyocr_conf"] == 0.95
            assert result["final_text"] == "MH 12 AB 1234"
            assert result["final_engine"] == "easyocr"
            assert result["format_valid"] is True
            assert result["needs_review"] is False
    
    def test_recognize_low_confidence_needs_review(self):
        """Test low confidence result triggers review"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock EasyOCR to return low confidence
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "MH 12 AB 1234", 0.45)
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop, confidence_threshold=0.70)
            
            assert result["easyocr_conf"] == 0.45
            assert result["needs_review"] is True
    
    def test_recognize_invalid_format_needs_review(self):
        """Test invalid plate format triggers review"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock EasyOCR to return invalid format
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "INVALID123", 0.95)
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop)
            
            assert result["format_valid"] is False
            assert result["needs_review"] is True
    
    def test_recognize_empty_output(self):
        """Test empty OCR output"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock EasyOCR to return empty
            mock_easy = Mock()
            mock_easy.readtext.return_value = []
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop)
            
            assert result["easyocr_text"] == ""
            assert result["final_text"] == "UNREADABLE"
            assert result["needs_review"] is True
    
    def test_recognize_multiple_text_regions(self):
        """Test OCR with multiple detected text regions"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock EasyOCR to return multiple regions
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "MH", 0.90),
                (None, "12", 0.92),
                (None, "AB", 0.88),
                (None, "1234", 0.91)
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop)
            
            # Should combine all regions
            assert "MH" in result["easyocr_text"]
            assert "12" in result["easyocr_text"]
            assert "AB" in result["easyocr_text"]
            assert "1234" in result["easyocr_text"]
            
            # Confidence should be average
            expected_conf = (0.90 + 0.92 + 0.88 + 0.91) / 4
            assert abs(result["easyocr_conf"] - expected_conf) < 0.01
    
    def test_recognize_engine_agreement(self):
        """Test both engines run and agree on result (when Paddle confidence below threshold)"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', True), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.PaddleOCR') as mock_paddle, \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock both engines to return same result
            # Use lower Paddle confidence so it doesn't early-return
            mock_paddle_inst = Mock()
            mock_paddle_inst.ocr.return_value = [[
                (None, ("MH 12 AB 1234", 0.65))  # Below threshold
            ]]
            mock_paddle.return_value = mock_paddle_inst
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "MH 12 AB 1234", 0.90)
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop, confidence_threshold=0.70)
            
            # Both should run since Paddle was below threshold
            assert result["paddleocr_text"] == "MH 12 AB 1234"
            assert result["easyocr_text"] == "MH 12 AB 1234"
            assert result["agreement"] is True
            # EasyOCR has higher confidence, should be used
            assert result["final_engine"] == "easyocr"
            assert result["needs_review"] is False
    
    def test_recognize_engine_disagreement(self):
        """Test engines disagree - should flag for review"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', True), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.PaddleOCR') as mock_paddle, \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock engines to return different results
            # Use lower Paddle confidence so it doesn't early-return
            mock_paddle_inst = Mock()
            mock_paddle_inst.ocr.return_value = [[
                (None, ("MH 12 AB 1234", 0.65))  # Below threshold
            ]]
            mock_paddle.return_value = mock_paddle_inst
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "MH 12 AB 123X", 0.68)  # Different and lower confidence
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop, confidence_threshold=0.70)
            
            # Both should run
            assert result["paddleocr_text"] == "MH 12 AB 1234"
            assert result["easyocr_text"] == "MH 12 AB 123X"
            assert result["agreement"] is False
            # Low confidence should trigger review
            assert result["needs_review"] is True
    
    def test_recognize_paddle_higher_confidence(self):
        """Test PaddleOCR preferred when higher confidence"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', True), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.PaddleOCR') as mock_paddle, \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock PaddleOCR with higher confidence
            mock_paddle_inst = Mock()
            mock_paddle_inst.ocr.return_value = [[
                (None, ("MH 12 AB 1234", 0.95))
            ]]
            mock_paddle.return_value = mock_paddle_inst
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "MH 12 AB 1235", 0.80)
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop, confidence_threshold=0.70)
            
            # Should use PaddleOCR result (higher confidence and valid format)
            assert result["final_engine"] == "paddleocr"
            assert result["final_text"] == "MH 12 AB 1234"
    
    def test_recognize_ocr_exception_handling(self):
        """Test graceful handling of OCR exceptions"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', False), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Mock EasyOCR to raise exception
            mock_easy = Mock()
            mock_easy.readtext.side_effect = Exception("OCR failed")
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop)
            
            # Should return UNREADABLE without crashing
            assert result["final_text"] == "UNREADABLE"
            assert result["easyocr_text"] == ""
    
    def test_recognize_disagreement_high_confidence(self):
        """Test disagreement flagged even with high confidence"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', True), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.PaddleOCR') as mock_paddle, \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # Both engines high confidence but disagree
            mock_paddle_inst = Mock()
            mock_paddle_inst.ocr.return_value = [[
                (None, ("MH 12 AB 1234", 0.65))  # Below threshold, so runs EasyOCR
            ]]
            mock_paddle.return_value = mock_paddle_inst
            
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "MH 12 AB 1235", 0.95)  # High confidence, different
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop, confidence_threshold=0.70)
            
            # Should flag for review despite high EasyOCR confidence
            assert result["agreement"] is False
            assert result["needs_review"] is True
            assert result["easyocr_conf"] == 0.95  # High confidence
    
    def test_recognize_one_engine_empty_text(self):
        """Test when one engine returns empty text"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', True), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.PaddleOCR') as mock_paddle, \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # PaddleOCR returns empty
            mock_paddle_inst = Mock()
            mock_paddle_inst.ocr.return_value = [[]]
            mock_paddle.return_value = mock_paddle_inst
            
            # EasyOCR returns text
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "MH 12 AB 1234", 0.85)
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop, confidence_threshold=0.70)
            
            # Should use EasyOCR result
            assert result["paddleocr_text"] == ""
            assert result["easyocr_text"] == "MH 12 AB 1234"
            assert result["final_engine"] == "easyocr"
            assert result["agreement"] is None  # Not compared since Paddle empty
    
    def test_recognize_paddle_exception(self):
        """Test when PaddleOCR raises exception"""
        with patch('src.ocr_engine.PADDLE_AVAILABLE', True), \
             patch('src.ocr_engine.EASY_AVAILABLE', True), \
             patch('src.ocr_engine.PaddleOCR') as mock_paddle, \
             patch('src.ocr_engine.easyocr.Reader') as mock_reader:
            
            # PaddleOCR raises exception
            mock_paddle_inst = Mock()
            mock_paddle_inst.ocr.side_effect = Exception("Paddle failed")
            mock_paddle.return_value = mock_paddle_inst
            
            # EasyOCR works
            mock_easy = Mock()
            mock_easy.readtext.return_value = [
                (None, "MH 12 AB 1234", 0.85)
            ]
            mock_reader.return_value = mock_easy
            
            engine = HybridOCREngine()
            plate_crop = np.zeros((50, 200, 3), dtype=np.uint8)
            
            result = engine.recognize(plate_crop, confidence_threshold=0.70)
            
            # Should fall back to EasyOCR
            assert result["paddleocr_text"] == ""
            assert result["easyocr_text"] == "MH 12 AB 1234"
            assert result["final_engine"] == "easyocr"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
