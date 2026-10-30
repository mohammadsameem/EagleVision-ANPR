"""
Inspect real CCTV video metadata before processing.
"""
import cv2
import sys
from pathlib import Path
import json

def inspect_video(video_path: Path) -> dict:
    """Extract video metadata."""
    cap = cv2.VideoCapture(str(video_path))
    
    if not cap.isOpened():
        return {"error": "Failed to open video"}
    
    metadata = {
        "filename": video_path.name,
        "path": str(video_path),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration_seconds": None,
        "codec": int(cap.get(cv2.CAP_PROP_FOURCC)),
        "file_size_mb": video_path.stat().st_size / (1024 * 1024)
    }
    
    if metadata["fps"] > 0:
        metadata["duration_seconds"] = metadata["frame_count"] / metadata["fps"]
    
    # Read first frame to verify readability
    ret, frame = cap.read()
    metadata["first_frame_readable"] = ret
    
    if ret:
        # Check frame quality
        import numpy as np
        metadata["first_frame_mean_brightness"] = float(np.mean(frame))
        metadata["first_frame_std"] = float(np.std(frame))
    
    cap.release()
    return metadata

def main():
    videos_dir = Path("data/test_videos")
    
    # Find WhatsApp videos
    video_files = list(videos_dir.glob("WhatsApp Video*.mp4"))
    
    if not video_files:
        print("❌ No WhatsApp videos found in data/test_videos/")
        sys.exit(1)
    
    print(f"Found {len(video_files)} CCTV videos\n")
    print("="*100)
    
    all_metadata = {}
    
    for video_file in sorted(video_files):
        print(f"\n📹 {video_file.name}")
        print("-"*100)
        
        metadata = inspect_video(video_file)
        all_metadata[video_file.name] = metadata
        
        if "error" in metadata:
            print(f"❌ {metadata['error']}")
            continue
        
        print(f"Resolution:  {metadata['width']}×{metadata['height']}")
        print(f"FPS:         {metadata['fps']:.2f}")
        print(f"Duration:    {metadata['duration_seconds']:.2f} seconds")
        print(f"Frames:      {metadata['frame_count']}")
        print(f"File size:   {metadata['file_size_mb']:.2f} MB")
        print(f"Readable:    {'✅' if metadata['first_frame_readable'] else '❌'}")
        
        if metadata['first_frame_readable']:
            print(f"Brightness:  {metadata['first_frame_mean_brightness']:.1f}/255")
            print(f"Contrast:    {metadata['first_frame_std']:.1f} (std dev)")
    
    print("\n" + "="*100)
    
    # Save metadata
    output_file = videos_dir / "cctv_videos_metadata.json"
    with open(output_file, 'w') as f:
        json.dump(all_metadata, f, indent=2)
    
    print(f"\n✅ Metadata saved to: {output_file}")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total videos: {len(video_files)}")
    readable_count = sum(1 for m in all_metadata.values() if m.get('first_frame_readable'))
    print(f"   Readable: {readable_count}/{len(video_files)}")
    
    total_duration = sum(m.get('duration_seconds', 0) for m in all_metadata.values())
    print(f"   Total duration: {total_duration:.1f} seconds")
    
    total_size = sum(m.get('file_size_mb', 0) for m in all_metadata.values())
    print(f"   Total size: {total_size:.1f} MB")

if __name__ == '__main__':
    main()
