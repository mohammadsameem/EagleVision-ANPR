"""
Authentication utilities for EagleVision ANPR

Provides API key authentication and user management.
"""
import os
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from src.database import get_db
from .models import User, APIKey

logger = logging.getLogger(__name__)

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.
    
    Args:
        api_key: Raw API key string
    
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """
    Generate a secure random API key.
    
    Returns:
        32-character hexadecimal key (128 bits of entropy)
    """
    return secrets.token_hex(16)  # 32 hex characters


def create_api_key(
    db: Session,
    user_id: int,
    name: Optional[str] = None,
    expires_in_days: Optional[int] = None
) -> tuple[APIKey, str]:
    """
    Create a new API key for a user.
    
    Args:
        db: Database session
        user_id: User ID
        name: Optional key name/description
        expires_in_days: Optional expiration in days
    
    Returns:
        Tuple of (APIKey model, raw_api_key_string)
        
    Note:
        The raw API key is only returned once and cannot be recovered.
        Store the returned key securely.
    """
    # Generate key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:8]
    
    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    # Create record
    api_key = APIKey(
        user_id=user_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        expires_at=expires_at,
        is_active=True
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    logger.info(f"Created API key for user {user_id}: {key_prefix}...")
    
    return api_key, raw_key


def verify_api_key(db: Session, api_key: str) -> Optional[tuple[int, str]]:
    """
    Verify an API key and return the associated user ID and key prefix.
    
    Args:
        db: Database session
        api_key: Raw API key string
    
    Returns:
        Tuple of (user_id, key_prefix) if valid, None if invalid
        
    Note:
        Returns scalar values instead of ORM object to avoid session issues.
    """
    key_hash = hash_api_key(api_key)
    
    # Look up key
    api_key_record = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()
    
    if not api_key_record:
        return None
    
    # Check expiration
    if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
        logger.warning(f"Expired API key used: {api_key_record.key_prefix}...")
        return None
    
    # Extract scalar values BEFORE any commits
    user_id = api_key_record.user_id
    key_prefix = api_key_record.key_prefix
    
    # Update last used timestamp
    api_key_record.last_used_at = datetime.utcnow()
    db.commit()
    
    return (user_id, key_prefix)


async def get_api_key_user(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current user from API key.
    
    Raises 401 if authentication fails.
    
    Args:
        api_key: API key from header
        db: Database session
    
    Returns:
        User model
    
    Raises:
        HTTPException: 401 if authentication fails
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Verify key - returns (user_id, key_prefix) tuple
    verify_result = verify_api_key(db, api_key)
    
    if not verify_result:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    user_id, key_prefix = verify_result
    
    # Get user
    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()
    
    if not user:
        logger.error(f"API key {key_prefix}... has no active user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive",
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return user


async def get_current_user_optional(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to optionally get current user from API key.
    
    Returns None if no key provided or authentication fails.
    Does not raise exceptions.
    
    Args:
        api_key: API key from header
        db: Database session
    
    Returns:
        User model or None
    """
    if not api_key:
        return None
    
    try:
        verify_result = verify_api_key(db, api_key)
        if not verify_result:
            return None
        
        user_id, key_prefix = verify_result
        
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if user:
            user.last_login_at = datetime.utcnow()
            db.commit()
        
        return user
    except Exception as e:
        logger.error(f"Error in optional auth: {e}")
        return None


# Aliases for clarity
get_current_user = get_api_key_user
require_api_key = get_api_key_user
