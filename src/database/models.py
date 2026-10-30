"""
SQLAlchemy models for EagleVision ANPR database

Schema designed for:
- Video processing metadata
- Vehicle detections
- Plate detections
- OCR results with review workflow
- Human review submissions
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Video(Base):
    """Video processing metadata"""

    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer)
    
    # Video properties
    resolution = Column(String(50))  # e.g., "1920x1080"
    fps = Column(Float)
    frame_count = Column(Integer)
    duration_sec = Column(Float)
    
    # Processing metadata
    status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed
    target_fps = Column(Float)  # Processing frame rate
    frames_processed = Column(Integer, default=0)
    
    # Statistics
    total_vehicles = Column(Integer, default=0)
    total_plates = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Error handling
    error_message = Column(Text)
    
    # Relationships
    owner = relationship("User", back_populates="videos", foreign_keys=[owner_id])
    vehicles = relationship("Vehicle", back_populates="video", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_status_created", "status", "created_at"),
        Index("idx_owner_status", "owner_id", "status"),
    )

    def __repr__(self):
        return f"<Video(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class Vehicle(Base):
    """Vehicle detection in a specific frame"""

    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Frame information
    frame_index = Column(Integer, nullable=False, index=True)  # Processed frame index (0, 1, 2, ...)
    source_frame = Column(Integer, nullable=False)  # Original video frame number
    timestamp_ms = Column(Integer, nullable=False, index=True)  # Timestamp in milliseconds
    
    # Detection data
    bbox_x = Column(Integer, nullable=False)  # Bounding box x coordinate
    bbox_y = Column(Integer, nullable=False)  # Bounding box y coordinate
    bbox_width = Column(Integer, nullable=False)
    bbox_height = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False, index=True)
    vehicle_class = Column(Integer, nullable=False)  # YOLOv8 class ID (2=car, 3=motorcycle, 5=bus, 7=truck)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    video = relationship("Video", back_populates="vehicles")
    plates = relationship("Plate", back_populates="vehicle", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_video_frame", "video_id", "frame_index"),
        Index("idx_video_timestamp", "video_id", "timestamp_ms"),
    )

    def __repr__(self):
        return f"<Vehicle(id={self.id}, video_id={self.video_id}, frame={self.frame_index})>"


class Plate(Base):
    """License plate detection within a vehicle"""

    __tablename__ = "plates"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Plate detection data (relative to vehicle crop)
    bbox_x_relative = Column(Integer, nullable=False)
    bbox_y_relative = Column(Integer, nullable=False)
    bbox_width_relative = Column(Integer, nullable=False)
    bbox_height_relative = Column(Integer, nullable=False)
    
    # Plate detection data (absolute frame coordinates)
    bbox_x_absolute = Column(Integer)
    bbox_y_absolute = Column(Integer)
    bbox_width_absolute = Column(Integer)
    bbox_height_absolute = Column(Integer)
    
    confidence = Column(Float, nullable=False, index=True)
    detection_method = Column(String(50))  # "yolo_model" or "heuristic_fallback"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="plates")
    ocr_results = relationship("OCRResult", back_populates="plate", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_vehicle_confidence", "vehicle_id", "confidence"),
    )

    def __repr__(self):
        return f"<Plate(id={self.id}, vehicle_id={self.vehicle_id}, confidence={self.confidence:.2f})>"


class OCRResult(Base):
    """OCR text recognition result for a plate"""

    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    plate_id = Column(Integer, ForeignKey("plates.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # OCR results
    text = Column(String(50), index=True)  # Recognized plate text
    confidence = Column(Float, index=True)
    
    # OCR engine details
    engine_used = Column(String(50))  # "easyocr", "paddleocr", or "hybrid"
    easyocr_text = Column(String(50))
    easyocr_confidence = Column(Float)
    paddleocr_text = Column(String(50))
    paddleocr_confidence = Column(Float)
    
    # Review flags
    needs_review = Column(Boolean, default=False, nullable=False, index=True)
    review_reason = Column(String(255))  # "low_confidence", "engine_disagreement", "invalid_format", etc.
    is_valid_format = Column(Boolean)
    
    # Processing metadata
    processing_time_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    plate = relationship("Plate", back_populates="ocr_results")
    reviews = relationship("Review", back_populates="ocr_result", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_needs_review_created", "needs_review", "created_at"),
        Index("idx_text_confidence", "text", "confidence"),
    )

    def __repr__(self):
        return f"<OCRResult(id={self.id}, text='{self.text}', confidence={self.confidence:.2f}, needs_review={self.needs_review})>"


class Review(Base):
    """Human review submission for OCR result"""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    ocr_result_id = Column(Integer, ForeignKey("ocr_results.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Review data
    reviewed_text = Column(String(50), nullable=False, index=True)  # Corrected plate text
    reviewer_notes = Column(Text)
    reviewer_id = Column(String(100), index=True)  # Deprecated: Use reviewer_user_id instead
    
    # Review metadata
    is_correct = Column(Boolean)  # True if original OCR was correct
    correction_type = Column(String(50))  # "confirmed", "corrected", "rejected", "ambiguous"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    ocr_result = relationship("OCRResult", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews", foreign_keys=[reviewer_user_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_reviewer_created", "reviewer_user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Review(id={self.id}, ocr_result_id={self.ocr_result_id}, reviewed_text='{self.reviewed_text}')>"
