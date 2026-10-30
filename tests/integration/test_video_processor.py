"""
Test video processor.
"""
import pytest
from pathlib import Path
from src.video_processor import VideoProcessor

def test_video_processor_initialization():
    """Test video processor can be created"""
    sample_video = "public/videos/cam-n4.mp4"
    
    if not Path(sample_video).exists():
        pytest.skip(f"Sample video not found: {sample_video}")
    
    processor = VideoProcessor(sample_video, target_fps=5)
    assert processor is not None
    assert processor.target_fps == 5

def test_video_processor_opens_valid_video():
    """Test processor opens and reads metadata from valid video"""
    sample_video = "public/videos/cam-n4.mp4"
    
    if not Path(sample_video).exists():
        pytest.skip(f"Sample video not found: {sample_video}")
    
    with VideoProcessor(sample_video, target_fps=5) as processor:
        assert processor.source_fps > 0
        assert processor.total_frames > 0
        assert processor.duration_sec > 0
        
        metadata = processor.get_metadata()
        assert "source_fps" in metadata
        assert "total_frames" in metadata
        assert metadata["target_fps"] == 5

def test_video_processor_extracts_frames():
    """Test frame extraction with timestamp preservation"""
    sample_video = "public/videos/cam-n4.mp4"
    
    if not Path(sample_video).exists():
        pytest.skip(f"Sample video not found: {sample_video}")
    
    frames_processed = 0
    with VideoProcessor(sample_video, target_fps=2) as processor:
        for frame_data in processor.extract_frames():
            # Check frame data structure
            assert "frame_index" in frame_data
            assert "source_frame" in frame_data
            assert "timestamp_ms" in frame_data
            assert "image" in frame_data
            
            # Check types
            assert isinstance(frame_data["frame_index"], int)
            assert isinstance(frame_data["timestamp_ms"], int)
            assert frame_data["image"] is not None
            
            frames_processed += 1
            
            # Only process first 10 frames for quick test
            if frames_processed >= 10:
                break
    
    assert frames_processed > 0, "Should extract at least one frame"
    print(f"\n✅ Extracted {frames_processed} frames from video")

def test_video_processor_timestamp_preservation():
    """Test that timestamps are preserved correctly"""
    sample_video = "public/videos/cam-n4.mp4"
    
    if not Path(sample_video).exists():
        pytest.skip(f"Sample video not found: {sample_video}")
    
    timestamps = []
    with VideoProcessor(sample_video, target_fps=5) as processor:
        for frame_data in processor.extract_frames():
            timestamps.append(frame_data["timestamp_ms"])
            
            # Only check first 20 frames
            if len(timestamps) >= 20:
                break
    
    # Timestamps should be monotonically increasing
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i-1], "Timestamps should not decrease"
    
    print(f"\n✅ Timestamps preserved correctly: {timestamps[0]}ms to {timestamps[-1]}ms")
