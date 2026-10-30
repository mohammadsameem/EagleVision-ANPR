"""
FastAPI application for EagleVision ANPR

Provides REST API for:
- Video upload and processing
- ANPR results retrieval
- Human review workflow
- CSV/JSON export
"""
import os
import logging
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil

from src.database import get_db, init_db
from src.database import crud
from src.auth import get_current_user
from src.auth.models import User
from src.auth.security import (
    validate_file_content,
    sanitize_filename,
    validate_video_ownership,
    check_rate_limit,
    generate_safe_filename
)
from .schemas import (
    VideoCreate,
    VideoResponse,
    VideoListResponse,
    VideoStatusResponse,
    DetectionResults,
    ReviewCreate,
    ReviewResponse,
    OCRResultResponse,
    ProcessingRequest,
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIServiceStatus,
)
from .processing import process_video_task
from src.services.nebius_nemotron import get_nemotron_service

# Initialize logging FIRST
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Celery - will be None if Redis unavailable
try:
    from src.celery_tasks import process_video_background
    CELERY_AVAILABLE = True
    logger.info("✅ Celery integration available")
except Exception as e:
    process_video_background = None
    CELERY_AVAILABLE = False
    logger.warning(f"⚠️  Celery not available: {e}. Using synchronous processing.")

# Create FastAPI app
app = FastAPI(
    title="EagleVision ANPR API",
    description="Automatic Number Plate Recognition system with multi-camera vehicle tracking",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration from environment
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").strip()
if ALLOWED_ORIGINS:
    # Parse comma-separated origins
    origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",") if origin.strip()]
else:
    # Default for development only
    origins = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    logger.warning("⚠️  No ALLOWED_ORIGINS set. Using development defaults. Set ALLOWED_ORIGINS in production!")

logger.info(f"CORS allowed origins: {origins}")

# CORS middleware with explicit allowlist
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Explicit allowlist, no wildcards
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Upload directory
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("🚀 Starting EagleVision ANPR API...")
    init_db()
    logger.info("✅ Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 Shutting down EagleVision ANPR API...")


# ============================================================================
# Health Check
# ============================================================================

@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "EagleVision ANPR API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected"
    }


# ============================================================================
# Video Upload and Management
# ============================================================================

