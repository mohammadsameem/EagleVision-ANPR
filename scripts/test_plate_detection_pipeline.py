"""
Test plate detection on actual vehicle crops from test video.

This script:
1. Loads the test video
2. Runs vehicle detection
3. Extracts vehicle crops
4. Runs plate detection on each crop
5. Reports actual detection results (no fabrication)
"""
import cv2
import json
import numpy as np
from pathlib import Path
from ultralytics import YOLO
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.plate_detector import PlateDetector

def test_plate_detection_on_video(video_path: str, output_dir: str = "data/plate_detection_test"):
    """
    Test plate detection pipeline on real video.
    
    Args:
        video_path: Path to test video
        output_dir: Directory for test outputs
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print("PLATE DETECTION PIPELINE TEST")
    print("="*80)
    print(f"Video: {video_path}")
    print(f"Output: {output_dir}")
    print()
    
    # Load models
    print("Loading models...")
    vehicle_detector = YOLO("yolov8n.pt")
    plate_detector = PlateDetector(
        model_path="models/plate_detector.pt",
        use_fallback=True,
        confidence_threshold=0.5,
        debug_output_dir=output_dir
    )
    
    if plate_detector.model_available:
        print("[OK] Plate detector using model")
    else:
        print("[!] Plate detector using heuristic fallback")
    print()
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Sample 5 frames
    sample_indices = [0, frame_count // 4, frame_count // 2, 3 * frame_count // 4, frame_count - 1]
    
    all_results = []
    total_vehicles = 0
    total_plates_detected = 0
    plates_by_method = {"yolo_model": 0, "heuristic_fallback": 0}
    
    print(f"Testing on {len(sample_indices)} sampled frames...")
    print()
    
    for frame_idx in sample_indices:
        # Read frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            print(f"[!] Could not read frame {frame_idx}")
            continue
        
        timestamp = frame_idx / fps
        print(f"Frame {frame_idx:3d} (t={timestamp:.2f}s):")
        
        # Detect vehicles
        vehicle_results = vehicle_detector.predict(
            frame,
            classes=[2, 3, 5, 7],  # car, motorcycle, bus, truck
            verbose=False,
            conf=0.5
        )
        
        vehicles_in_frame = 0
        plates_in_frame = 0
        
        if vehicle_results and vehicle_results[0].boxes:
            vehicles_in_frame = len(vehicle_results[0].boxes)
            print(f"  Vehicles: {vehicles_in_frame}")
            
            for vehicle_idx, box in enumerate(vehicle_results[0].boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
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
                    
                    for plate in plate_detections:
                        px, py, pw, ph = plate["bbox"]
                        plate_crop = vehicle_crop[py:py+ph, px:px+pw]
                        
                        # Save plate crop
                        if plate_crop.size > 0:
                            crop_filename = f"plate_crop_f{frame_idx}_v{vehicle_idx}.jpg"
                            crop_path = output_path / crop_filename
                            cv2.imwrite(str(crop_path), plate_crop)
                        
                        # Record result
                        result = {
                            "frame_index": frame_idx,
                            "timestamp_sec": timestamp,
                            "vehicle_index": vehicle_idx,
                            "vehicle_bbox": [x1, y1, x2-x1, y2-y1],
                            "plate_bbox_relative": plate["bbox"],
                            "plate_bbox_absolute": [
                                x1 + px, y1 + py, pw, ph
                            ],
                            "confidence": plate["confidence"],
                            "method": plate["method"],
                            "class": plate["class"]
                        }
                        all_results.append(result)
                        
                        # Count by method
                        method = plate["method"]
                        plates_by_method[method] = plates_by_method.get(method, 0) + 1
            
            print(f"  Plates:   {plates_in_frame}")
        else:
            print(f"  Vehicles: 0")
        
        total_vehicles += vehicles_in_frame
        total_plates_detected += plates_in_frame
        print()
    
    cap.release()
    
    # Save results JSON
    results_file = output_path / "plate_detection_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "video": video_path,
            "frames_tested": len(sample_indices),
            "total_vehicles": total_vehicles,
            "total_plates_detected": total_plates_detected,
            "plates_by_method": plates_by_method,
            "model_available": plate_detector.model_available,
            "detections": all_results
        }, f, indent=2)
    
    # Print summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Frames tested:          {len(sample_indices)}")
    print(f"Total vehicles:         {total_vehicles}")
    print(f"Total plates detected:  {total_plates_detected}")
    print(f"Detection rate:         {total_plates_detected/total_vehicles*100:.1f}%" if total_vehicles > 0 else "N/A")
    print()
    print("Detections by method:")
    for method, count in plates_by_method.items():
        print(f"  {method:<20}: {count}")
    print()
    print(f"Results saved: {results_file}")
    print(f"Debug images: {output_path}/*.jpg")
    print("="*80)
    
    # Validation notes
    print()
    print("IMPORTANT NOTES:")
    print()
    if not plate_detector.model_available:
        print("[!] Model was not available - results are from heuristic fallback only")
        print("[!] Heuristic crops are NOT real detections")
    else:
        print("[OK] Results are from YOLOv8 plate detection model")
    
    if plates_by_method.get("heuristic_fallback", 0) > 0:
        heuristic_count = plates_by_method["heuristic_fallback"]
        print(f"[!] {heuristic_count} detection(s) used heuristic fallback")
        print("[!] These should not be counted as successful model detections")
    
    print()
    print("TO VERIFY PLATE VISIBILITY:")
    print("1. Open plate crop images in", output_dir)
    print("2. Manually check if actual license plates are visible")
    print("3. Note that SampleLib test video may not have readable plates")
    print()
    
    return {
        "total_vehicles": total_vehicles,
        "total_plates": total_plates_detected,
        "model_used": plate_detector.model_available
    }

if __name__ == "__main__":
    video_path = "data/test_videos/traffic_park_720p.mp4"
    
    if not Path(video_path).exists():
        print(f"[ERROR] Test video not found: {video_path}")
        print("Run vehicle detection validation first to download test video")
        sys.exit(1)
    
    results = test_plate_detection_on_video(video_path)
    
    if results["model_used"]:
        print("\n[SUCCESS] Plate detection model test complete")
    else:
        print("\n[WARNING] Test ran with heuristic fallback only")
        print("Model-based detection was not validated")
