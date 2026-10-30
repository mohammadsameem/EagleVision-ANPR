"""
CRUD operations for EagleVision ANPR database

Provides database operations for:
- Video management
- Detection storage
- Review workflow
- Query and filtering
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func

from .models import Video, Vehicle, Plate, OCRResult, Review


# ============================================================================
# Video CRUD
# ============================================================================

def create_video(
    db: Session,
    owner_id: int,
    filename: str,
    file_path: str,
    file_size_bytes: int,
    resolution: str,
    fps: float,
    frame_count: int,
    duration_sec: float,
    target_fps: float
) -> Video:
    """Create new video record"""
    video = Video(
        owner_id=owner_id,
        filename=filename,
        file_path=file_path,
        file_size_bytes=file_size_bytes,
        resolution=resolution,
        fps=fps,
        frame_count=frame_count,
        duration_sec=duration_sec,
        target_fps=target_fps,
        status="pending"
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def get_video(db: Session, video_id: int) -> Optional[Video]:
    """Get video by ID"""
    return db.query(Video).filter(Video.id == video_id).first()


def get_video_by_filename(db: Session, filename: str) -> Optional[Video]:
    """Get video by filename"""
    return db.query(Video).filter(Video.filename == filename).first()


def get_videos(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    owner_id: Optional[int] = None
) -> List[Video]:
    """Get videos with pagination and optional filters"""
    query = db.query(Video)
    
    if status:
        query = query.filter(Video.status == status)
    
    if owner_id:
        query = query.filter(Video.owner_id == owner_id)
    
    return query.order_by(desc(Video.created_at)).offset(skip).limit(limit).all()


def update_video_status(
    db: Session,
    video_id: int,
    status: str,
    error_message: Optional[str] = None
) -> Optional[Video]:
    """Update video processing status"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return None
    
    video.status = status
    if error_message:
        video.error_message = error_message
    
    if status == "processing":
        video.processing_started_at = datetime.utcnow()
    elif status in ("completed", "failed"):
        video.processing_completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(video)
    return video


def update_video_stats(
    db: Session,
    video_id: int,
    frames_processed: int,
    total_vehicles: int,
    total_plates: int
) -> Optional[Video]:
    """Update video statistics after processing"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return None
    
    video.frames_processed = frames_processed
    video.total_vehicles = total_vehicles
    video.total_plates = total_plates
    
    db.commit()
    db.refresh(video)
    return video


def delete_video(db: Session, video_id: int) -> bool:
    """Delete video and all related detections (cascade)"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return False
    
    db.delete(video)
    db.commit()
    return True


# ============================================================================
# Vehicle Detection CRUD
# ============================================================================

def create_vehicle_detection(db: Session, video_id: int, detection: Dict[str, Any]) -> Vehicle:
    """Create vehicle detection record"""
    vehicle = Vehicle(
        video_id=video_id,
        frame_index=detection["frame_index"],
        source_frame=detection["source_frame"],
        timestamp_ms=detection["timestamp_ms"],
        bbox_x=detection["vehicle_bbox"][0],
        bbox_y=detection["vehicle_bbox"][1],
        bbox_width=detection["vehicle_bbox"][2],
        bbox_height=detection["vehicle_bbox"][3],
        confidence=detection["vehicle_confidence"],
        vehicle_class=detection["vehicle_class"]
    )
    db.add(vehicle)
    db.flush()  # Get ID without committing transaction
    return vehicle


def get_vehicles_by_video(
    db: Session,
    video_id: int,
    min_confidence: Optional[float] = None
) -> List[Vehicle]:
    """Get all vehicles detected in a video"""
    query = db.query(Vehicle).filter(Vehicle.video_id == video_id)
    
    if min_confidence is not None:
        query = query.filter(Vehicle.confidence >= min_confidence)
    
    return query.order_by(Vehicle.frame_index, Vehicle.id).all()


# ============================================================================
# Plate Detection CRUD
# ============================================================================

