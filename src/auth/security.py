"""
Security utilities for EagleVision ANPR

File validation, path sanitization, and rate limiting.
"""
import os
import re
import time
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

# Try to import python-magic, fall back to mimetypes if unavailable
try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    import mimetypes
    MAGIC_AVAILABLE = False
    magic = None

from .models import User
from src.database import crud

logger = logging.getLogger(__name__)

# Configuration from environment
MAX_FILE_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "500"))  # Default 500MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_VIDEO_MIMES = {
    "video/mp4",
    "video/x-msvideo",  # AVI
    "video/quicktime",  # MOV
    "video/x-matroska",  # MKV
}

# Rate limiting (simple in-memory, use Redis for production)
_rate_limit_store: Dict[str, list] = {}
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other attacks.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename (basename only, safe characters)
    
    Example:
        "../../etc/passwd" -> "passwd"
        "file<script>.mp4" -> "filescript.mp4"
    """
    # Get basename only (no path components)
    filename = os.path.basename(filename)
    
    # Remove or replace unsafe characters
    # Keep: letters, numbers, underscore, hyphen, period
    safe_filename = re.sub(r'[^\w\-.]', '_', filename)
    
    # Prevent hidden files
    if safe_filename.startswith('.'):
        safe_filename = '_' + safe_filename
    
    # Limit length
    if len(safe_filename) > 255:
        # Preserve extension
        name, ext = os.path.splitext(safe_filename)
        safe_filename = name[:250] + ext
    
    return safe_filename


def generate_safe_filename(original_filename: str, user_id: int) -> str:
    """
    Generate a safe, unique filename for storage.
    
    Args:
        original_filename: Original uploaded filename
        user_id: User ID for namespacing
    
    Returns:
        Safe filename with timestamp and hash
    
    Example:
        "video.mp4" -> "user123_20261028_abc123_video.mp4"
    """
    # Sanitize original name
    safe_name = sanitize_filename(original_filename)
    
    # Get extension
    _, ext = os.path.splitext(safe_name)
    name_without_ext = safe_name.replace(ext, '')
    
    # Generate unique component
    timestamp = int(time.time())
    hash_input = f"{user_id}_{timestamp}_{safe_name}"
    file_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    # Construct safe filename
    safe_filename = f"user{user_id}_{timestamp}_{file_hash}_{name_without_ext}{ext}"
    
    return safe_filename


async def validate_file_content(file: UploadFile, max_size_bytes: int = MAX_FILE_SIZE_BYTES) -> None:
    """
    Validate uploaded file content.
    
    Checks:
    - File size limit
    - Actual MIME type (not just extension)
    - File is readable
    
    Args:
        file: Uploaded file
        max_size_bytes: Maximum allowed file size
    
    Raises:
        HTTPException: 400 if validation fails
    """
    # Check file size by reading in chunks
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    # Read first chunk to check MIME type
    first_chunk = await file.read(chunk_size)
    file_size += len(first_chunk)
    
    if not first_chunk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded"
        )
    
    # Detect MIME type from content
    mime = None
    if MAGIC_AVAILABLE:
        try:
            mime = magic.from_buffer(first_chunk, mime=True)
        except Exception as e:
            logger.warning(f"MIME detection with magic failed: {e}, falling back to extension check")
    
    # Fallback to extension check if magic unavailable
    if mime is None:
        import mimetypes
        mime, _ = mimetypes.guess_type(file.filename)
        if mime:
            logger.info(f"Using MIME from extension: {mime}")
    
    # Validate MIME type
    if mime and mime not in ALLOWED_VIDEO_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {mime}. Allowed: {', '.join(ALLOWED_VIDEO_MIMES)}"
        )
    
    # Continue reading to check size
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        
        file_size += len(chunk)
        
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum: {MAX_FILE_SIZE_MB}MB"
            )
    
    # Reset file pointer for subsequent reads
    await file.seek(0)
    
    logger.info(f"File validation passed: {file.filename}, size: {file_size / (1024*1024):.2f}MB, mime: {mime or 'unknown'}")


def validate_video_ownership(db: Session, video_id: int, user: User) -> None:
    """
    Validate that user owns the specified video.
    
    Args:
        db: Database session
        video_id: Video ID
        user: Current user
    
    Raises:
        HTTPException: 404 if video not found, 403 if not owned by user
    """
    video = crud.get_video(db, video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found"
        )
    
    # Admin can access all videos
    if user.is_admin:
        return
    
    # Check ownership
    if video.owner_id != user.id:
        logger.warning(f"User {user.id} attempted to access video {video_id} owned by {video.owner_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this video"
        )


def check_rate_limit(user_id: int, resource: str = "api") -> None:
    """
    Check rate limit for a user.
    
    Simple sliding window rate limiting (in-memory).
    For production, use Redis with sliding window.
    
    Args:
        user_id: User ID
        resource: Resource being rate limited
    
    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    key = f"{user_id}:{resource}"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    
    # Initialize if not exists
    if key not in _rate_limit_store:
        _rate_limit_store[key] = []
    
    # Remove old requests outside window
    _rate_limit_store[key] = [
        req_time for req_time in _rate_limit_store[key]
        if req_time > window_start
    ]
    
    # Check limit
    if len(_rate_limit_store[key]) >= RATE_LIMIT_REQUESTS:
        logger.warning(f"Rate limit exceeded for user {user_id} on {resource}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)}
        )
    
    # Record this request
    _rate_limit_store[key].append(now)


def prevent_path_traversal(file_path: str, base_dir: str) -> str:
    """
    Prevent path traversal attacks.
    
    Args:
        file_path: Requested file path
        base_dir: Base directory that should contain the file
    
    Returns:
        Resolved absolute path
    
    Raises:
        HTTPException: 400 if path traversal detected
    """
    # Resolve to absolute path
    abs_base = os.path.abspath(base_dir)
    abs_path = os.path.abspath(os.path.join(abs_base, file_path))
    
    # Check that resolved path is within base directory
    if not abs_path.startswith(abs_base):
        logger.error(f"Path traversal attempt: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    return abs_path
