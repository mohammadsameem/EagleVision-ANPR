"""
Complete ANPR pipeline: Video -> Detection -> Tracking -> Plate Detection -> OCR

Note: This implementation requires ultralytics, opencv, and OCR engines to be installed.
Falls back gracefully when dependencies are not available.
"""
import logging
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Try to import dependencies
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics not available - vehicle detection disabled")

try:
    from src.video_processor import VideoProcessor
    VIDEO_PROCESSOR_AVAILABLE = True
except ImportError:
    VIDEO_PROCESSOR_AVAILABLE = False

try:
    from src.plate_detector import PlateDetector
    PLATE_DETECTOR_AVAILABLE = True
except ImportError:
    PLATE_DETECTOR_AVAILABLE = False

try:
    from src.ocr_engine import HybridOCREngine
    OCR_ENGINE_AVAILABLE = True
except ImportError:
    OCR_ENGINE_AVAILABLE = False

class ANPRPipeline:
    """
    Complete ANPR pipeline with graceful degradation.
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize ANPR pipeline.
        
        Args:
            config: Configuration dict with optional keys:
                - vehicle_model: Path to YOLOv8 model (default: "yolov8n.pt")
                - use_gpu: Use GPU acceleration (default: False)
                - confidence_threshold: OCR confidence threshold (default: 0.70)
        """
        config = config or {}
        self.config = config
        
        logger.info("="*60)
        logger.info("Initializing ANPR Pipeline")
        logger.info("="*60)
        
        # Initialize vehicle detector
        self.vehicle_detector = None
        if YOLO_AVAILABLE:
            vehicle_model = config.get("vehicle_model", "yolov8n.pt")
            try:
                self.vehicle_detector = YOLO(vehicle_model)
                logger.info(f"✅ Vehicle detector loaded: {vehicle_model}")
            except Exception as e:
                logger.error(f"❌ Failed to load vehicle detector: {e}")
        else:
            logger.warning("⚠️  Vehicle detector not available (ultralytics not installed)")
        
        # Initialize plate detector
        self.plate_detector = None
        if PLATE_DETECTOR_AVAILABLE:
            try:
                self.plate_detector = PlateDetector(use_fallback=True)
                if self.plate_detector.model_available:
                    logger.info("✅ Plate detector loaded (model)")
                else:
                    logger.info("⚠️  Plate detector using heuristic fallback")
            except Exception as e:
                logger.error(f"❌ Failed to initialize plate detector: {e}")
        else:
            logger.warning("⚠️  Plate detector not available")
        
        # Initialize OCR engine
        self.ocr_engine = None
        if OCR_ENGINE_AVAILABLE:
            try:
                use_gpu = config.get("use_gpu", False)
                self.ocr_engine = HybridOCREngine(use_gpu=use_gpu)
                logger.info("✅ OCR engine initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OCR engine: {e}")
        else:
            logger.warning("⚠️  OCR engine not available")
        
        self.confidence_threshold = config.get("confidence_threshold", 0.70)
        
        logger.info("="*60)
    
    def process_video(self, video_path: str, fps: int = 5) -> List[Dict[str, Any]]:
        """
        Process video and return ANPR results.
        
        Args:
            video_path: Path to video file
            fps: Processing frame rate (default: 5)
        
        Returns:
            List of detection dicts with OCR results
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {video_path}")
        logger.info(f"Target FPS: {fps}")
        logger.info(f"{'='*60}\n")
        
        results = []
        start_time = time.time()
        
        if not VIDEO_PROCESSOR_AVAILABLE:
            logger.error("VideoProcessor not available - cannot process video")
            return results
        
        with VideoProcessor(video_path, target_fps=fps) as processor:
            metadata = processor.get_metadata()
            logger.info(f"Expected frames to process: ~{int(metadata['duration_sec'] * fps)}")
            
            for frame_data in processor.extract_frames():
                frame_results = self._process_frame(frame_data)
                results.extend(frame_results)
        
        elapsed = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing complete")
        logger.info(f"Total detections: {len(results)}")
        logger.info(f"Time elapsed: {elapsed:.2f}s")
        logger.info(f"Average FPS: {len(results)/elapsed:.2f}" if elapsed > 0 else "N/A")
        logger.info(f"{'='*60}\n")
        
        return results
    
    def _process_frame(self, frame_data: dict) -> List[Dict[str, Any]]:
        """
        Process single frame through pipeline.
        
        Args:
            frame_data: Dict with frame_index, source_frame, timestamp_ms, image
        
        Returns:
            List of detections for this frame
        """
        frame = frame_data["image"]
        detections = []
        
        if not self.vehicle_detector:
            # Cannot process without vehicle detector
            return []
        
        # 1. Detect vehicles
        try:
            vehicle_results = self.vehicle_detector.predict(
                frame,
                classes=[2, 3, 5, 7],  # car, motorcycle, bus, truck
                verbose=False,
                conf=0.5
            )
        except Exception as e:
            logger.error(f"Vehicle detection failed on frame {frame_data['frame_index']}: {e}")
            return []
        
        if not vehicle_results or not vehicle_results[0].boxes:
            return []
        
        # 2. Process each detected vehicle
        for idx, box in enumerate(vehicle_results[0].boxes):
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            vehicle_bbox = [int(x1), int(y1), int(x2-x1), int(y2-y1)]
            
            # Extract vehicle crop
            vehicle_crop = frame[int(y1):int(y2), int(x1):int(x2)]
            
            if vehicle_crop.size == 0:
                continue
            
            detection = {
                "frame_index": frame_data["frame_index"],
                "source_frame": frame_data["source_frame"],
                "timestamp_ms": frame_data["timestamp_ms"],
                "vehicle_bbox": vehicle_bbox,
                "vehicle_confidence": float(box.conf[0]),
                "vehicle_class": int(box.cls[0]),
                "plate_bbox": None,
                "plate_confidence": None,
                "plate_method": None,
                "ocr_result": None
            }
            
            # 3. Detect plate within vehicle (if detector available)
            if self.plate_detector:
                try:
                    plates = self.plate_detector.detect_plates(vehicle_crop)
                    
                    if plates:
                        # Take highest confidence plate
                        best_plate = max(plates, key=lambda p: p["confidence"])
                        detection["plate_bbox"] = best_plate["bbox"]
                        detection["plate_confidence"] = best_plate["confidence"]
                        detection["plate_method"] = best_plate.get("method", "unknown")
                        
                        # Extract plate crop
                        px, py, pw, ph = best_plate["bbox"]
                        plate_crop = vehicle_crop[py:py+ph, px:px+pw]
                        
                        # 4. Run OCR (if available)
                        if plate_crop.size > 0 and self.ocr_engine:
                            try:
                                ocr_start = time.time()
                                ocr_result = self.ocr_engine.recognize(
                                    plate_crop,
                                    confidence_threshold=self.confidence_threshold
                                )
                                ocr_result["processing_time_ms"] = int(
                                    (time.time() - ocr_start) * 1000
                                )
                                detection["ocr_result"] = ocr_result
                            except Exception as e:
                                logger.error(f"OCR failed: {e}")
                
                except Exception as e:
                    logger.error(f"Plate detection failed: {e}")
            
            detections.append(detection)
        
        return detections
    
    def get_capabilities(self) -> dict:
        """Return pipeline capabilities based on available components"""
        return {
            "vehicle_detection": self.vehicle_detector is not None,
            "plate_detection": self.plate_detector is not None,
            "plate_detection_method": "model" if (self.plate_detector and self.plate_detector.model_available) else "heuristic" if self.plate_detector else "unavailable",
            "ocr": self.ocr_engine is not None,
            "ocr_engines": {
                "paddleocr": self.ocr_engine.paddle is not None if self.ocr_engine else False,
                "easyocr": self.ocr_engine.easy is not None if self.ocr_engine else False
            } if self.ocr_engine else {"paddleocr": False, "easyocr": False}
        }
