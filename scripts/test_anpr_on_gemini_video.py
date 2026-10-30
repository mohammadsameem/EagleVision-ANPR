"""
Test complete ANPR pipeline on gemini generated video.

Uses:
- YOLOv8n vehicle detector
- YOLOv8n plate detector (Koushim model)
- EasyOCR (PaddleOCR if available)

Reports actual results without fabrication.
"""
import cv2
import json
import numpy as np
from pathlib import Path
from ultralytics import YOLO
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.plate_detector import PlateDetector

# Try to import OCR engines
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False

def run_anpr_pipeline(video_path: str, target_fps: int = 5, output_dir: str = "data/gemini_anpr_test"):
    """
    Run complete ANPR pipeline on video.
    
    Args:
        video_path: Path to video file
        target_fps: Processing frame rate
        output_dir: Output directory for results
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print("EAGLEVISION ANPR PIPELINE TEST - GEMINI VIDEO")
    print("="*80)
    print(f"Video: {video_path}")
    print(f"Output: {output_dir}")
    print(f"Target FPS: {target_fps}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Load models
    print("Loading models...")
    vehicle_detector = YOLO("yolov8n.pt")
    print("  [OK] Vehicle detector: yolov8n.pt")
    
    plate_detector = PlateDetector(
        model_path="models/plate_detector.pt",
        use_fallback=False,  # Do not use fallback - test real model only
        confidence_threshold=0.5,
        debug_output_dir=str(output_path / "plate_debug")
    )
    
    if not plate_detector.model_available:
        print("  [ERROR] Plate detection model not available")
        print("  Model path: models/plate_detector.pt")
        return
    
    print(f"  [OK] Plate detector: models/plate_detector.pt")
    print(f"       Model available: {plate_detector.model_available}")
    print(f"       Confidence threshold: {plate_detector.confidence_threshold}")
    
    # Initialize OCR
    ocr_easy = None
    ocr_paddle = None
    
    if EASYOCR_AVAILABLE:
        try:
            ocr_easy = easyocr.Reader(['en'], gpu=False)
            print("  [OK] EasyOCR initialized")
        except Exception as e:
            print(f"  [!] EasyOCR failed: {e}")
    
    if PADDLEOCR_AVAILABLE:
        try:
            ocr_paddle = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            print("  [OK] PaddleOCR initialized")
        except Exception as e:
            print(f"  [!] PaddleOCR failed: {e}")
    
    if not ocr_easy and not ocr_paddle:
        print("  [!] No OCR engines available")
    
    print()
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return
    
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / video_fps
    
    print("Video properties:")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {video_fps}")
    print(f"  Frames: {frame_count}")
    print(f"  Duration: {duration:.2f}s")
    print()
    
    # Calculate frame sampling
    frame_interval = int(video_fps / target_fps)
    frames_to_process = list(range(0, frame_count, frame_interval))
    
    print(f"Processing {len(frames_to_process)} frames at {target_fps} FPS")
    print(f"Frame interval: {frame_interval}")
    print()
    
    # Process frames
    all_results = []
    total_vehicles = 0
    total_plates = 0
    frames_with_vehicles = 0
    frames_with_plates = 0
    
    print("Processing frames...")
    print()
    
    for process_idx, frame_idx in enumerate(frames_to_process):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            print(f"[!] Could not read frame {frame_idx}")
            continue
        
        timestamp_ms = int((frame_idx / video_fps) * 1000)
        
        # Save original frame
        if process_idx < 5:  # Save first 5 processed frames
            frame_path = output_path / f"original_frame_{frame_idx:04d}.jpg"
            cv2.imwrite(str(frame_path), frame)
        
        # Detect vehicles
        vehicle_results = vehicle_detector.predict(
            frame,
            classes=[2, 3, 5, 7],  # car, motorcycle, bus, truck
            verbose=False,
            conf=0.3  # Lower threshold to catch more vehicles
        )
        
        vehicles_in_frame = 0
        plates_in_frame = 0
        
        if vehicle_results and vehicle_results[0].boxes and len(vehicle_results[0].boxes) > 0:
            vehicles_in_frame = len(vehicle_results[0].boxes)
            frames_with_vehicles += 1
            
            # Create annotated frame with vehicle bboxes
            annotated_frame = frame.copy()
            
            for vehicle_idx, box in enumerate(vehicle_results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                vehicle_conf = float(box.conf[0].cpu().numpy())
                vehicle_cls = int(box.cls[0].cpu().numpy())
                
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Draw vehicle bbox on annotated frame
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"Vehicle {vehicle_conf:.2f}",
                           (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Extract vehicle crop
                vehicle_crop = frame[y1:y2, x1:x2]
                
                if vehicle_crop.size == 0:
                    continue
                
                # Detect plates in vehicle
                plate_detections = plate_detector.detect_plates(
                    vehicle_crop,
                    vehicle_id=vehicle_idx,
                    frame_index=frame_idx
                )
                
                if plate_detections:
                    plates_in_frame += len(plate_detections)
                    
                    for plate_idx, plate in enumerate(plate_detections):
                        px, py, pw, ph = plate["bbox"]
                        plate_conf = plate["confidence"]
                        plate_method = plate["method"]
                        
                        # Only count real model detections
                        if plate_method != "yolo_model":
                            continue  # Skip heuristic crops
                        
                        # Extract plate crop
                        plate_crop = vehicle_crop[py:py+ph, px:px+pw]
                        
                        if plate_crop.size == 0:
                            continue
                        
                        # Save plate crop
                        crop_filename = f"plate_f{frame_idx:04d}_v{vehicle_idx}_p{plate_idx}.jpg"
                        crop_path = output_path / crop_filename
                        cv2.imwrite(str(crop_path), plate_crop)
                        
                        # Draw plate bbox on annotated frame (in original frame coordinates)
                        plate_x1 = x1 + px
                        plate_y1 = y1 + py
                        plate_x2 = plate_x1 + pw
                        plate_y2 = plate_y1 + ph
                        
                        cv2.rectangle(annotated_frame, (plate_x1, plate_y1), (plate_x2, plate_y2), (255, 0, 0), 2)
                        cv2.putText(annotated_frame, f"Plate {plate_conf:.2f}",
                                   (plate_x1, plate_y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
                        
                        # Run OCR
                        ocr_results = {}
                        
                        if ocr_easy:
                            try:
                                easy_result = ocr_easy.readtext(plate_crop)
                                if easy_result:
                                    ocr_results["easyocr"] = {
                                        "text": " ".join([r[1] for r in easy_result]),
                                        "confidence": float(np.mean([r[2] for r in easy_result])),
                                        "raw": easy_result
                                    }
                            except Exception as e:
                                ocr_results["easyocr"] = {"error": str(e)}
                        
                        if ocr_paddle:
                            try:
                                paddle_result = ocr_paddle.ocr(plate_crop, cls=True)
                                if paddle_result and paddle_result[0]:
                                    texts = [line[1][0] for line in paddle_result[0]]
                                    confs = [line[1][1] for line in paddle_result[0]]
                                    ocr_results["paddleocr"] = {
                                        "text": " ".join(texts),
                                        "confidence": float(np.mean(confs)) if confs else 0.0,
                                        "raw": paddle_result
                                    }
                            except Exception as e:
                                ocr_results["paddleocr"] = {"error": str(e)}
                        
                        # Record result
                        result = {
                            "frame_index": frame_idx,
                            "source_frame": frame_idx,
                            "timestamp_ms": timestamp_ms,
                            "vehicle_index": vehicle_idx,
                            "vehicle_bbox": [x1, y1, x2-x1, y2-y1],
                            "vehicle_confidence": vehicle_conf,
                            "vehicle_class": vehicle_cls,
                            "plate_bbox_relative": [px, py, pw, ph],
                            "plate_bbox_absolute": [plate_x1, plate_y1, pw, ph],
                            "plate_confidence": plate_conf,
                            "plate_method": plate_method,
                            "plate_crop_file": crop_filename,
                            "ocr_results": ocr_results
                        }
                        all_results.append(result)
            
            # Save annotated frame
            if process_idx < 10:  # Save first 10 annotated frames
                annotated_path = output_path / f"annotated_frame_{frame_idx:04d}.jpg"
                cv2.imwrite(str(annotated_path), annotated_frame)
        
        # Print progress
        if vehicles_in_frame > 0 or plates_in_frame > 0:
            print(f"Frame {frame_idx:4d} (t={timestamp_ms/1000:.2f}s): "
                  f"vehicles={vehicles_in_frame}, plates={plates_in_frame}")
        
        total_vehicles += vehicles_in_frame
        total_plates += plates_in_frame
        if plates_in_frame > 0:
            frames_with_plates += 1
    
    cap.release()
    
    # Save results JSON
    results_file = output_path / "anpr_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "video": video_path,
            "video_properties": {
                "resolution": f"{width}x{height}",
                "fps": video_fps,
                "frame_count": frame_count,
                "duration_sec": duration
            },
            "processing": {
                "target_fps": target_fps,
                "frames_processed": len(frames_to_process),
                "frame_interval": frame_interval
            },
            "detection_summary": {
                "total_vehicles": total_vehicles,
                "total_plates": total_plates,
                "frames_with_vehicles": frames_with_vehicles,
                "frames_with_plates": frames_with_plates,
                "detection_rate": f"{total_plates/total_vehicles*100:.1f}%" if total_vehicles > 0 else "N/A"
            },
            "models": {
                "vehicle_detector": "yolov8n.pt",
                "plate_detector": "models/plate_detector.pt (Koushim YOLOv8n)",
                "plate_model_available": plate_detector.model_available,
                "easyocr_available": EASYOCR_AVAILABLE and ocr_easy is not None,
                "paddleocr_available": PADDLEOCR_AVAILABLE and ocr_paddle is not None
            },
            "detections": all_results
        }, f, indent=2)
    
    # Print summary
    print()
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Frames processed:       {len(frames_to_process)}")
    print(f"Frames with vehicles:   {frames_with_vehicles}")
    print(f"Frames with plates:     {frames_with_plates}")
    print(f"Total vehicles:         {total_vehicles}")
    print(f"Total plates:           {total_plates}")
    print(f"Detection rate:         {total_plates/total_vehicles*100:.1f}%" if total_vehicles > 0 else "N/A")
    print()
    print(f"Results saved: {results_file}")
    print(f"Plate crops:   {output_path}/*.jpg")
    print(f"Annotations:   {output_path}/annotated_frame_*.jpg")
    print("="*80)
    
    # Honest assessment
    print()
    print("VALIDATION NOTES:")
    print()
    if total_plates == 0:
        print("[!] Zero plates detected.")
        print("    Possible causes:")
        print("    - Video may not contain visible license plates")
        print("    - Plates may be too small/blurred for model")
        print("    - Model trained on different plate types")
        print("    - Confidence threshold too high")
        print("    - AI-generated video may have artificial/inconsistent plates")
    else:
        print(f"[OK] {total_plates} plate(s) detected using YOLOv8 model")
        print("     Note: This is synthetic/AI-generated footage")
        print("     Use for pipeline testing, not accuracy measurement")
    
    if not (EASYOCR_AVAILABLE and ocr_easy) and not (PADDLEOCR_AVAILABLE and ocr_paddle):
        print()
        print("[!] No OCR engines available - install easyocr or paddleocr")
    
    print()
    print("IMPORTANT: This video appears to be AI-generated.")
    print("Registration numbers may be artificial or inconsistent.")
    print("Do not report precision/recall without verified ground truth.")
    print()
    
    return {
        "frames_processed": len(frames_to_process),
        "total_vehicles": total_vehicles,
        "total_plates": total_plates,
        "output_dir": str(output_path)
    }

if __name__ == "__main__":
    video_path = "data/test_videos/gemini_generated_video_0eb4eec1.mp4"
    
    if not Path(video_path).exists():
        print(f"[ERROR] Video not found: {video_path}")
        print("Expected path: data/test_videos/gemini_generated_video_0eb4eec1.mp4")
        sys.exit(1)
    
    results = run_anpr_pipeline(video_path, target_fps=5)
    
    if results:
        print(f"\n[SUCCESS] Pipeline test complete")
        print(f"Results in: {results['output_dir']}")
    else:
        print("\n[FAILURE] Pipeline test failed")
        sys.exit(1)
