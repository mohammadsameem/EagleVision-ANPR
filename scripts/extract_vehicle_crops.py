"""Extract vehicle crops from test video to manually inspect plate visibility."""
import cv2
from pathlib import Path
from ultralytics import YOLO

def extract_vehicle_crops(video_path: str, output_dir: str = "data/vehicle_crops"):
    """Extract vehicle crops for manual inspection."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("Extracting vehicle crops for manual inspection...")
    print(f"Video: {video_path}")
    print(f"Output: {output_dir}")
    print()
    
    # Load vehicle detector
    model = YOLO("yolov8n.pt")
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Extract from first frame only
    frame_idx = 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("[ERROR] Could not read frame")
        return
    
    # Save full frame
    cv2.imwrite(str(output_path / "full_frame.jpg"), frame)
    print(f"Saved full frame: full_frame.jpg")
    
    # Detect vehicles
    results = model.predict(frame, classes=[2, 3, 5, 7], verbose=False, conf=0.3)
    
    if not results or not results[0].boxes:
        print("[!] No vehicles detected")
        return
    
    print(f"Found {len(results[0].boxes)} vehicles")
    print()
    
    for idx, box in enumerate(results[0].boxes):
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        conf = float(box.conf[0])
        cls = int(box.cls[0])
        
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        
        # Extract crop
        crop = frame[y1:y2, x1:x2]
        
        if crop.size == 0:
            continue
        
        # Save crop
        filename = f"vehicle_{idx}_conf{conf:.2f}.jpg"
        cv2.imwrite(str(output_path / filename), crop)
        
        h, w = crop.shape[:2]
        print(f"Vehicle {idx}: {w}x{h}px, confidence={conf:.3f}, class={cls}")
    
    print()
    print(f"Vehicle crops saved to: {output_dir}")
    print("Manually inspect these images to check for visible license plates")

if __name__ == "__main__":
    extract_vehicle_crops("data/test_videos/traffic_park_720p.mp4")
