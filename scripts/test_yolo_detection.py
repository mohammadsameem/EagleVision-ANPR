"""Test YOLOv8 vehicle detection on traffic video."""
import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import json

# COCO class names for vehicles
VEHICLE_CLASSES = {
    2: 'car',
    3: 'motorcycle', 
    5: 'bus',
    7: 'truck'
}

def test_vehicle_detection(video_path: str, output_dir: str = "data/test_videos"):
    """
    Test YOLOv8 vehicle detection on video frames.
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save annotated frames
    """
    print("=" * 70)
    print("YOLOV8 VEHICLE DETECTION TEST")
    print("=" * 70)
    print(f"Video: {video_path}")
    print(f"Model: YOLOv8n")
    print()
    
    # Load model
    print("Loading YOLOv8n model...")
    model = YOLO('yolov8n.pt')
    print("[OK] Model loaded")
    print()
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("[ERROR] Cannot open video")
        return
    
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Sample frames: first, 25%, 50%, 75%, last
    sample_indices = [
        0,
        frame_count // 4,
        frame_count // 2,
        3 * frame_count // 4,
        frame_count - 1
    ]
    
    all_detections = []
    frames_with_detections = 0
    total_vehicles = 0
    
    print(f"Testing on {len(sample_indices)} sampled frames...")
    print()
    
    for frame_idx in sample_indices:
        # Read frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if not ret:
            print(f"[!] Could not read frame {frame_idx}")
            continue
        
        # Run detection
        results = model(frame, verbose=False)
        
        # Extract vehicle detections
        frame_detections = []
        for r in results:
            boxes = r.boxes
            for i in range(len(boxes)):
                cls = int(boxes.cls[i])
                if cls in VEHICLE_CLASSES:
                    conf = float(boxes.conf[i])
                    bbox = boxes.xyxy[i].cpu().numpy()
                    
                    detection = {
                        'frame': frame_idx,
                        'class_id': cls,
                        'class_name': VEHICLE_CLASSES[cls],
                        'confidence': conf,
                        'bbox': bbox.tolist()
                    }
                    frame_detections.append(detection)
                    
                    # Draw on frame
                    x1, y1, x2, y2 = bbox.astype(int)
                    color = (0, 255, 0)  # Green
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Add label
                    label = f"{VEHICLE_CLASSES[cls]} {conf:.2f}"
                    cv2.putText(frame, label, (x1, y1-10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Report
        timestamp = frame_idx / fps
        if frame_detections:
            print(f"Frame {frame_idx:3d} (t={timestamp:.2f}s): {len(frame_detections)} vehicle(s)")
            for det in frame_detections:
                print(f"  - {det['class_name']:<10} confidence={det['confidence']:.3f}")
            
            frames_with_detections += 1
            total_vehicles += len(frame_detections)
        else:
            print(f"Frame {frame_idx:3d} (t={timestamp:.2f}s): 0 vehicles")
        
        all_detections.extend(frame_detections)
        
        # Save annotated frame
        output_path = f"{output_dir}/detection_frame_{frame_idx:04d}.jpg"
        cv2.imwrite(output_path, frame)
    
    cap.release()
    
    # Summary
    print()
    print("=" * 70)
    print("DETECTION SUMMARY")
    print("=" * 70)
    print(f"Frames tested:              {len(sample_indices)}")
    print(f"Frames with detections:     {frames_with_detections}")
    print(f"Total vehicle detections:   {total_vehicles}")
    print(f"Average per frame:          {total_vehicles / len(sample_indices):.2f}")
    print()
    
    # Class breakdown
    if all_detections:
        print("Detections by vehicle type:")
        class_counts = {}
        for det in all_detections:
            cls_name = det['class_name']
            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
        
        for cls_name, count in sorted(class_counts.items()):
            print(f"  {cls_name:<10}: {count}")
        print()
        
        # Confidence statistics
        confidences = [det['confidence'] for det in all_detections]
        print("Confidence scores:")
        print(f"  Min:  {min(confidences):.3f}")
        print(f"  Max:  {max(confidences):.3f}")
        print(f"  Mean: {np.mean(confidences):.3f}")
        print(f"  Std:  {np.std(confidences):.3f}")
        print()
    
    # Save detection results as JSON
    output_json = f"{output_dir}/detection_results.json"
    with open(output_json, 'w') as f:
        json.dump({
            'video': video_path,
            'model': 'yolov8n',
            'frames_tested': len(sample_indices),
            'total_detections': total_vehicles,
            'detections': all_detections
        }, f, indent=2)
    
    print(f"Results saved to: {output_json}")
    print(f"Annotated frames saved to: {output_dir}/detection_frame_*.jpg")
    print("=" * 70)
    
    return {
        'frames_tested': len(sample_indices),
        'frames_with_detections': frames_with_detections,
        'total_detections': total_vehicles,
        'detections': all_detections
    }

if __name__ == "__main__":
    video_path = "data/test_videos/traffic_park_720p.mp4"
    results = test_vehicle_detection(video_path)
    
    if results['total_detections'] > 0:
        print("\n[SUCCESS] Vehicle detection is working!")
    else:
        print("\n[WARNING] No vehicles detected - may need different test video")
