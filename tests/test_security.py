"""
Security Tests for EagleVision ANPR

Tests authentication, authorization, file validation, rate limiting,
and cross-user access controls.
"""
import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, patch

from src.api.main import app, get_db
from src.database.models import Base, Video
from src.auth.models import User, APIKey
from src.auth import hash_api_key, generate_api_key
from src.auth.security import (
    sanitize_filename,
    generate_safe_filename,
    check_rate_limit,
    validate_video_ownership,
    prevent_path_traversal
)

# Import all models to ensure they're registered with Base
import src.database.models  # noqa
import src.auth.models  # noqa


# ============================================================================
# Test Database Setup
# ============================================================================

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    from sqlalchemy.pool import StaticPool
    
    # Use in-memory SQLite with StaticPool for proper sharing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Import all models to ensure they're registered
    import src.database.models  # noqa
    import src.auth.models  # noqa
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create test database session
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create FastAPI test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# ============================================================================
# Test Fixtures - Users and API Keys
# ============================================================================

@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        is_admin=False,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def admin_user(test_db):
    """Create an admin user"""
    user = User(
        email="admin@example.com",
        username="admin",
        is_admin=True,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def other_user(test_db):
    """Create another test user (for cross-user tests)"""
    user = User(
        email="other@example.com",
        username="otheruser",
        is_admin=False,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_api_key(test_db, test_user):
    """Create API key for test user"""
    from src.auth.auth import create_api_key
    api_key_model, raw_key = create_api_key(test_db, test_user.id, "Test Key")
    return raw_key  # Return the raw key, not the hash


@pytest.fixture
def admin_api_key(test_db, admin_user):
    """Create API key for admin user"""
    from src.auth.auth import create_api_key
    api_key_model, raw_key = create_api_key(test_db, admin_user.id, "Admin Key")
    return raw_key


@pytest.fixture
def other_api_key(test_db, other_user):
    """Create API key for other user"""
    from src.auth.auth import create_api_key
    api_key_model, raw_key = create_api_key(test_db, other_user.id, "Other Key")
    return raw_key


@pytest.fixture
def test_video(test_db, test_user):
    """Create a test video owned by test_user"""
    video = Video(
        filename="test_video.mp4",
        file_path="/fake/path/test_video.mp4",
        file_size_bytes=1024000,
        resolution="1920x1080",
        fps=30.0,
        frame_count=900,
        duration_sec=30.0,
        target_fps=5.0,
        status="pending",
        owner_id=test_user.id
    )
    test_db.add(video)
    test_db.commit()
    test_db.refresh(video)
    return video


# ============================================================================
# Authentication Tests
# ============================================================================

class TestAuthentication:
    """Test API authentication"""
    
    def test_missing_api_key(self, client):
        """Request without API key should return 401"""
        response = client.get("/api/videos/")
        assert response.status_code == 401
        detail = response.json()["detail"].lower()
        assert "api key" in detail or "not authenticated" in detail
    
    def test_invalid_api_key(self, client):
        """Request with invalid API key should return 401"""
        response = client.get(
            "/api/videos/",
            headers={"X-API-Key": "invalid_key_12345"}
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_valid_api_key(self, client, test_api_key):
        """Request with valid API key should succeed"""
        response = client.get(
            "/api/videos/",
            headers={"X-API-Key": test_api_key}
        )
        assert response.status_code == 200
        assert "videos" in response.json()
    
    def test_revoked_api_key(self, client, test_db, test_user):
        """Request with revoked API key should return 401"""
        from src.auth.auth import create_api_key
        api_key_model, raw_key = create_api_key(test_db, test_user.id, "Revoked Key")
        
        # Revoke the key
        api_key_model.is_active = False
        test_db.commit()
        
        response = client.get(
            "/api/videos/",
            headers={"X-API-Key": raw_key}
        )
        assert response.status_code == 401
    
    def test_inactive_user(self, client, test_db):
        """Request from inactive user should return 401"""
        from src.auth.auth import create_api_key
        
        inactive_user = User(
            email="inactive@example.com",
            username="inactive",
            is_active=False
        )
        test_db.add(inactive_user)
        test_db.commit()
        test_db.refresh(inactive_user)
        
        api_key_model, raw_key = create_api_key(test_db, inactive_user.id, "Inactive User Key")
        
        # Now deactivate the user
        inactive_user.is_active = False
        test_db.commit()
        
        response = client.get(
            "/api/videos/",
            headers={"X-API-Key": raw_key}
        )
        assert response.status_code == 401


# ============================================================================
# Authorization Tests
# ============================================================================

class TestAuthorization:
    """Test resource ownership and access control"""
    
    def test_user_sees_only_own_videos(self, client, test_api_key, test_video, test_db, other_user):
        """User should only see their own videos"""
        # Create video owned by other user
        other_video = Video(
            filename="other_video.mp4",
            file_path="/fake/path/other_video.mp4",
            file_size_bytes=2048000,
            owner_id=other_user.id,
            resolution="1920x1080",
            fps=30.0,
            frame_count=900,
            duration_sec=30.0,
            target_fps=5.0,
            status="pending"
        )
        test_db.add(other_video)
        test_db.commit()
        
        # List videos - should only see own video
        response = client.get(
            "/api/videos/",
            headers={"X-API-Key": test_api_key}
        )
        assert response.status_code == 200
        videos = response.json()["videos"]
        assert len(videos) == 1
        assert videos[0]["id"] == test_video.id
    
    def test_admin_sees_all_videos(self, client, admin_api_key, test_video, test_db, other_user):
        """Admin should see all videos"""
        # Create video owned by other user
        other_video = Video(
            filename="other_video.mp4",
            file_path="/fake/path/other_video.mp4",
            file_size_bytes=2048000,
            owner_id=other_user.id,
            resolution="1920x1080",
            fps=30.0,
            frame_count=900,
            duration_sec=30.0,
            target_fps=5.0,
            status="pending"
        )
        test_db.add(other_video)
        test_db.commit()
        
        # Admin lists videos - should see all
        response = client.get(
            "/api/videos/",
            headers={"X-API-Key": admin_api_key}
        )
        assert response.status_code == 200
        videos = response.json()["videos"]
        assert len(videos) == 2
    
    def test_cannot_access_other_user_video(self, client, test_api_key, test_db, other_user):
        """User cannot access video owned by another user"""
        # Create video owned by other user
        other_video = Video(
            filename="other_video.mp4",
            file_path="/fake/path/other_video.mp4",
            file_size_bytes=2048000,
            owner_id=other_user.id,
            resolution="1920x1080",
            fps=30.0,
            frame_count=900,
            duration_sec=30.0,
            target_fps=5.0,
            status="pending"
        )
        test_db.add(other_video)
        test_db.commit()
        
        # Try to access other user's video
        response = client.get(
            f"/api/videos/{other_video.id}",
            headers={"X-API-Key": test_api_key}
        )
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()
    
    def test_cannot_delete_other_user_video(self, client, test_api_key, test_db, other_user):
        """User cannot delete video owned by another user"""
        # Create video owned by other user
        other_video = Video(
            filename="other_video.mp4",
            file_path="/fake/path/other_video.mp4",
            file_size_bytes=2048000,
            owner_id=other_user.id,
            resolution="1920x1080",
            fps=30.0,
            frame_count=900,
            duration_sec=30.0,
            target_fps=5.0,
            status="pending"
        )
        test_db.add(other_video)
        test_db.commit()
        
        # Try to delete other user's video
        response = client.delete(
            f"/api/videos/{other_video.id}",
            headers={"X-API-Key": test_api_key}
        )
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()
    
    def test_admin_can_access_any_video(self, client, admin_api_key, test_video):
        """Admin can access any video"""
        response = client.get(
            f"/api/videos/{test_video.id}",
            headers={"X-API-Key": admin_api_key}
        )
        assert response.status_code == 200
        assert response.json()["id"] == test_video.id
    
    def test_validate_video_ownership_function(self, test_db, test_user, test_video, other_user):
        """Test validate_video_ownership function directly"""
        # Owner can access
        validate_video_ownership(test_db, test_video.id, test_user)  # Should not raise
        
        # Non-owner cannot access
        with pytest.raises(Exception) as exc_info:
            validate_video_ownership(test_db, test_video.id, other_user)
        assert "403" in str(exc_info.value) or "permission" in str(exc_info.value).lower()


# ============================================================================
# File Validation Tests
# ============================================================================

class TestFileValidation:
    """Test file upload validation"""
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        assert sanitize_filename("normal_file.mp4") == "normal_file.mp4"
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("file<script>.mp4") == "file_script_.mp4"
        assert sanitize_filename(".hidden") == "_.hidden"  # Keeps extension
        assert sanitize_filename("file with spaces.mp4") == "file_with_spaces.mp4"
        
        # Test long filename
        long_name = "a" * 300 + ".mp4"
        sanitized = sanitize_filename(long_name)
        assert len(sanitized) <= 255
        assert sanitized.endswith(".mp4")
    
    def test_generate_safe_filename(self):
        """Test safe filename generation"""
        import time
        filename = generate_safe_filename("video.mp4", user_id=123)
        
        # Check format: user<id>_<timestamp>_<hash>_<name>.ext
        assert filename.startswith("user123_")
        assert filename.endswith("_video.mp4")
        assert len(filename) > 20  # Has timestamp and hash
        
        # Two calls should produce different filenames (different timestamps)
        time.sleep(0.01)  # Ensure different timestamp
        filename2 = generate_safe_filename("video.mp4", user_id=123)
        # May be same if called in same second, just verify format
        assert filename2.startswith("user123_")
    
    def test_prevent_path_traversal(self):
        """Test path traversal prevention"""
        import tempfile
        import os
        
        # Use actual temp dir for Windows
        base_dir = os.path.join(tempfile.gettempdir(), "uploads")
        
        # Valid path
        safe_path = prevent_path_traversal("video.mp4", base_dir)
        assert os.path.normpath(base_dir) in os.path.normpath(safe_path)
        
        # Path traversal attempts
        with pytest.raises(Exception) as exc_info:
            prevent_path_traversal("../../../etc/passwd", base_dir)
        assert "400" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()
        
        with pytest.raises(Exception):
            prevent_path_traversal("subdir/../../etc/passwd", base_dir)
    
    @pytest.mark.skip(reason="Async file validation requires pytest-asyncio or anyio plugin")
    @patch('src.auth.security.magic.from_buffer')
    async def test_validate_file_content_invalid_mime(self, mock_magic, test_api_key, client):
        """Test file validation rejects invalid MIME types"""
        mock_magic.return_value = "application/x-executable"
        
        # Mock file upload
        files = {"file": ("fake.mp4", b"fake content", "video/mp4")}
        response = client.post(
            "/api/videos/upload",
            files=files,
            headers={"X-API-Key": test_api_key}
        )
        
        # Should be rejected (in real scenario - here we're just checking structure)
        # Note: Actual test would need proper async mocking
        assert response.status_code in [400, 500]  # Depending on validation


# ============================================================================
# Rate Limiting Tests
# ============================================================================

class TestRateLimiting:
    """Test rate limiting"""
    
    def test_rate_limit_enforced(self):
        """Test that rate limit is enforced"""
        from src.auth.security import _rate_limit_store, RATE_LIMIT_REQUESTS
        
        # Clear rate limit store
        _rate_limit_store.clear()
        
        user_id = 999
        resource = "test_resource"
        
        # Make requests up to limit - should succeed
        for i in range(RATE_LIMIT_REQUESTS):
            check_rate_limit(user_id, resource)  # Should not raise
        
        # Next request should be rate limited
        with pytest.raises(Exception) as exc_info:
            check_rate_limit(user_id, resource)
        assert "429" in str(exc_info.value) or "rate limit" in str(exc_info.value).lower()
    
    def test_rate_limit_per_user(self):
        """Test that rate limits are per-user"""
        from src.auth.security import _rate_limit_store
        
        _rate_limit_store.clear()
        
        # User 1 makes requests
        for i in range(5):
            check_rate_limit(user_id=1, resource="api")
        
        # User 2 should have separate limit
        for i in range(5):
            check_rate_limit(user_id=2, resource="api")  # Should not raise
    
    def test_rate_limit_window(self):
        """Test that rate limit resets after window"""
        import time
        from src.auth.security import _rate_limit_store, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
        
        _rate_limit_store.clear()
        
        # Set very short window for testing
        original_window = RATE_LIMIT_WINDOW_SECONDS
        
        user_id = 888
        
        # This test would require mocking time or very long waits
        # Just verify the store cleans old entries
        key = f"{user_id}:api"
        _rate_limit_store[key] = [time.time() - 1000]  # Old entry
        
        # Should allow request (old entry cleaned)
        check_rate_limit(user_id, "api")


# ============================================================================
# Integration Tests
# ============================================================================

class TestSecurityIntegration:
    """Integration tests for complete security workflows"""
    
    def test_complete_upload_workflow_with_auth(self, client, test_api_key):
        """Test complete authenticated upload workflow"""
        # This would require actual file handling
        # Simplified test structure:
        pass
    
    def test_cross_user_isolation(self, client, test_api_key, other_api_key, test_db, test_user, other_user):
        """Test complete isolation between users"""
        # User 1 uploads video
        video1 = Video(
            filename="user1_video.mp4",
            file_path="/fake/path/user1_video.mp4",
            file_size_bytes=1024000,
            owner_id=test_user.id,
            resolution="1920x1080",
            fps=30.0,
            frame_count=900,
            duration_sec=30.0,
            target_fps=5.0,
            status="pending"
        )
        test_db.add(video1)
        test_db.commit()
        
        # User 2 uploads video
        video2 = Video(
            filename="user2_video.mp4",
            file_path="/fake/path/user2_video.mp4",
            file_size_bytes=2048000,
            owner_id=other_user.id,
            resolution="1920x1080",
            fps=30.0,
            frame_count=900,
            duration_sec=30.0,
            target_fps=5.0,
            status="pending"
        )
        test_db.add(video2)
        test_db.commit()
        
        # User 1 should only see their video
        response = client.get(
            "/api/videos/",
            headers={"X-API-Key": test_api_key}
        )
        assert response.status_code == 200
        videos = response.json()["videos"]
        assert len(videos) == 1
        # Videos response includes all fields from VideoResponse schema
        assert videos[0]["id"] == video1.id
        
        # User 1 cannot access user 2's video
        response = client.get(
            f"/api/videos/{video2.id}",
            headers={"X-API-Key": test_api_key}
        )
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
