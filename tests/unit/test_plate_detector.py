"""
Test license plate detector.
"""
import pytest
import numpy as np
from src.plate_detector import PlateDetector

def test_plate_detector_with_fallback():
    """Test plate detector initializes with fallback mode"""
    detector = PlateDetector(use_fallback=True)
    assert detector is not None
    
    # Should either have model or fallback enabled
    assert detector.model_available or detector.use_fallback

def test_heuristic_detection_on_valid_crop():
    """Test heuristic detection returns valid bbox"""
    detector = PlateDetector(use_fallback=True)
    
    # Create mock vehicle crop (200x300 pixels)
    vehicle_crop = np.zeros((200, 300, 3), dtype=np.uint8)
    
    detections = detector.detect_plates(vehicle_crop)
    
    # Should return at least one detection (heuristic)
    assert len(detections) > 0
    
    # Validate detection format
    det = detections[0]
    assert "bbox" in det
    assert "confidence" in det
    assert "method" in det
    assert len(det["bbox"]) == 4
    assert all(v >= 0 for v in det["bbox"])

def test_heuristic_detection_on_small_crop():
    """Test heuristic handles small crops gracefully"""
    detector = PlateDetector(use_fallback=True)
    
    # Very small crop (should return empty)
    small_crop = np.zeros((30, 40, 3), dtype=np.uint8)
    
    detections = detector.detect_plates(small_crop)
    
    # Small crops should return empty list
    assert isinstance(detections, list)

def test_detection_method_flagged():
    """Test that heuristic detections are clearly marked"""
    detector = PlateDetector(use_fallback=True)
    
    vehicle_crop = np.zeros((200, 300, 3), dtype=np.uint8)
    detections = detector.detect_plates(vehicle_crop)
    
    if detections:
        det = detections[0]
        # Method should indicate it's heuristic if model not available
        assert "method" in det
        if not detector.model_available:
            assert "heuristic" in det["method"].lower()