@app.post("/api/videos/upload", response_model=VideoResponse, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    target_fps: Optional[float] = Query(5.0, description="Processing frame rate"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload video file for ANPR processing.
    
    Requires valid API key (X-API-Key header).
    
    - **file**: Video file (MP4, AVI, MOV, etc.)
    - **target_fps**: Processing frame rate (default: 5 FPS)
    
    Returns video metadata with status="pending".
    Processing will be triggered separately.
    """
    # Rate limit check
    check_rate_limit(current_user.id, "upload")
    
    # Validate file content (MIME type and size)
    try:
        await validate_file_content(file)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File validation error: {e}")
        raise HTTPException(status_code=400, detail="File validation failed")
    
    # Sanitize and generate safe filename
    safe_original = sanitize_filename(file.filename)
    safe_filename = generate_safe_filename(safe_original, current_user.id)
    
    # Validate file extension
    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv"}
    file_ext = Path(safe_original).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check if user already uploaded this file
    existing = crud.get_video_by_filename(db, safe_original)
    if existing and existing.owner_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail=f"Video '{safe_original}' already uploaded (ID: {existing.id})"
        )
    
    # Save uploaded file with safe name
    file_path = UPLOAD_DIR / safe_filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    
    file_size = file_path.stat().st_size
    
    # Extract video metadata (basic - will be updated during processing)
    try:
        from src.video_processor import VideoProcessor
        with VideoProcessor(str(file_path)) as processor:
            metadata = processor.get_metadata()
    except Exception as e:
        logger.error(f"Failed to read video metadata: {e}")
        file_path.unlink()  # Clean up file
        raise HTTPException(status_code=400, detail="Invalid or corrupted video file")
    
    # Create database record with owner
    video = crud.create_video(
        db=db,
        filename=safe_original,  # Store original safe filename
        file_path=str(file_path),  # Store actual safe path
        file_size_bytes=file_size,
        resolution=metadata.get("resolution", "unknown"),
        fps=metadata.get("fps", 0),
        frame_count=metadata.get("frame_count", 0),
        duration_sec=metadata.get("duration_sec", 0),
        target_fps=target_fps,
        owner_id=current_user.id
    )
    
    logger.info(f"✅ Video uploaded: {video.id} - {safe_original} by user {current_user.id}")
    
    return video


@app.get("/api/videos/", response_model=VideoListResponse)
def list_videos(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List uploaded videos with pagination.
    
    Requires valid API key (X-API-Key header).
    Users see only their own videos unless they are admin.
    
    - **skip**: Pagination offset (default: 0)
    - **limit**: Maximum results (default: 100, max: 1000)
    - **status**: Filter by status (pending, processing, completed, failed)
    """
    # Admin can see all videos, users see only their own
    owner_id = None if current_user.is_admin else current_user.id
    
    videos = crud.get_videos(db, skip=skip, limit=limit, status=status, owner_id=owner_id)
    total = len(crud.get_videos(db, skip=0, limit=10000, status=status, owner_id=owner_id))  # TODO: Optimize
    
    return {
        "videos": videos,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@app.get("/api/videos/{video_id}", response_model=VideoResponse)
def get_video_details(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get video details by ID.
    
    Requires valid API key and ownership of the video.
    """
    validate_video_ownership(db, video_id, current_user)
    video = crud.get_video(db, video_id)
    return video


@app.get("/api/videos/{video_id}/status", response_model=VideoStatusResponse)
def get_video_status(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get video processing status.
    
    Requires valid API key and ownership of the video.
    Returns status and progress information.
    """
    validate_video_ownership(db, video_id, current_user)
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
    
    stats = crud.get_detection_statistics(db, video_id)
    
    return {
        "video_id": video.id,
        "filename": video.filename,
        "status": video.status,
        "frames_processed": video.frames_processed or 0,
        "total_frames": int(video.duration_sec * video.target_fps) if video.duration_sec and video.target_fps else 0,
        "progress_percent": (video.frames_processed / (video.duration_sec * video.target_fps) * 100) if video.frames_processed and video.duration_sec and video.target_fps else 0,
        "total_vehicles": stats.get("total_vehicles", 0),
        "total_plates": stats.get("total_plates", 0),
        "error_message": video.error_message
    }


@app.post("/api/videos/{video_id}/process", response_model=VideoStatusResponse)
async def process_video(
    video_id: int,
    use_celery: bool = Query(True, description="Use background processing (requires Redis)"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger ANPR processing for an uploaded video.
    
    Requires valid API key and ownership of the video.
    Processing runs in background using Celery if available.
    Check status with GET /api/videos/{video_id}/status
    
    - **use_celery**: Use Celery for background processing (requires Redis)
      - True (default): Submit to Celery worker queue (returns immediately)
      - False: Process synchronously in current request (for testing)
    
    Returns immediately with status="pending" if using Celery.
    """
    validate_video_ownership(db, video_id, current_user)
    check_rate_limit(current_user.id, "process")
    
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
    
    if video.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Video cannot be processed (status: {video.status})"
        )
    
    # Reset to pending if failed
    if video.status == "failed":
        crud.update_video_status(db, video_id, "pending", error_message=None)
        db.commit()
    
    logger.info(f"🎬 Triggering processing for video {video_id} (use_celery={use_celery})")
    
    # Determine processing method
    use_background = use_celery and CELERY_AVAILABLE
    
    if use_background:
        # Submit to Celery worker
        try:
            task = process_video_background.delay(video_id)
            logger.info(f"✅ Submitted to Celery worker: task_id={task.id}")
            task_id = task.id
        except Exception as e:
            logger.error(f"❌ Failed to submit to Celery: {e}")
            raise HTTPException(
                status_code=503,
                detail="Background processing service temporarily unavailable. Try use_celery=false for immediate processing"
            )
    else:
        # Process synchronously
        if use_celery and not CELERY_AVAILABLE:
            logger.warning("⚠️  Celery requested but unavailable, using synchronous processing")
        
        try:
            result = process_video_task(video_id)
            logger.info(f"✅ Synchronous processing completed: {result}")
            task_id = None
        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            raise HTTPException(status_code=500, detail="Video processing failed. Please check the file and try again")
    
    # Refresh the db session to get updated video record
    db.expire_all()  # Clear cached objects
    video = crud.get_video(db, video_id)
    
    # Get statistics
    stats = crud.get_detection_statistics(db, video_id)
    
    # Calculate progress
    if video.duration_sec and video.target_fps:
        total_frames = int(video.duration_sec * video.target_fps)
        progress_percent = (video.frames_processed / total_frames * 100) if video.frames_processed else 0
    else:
        total_frames = 0
        progress_percent = 0 if video.status == "pending" else (100.0 if video.status == "completed" else 0.0)
    
    response = {
        "video_id": video.id,
        "filename": video.filename,
        "status": video.status,
        "frames_processed": video.frames_processed or 0,
        "total_frames": total_frames,
        "progress_percent": progress_percent,
        "total_vehicles": stats.get("total_vehicles", 0),
        "total_plates": stats.get("total_plates", 0),
        "error_message": video.error_message
    }
    
    # Add task_id if using Celery
    if use_background and task_id:
        response["task_id"] = task_id
    
    return response


@app.delete("/api/videos/{video_id}", status_code=204)
def delete_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete video and all related detections.
    
    Requires valid API key and ownership of the video.
    Also removes the uploaded file.
    """
    validate_video_ownership(db, video_id, current_user)
    
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
    
    # Delete file from filesystem
    file_path = Path(video.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
    
    # Delete from database (cascades to all related records)
    crud.delete_video(db, video_id)
    logger.info(f"Deleted video: {video_id}")
    
    return None  # 204 No Content


# ============================================================================
# ANPR Results
# ============================================================================

@app.get("/api/videos/{video_id}/results", response_model=DetectionResults)
def get_video_results(
    video_id: int,
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum detection confidence"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete ANPR results for a video.
    
    Requires valid API key and ownership of the video.
    Returns all detected vehicles, plates, and OCR results.
    
    - **min_confidence**: Filter vehicles by minimum confidence (optional)
    """
    validate_video_ownership(db, video_id, current_user)
    
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
    
    if video.status not in ("completed", "processing"):
        raise HTTPException(
            status_code=400,
            detail=f"Video processing not started or failed (status: {video.status})"
        )
    
    vehicles = crud.get_vehicles_by_video(db, video_id, min_confidence=min_confidence)
    stats = crud.get_detection_statistics(db, video_id)
    
    # Build result structure
    detections = []
    for vehicle in vehicles:
        vehicle_data = {
            "vehicle_id": vehicle.id,
            "frame_index": vehicle.frame_index,
            "timestamp_ms": vehicle.timestamp_ms,
            "bbox": [vehicle.bbox_x, vehicle.bbox_y, vehicle.bbox_width, vehicle.bbox_height],
            "confidence": vehicle.confidence,
            "vehicle_class": vehicle.vehicle_class,
            "plates": []
        }
        
        for plate in vehicle.plates:
            plate_data = {
                "plate_id": plate.id,
                "bbox_relative": [
                    plate.bbox_x_relative,
                    plate.bbox_y_relative,
                    plate.bbox_width_relative,
                    plate.bbox_height_relative
                ],
                "confidence": plate.confidence,
                "detection_method": plate.detection_method,
                "ocr_results": []
            }
            
            for ocr in plate.ocr_results:
                plate_data["ocr_results"].append({
                    "ocr_id": ocr.id,
                    "text": ocr.text,
                    "confidence": ocr.confidence,
                    "engine_used": ocr.engine_used,
                    "needs_review": ocr.needs_review,
                    "review_reason": ocr.review_reason,
                    "is_valid_format": ocr.is_valid_format
                })
            
            vehicle_data["plates"].append(plate_data)
        
        detections.append(vehicle_data)
    
    return {
        "video_id": video_id,
        "filename": video.filename,
        "status": video.status,
        "statistics": stats,
        "detections": detections
    }


# ============================================================================
# Review Workflow
# ============================================================================

@app.get("/api/detections/needs-review", response_model=List[OCRResultResponse])
def get_detections_needing_review(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get OCR results that need human review.
    
    Requires valid API key.
    Returns detections with low confidence, engine disagreements,
    or invalid plate formats.
    
    Users see only results from their own videos unless they are admin.
    """
    # Admin can see all, users see only their own
    owner_id = None if current_user.is_admin else current_user.id
    
    ocr_results = crud.get_ocr_results_needing_review(db, skip=skip, limit=limit, owner_id=owner_id)
    
    response = []
    for ocr in ocr_results:
        response.append({
            "ocr_id": ocr.id,
            "plate_id": ocr.plate_id,
            "video_id": ocr.plate.vehicle.video_id,
            "filename": ocr.plate.vehicle.video.filename,
            "frame_index": ocr.plate.vehicle.frame_index,
            "timestamp_ms": ocr.plate.vehicle.timestamp_ms,
            "text": ocr.text,
            "confidence": ocr.confidence,
            "needs_review": ocr.needs_review,
            "review_reason": ocr.review_reason,
            "easyocr_text": ocr.easyocr_text,
            "easyocr_confidence": ocr.easyocr_confidence,
            "paddleocr_text": ocr.paddleocr_text,
            "paddleocr_confidence": ocr.paddleocr_confidence
        })
    
    return response


@app.post("/api/reviews/{ocr_id}", response_model=ReviewResponse, status_code=201)
def submit_review(
    ocr_id: int,
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit human review for an OCR result.
    
    Requires valid API key. User must own the video containing the OCR result.
    
    - **ocr_id**: OCR result ID to review
    - **reviewed_text**: Corrected plate text
    - **reviewer_id**: Reviewer identifier (email, username, etc.)
    - **reviewer_notes**: Optional notes
    - **is_correct**: Whether original OCR was correct
    - **correction_type**: Type of correction (confirmed, corrected, rejected, ambiguous)
    """
    # Verify OCR result exists and get its video
    ocr_result = crud.get_ocr_result(db, ocr_id)
    if not ocr_result:
        raise HTTPException(status_code=404, detail=f"OCR result {ocr_id} not found")
    
    # Verify user owns the video
    video_id = ocr_result.plate.vehicle.video_id
    validate_video_ownership(db, video_id, current_user)
    
    # Create review with current user
    review = crud.create_review(
        db=db,
        ocr_result_id=ocr_id,
        reviewed_text=review_data.reviewed_text,
        reviewer_id=review_data.reviewer_id,
        reviewer_user_id=current_user.id,  # Link to user
        reviewer_notes=review_data.reviewer_notes,
        is_correct=review_data.is_correct,
        correction_type=review_data.correction_type
    )
    
    logger.info(f"✅ Review submitted: OCR {ocr_id} by user {current_user.id}")
    
    return review


# ============================================================================
# Export
# ============================================================================

@app.get("/api/videos/{video_id}/export/json")
def export_json(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export video results as JSON.
    
    Requires valid API key and ownership of the video.
    """
    # Call get_video_results with proper parameter order
    results = get_video_results(video_id=video_id, min_confidence=None, current_user=current_user, db=db)
    return results


@app.get("/api/videos/{video_id}/export/csv")
def export_csv(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export video results as CSV.
    
    Requires valid API key and ownership of the video.
    Returns a CSV file with plate detections and OCR results.
    """
    validate_video_ownership(db, video_id, current_user)
    
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    video = crud.get_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
    
    vehicles = crud.get_vehicles_by_video(db, video_id)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "video_id",
        "filename",
        "frame_index",
        "timestamp_ms",
        "vehicle_id",
        "vehicle_confidence",
        "plate_id",
        "plate_confidence",
        "plate_text",
        "ocr_confidence",
        "needs_review",
        "review_reason"
    ])
    
    # Data rows
    for vehicle in vehicles:
        for plate in vehicle.plates:
            for ocr in plate.ocr_results:
                writer.writerow([
                    video_id,
                    video.filename,
                    vehicle.frame_index,
                    vehicle.timestamp_ms,
                    vehicle.id,
                    vehicle.confidence,
                    plate.id,
                    plate.confidence,
                    ocr.text or "",
                    ocr.confidence or "",
                    ocr.needs_review,
                    ocr.review_reason or ""
                ])
    
    # Return as downloadable file
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=anpr_results_{video_id}.csv"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



# ============================================================================
# AI Investigation (NVIDIA Nemotron via Nebius Token Factory)
# ============================================================================

@app.get("/api/ai/status", response_model=AIServiceStatus)
async def get_ai_service_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get AI service status and available models.
    
    Verifies connection to Nebius Token Factory and lists available NVIDIA Nemotron models.
    """
    nemotron = get_nemotron_service()
    status = await nemotron.verify_connection()
    return AIServiceStatus(**status)


@app.post("/api/ai/analyze-event", response_model=AIAnalysisResponse)
async def analyze_anpr_event(
    request: AIAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze an ANPR event using NVIDIA Nemotron AI.
    
    Provides AI-powered investigation assistance including:
    - Incident summary
    - Detection quality assessment
    - Pattern detection
    - OCR uncertainty analysis
    - Recommended review actions
    
    **Note:** This is an additional intelligence layer. It does NOT:
    - Replace vehicle/plate detection
    - Replace OCR engines
    - Make criminality judgments
    - Override security rules
    """
    # Check rate limit
    check_rate_limit(current_user.id)
    
    # Get Nemotron service
    nemotron = get_nemotron_service()
    
    if not nemotron.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI investigation service not configured. Set NEBIUS_API_KEY environment variable."
        )
    
    # Build event data from request
    event_data = {}
    
    # If OCR result ID provided, fetch from database
    if request.ocr_result_id:
        ocr_result = crud.get_ocr_result_by_id(db, request.ocr_result_id)
        if not ocr_result:
            raise HTTPException(status_code=404, detail="OCR result not found")
        
        # Verify ownership
        plate = crud.get_plate_by_id(db, ocr_result.plate_id)
        if not plate:
            raise HTTPException(status_code=404, detail="Plate not found")
        
        vehicle = crud.get_vehicle_by_id(db, plate.vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        video = crud.get_video(db, vehicle.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Verify user owns this video
        validate_video_ownership(video, current_user)
        
        # Build comprehensive event data
        event_data = {
            "event_id": f"ocr_{ocr_result.id}",
            "timestamp": vehicle.timestamp_ms if hasattr(vehicle, 'timestamp_ms') else None,
            "camera_id": video.filename,  # Using filename as camera ID
            "vehicle_class": vehicle.vehicle_class if hasattr(vehicle, 'vehicle_class') else "unknown",
            "vehicle_confidence": round(vehicle.confidence * 100, 2) if hasattr(vehicle, 'confidence') else None,
            "plate_method": plate.detection_method if hasattr(plate, 'detection_method') else "unknown",
            "plate_confidence": round(plate.confidence * 100, 2) if hasattr(plate, 'confidence') else None,
            "ocr_text": ocr_result.text or "N/A",
            "ocr_confidence": round(ocr_result.confidence * 100, 2) if ocr_result.confidence else None,
            "ocr_engine": ocr_result.engine_used or "unknown",
            "needs_review": ocr_result.needs_review,
            "review_reason": ocr_result.review_reason,
            "context": {
                "video_id": video.id,
                "frame_index": vehicle.frame_index if hasattr(vehicle, 'frame_index') else None,
                "video_filename": video.filename,
                "processing_status": video.status
            }
        }
    
    # If vehicle ID provided
    elif request.vehicle_id:
        vehicle = crud.get_vehicle_by_id(db, request.vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        video = crud.get_video(db, vehicle.video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        validate_video_ownership(video, current_user)
        
        # Get plates for this vehicle
        plates = crud.get_plates_by_vehicle(db, vehicle.id) if hasattr(crud, 'get_plates_by_vehicle') else []
        
        event_data = {
            "event_id": f"vehicle_{vehicle.id}",
            "timestamp": vehicle.timestamp_ms if hasattr(vehicle, 'timestamp_ms') else None,
            "camera_id": video.filename,
            "vehicle_class": vehicle.vehicle_class if hasattr(vehicle, 'vehicle_class') else "unknown",
            "vehicle_confidence": round(vehicle.confidence * 100, 2) if hasattr(vehicle, 'confidence') else None,
            "plate_method": plates[0].detection_method if plates and hasattr(plates[0], 'detection_method') else "unknown",
            "plate_confidence": round(plates[0].confidence * 100, 2) if plates and hasattr(plates[0], 'confidence') else None,
            "ocr_text": "See plates",
            "ocr_confidence": None,
            "ocr_engine": "N/A",
            "needs_review": False,
            "review_reason": None,
            "context": {
                "video_id": video.id,
                "frame_index": vehicle.frame_index if hasattr(vehicle, 'frame_index') else None,
                "total_plates": len(plates),
                "video_filename": video.filename
            }
        }
    
    else:
        # Generic event with provided event_id
        event_data = {
            "event_id": request.event_id or "manual_request",
            "timestamp": None,
            "camera_id": "unknown",
            "vehicle_class": "unknown",
            "vehicle_confidence": None,
            "plate_method": "unknown",
            "plate_confidence": None,
            "ocr_text": "N/A",
            "ocr_confidence": None,
            "ocr_engine": "unknown",
            "needs_review": False,
            "review_reason": None,
            "context": {}
        }
    
    # Call Nemotron analysis
    logger.info(f"🔍 Requesting AI analysis for event: {event_data.get('event_id')}")
    
    result = await nemotron.analyze_anpr_event(
        event_data,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    
    return AIAnalysisResponse(**result)


@app.post("/api/ai/batch-analyze", response_model=List[AIAnalysisResponse])
async def batch_analyze_events(
    ocr_result_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch analyze multiple ANPR events.
    
    Analyzes multiple OCR results concurrently for efficiency.
    Limited to 10 events per request to prevent abuse.
    """
    # Check rate limit
    check_rate_limit(current_user.id)
    
    # Limit batch size
    if len(ocr_result_ids) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 events per batch request"
        )
    
    nemotron = get_nemotron_service()
    
    if not nemotron.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI investigation service not configured"
        )
    
    # Build event data for each OCR result
    events = []
    for ocr_id in ocr_result_ids:
        ocr_result = crud.get_ocr_result_by_id(db, ocr_id)
        if not ocr_result:
            continue
        
        # Verify ownership (simplified for batch)
        # TODO: Add full ownership verification
        
        events.append({
            "event_id": f"ocr_{ocr_result.id}",
            "ocr_text": ocr_result.text or "N/A",
            "ocr_confidence": round(ocr_result.confidence * 100, 2) if ocr_result.confidence else None,
            "needs_review": ocr_result.needs_review,
            "review_reason": ocr_result.review_reason,
            "context": {"ocr_result_id": ocr_result.id}
        })
    
    # Batch analyze
    results = await nemotron.batch_analyze_events(events, max_concurrent=3)
    
    return [AIAnalysisResponse(**result) for result in results]
