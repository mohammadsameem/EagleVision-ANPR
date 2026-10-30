"""Validate downloaded test video file."""
import cv2
import sys
from pathlib import Path

def validate_video(video_path: str) -> dict:
    """
    Validate video file and return metadata.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dictionary with validation results and metadata
    """
    result = {
        'valid': False,
        'path': video_path,
        'exists': False,
        'opens': False,
        'has_frames': False,
        'has_visible_content': False,
        'metadata': {}
    }
    
    # Check file exists
    path = Path(video_path)
    if not path.exists():
        print(f"[ERROR] File does not exist: {video_path}")
        return result
    
    result['exists'] = True
    result['metadata']['file_size_mb'] = path.stat().st_size / (1024 * 1024)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return result
    
    result['opens'] = True
    
    # Get metadata
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = frame_count / fps if fps > 0 else 0
    
    result['metadata'].update({
        'frame_count': frame_count,
        'width': width,
        'height': height,
        'fps': fps,
        'duration_sec': duration
    })
    
    if frame_count == 0:
        print(f"[ERROR] Video has 0 frames")
        cap.release()
        return result
    
    result['has_frames'] = True
    
    # Sample frames throughout the video
    sample_indices = [0, frame_count // 4, frame_count // 2, 3 * frame_count // 4, frame_count - 1]
    sample_indices = [i for i in sample_indices if 0 <= i < frame_count]
    
    frames_analyzed = 0
    total_mean = 0
    total_std = 0
    
    for idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
        frames_analyzed += 1
        mean_val = frame.mean()
        std_val = frame.std()
        total_mean += mean_val
        total_std += std_val
        
        # Save first frame for inspection
        if idx == 0:
            output_path = video_path.replace('.mp4', '_frame0.jpg')
            cv2.imwrite(output_path, frame)
            result['metadata']['sample_frame'] = output_path
    
    cap.release()
    
    if frames_analyzed > 0:
        avg_mean = total_mean / frames_analyzed
        avg_std = total_std / frames_analyzed
        
        result['metadata']['avg_pixel_mean'] = avg_mean
        result['metadata']['avg_pixel_std'] = avg_std
        
        # Check if content is visible (not too dark, has variation)
        if avg_mean > 30 and avg_std > 15:
            result['has_visible_content'] = True
        else:
            print(f"[WARNING] Video may be too dark or low contrast")
            print(f"  Average pixel mean: {avg_mean:.2f} (expected > 30)")
            print(f"  Average pixel std: {avg_std:.2f} (expected > 15)")
    
    # Overall validation
    result['valid'] = all([
        result['exists'],
        result['opens'],
        result['has_frames'],
        result['has_visible_content']
    ])
    
    return result

def print_validation_report(result: dict):
    """Print validation report."""
    print("\n" + "=" * 70)
    print("VIDEO VALIDATION REPORT")
    print("=" * 70)
    print(f"File: {result['path']}")
    print(f"Overall Status: {'[OK] VALID' if result['valid'] else '[FAIL] INVALID'}")
    print()
    
    print("Checks:")
    print(f"  File exists:        {'[OK]' if result['exists'] else '[FAIL]'}")
    print(f"  Video opens:        {'[OK]' if result['opens'] else '[FAIL]'}")
    print(f"  Has frames:         {'[OK]' if result['has_frames'] else '[FAIL]'}")
    print(f"  Visible content:    {'[OK]' if result['has_visible_content'] else '[FAIL]'}")
    print()
    
    if result['metadata']:
        print("Metadata:")
        meta = result['metadata']
        print(f"  File size:          {meta.get('file_size_mb', 0):.2f} MB")
        print(f"  Dimensions:         {meta.get('width', 0)}x{meta.get('height', 0)}")
        print(f"  Frame count:        {meta.get('frame_count', 0)}")
        print(f"  FPS:                {meta.get('fps', 0):.2f}")
        print(f"  Duration:           {meta.get('duration_sec', 0):.2f}s")
        
        if 'avg_pixel_mean' in meta:
            print(f"  Avg pixel mean:     {meta['avg_pixel_mean']:.2f}")
            print(f"  Avg pixel std:      {meta['avg_pixel_std']:.2f}")
        
        if 'sample_frame' in meta:
            print(f"  Sample frame saved: {meta['sample_frame']}")
    
    print("=" * 70)
    print()

if __name__ == "__main__":
    video_path = "data/test_videos/traffic_park_720p.mp4"
    
    result = validate_video(video_path)
    print_validation_report(result)
    
    if result['valid']:
        print("[SUCCESS] Video is valid and ready for testing")
        sys.exit(0)
    else:
        print("[FAILURE] Video validation failed")
        sys.exit(1)
