"""
Video frame extraction with timestamp preservation.
Processes at configurable FPS (default 5).
"""
import cv2
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Extract frames from video at configurable FPS with timestamp preservation.
    """
    
    def __init__(self, video_path: str, target_fps: int = 5):
        """
        Initialize video processor.
        
        Args:
            video_path: Path to video file
            target_fps: Target frame rate for processing (default 5)
        """
        self.video_path = video_path
        self.target_fps = target_fps
        self.cap = None
        self.source_fps = None
        self.total_frames = None
        self.duration_sec = None
    
    def __enter__(self):
        """Open video file and extract metadata"""
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {self.video_path}")
        
        self.source_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_sec = self.total_frames / self.source_fps if self.source_fps > 0 else 0
        
        logger.info(f"Video: {Path(self.video_path).name}")
        logger.info(f"Source FPS: {self.source_fps:.2f}")
        logger.info(f"Total frames: {self.total_frames}")
        logger.info(f"Duration: {self.duration_sec:.2f}s")
        logger.info(f"Processing at: {self.target_fps} FPS")
        
        return self
    
    def __exit__(self, *args):
        """Release video capture"""
        if self.cap:
            self.cap.release()
    
    def extract_frames(self):
        """
        Generator yielding frames at target FPS with preserved timestamps.
        
        Samples frames at regular time intervals based on target FPS.
        For example, 5 FPS means one frame every 200ms (1000ms / 5 = 200ms).
        
        Yields:
            dict with keys:
                - frame_index: int (in processed sequence, 0-based)
                - source_frame: int (in original video, 0-based)
                - timestamp_ms: int (from original video)
                - image: np.ndarray (BGR format)
        """
        if not self.cap:
            raise RuntimeError("VideoProcessor not initialized. Use with context manager.")
        
        if self.source_fps <= 0:
            logger.warning("Invalid source FPS, processing all frames")
            # Fallback: process all frames
            frame_index = 0
            source_frame = 0
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break
                timestamp_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))
                yield {
                    "frame_index": frame_index,
                    "source_frame": source_frame,
                    "timestamp_ms": timestamp_ms,
                    "image": frame
                }
                frame_index += 1
                source_frame += 1
            return
        
        # Calculate time interval between samples (in milliseconds)
        sample_interval_ms = 1000.0 / self.target_fps
        
        # Calculate which source frames to extract
        # We want frames at times: 0, sample_interval_ms, 2*sample_interval_ms, etc.
        next_sample_time_ms = 0
        frame_index = 0
        source_frame = 0
        
        logger.info(f"Sampling at {self.target_fps} FPS (interval: {sample_interval_ms:.1f}ms per frame)")
        logger.info(f"Expected frames: ~{int(self.duration_sec * self.target_fps)}")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Get current frame timestamp
            timestamp_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
            
            # Check if this frame is at or past the next sample time
            if timestamp_ms >= next_sample_time_ms:
                yield {
                    "frame_index": frame_index,
                    "source_frame": source_frame,
                    "timestamp_ms": int(timestamp_ms),
                    "image": frame
                }
                
                frame_index += 1
                
                # Calculate next sample time
                next_sample_time_ms += sample_interval_ms
                
                # Log progress every 50 processed frames
                if frame_index % 50 == 0:
                    progress = (source_frame / self.total_frames) * 100 if self.total_frames > 0 else 0
                    logger.info(f"Progress: {progress:.1f}% ({frame_index} frames processed)")
            
            source_frame += 1
        
        logger.info(f"Extraction complete: {frame_index} frames processed from {source_frame} source frames")
    
    def get_metadata(self) -> dict:
        """Get video metadata"""
        sample_interval_ms = 1000.0 / self.target_fps if self.target_fps > 0 else 0
        expected_frames = int(self.duration_sec * self.target_fps) if self.duration_sec and self.target_fps else 0
        
        return {
            "video_path": self.video_path,
            "source_fps": self.source_fps,
            "target_fps": self.target_fps,
            "total_frames": self.total_frames,
            "duration_sec": self.duration_sec,
            "sample_interval_ms": sample_interval_ms,
            "expected_frames": expected_frames
        }
