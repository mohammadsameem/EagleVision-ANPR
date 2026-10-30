"""Create a test video with simulated vehicle (white rectangle) on gray background."""
import cv2
import numpy as np

def create_test_video(output_path: str, duration: int = 3, fps: int = 24):
    """
    Create a simple test video with a moving white rectangle (simulated vehicle).
    
    Args:
        output_path: Output video file path
        duration: Video duration in seconds
        fps: Frames per second
    """
    width, height = 640, 360
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = duration * fps
    
    for frame_idx in range(total_frames):
        # Create gray background
        frame = np.ones((height, width, 3), dtype=np.uint8) * 128
        
        # Calculate vehicle position (moving left to right)
        progress = frame_idx / total_frames
        vehicle_x = int(50 + progress * (width - 150))
        vehicle_y = height // 2 - 40
        vehicle_w = 100
        vehicle_h = 80
        
        # Draw white "vehicle"
        cv2.rectangle(frame, 
                     (vehicle_x, vehicle_y),
                     (vehicle_x + vehicle_w, vehicle_y + vehicle_h),
                     (200, 200, 200), -1)
        
        # Draw darker "license plate" area at bottom of vehicle
        plate_h = 15
        plate_w = 50
        plate_x = vehicle_x + (vehicle_w - plate_w) // 2
        plate_y = vehicle_y + vehicle_h - plate_h - 5
        
        cv2.rectangle(frame,
                     (plate_x, plate_y),
                     (plate_x + plate_w, plate_y + plate_h),
                     (50, 50, 50), -1)
        
        # Add some text on the plate
        cv2.putText(frame, "ABC123", 
                   (plate_x + 2, plate_y + 11),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
        
        out.write(frame)
    
    out.release()
    print(f"Test video created: {output_path}")
    print(f"  Duration: {duration}s @ {fps}fps = {total_frames} frames")
    print(f"  Resolution: {width}x{height}")
    print(f"  Content: Moving white rectangle with simulated license plate")

if __name__ == "__main__":
    create_test_video("public/videos/test_vehicle.mp4", duration=3, fps=24)
