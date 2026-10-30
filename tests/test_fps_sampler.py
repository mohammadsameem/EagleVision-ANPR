"""
FPS Sampler Validation Tests

Tests frame sampling at various target FPS rates to ensure:
1. Correct frame counts within tolerance
2. Valid timestamps corresponding to original video timeline
3. Proper handling of non-divisible FPS combinations
4. Correct final frame handling
5. Robust error handling for invalid inputs
"""
import pytest
import cv2
from pathlib import Path
from src.video_processor import VideoProcessor


class TestFPSSampler:
    """Test suite for FPS sampling validation"""
    
    # Test videos with known properties
    VIDEO_30FPS = "data/test_videos/traffic_park_720p.mp4"  # 30 FPS, 171 frames, 5.7s
    VIDEO_24FPS = "data/test_videos/gemini_generated_video_0eb4eec1.mp4"  # 24 FPS, 240 frames, 10.0s
    
    # Sampling tolerance: allow ±1 frame for rounding differences
    FRAME_COUNT_TOLERANCE = 1
    
    @staticmethod
    def get_video_info(video_path: str) -> dict:
        """Get actual video metadata"""
        cap = cv2.VideoCapture(video_path)
        info = {
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "duration_sec": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
        }
        cap.release()
        return info
    
    @staticmethod
    def calculate_expected_frames(source_fps: float, duration_sec: float, target_fps: int) -> int:
        """
        Calculate expected number of frames for given sampling rate.
        
        Formula: expected_frames = duration_sec * target_fps
        This assumes we sample at regular intervals across the video timeline.
        """
        return int(duration_sec * target_fps)
    
    def test_video_files_exist(self):
        """Verify test videos are available"""
        assert Path(self.VIDEO_30FPS).exists(), f"Test video not found: {self.VIDEO_30FPS}"
        assert Path(self.VIDEO_24FPS).exists(), f"Test video not found: {self.VIDEO_24FPS}"
        print("\n✅ Test videos found")
    
    def test_30fps_video_at_1fps(self):
        """Test 30 FPS video sampled at 1 FPS"""
        video_info = self.get_video_info(self.VIDEO_30FPS)
        expected_frames = self.calculate_expected_frames(
            video_info["fps"], 
            video_info["duration_sec"], 
            target_fps=1
        )
        
        frames = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=1) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        actual_frames = len(frames)
        
        print(f"\n30 FPS → 1 FPS Sampling:")
        print(f"  Source: {video_info['fps']} FPS, {video_info['total_frames']} frames, {video_info['duration_sec']:.2f}s")
        print(f"  Expected: ~{expected_frames} frames (±{self.FRAME_COUNT_TOLERANCE})")
        print(f"  Actual: {actual_frames} frames")
        
        # Assert frame count within tolerance
        assert abs(actual_frames - expected_frames) <= self.FRAME_COUNT_TOLERANCE, \
            f"Frame count mismatch: expected {expected_frames}±{self.FRAME_COUNT_TOLERANCE}, got {actual_frames}"
        
        # Verify timestamps
        self._validate_timestamps(frames, video_info["duration_sec"])
        print("  ✅ Frame count and timestamps valid")
    
    def test_30fps_video_at_5fps(self):
        """Test 30 FPS video sampled at 5 FPS"""
        video_info = self.get_video_info(self.VIDEO_30FPS)
        expected_frames = self.calculate_expected_frames(
            video_info["fps"], 
            video_info["duration_sec"], 
            target_fps=5
        )
        
        frames = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=5) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        actual_frames = len(frames)
        
        print(f"\n30 FPS → 5 FPS Sampling:")
        print(f"  Source: {video_info['fps']} FPS, {video_info['total_frames']} frames, {video_info['duration_sec']:.2f}s")
        print(f"  Expected: ~{expected_frames} frames (±{self.FRAME_COUNT_TOLERANCE})")
        print(f"  Actual: {actual_frames} frames")
        
        assert abs(actual_frames - expected_frames) <= self.FRAME_COUNT_TOLERANCE, \
            f"Frame count mismatch: expected {expected_frames}±{self.FRAME_COUNT_TOLERANCE}, got {actual_frames}"
        
        self._validate_timestamps(frames, video_info["duration_sec"])
        print("  ✅ Frame count and timestamps valid")
    
    def test_30fps_video_at_10fps(self):
        """Test 30 FPS video sampled at 10 FPS"""
        video_info = self.get_video_info(self.VIDEO_30FPS)
        expected_frames = self.calculate_expected_frames(
            video_info["fps"], 
            video_info["duration_sec"], 
            target_fps=10
        )
        
        frames = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=10) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        actual_frames = len(frames)
        
        print(f"\n30 FPS → 10 FPS Sampling:")
        print(f"  Source: {video_info['fps']} FPS, {video_info['total_frames']} frames, {video_info['duration_sec']:.2f}s")
        print(f"  Expected: ~{expected_frames} frames (±{self.FRAME_COUNT_TOLERANCE})")
        print(f"  Actual: {actual_frames} frames")
        
        assert abs(actual_frames - expected_frames) <= self.FRAME_COUNT_TOLERANCE, \
            f"Frame count mismatch: expected {expected_frames}±{self.FRAME_COUNT_TOLERANCE}, got {actual_frames}"
        
        self._validate_timestamps(frames, video_info["duration_sec"])
        print("  ✅ Frame count and timestamps valid")
    
    def test_24fps_video_at_5fps(self):
        """Test 24 FPS video sampled at 5 FPS (non-divisible)"""
        video_info = self.get_video_info(self.VIDEO_24FPS)
        expected_frames = self.calculate_expected_frames(
            video_info["fps"], 
            video_info["duration_sec"], 
            target_fps=5
        )
        
        frames = []
        with VideoProcessor(self.VIDEO_24FPS, target_fps=5) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        actual_frames = len(frames)
        
        print(f"\n24 FPS → 5 FPS Sampling (non-divisible):")
        print(f"  Source: {video_info['fps']} FPS, {video_info['total_frames']} frames, {video_info['duration_sec']:.2f}s")
        print(f"  Expected: ~{expected_frames} frames (±{self.FRAME_COUNT_TOLERANCE})")
        print(f"  Actual: {actual_frames} frames")
        
        assert abs(actual_frames - expected_frames) <= self.FRAME_COUNT_TOLERANCE, \
            f"Frame count mismatch: expected {expected_frames}±{self.FRAME_COUNT_TOLERANCE}, got {actual_frames}"
        
        self._validate_timestamps(frames, video_info["duration_sec"])
        print("  ✅ Frame count and timestamps valid")
    
    def test_24fps_video_at_1fps(self):
        """Test 24 FPS video sampled at 1 FPS"""
        video_info = self.get_video_info(self.VIDEO_24FPS)
        expected_frames = self.calculate_expected_frames(
            video_info["fps"], 
            video_info["duration_sec"], 
            target_fps=1
        )
        
        frames = []
        with VideoProcessor(self.VIDEO_24FPS, target_fps=1) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        actual_frames = len(frames)
        
        print(f"\n24 FPS → 1 FPS Sampling:")
        print(f"  Source: {video_info['fps']} FPS, {video_info['total_frames']} frames, {video_info['duration_sec']:.2f}s")
        print(f"  Expected: ~{expected_frames} frames (±{self.FRAME_COUNT_TOLERANCE})")
        print(f"  Actual: {actual_frames} frames")
        
        assert abs(actual_frames - expected_frames) <= self.FRAME_COUNT_TOLERANCE, \
            f"Frame count mismatch: expected {expected_frames}±{self.FRAME_COUNT_TOLERANCE}, got {actual_frames}"
        
        self._validate_timestamps(frames, video_info["duration_sec"])
        print("  ✅ Frame count and timestamps valid")
    
    def test_timestamps_are_ordered(self):
        """Test that timestamps are monotonically increasing"""
        frames = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=5) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        timestamps = [f["timestamp_ms"] for f in frames]
        
        # Check ordering
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], \
                f"Timestamp decreased: frame {i-1} ({timestamps[i-1]}ms) → frame {i} ({timestamps[i]}ms)"
        
        print(f"\n✅ Timestamps ordered correctly: {timestamps[0]}ms → {timestamps[-1]}ms ({len(timestamps)} frames)")
    
    def test_timestamps_within_duration(self):
        """Test that all timestamps are within video duration"""
        video_info = self.get_video_info(self.VIDEO_30FPS)
        max_timestamp_ms = video_info["duration_sec"] * 1000
        
        frames = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=5) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        for frame in frames:
            assert 0 <= frame["timestamp_ms"] <= max_timestamp_ms, \
                f"Timestamp {frame['timestamp_ms']}ms exceeds video duration {max_timestamp_ms}ms"
        
        print(f"\n✅ All {len(frames)} timestamps within video duration (0-{max_timestamp_ms:.0f}ms)")
    
    def test_frame_indices_sequential(self):
        """Test that frame indices are sequential starting from 0"""
        frames = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=5) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        for i, frame in enumerate(frames):
            assert frame["frame_index"] == i, \
                f"Frame index mismatch at position {i}: expected {i}, got {frame['frame_index']}"
        
        print(f"\n✅ Frame indices sequential: 0 → {len(frames)-1}")
    
    def test_source_frame_values(self):
        """Test that source_frame values are valid"""
        video_info = self.get_video_info(self.VIDEO_30FPS)
        
        frames = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=5) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        source_frames = [f["source_frame"] for f in frames]
        
        # All source frames should be within valid range
        for sf in source_frames:
            assert 0 <= sf < video_info["total_frames"], \
                f"Source frame {sf} outside valid range [0, {video_info['total_frames']})"
        
        # Source frames should be increasing
        for i in range(1, len(source_frames)):
            assert source_frames[i] > source_frames[i-1], \
                f"Source frame not increasing: {source_frames[i-1]} → {source_frames[i]}"
        
        print(f"\n✅ Source frames valid: {source_frames[0]} → {source_frames[-1]}")
    
    def test_invalid_video_file(self):
        """Test error handling for invalid video file"""
        with pytest.raises(ValueError, match="Cannot open video"):
            with VideoProcessor("nonexistent_video.mp4", target_fps=5) as processor:
                pass
        
        print("\n✅ Invalid video file handled correctly")
    
    def test_high_target_fps(self):
        """Test sampling at higher FPS than source (should process all frames)"""
        video_info = self.get_video_info(self.VIDEO_30FPS)
        
        frames = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=60) as processor:
            for frame_data in processor.extract_frames():
                frames.append(frame_data)
        
        actual_frames = len(frames)
        
        print(f"\n30 FPS → 60 FPS Sampling (higher than source):")
        print(f"  Source frames: {video_info['total_frames']}")
        print(f"  Processed frames: {actual_frames}")
        
        # When target FPS > source FPS, should process all source frames
        assert actual_frames == video_info["total_frames"], \
            f"Should process all {video_info['total_frames']} frames when target FPS > source FPS"
        
        print("  ✅ All source frames processed")
    
    def _validate_timestamps(self, frames: list, duration_sec: float):
        """
        Validate timestamp properties.
        
        Args:
            frames: List of frame data dicts
            duration_sec: Video duration in seconds
        """
        timestamps = [f["timestamp_ms"] for f in frames]
        max_timestamp_ms = duration_sec * 1000
        
        # Check ordering
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], \
                f"Timestamps not ordered: {timestamps[i-1]}ms → {timestamps[i]}ms"
        
        # Check range
        assert timestamps[0] >= 0, f"First timestamp negative: {timestamps[0]}ms"
        assert timestamps[-1] <= max_timestamp_ms, \
            f"Last timestamp {timestamps[-1]}ms exceeds duration {max_timestamp_ms}ms"
    
    def test_sampling_consistency(self):
        """Test that repeated sampling produces consistent results"""
        frames1 = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=5) as processor:
            for frame_data in processor.extract_frames():
                frames1.append(frame_data)
        
        frames2 = []
        with VideoProcessor(self.VIDEO_30FPS, target_fps=5) as processor:
            for frame_data in processor.extract_frames():
                frames2.append(frame_data)
        
        assert len(frames1) == len(frames2), "Repeated sampling produced different frame counts"
        
        # Check timestamps match
        for i in range(len(frames1)):
            assert frames1[i]["timestamp_ms"] == frames2[i]["timestamp_ms"], \
                f"Timestamp mismatch at frame {i}: {frames1[i]['timestamp_ms']} vs {frames2[i]['timestamp_ms']}"
        
        print(f"\n✅ Repeated sampling consistent: {len(frames1)} frames each time")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
