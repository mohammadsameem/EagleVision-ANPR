"""Validate gemini generated video properties and sample frames."""
import cv2
import sys
from pathlib import Path

def validate_video(video_path: str):
    """Validate video file and extract sample frames."""
    print("="*70)
    print("GEMINI VIDEO VALIDATION")
    print("="*70)
    print(f"Video: {video_path}")
    print()
    
    # Check file exists
    if not Path(video_path).exists():
        print(f"[ERROR] Video not found: {video_path}")
        return False
    
    file_size = Path(video_path).stat().st_size / (1024 * 1024)
    print(f"File size: {file_size:.2f} MB")
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("[ERROR] Cannot open video")
        return False
    
    # Get metadata
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = frame_count / fps if fps > 0 else 0
    
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Frame count: {frame_count}")
    print(f"Duration: {duration:.2f}s")
    print()
    
    # Sample first 3 frames
    print("Sampling first 3 frames...")
    output_dir = Path("data/gemini_video_validation")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for frame_idx in range(min(3, frame_count)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if ret:
            mean_val = frame.mean()
            std_val = frame.std()
            
            # Save frame
            output_path = output_dir / f"frame_{frame_idx:03d}.jpg"
            cv2.imwrite(str(output_path), frame)
            
            print(f"Frame {frame_idx}: mean={mean_val:.2f}, std={std_val:.2f}")
    
    cap.release()
    
    print()
    print(f"Sample frames saved to: {output_dir}")
    print("="*70)
    return True

if __name__ == "__main__":
    video_path = "data/test_videos/gemini_generated_video_0eb4eec1.mp4"
    
    # Try alternative path if first doesn't exist
    if not Path(video_path).exists():
        video_path = "public/assets/aistudio/gemini_generated_video_0eb4eec1_ad35fc48.mp4"
    
    if validate_video(video_path):
        sys.exit(0)
    else:
        sys.exit(1)
