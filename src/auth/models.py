"""
Authentication models for EagleVision ANPR

User and API key models for access control.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.database.models import Base


class User(Base):
    """User account"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="owner", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_user_id")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class APIKey(Base):
    """API key for authentication"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 hash
    key_prefix = Column(String(8), nullable=False)  # First 8 chars for identification
    name = Column(String(100))  # Optional key name/description
    
    # Security
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)  # Optional expiration
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index("idx_key_hash_active", "key_hash", "is_active"),
    )
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, user_id={self.user_id}, prefix='{self.key_prefix}')>"
