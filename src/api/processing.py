"""
Background processing for ANPR pipeline

Handles asynchronous video processing with the ANPR pipeline.
"""
import logging
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.orm import Session

from src.anpr_pipeline import ANPRPipeline
from src.database import crud
from src.database.connection import SessionLocal

logger = logging.getLogger(__name__)


def process_video_task(video_id: int) -> Dict[str, Any]:
    """
    Process a video through the ANPR pipeline.
    
    This function is designed to be run in a background task or worker queue.
    
    Args:
        video_id: Database ID of video to process
    
    Returns:
        Processing results summary
    """
    db = SessionLocal()
    
    try:
        # Get video from database
        video = crud.get_video(db, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")
        
        if video.status != "pending":
            raise ValueError(f"Video {video_id} not in pending status (current: {video.status})")
        
        logger.info(f"🎬 Starting processing for video {video_id}: {video.filename}")
        
        # Update status to processing
        crud.update_video_status(db, video_id, "processing")
        
        # Initialize ANPR pipeline
        pipeline = ANPRPipeline(config={
            "vehicle_model": "yolov8n.pt",
            "use_gpu": False,
            "confidence_threshold": 0.70
        })
        
        # Check capabilities
        capabilities = pipeline.get_capabilities()
        logger.info(f"Pipeline capabilities: {capabilities}")
        
        if not capabilities["vehicle_detection"]:
            raise RuntimeError("Vehicle detection not available")
        
        # Process video
        video_path = video.file_path
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"Processing {video_path} at {video.target_fps} FPS...")
        detections = pipeline.process_video(video_path, fps=int(video.target_fps or 5))
        
        logger.info(f"Got {len(detections)} detections")
        
        # Store results in database
        if detections:
            stored_count = crud.store_anpr_results(db, video_id, detections)
            logger.info(f"Stored {stored_count} detections to database")
            
            # Update video statistics
            plates_count = sum(1 for d in detections if d.get("plate_bbox"))
            crud.update_video_stats(
                db,
                video_id,
                frames_processed=len(set(d["frame_index"] for d in detections)),
                total_vehicles=len(detections),
                total_plates=plates_count
            )
        
        # Update status to completed
        crud.update_video_status(db, video_id, "completed")
        
        result = {
            "video_id": video_id,
            "status": "completed",
            "detections_count": len(detections),
            "vehicles_count": len(detections),
            "plates_count": sum(1 for d in detections if d.get("plate_bbox"))
        }
        
        logger.info(f"✅ Video {video_id} processing completed: {result}")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Video {video_id} processing failed: {e}", exc_info=True)
        
        # Update status to failed
        try:
            crud.update_video_status(db, video_id, "failed", error_message=str(e))
        except Exception as update_error:
            logger.error(f"Failed to update video status: {update_error}")
        
        raise
    
    finally:
        db.close()
