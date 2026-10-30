"""
Pydantic schemas for API request/response validation
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Video Schemas
# ============================================================================

class VideoCreate(BaseModel):
    """Schema for video upload"""
    filename: str
    target_fps: float = Field(default=5.0, ge=1.0, le=30.0)


class VideoResponse(BaseModel):
    """Schema for video response"""
    id: int
    filename: str
    file_path: str
    file_size_bytes: Optional[int] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    frame_count: Optional[int] = None
    duration_sec: Optional[float] = None
    status: str
    target_fps: Optional[float] = None
    frames_processed: Optional[int] = None
    total_vehicles: Optional[int] = None
    total_plates: Optional[int] = None
    created_at: datetime
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    """Schema for video list with pagination"""
    videos: List[VideoResponse]
    total: int
    skip: int
    limit: int


class VideoStatusResponse(BaseModel):
    """Schema for video processing status"""
    video_id: int
    filename: str
    status: str
    frames_processed: int
    total_frames: int
    progress_percent: float
    total_vehicles: int
    total_plates: int
    error_message: Optional[str] = None
    task_id: Optional[str] = None  # Celery task ID if using background processing


# ============================================================================
# Detection Schemas
# ============================================================================

class OCRResultDetail(BaseModel):
    """OCR result details"""
    ocr_id: int
    text: Optional[str] = None
    confidence: Optional[float] = None
    engine_used: Optional[str] = None
    needs_review: bool
    review_reason: Optional[str] = None
    is_valid_format: Optional[bool] = None


class PlateDetail(BaseModel):
    """Plate detection details"""
    plate_id: int
    bbox_relative: List[int]  # [x, y, width, height]
    confidence: float
    detection_method: Optional[str] = None
    ocr_results: List[OCRResultDetail] = []


class VehicleDetail(BaseModel):
    """Vehicle detection details"""
    vehicle_id: int
    frame_index: int
    timestamp_ms: int
    bbox: List[int]  # [x, y, width, height]
    confidence: float
    vehicle_class: int
    plates: List[PlateDetail] = []


class DetectionStatistics(BaseModel):
    """Detection statistics"""
    video_id: int
    total_vehicles: int
    total_plates: int
    plates_with_text: int
    needs_review: int
    detection_rate: str
    ocr_success_rate: str


class DetectionResults(BaseModel):
    """Complete detection results for a video"""
    video_id: int
    filename: str
    status: str
    statistics: DetectionStatistics
    detections: List[VehicleDetail]


# ============================================================================
# Review Schemas
# ============================================================================

class ReviewCreate(BaseModel):
    """Schema for creating a review"""
    reviewed_text: str = Field(..., min_length=1, max_length=50)
    reviewer_id: str = Field(..., min_length=1, max_length=100)
    reviewer_notes: Optional[str] = Field(None, max_length=1000)
    is_correct: Optional[bool] = None
    correction_type: Optional[str] = Field(None, pattern="^(confirmed|corrected|rejected|ambiguous)$")

    @field_validator("reviewed_text")
    @classmethod
    def validate_reviewed_text(cls, v: str) -> str:
        """Normalize reviewed text"""
        return v.strip().upper()


class ReviewResponse(BaseModel):
    """Schema for review response"""
    id: int
    ocr_result_id: int
    reviewed_text: str
    reviewer_id: str
    reviewer_notes: Optional[str] = None
    is_correct: Optional[bool] = None
    correction_type: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OCRResultResponse(BaseModel):
    """Schema for OCR result needing review"""
    ocr_id: int
    plate_id: int
    video_id: int
    filename: str
    frame_index: int
    timestamp_ms: int
    text: Optional[str] = None
    confidence: Optional[float] = None
    needs_review: bool
    review_reason: Optional[str] = None
    easyocr_text: Optional[str] = None
    easyocr_confidence: Optional[float] = None
    paddleocr_text: Optional[str] = None
    paddleocr_confidence: Optional[float] = None


# ============================================================================
# Processing Schemas
# ============================================================================

class ProcessingRequest(BaseModel):
    """Schema for triggering video processing"""
    video_id: int
    target_fps: Optional[float] = Field(default=5.0, ge=1.0, le=30.0)
    confidence_threshold: Optional[float] = Field(default=0.70, ge=0.0, le=1.0)


class ProcessingStatus(BaseModel):
    """Schema for processing status updates"""
    video_id: int
    status: str
    progress_percent: float
    current_frame: int
    total_frames: int
    elapsed_seconds: float
    estimated_remaining_seconds: Optional[float] = None


# ============================================================================
# AI Investigation Schemas (Nemotron)
# ============================================================================

class AIAnalysisRequest(BaseModel):
    """Schema for AI analysis request"""
    event_id: Optional[str] = None
    ocr_result_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    include_context: bool = Field(default=True)
    max_tokens: int = Field(default=1000, ge=100, le=2000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class AIAnalysisResponse(BaseModel):
    """Schema for AI analysis response"""
    success: bool
    analysis: Optional[str] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    timestamp: str
    event_id: Optional[str] = None
    error: Optional[str] = None


class AIServiceStatus(BaseModel):
    """Schema for AI service status"""
    available: bool
    base_url: Optional[str] = None
    configured_model: Optional[str] = None
    model_available: Optional[bool] = None
    available_models: Optional[List[str]] = None
    total_models: Optional[int] = None
    error: Optional[str] = None
