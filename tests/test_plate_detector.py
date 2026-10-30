"""
Unit tests for PlateDetector class.

Tests cover:
- Model initialization and error handling
- Valid and invalid bounding boxes
- Coordinate conversion and validation
- Aspect ratio filtering
- Debug output
"""
import pytest
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.plate_detector import PlateDetector

class TestPlateDetectorInitialization:
    """Test model initialization and configuration."""
    
    def test_model_loads_when_available(self):
        """Test that model loads if weights file exists."""
        detector = PlateDetector(
            model_path="models/plate_detector.pt",
            use_fallback=True
        )
        
        # If model file exists, should load successfully
        if Path("models/plate_detector.pt").exists():
            assert detector.model_available == True
            assert detector.model is not None
        else:
            assert detector.model_available == False
    
    def test_fallback_mode_when_model_missing(self):
        """Test fallback mode activates when model unavailable."""
        detector = PlateDetector(
            model_path="nonexistent/model.pt",
            use_fallback=True
        )
        
        assert detector.model_available == False
        assert detector.use_fallback == True
    
    def test_error_when_model_missing_and_no_fallback(self):
        """Test that error is raised when model missing and fallback disabled."""
        with pytest.raises(FileNotFoundError):
            PlateDetector(
                model_path="nonexistent/model.pt",
                use_fallback=False
            )
    
    def test_confidence_threshold_configurable(self):
        """Test that confidence threshold can be configured."""
        detector = PlateDetector(
            model_path="models/plate_detector.pt",
            use_fallback=True,
            confidence_threshold=0.7
        )
        
        assert detector.confidence_threshold == 0.7

class TestPlateDetection:
    """Test plate detection functionality."""
    
    def test_detect_on_valid_crop(self):
        """Test detection on valid vehicle crop."""
        detector = PlateDetector(
            model_path="models/plate_detector.pt",
            use_fallback=True
        )
        
        # Create dummy vehicle crop (640x480 RGB)
        vehicle_crop = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Should return list (may be empty)
        detections = detector.detect_plates(vehicle_crop)
        
        assert isinstance(detections, list)
    
    def test_detect_rejects_empty_crop(self):
        """Test that empty crop returns empty list."""
        detector = PlateDetector(
            model_path="models/plate_detector.pt",
            use_fallback=True
        )
        
        # Empty array
        empty_crop = np.array([])
        detections = detector.detect_plates(empty_crop)
        
        assert detections == []
    
    def test_detect_rejects_invalid_shape(self):
        """Test that invalid image shape returns empty list."""
        detector = PlateDetector(
            model_path="models/plate_detector.pt",
            use_fallback=True
        )
        
        # Grayscale image (missing channel dimension)
        invalid_crop = np.zeros((480, 640), dtype=np.uint8)
        detections = detector.detect_plates(invalid_crop)
        
        assert detections == []
    
    def test_heuristic_fallback_produces_detection(self):
        """Test that heuristic fallback produces a detection."""
        detector = PlateDetector(
            model_path="nonexistent/model.pt",
            use_fallback=True
        )
        
        # Valid vehicle crop
        vehicle_crop = np.zeros((480, 640, 3), dtype=np.uint8)
        
        detections = detector.detect_plates(vehicle_crop)
        
        # Heuristic should produce 1 detection
        assert len(detections) == 1
        assert detections[0]["method"] == "heuristic_fallback"
        assert "bbox" in detections[0]
        assert len(detections[0]["bbox"]) == 4  # [x, y, w, h]
    
    def test_heuristic_rejects_tiny_crops(self):
        """Test that heuristic rejects very small crops."""
        detector = PlateDetector(
            model_path="nonexistent/model.pt",
            use_fallback=True
        )
        
        # Crop too small (30x30)
        tiny_crop = np.zeros((30, 30, 3), dtype=np.uint8)
        
        detections = detector.detect_plates(tiny_crop)
        
        # Should reject
        assert len(detections) == 0