def create_plate_detection(db: Session, vehicle_id: int, detection: Dict[str, Any]) -> Plate:
    """Create plate detection record"""
    plate_data = {
        "vehicle_id": vehicle_id,
        "confidence": detection["plate_confidence"],
        "detection_method": detection.get("plate_method", "unknown")
    }
    
    # Relative coordinates (within vehicle crop)
    if "plate_bbox" in detection and detection["plate_bbox"]:
        bbox = detection["plate_bbox"]
        plate_data.update({
            "bbox_x_relative": bbox[0],
            "bbox_y_relative": bbox[1],
            "bbox_width_relative": bbox[2],
            "bbox_height_relative": bbox[3]
        })
    
    # Absolute coordinates (full frame)
    if "plate_bbox_absolute" in detection and detection["plate_bbox_absolute"]:
        bbox_abs = detection["plate_bbox_absolute"]
        plate_data.update({
            "bbox_x_absolute": bbox_abs[0],
            "bbox_y_absolute": bbox_abs[1],
            "bbox_width_absolute": bbox_abs[2],
            "bbox_height_absolute": bbox_abs[3]
        })
    
    plate = Plate(**plate_data)
    db.add(plate)
    db.flush()
    return plate


def get_plates_by_video(db: Session, video_id: int) -> List[Plate]:
    """Get all plates detected in a video"""
    return (
        db.query(Plate)
        .join(Vehicle)
        .filter(Vehicle.video_id == video_id)
        .order_by(Vehicle.frame_index, Plate.id)
        .all()
    )


# ============================================================================
# OCR Result CRUD
# ============================================================================

def create_ocr_result(db: Session, plate_id: int, ocr_data: Dict[str, Any]) -> OCRResult:
    """Create OCR result record"""
    ocr_result = OCRResult(
        plate_id=plate_id,
        text=ocr_data.get("text"),
        confidence=ocr_data.get("confidence"),
        engine_used=ocr_data.get("engine_used"),
        easyocr_text=ocr_data.get("easyocr_text"),
        easyocr_confidence=ocr_data.get("easyocr_confidence"),
        paddleocr_text=ocr_data.get("paddleocr_text"),
        paddleocr_confidence=ocr_data.get("paddleocr_confidence"),
        needs_review=ocr_data.get("needs_review", False),
        review_reason=ocr_data.get("review_reason"),
        is_valid_format=ocr_data.get("is_valid_format"),
        processing_time_ms=ocr_data.get("processing_time_ms")
    )
    db.add(ocr_result)
    db.flush()
    return ocr_result


