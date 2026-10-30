"""Test vehicle detection on sample video frames."""
import cv2
from ultralytics import YOLO
import numpy as np

def test_detection(video_path: str):
    """Test YOLOv8 vehicle detection on video."""
    print(f"Testing detection on: {video_path}")
    print("=" * 60)
    
    # Load YOLOv8 model
    print("Loading YOLOv8n model...")
    model = YOLO('yolov8n.pt')
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("[ERROR] Cannot open video")
        return
    
    # Test on first 10 frames
    frame_idx = 0
    total_detections = 0
    
    while frame_idx < 10:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Run detection
        results = model(frame, verbose=False)
        
        # Count vehicle detections (classes: car=2, motorcycle=3, bus=5, truck=7)
        vehicle_classes = [2, 3, 5, 7]
        detections = []
        
        for r in results:
            boxes = r.boxes
            for i in range(len(boxes)):
                cls = int(boxes.cls[i])
                conf = float(boxes.conf[i])
                if cls in vehicle_classes:
                    detections.append({
                        'class': cls,
                        'confidence': conf,
                        'bbox': boxes.xyxy[i].tolist()
                    })
        
        if detections:
            print(f"Frame {frame_idx}: {len(detections)} vehicle(s) detected")
            for det in detections:
                print(f"  - Class {det['class']}, Conf: {det['confidence']:.3f}")
            total_detections += len(detections)
        else:
            print(f"Frame {frame_idx}: 0 vehicles")
        
        frame_idx += 1
    
    cap.release()
    print(f"\nTotal: {total_detections} detections across {frame_idx} frames")
    print()

def test_brightened_frame(video_path: str):
    """Test detection on artificially brightened frame."""
    print(f"Testing with brightened frame from: {video_path}")
    print("=" * 60)
    
    model = YOLO('yolov8n.pt')
    
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("[ERROR] Cannot read frame")
        return
    
    # Brighten frame by multiplying pixel values
    brightened = np.clip(frame.astype(np.float32) * 5.0, 0, 255).astype(np.uint8)
    
    print(f"Original frame - mean: {frame.mean():.2f}, max: {frame.max()}")
    print(f"Brightened frame - mean: {brightened.mean():.2f}, max: {brightened.max()}")
    
    # Save brightened frame
    output_path = video_path.replace('.mp4', '_brightened.jpg')
    cv2.imwrite(output_path, brightened)
    print(f"Brightened frame saved to: {output_path}")
    
    # Test detection on brightened frame
    results = model(brightened, verbose=False)
    
    vehicle_classes = [2, 3, 5, 7]
    detections = []
    
    for r in results:
        boxes = r.boxes
        for i in range(len(boxes)):
            cls = int(boxes.cls[i])
            conf = float(boxes.conf[i])
            if cls in vehicle_classes:
                detections.append({
                    'class': cls,
                    'confidence': conf
                })
    
    print(f"\nDetections on brightened frame: {len(detections)}")
    if detections:
        for det in detections:
            print(f"  - Class {det['class']}, Conf: {det['confidence']:.3f}")
    print()

if __name__ == "__main__":
    video_path = "public/videos/cam-n4.mp4"
    
    print("TEST 1: Detection on original dark frames")
    print()
    test_detection(video_path)
    
    print("\nTEST 2: Detection on artificially brightened frame")
    print()
    test_brightened_frame(video_path)