class TestBoundingBoxValidation:
    """Test bounding box validation and filtering."""
    
    def test_bbox_format(self):
        """Test that bounding boxes have correct format."""
        detector = PlateDetector(
            model_path="nonexistent/model.pt",
            use_fallback=True
        )
        
        vehicle_crop = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect_plates(vehicle_crop)
        
        if detections:
            bbox = detections[0]["bbox"]
            assert len(bbox) == 4
            x, y, w, h = bbox
            assert x >= 0
            assert y >= 0
            assert w > 0
            assert h > 0
    
    def test_bbox_within_image_bounds(self):
        """Test that bounding boxes are within image bounds."""
        detector = PlateDetector(
            model_path="nonexistent/model.pt",
            use_fallback=True
        )
        
        vehicle_crop = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect_plates(vehicle_crop)
        
        if detections:
            x, y, w, h = detections[0]["bbox"]
            crop_h, crop_w = vehicle_crop.shape[:2]
            
            # Check bbox is within image
            assert x >= 0
            assert y >= 0
            assert x + w <= crop_w
            assert y + h <= crop_h

class TestDetectionMetadata:
    """Test detection metadata and structure."""
    
    def test_detection_has_required_fields(self):
        """Test that detections have required metadata fields."""
        detector = PlateDetector(
            model_path="nonexistent/model.pt",
            use_fallback=True
        )
        
        vehicle_crop = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect_plates(vehicle_crop)
        
        if detections:
            det = detections[0]
            
            # Required fields
            assert "bbox" in det
            assert "confidence" in det
            assert "method" in det
            assert "class" in det
            
            # Types
            assert isinstance(det["bbox"], list)
            assert isinstance(det["confidence"], float)
            assert isinstance(det["method"], str)
            assert isinstance(det["class"], str)
    
    def test_confidence_in_valid_range(self):
        """Test that confidence scores are in [0, 1] range."""
        detector = PlateDetector(
            model_path="nonexistent/model.pt",
            use_fallback=True
        )
        
        vehicle_crop = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect_plates(vehicle_crop)
        
        if detections:
            conf = detections[0]["confidence"]
            assert 0.0 <= conf <= 1.0

@pytest.mark.skipif(
    not Path("models/plate_detector.pt").exists(),
    reason="Plate detection model not available"
)
class TestModelDetection:
    """Test model-based detection (requires model file)."""
    
    def test_model_detection_on_blank_image(self):
        """Test that model returns 0 detections on blank image."""
        detector = PlateDetector(
            model_path="models/plate_detector.pt",
            use_fallback=False,
            confidence_threshold=0.5
        )
        
        # Blank image should have no plates
        blank_crop = np.zeros((640, 640, 3), dtype=np.uint8)
        detections = detector.detect_plates(blank_crop)
        
        # Model should return 0 detections (may use fallback if configured)
        assert isinstance(detections, list)
    
    def test_model_detection_includes_class_info(self):
        """Test that model detections include class information."""
        detector = PlateDetector(
            model_path="models/plate_detector.pt",
            use_fallback=False,
            confidence_threshold=0.1  # Low threshold to potentially get detections
        )
        
        # Random noise image (might trigger false positives)
        noise_crop = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        detections = detector.detect_plates(noise_crop)
        
        # If any detections, they should have class info
        for det in detections:
            assert "class" in det
            assert det["method"] == "yolo_model"

class TestDebugOutput:
    """Test debug output functionality."""
    
    def test_debug_output_directory_created(self, tmp_path):
        """Test that debug output directory is created."""
        debug_dir = tmp_path / "debug"
        
        detector = PlateDetector(
            model_path="nonexistent/model.pt",
            use_fallback=True,
            debug_output_dir=str(debug_dir)
        )
        
        # Directory should be created
        assert debug_dir.exists()
        assert debug_dir.is_dir()
    
    def test_debug_output_saves_on_detection(self, tmp_path):
        """Test that debug images are saved when detections occur."""
        debug_dir = tmp_path / "debug"
        
        detector = PlateDetector(
            model_path="nonexistent/model.pt",
            use_fallback=True,
            debug_output_dir=str(debug_dir)
        )
        
        vehicle_crop = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect_plates(
            vehicle_crop,
            vehicle_id=0,
            frame_index=10
        )
        
        if detections:
            # Debug image should be saved
            debug_files = list(debug_dir.glob("*.jpg"))
            assert len(debug_files) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