def get_ocr_results_needing_review(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: Optional[int] = None
) -> List[OCRResult]:
    """
    Get OCR results that need human review.
    
    Args:
        db: Database session
        skip: Number of results to skip (pagination)
        limit: Maximum results to return
        owner_id: Optional filter by video owner ID (None = all)
    
    Returns:
        List of OCR results needing review
    """
    query = (
        db.query(OCRResult)
        .join(OCRResult.plate)
        .join(Plate.vehicle)
        .join(Vehicle.video)
        .filter(OCRResult.needs_review == True)
    )
    
    # Filter by owner if specified
    if owner_id is not None:
        query = query.filter(Video.owner_id == owner_id)
    
    return (
        query
        .options(joinedload(OCRResult.plate).joinedload(Plate.vehicle).joinedload(Vehicle.video))
        .order_by(desc(OCRResult.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_ocr_result(db: Session, ocr_result_id: int) -> Optional[OCRResult]:
    """Get OCR result by ID with related data"""
    return (
        db.query(OCRResult)
        .options(joinedload(OCRResult.plate).joinedload(Plate.vehicle).joinedload(Vehicle.video))
        .filter(OCRResult.id == ocr_result_id)
        .first()
    )


# ============================================================================
# Review CRUD
# ============================================================================

def create_review(
    db: Session,
    ocr_result_id: int,
    reviewed_text: str,
    reviewer_id: str,
    reviewer_user_id: Optional[int] = None,
    reviewer_notes: Optional[str] = None,
    is_correct: Optional[bool] = None,
    correction_type: Optional[str] = None
) -> Review:
    """
    Create review submission.
    
    Args:
        db: Database session
        ocr_result_id: OCR result being reviewed
        reviewed_text: Corrected plate text
        reviewer_id: Reviewer identifier (email, username, etc.)
        reviewer_user_id: Optional user ID if authenticated
        reviewer_notes: Optional notes
        is_correct: Whether original OCR was correct
        correction_type: Type of correction
    
    Returns:
        Created review record
    """
    review = Review(
        ocr_result_id=ocr_result_id,
        reviewed_text=reviewed_text,
        reviewer_id=reviewer_id,
        reviewer_user_id=reviewer_user_id,
        reviewer_notes=reviewer_notes,
        is_correct=is_correct,
        correction_type=correction_type
    )
    db.add(review)
    
    # Update OCR result to mark as reviewed
    ocr_result = db.query(OCRResult).filter(OCRResult.id == ocr_result_id).first()
    if ocr_result:
        ocr_result.needs_review = False  # Mark as reviewed
    
    db.commit()
    db.refresh(review)
    return review


def get_reviews_by_reviewer(
    db: Session,
    reviewer_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[Review]:
    """Get reviews submitted by a specific reviewer"""
    return (
        db.query(Review)
        .filter(Review.reviewer_id == reviewer_id)
        .order_by(desc(Review.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


# ============================================================================
# Bulk Operations
# ============================================================================

def store_anpr_results(db: Session, video_id: int, detections: List[Dict[str, Any]]) -> int:
    """
    Store complete ANPR pipeline results for a video.
    
    Stores vehicles, plates, and OCR results in a single transaction.
    
    Returns:
        Number of detections stored
    """
    stored_count = 0
    
    for detection in detections:
        # Create vehicle
        vehicle = create_vehicle_detection(db, video_id, detection)
        
        # Create plate if detected
        if detection.get("plate_bbox") and detection.get("plate_confidence"):
            plate = create_plate_detection(db, vehicle.id, detection)
            
            # Create OCR result if available
            if detection.get("ocr_result"):
                create_ocr_result(db, plate.id, detection["ocr_result"])
        
        stored_count += 1
    
    db.commit()
    return stored_count


# ============================================================================
# Statistics and Analytics
# ============================================================================

def get_detection_statistics(db: Session, video_id: int) -> Dict[str, Any]:
    """Get detection statistics for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return {}
    
    vehicles_count = db.query(func.count(Vehicle.id)).filter(Vehicle.video_id == video_id).scalar()
    
    plates_count = (
        db.query(func.count(Plate.id))
        .join(Vehicle)
        .filter(Vehicle.video_id == video_id)
        .scalar()
    )
    
    ocr_with_text = (
        db.query(func.count(OCRResult.id))
        .join(Plate)
        .join(Vehicle)
        .filter(
            and_(
                Vehicle.video_id == video_id,
                OCRResult.text.isnot(None),
                OCRResult.text != ""
            )
        )
        .scalar()
    )
    
    needs_review = (
        db.query(func.count(OCRResult.id))
        .join(Plate)
        .join(Vehicle)
        .filter(
            and_(
                Vehicle.video_id == video_id,
                OCRResult.needs_review == True
            )
        )
        .scalar()
    )
    
    return {
        "video_id": video_id,
        "total_vehicles": vehicles_count,
        "total_plates": plates_count,
        "plates_with_text": ocr_with_text,
        "needs_review": needs_review,
        "detection_rate": f"{(plates_count / vehicles_count * 100):.1f}%" if vehicles_count > 0 else "0%",
        "ocr_success_rate": f"{(ocr_with_text / plates_count * 100):.1f}%" if plates_count > 0 else "0%"
    }



# ============================================================================
# Helper Functions for AI Investigation
# ============================================================================

def get_vehicle_by_id(db: Session, vehicle_id: int):
    """Get a single vehicle by ID."""
    from .models import Vehicle
    return db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()


def get_plate_by_id(db: Session, plate_id: int):
    """Get a single plate by ID."""
    from .models import Plate
    return db.query(Plate).filter(Plate.id == plate_id).first()


def get_ocr_result_by_id(db: Session, ocr_id: int):
    """Get a single OCR result by ID."""
    from .models import OCRResult
    return db.query(OCRResult).filter(OCRResult.id == ocr_id).first()


def get_plates_by_vehicle(db: Session, vehicle_id: int):
    """Get all plates for a vehicle."""
    from .models import Plate
    return db.query(Plate).filter(Plate.vehicle_id == vehicle_id).all()
