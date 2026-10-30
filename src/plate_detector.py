"""
License plate detection using YOLOv8 model.
Model source and license documented in models/README.md

Falls back to heuristic cropping if model not available.
"""
import numpy as np
import os
import logging
import cv2
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics not available - plate detection will use fallback")

class PlateDetector:
    """
    License plate detector with model-based detection and heuristic fallback.
    
    Uses YOLOv8n model trained specifically for license plate detection.
    Falls back to heuristic cropping if model is unavailable.
    """
    
    def __init__(
        self, 
        model_path: str = "models/plate_detector.pt", 
        use_fallback: bool = True,
        confidence_threshold: float = 0.5,
        debug_output_dir: Optional[str] = None
    ):
        """
        Initialize plate detector.
        
        Args:
            model_path: Path to YOLO plate detection model
            use_fallback: If True, use heuristic when model unavailable
            confidence_threshold: Minimum detection confidence (0.0-1.0)
            debug_output_dir: If provided, save debug images to this directory
        """
        self.model = None
        self.use_fallback = use_fallback
        self.model_available = False
        self.confidence_threshold = confidence_threshold
        self.debug_output_dir = debug_output_dir
        
        if debug_output_dir:
            Path(debug_output_dir).mkdir(parents=True, exist_ok=True)
        
        if YOLO_AVAILABLE and os.path.exists(model_path):
            try:
                self.model = YOLO(model_path)
                self.model_available = True
                logger.info(f"✅ Loaded plate detection model: {model_path}")
                logger.info(f"   Model classes: {self.model.names}")
            except Exception as e:
                logger.warning(f"Failed to load plate model: {e}")
        
        if not self.model_available:
            if use_fallback:
                logger.warning(
                    "⚠️  Plate detection model not available. "
                    "Using heuristic fallback (lower accuracy expected)."
                )
            else:
                raise FileNotFoundError(
                    f"Plate detection model not found at {model_path}. "
                    f"Model weights must be downloaded first."
                )
    
    def detect_plates(
        self, 
        vehicle_crop: np.ndarray,
        vehicle_id: Optional[int] = None,
        frame_index: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect license plates within vehicle crop.
        
        Args:
            vehicle_crop: BGR image of vehicle region
            vehicle_id: Optional vehicle ID for debug output
            frame_index: Optional frame index for debug output
        
        Returns:
            List of detections: [{"bbox": [x,y,w,h], "confidence": float, "method": str, "class": str}]
        """
        if vehicle_crop is None or vehicle_crop.size == 0:
            logger.warning("Empty vehicle crop provided")
            return []
        
        # Validate image
        if len(vehicle_crop.shape) != 3 or vehicle_crop.shape[2] != 3:
            logger.warning(f"Invalid vehicle crop shape: {vehicle_crop.shape}")
            return []
        
        if self.model_available:
            detections = self._detect_with_model(vehicle_crop)
        elif self.use_fallback:
            detections = self._detect_with_heuristic(vehicle_crop)
        else:
            return []
        
        # Save debug output if enabled
        if self.debug_output_dir and detections:
            self._save_debug_output(vehicle_crop, detections, vehicle_id, frame_index)
        
        return detections
    
    def _detect_with_model(self, vehicle_crop: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect plates using YOLOv8 model.
        
        Args:
            vehicle_crop: BGR image of vehicle region
            
        Returns:
            List of plate detections with bboxes, confidence, and metadata
        """
        try:
            results = self.model.predict(
                vehicle_crop, 
                conf=self.confidence_threshold,
                verbose=False,
                imgsz=640  # Model trained on 640x640
            )
            
            detections = []
            for result in results:
                if result.boxes is None or len(result.boxes) == 0:
                    continue
                    
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    cls = int(box.cls[0].cpu().numpy())
                    
                    # Validate bounding box
                    h, w = vehicle_crop.shape[:2]
                    x1, y1 = max(0, int(x1)), max(0, int(y1))
                    x2, y2 = min(w, int(x2)), min(h, int(y2))
                    
                    bbox_w = x2 - x1
                    bbox_h = y2 - y1
                    
                    # Filter invalid detections
                    if bbox_w < 10 or bbox_h < 5:
                        logger.debug(f"Rejected tiny plate bbox: {bbox_w}x{bbox_h}")
                        continue
                    
                    # Check aspect ratio (plates are typically wide)
                    aspect_ratio = bbox_w / bbox_h if bbox_h > 0 else 0
                    if aspect_ratio < 1.0 or aspect_ratio > 10.0:
                        logger.debug(f"Rejected implausible aspect ratio: {aspect_ratio:.2f}")
                        continue
                    
                    detections.append({
                        "bbox": [x1, y1, bbox_w, bbox_h],
                        "confidence": confidence,
                        "class": self.model.names.get(cls, f"class_{cls}"),
                        "method": "yolo_model",
                        "class_id": cls
                    })
            
            if not detections:
                logger.debug("Model returned 0 valid plate detections")
            else:
                logger.debug(f"Model detected {len(detections)} plate(s)")
            
            return detections
            
        except Exception as e:
            logger.error(f"Model detection failed: {e}")
            if self.use_fallback:
                logger.info("Falling back to heuristic detection")
                return self._detect_with_heuristic(vehicle_crop)
            return []
    
    def _detect_with_heuristic(self, vehicle_crop: np.ndarray) -> List[Dict[str, Any]]:
        """
        Fallback heuristic: Crop lower portion of vehicle.
        This is NOT a real detection - just a reasonable guess.
        
        Args:
            vehicle_crop: BGR image of vehicle region
            
        Returns:
            List with single heuristic detection
        """
        h, w = vehicle_crop.shape[:2]
        
        if h < 50 or w < 50:
            logger.debug("Vehicle crop too small for heuristic detection")
            return []
        
        # Typical plate location: lower 30% of vehicle, centered horizontally
        plate_height = int(h * 0.3)
        plate_y = h - plate_height
        
        # Add some horizontal margin (plates aren't full vehicle width)
        margin_x = int(w * 0.15)
        plate_x = margin_x
        plate_width = w - 2 * margin_x
        
        logger.debug("Using heuristic fallback for plate detection")
        
        return [{
            "bbox": [plate_x, plate_y, plate_width, plate_height],
            "confidence": 0.5,  # Arbitrary - this is a heuristic guess
            "class": "license_plate_heuristic",
            "method": "heuristic_fallback",
            "note": "Heuristic crop, not a real detection. Model weights should be downloaded for accurate detection."
        }]
    
    def _save_debug_output(
        self, 
        vehicle_crop: np.ndarray, 
        detections: List[Dict[str, Any]],
        vehicle_id: Optional[int],
        frame_index: Optional[int]
    ):
        """Save annotated vehicle crop with detected plate bboxes."""
        try:
            annotated = vehicle_crop.copy()
            
            for det in detections:
                x, y, w, h = det["bbox"]
                conf = det["confidence"]
                method = det["method"]
                
                # Color based on method
                color = (0, 255, 0) if method == "yolo_model" else (0, 165, 255)  # Green for model, orange for heuristic
                
                # Draw bounding box
                cv2.rectangle(annotated, (x, y), (x+w, y+h), color, 2)
                
                # Draw label
                label = f"{det['class']} {conf:.2f}"
                cv2.putText(annotated, label, (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Generate filename
            vid_str = f"v{vehicle_id}" if vehicle_id is not None else "vX"
            frame_str = f"f{frame_index}" if frame_index is not None else "fX"
            filename = f"plate_detection_{frame_str}_{vid_str}.jpg"
            
            output_path = os.path.join(self.debug_output_dir, filename)
            cv2.imwrite(output_path, annotated)
            logger.debug(f"Saved debug output: {output_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save debug output: {e}")
