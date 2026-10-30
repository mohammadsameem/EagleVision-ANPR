"""
Celery tasks for EagleVision ANPR

Background video processing tasks with retry logic and progress tracking.
"""
import logging
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.anpr_pipeline import ANPRPipeline
from src.database import crud
from src.database.connection import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="process_video_background",
    max_retries=2,
    default_retry_delay=30
)
def process_video_background(self, video_id: int) -> Dict[str, Any]:
    """
    Process a video through the ANPR pipeline in background.
    
    This Celery task handles:
    - Video loading and validation
    - ANPR pipeline execution
    - Database status updates
    - Progress reporting
    - Error handling and retries
    
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
            logger.error(f"Video {video_id} not found in database")
            raise ValueError(f"Video {video_id} not found")
        
        # Check if already processed (idempotency)
        if video.status == "completed":
            logger.info(f"Video {video_id} already completed, skipping")
            return {
                "video_id": video_id,
                "status": "completed",
                "message": "Already processed",
                "detections_count": video.total_vehicles,
                "plates_count": video.total_plates
            }
        
        # Check if already processing (prevent duplicates)
        if video.status == "processing":
            # If task was retried, allow reprocessing
            if self.request.retries > 0:
                logger.warning(f"Video {video_id} processing retry #{self.request.retries}")
            else:
                logger.warning(f"Video {video_id} already processing, may be duplicate")
        
        logger.info(f"🎬 Starting background processing for video {video_id}: {video.filename}")
        
        # Update status to processing
        crud.update_video_status(db, video_id, "processing")
        db.commit()  # Commit immediately so API can see status change
        
        # Verify file exists
        video_path = Path(video.file_path)
        if not video_path.exists():
            error_msg = f"Video file not found: {video_path}"
            logger.error(error_msg)
            crud.update_video_status(db, video_id, "failed", error_message=error_msg)
            db.commit()
            raise FileNotFoundError(error_msg)
        
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
            error_msg = "Vehicle detection not available"
            logger.error(error_msg)
            crud.update_video_status(db, video_id, "failed", error_message=error_msg)
            db.commit()
            raise RuntimeError(error_msg)
        
        # Process video with progress tracking
        target_fps = int(video.target_fps or 5)
        logger.info(f"Processing {video_path} at {target_fps} FPS...")
        
        # Update progress: 0% started
        self.update_state(
            state="PROGRESS",
            meta={
                "video_id": video_id,
                "progress": 0,
                "status": "Starting pipeline",
                "frames_processed": 0,
                "total_frames": video.frame_count
            }
        )
        
        detections = pipeline.process_video(str(video_path), fps=target_fps)
        
        logger.info(f"Got {len(detections)} detections from video {video_id}")
        
        # Store results in database (idempotent - will skip if exists)
        if detections:
            # Check for existing results to prevent duplicates
            existing_vehicles = db.query(crud.Vehicle).filter(
                crud.Vehicle.video_id == video_id
            ).count()
            
            if existing_vehicles > 0:
                logger.warning(f"Video {video_id} already has {existing_vehicles} results, skipping insert")
            else:
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
            db.commit()
        
        # Update status to completed
        crud.update_video_status(db, video_id, "completed")
        db.commit()
        
        result = {
            "video_id": video_id,
            "status": "completed",
            "detections_count": len(detections),
            "vehicles_count": len(detections),
            "plates_count": sum(1 for d in detections if d.get("plate_bbox")),
            "task_id": self.request.id
        }
        
        logger.info(f"✅ Video {video_id} processing completed: {result}")
        
        return result
    
    except FileNotFoundError as e:
        # File not found - don't retry
        logger.error(f"❌ Video {video_id} file not found: {e}")
        try:
            crud.update_video_status(db, video_id, "failed", error_message=str(e))
            db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update video status: {update_error}")
        raise  # Don't retry
    
    except Exception as e:
        logger.error(f"❌ Video {video_id} processing failed: {e}", exc_info=True)
        
        # Update status to failed (will be retried)
        try:
            error_msg = f"{type(e).__name__}: {str(e)}"
            crud.update_video_status(db, video_id, "failed", error_message=error_msg)
            db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update video status: {update_error}")
        
        # Retry with exponential backoff (handled by Celery config)
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying video {video_id} (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)
        else:
            logger.error(f"Max retries exceeded for video {video_id}")
            raise
    
    finally:
        db.close()


@celery_app.task(name="cleanup_old_videos")
def cleanup_old_videos(days_old: int = 30) -> Dict[str, int]:
    """
    Cleanup old completed videos (optional maintenance task).
    
    Args:
        days_old: Delete videos older than this many days
    
    Returns:
        Number of videos deleted
    """
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old completed videos
        old_videos = db.query(crud.Video).filter(
            crud.Video.status == "completed",
            crud.Video.processing_completed_at < cutoff_date
        ).all()
        
        deleted_count = 0
        for video in old_videos:
            # Delete file
            video_path = Path(video.file_path)
            if video_path.exists():
                video_path.unlink()
            
            # Delete database record (cascade deletes children)
            db.delete(video)
            deleted_count += 1
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old videos")
        return {"deleted": deleted_count}
    
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()
