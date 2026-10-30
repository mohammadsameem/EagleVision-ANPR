"""Inspect video file properties and content."""
import cv2
import sys
import numpy as np

def inspect_video(video_path: str):
    """Inspect video file and display properties."""
    print(f"Inspecting: {video_path}")
    print("=" * 60)
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("[ERROR] Cannot open video file")
        return
    
    # Get video properties
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Video opened: True")
    print(f"Frame count: {frame_count}")
    print(f"Dimensions: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Duration: {frame_count/fps:.2f}s" if fps > 0 else "Duration: N/A")
    print()
    
    # Read and analyze first frame
    ret, frame = cap.read()
    
    if ret:
        print(f"First frame read: True")
        print(f"Frame shape: {frame.shape}")
        print(f"Frame dtype: {frame.dtype}")
        print(f"Frame mean pixel value: {frame.mean():.2f}")
        print(f"Frame min/max: {frame.min()}/{frame.max()}")
        
        # Check if frame is mostly black
        if frame.mean() < 10:
            print("[WARNING] Frame appears to be mostly black")
        
        # Save first frame for visual inspection
        output_path = video_path.replace('.mp4', '_first_frame.jpg')
        cv2.imwrite(output_path, frame)
        print(f"First frame saved to: {output_path}")
    else:
        print(f"First frame read: False")
        print("[ERROR] Cannot read first frame")
    
    cap.release()
    print()

if __name__ == "__main__":
    videos = [
        "public/videos/cam-n4.mp4",
        "public/videos/cam-w2.mp4",
        "public/videos/cam-s1.mp4"
    ]
    
    for video in videos:
        inspect_video(video)
        print()
