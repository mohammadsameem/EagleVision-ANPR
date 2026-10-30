"""
Authentication and authorization for EagleVision ANPR API

Provides:
- API key authentication
- User management
- Access control
- Security utilities
"""
from .models import User, APIKey
from .auth import (
    get_current_user,
    get_current_user_optional,
    require_api_key,
    get_api_key_user,
    hash_api_key,
    verify_api_key,
    create_api_key,
    generate_api_key,
)
from .security import (
    validate_video_ownership,
    sanitize_filename,
    validate_file_content,
    check_rate_limit,
)

__all__ = [
    "User",
    "APIKey",
    "get_current_user",
    "get_current_user_optional",
    "require_api_key",
    "get_api_key_user",
    "hash_api_key",
    "verify_api_key",
    "create_api_key",
    "generate_api_key",
    "validate_video_ownership",
    "sanitize_filename",
    "validate_file_content",
    "check_rate_limit",
]
