"""
Integration tests for Celery background processing

Requires:
- Redis running on localhost:6379
- Celery worker running
- Real video file for testing

Run with: pytest tests/test_celery_integration.py -v --redis

Mark tests that require Redis with @pytest.mark.redis
"""
import pytest
import time
import requests
from pathlib import Path

# Mark all tests in this module as requiring Redis
pytestmark = pytest.mark.redis

# Test configuration
API_BASE = "http://localhost:8000"
TEST_VIDEO = "data/test_videos/gemini_generated_video_0eb4eec1.mp4"
REDIS_REQUIRED_MSG = "Redis integration tests skipped (use --redis to run)"


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "redis: mark test as requiring Redis broker and Celery worker"
    )


def check_redis_available():
    """Check if Redis is accessible"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        r.ping()
        return True
    except Exception:
        return False


def check_api_available():
    """Check if API is accessible"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=1)
        return response.status_code == 200
    except Exception:
        return False


def check_celery_worker_available():
    """Check if Celery worker is running"""
    try:
        from src.celery_app import celery_app
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        return active_workers is not None and len(active_workers) > 0
    except Exception:
        return False


@pytest.fixture(scope="module")
def redis_available():
    """Fixture to check Redis availability"""
    if not check_redis_available():
        pytest.skip("Redis not available")
    return True


@pytest.fixture(scope="module")
def api_available():
    """Fixture to check API availability"""
    if not check_api_available():
        pytest.skip("FastAPI not running")
    return True


@pytest.fixture(scope="module")
def celery_worker_available():
    """Fixture to check Celery worker availability"""
    if not check_celery_worker_available():
        pytest.skip("Celery worker not running")
    return True


@pytest.fixture(scope="module")
def test_video_available():
    """Fixture to check test video availability"""
    if not Path(TEST_VIDEO).exists():
        pytest.skip(f"Test video not found: {TEST_VIDEO}")
    return TEST_VIDEO


class TestBackgroundProcessingIntegration:
    """Integration tests with real Redis, Celery, and API"""
    
    def test_redis_connection(self, redis_available):
        """Test Redis connection"""
        import redis
        r = redis.Redis(host='localhost', port=6379)
        assert r.ping() == True
    
    def test_celery_worker_registered(self, redis_available, celery_worker_available):
        """Test Celery worker has registered tasks"""
        from src.celery_app import celery_app
        inspect = celery_app.control.inspect()
        registered = inspect.registered()
        
        assert registered is not None
        assert len(registered) > 0
        
        # Check process_video_background is registered
        for worker, tasks in registered.items():
            assert "process_video_background" in tasks
    
    def test_upload_and_background_processing(
        self,
        redis_available,
        api_available,
        celery_worker_available,
        test_video_available
    ):
        """Test complete workflow: upload → background processing → results"""
        
        # Step 1: Upload video
        with open(test_video_available, "rb") as f:
            response = requests.post(
                f"{API_BASE}/api/videos/upload",
                files={"file": (Path(test_video_available).name, f, "video/mp4")},
                params={"target_fps": 1}
            )
        
        assert response.status_code == 201
        video_data = response.json()
        video_id = video_data["id"]
        assert video_data["status"] == "pending"
        
        # Step 2: Submit for background processing
        response = requests.post(
            f"{API_BASE}/api/videos/{video_id}/process",
            params={"use_celery": True}
        )
        
        assert response.status_code == 200
        process_data = response.json()
        assert "task_id" in process_data
        task_id = process_data["task_id"]
        
        print(f"\n[Integration Test] Video {video_id} submitted with task {task_id}")
        
        # Step 3: Poll status until completion
        max_wait = 120  # 2 minutes timeout
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < max_wait:
            response = requests.get(f"{API_BASE}/api/videos/{video_id}/status")
            assert response.status_code == 200
            
            status_data = response.json()
            current_status = status_data["status"]
            
            if current_status != last_status:
                print(f"  Status: {current_status} ({status_data['progress_percent']:.1f}%)")
                last_status = current_status
            
            if current_status == "completed":
                print(f"  Completed in {time.time() - start_time:.1f}s")
                break
            elif current_status == "failed":
                pytest.fail(f"Processing failed: {status_data.get('error_message')}")
            
            time.sleep(2)
        
        assert current_status == "completed", f"Processing timed out (status: {current_status})"
        
        # Step 4: Verify results
        response = requests.get(f"{API_BASE}/api/videos/{video_id}/results")
        assert response.status_code == 200
        
        results_data = response.json()
        stats = results_data["statistics"]
        
        assert stats["total_vehicles"] > 0, "Should have detected vehicles"
        print(f"  Vehicles: {stats['total_vehicles']}, Plates: {stats['total_plates']}")
        
        # Step 5: Cleanup
        response = requests.delete(f"{API_BASE}/api/videos/{video_id}")
        assert response.status_code == 204
    
    def test_duplicate_processing_prevented(
        self,
        redis_available,
        api_available,
        test_video_available
    ):
        """Test that duplicate processing requests are handled correctly"""
        
        # Upload
        with open(test_video_available, "rb") as f:
            response = requests.post(
                f"{API_BASE}/api/videos/upload",
                files={"file": (Path(test_video_available).name, f, "video/mp4")},
                params={"target_fps": 1}
            )
        
        video_id = response.json()["id"]
        
        # Process once (synchronous for speed)
        response = requests.post(
            f"{API_BASE}/api/videos/{video_id}/process",
            params={"use_celery": False}
        )
        assert response.status_code == 200
        
        # Try to process again
        response = requests.post(
            f"{API_BASE}/api/videos/{video_id}/process",
            params={"use_celery": False}
        )
        
        # Should be rejected
        assert response.status_code == 400
        assert "cannot be processed" in response.json()["detail"].lower()
        
        # Cleanup
        requests.delete(f"{API_BASE}/api/videos/{video_id}")
    
    def test_synchronous_fallback_still_works(
        self,
        api_available,
        test_video_available
    ):
        """Test synchronous processing still works (Celery not required)"""
        
        # Upload
        with open(test_video_available, "rb") as f:
            response = requests.post(
                f"{API_BASE}/api/videos/upload",
                files={"file": (Path(test_video_available).name, f, "video/mp4")},
                params={"target_fps": 1}
            )
        
        video_id = response.json()["id"]
        
        # Process synchronously
        response = requests.post(
            f"{API_BASE}/api/videos/{video_id}/process",
            params={"use_celery": False}
        )
        
        assert response.status_code == 200
        process_data = response.json()
        assert process_data["status"] == "completed"
        assert "task_id" not in process_data  # No Celery task for sync
        
        # Verify results exist
        response = requests.get(f"{API_BASE}/api/videos/{video_id}/results")
        assert response.status_code == 200
        
        # Cleanup
        requests.delete(f"{API_BASE}/api/videos/{video_id}")


class TestErrorHandling:
    """Test error handling and failure scenarios"""
    
    def test_api_handles_redis_unavailable(self, api_available, test_video_available):
        """Test API behavior when Redis is unavailable"""
        
        # Upload video
        with open(test_video_available, "rb") as f:
            response = requests.post(
                f"{API_BASE}/api/videos/upload",
                files={"file": (Path(test_video_available).name, f, "video/mp4")},
                params={"target_fps": 1}
            )
        
        video_id = response.json()["id"]
        
        # Try to use Celery (may fail if Redis down)
        response = requests.post(
            f"{API_BASE}/api/videos/{video_id}/process",
            params={"use_celery": True}
        )
        
        # Should either:
        # 1. Return 503 (service unavailable) if Redis is down, OR
        # 2. Return 200 if Redis/Celery available
        assert response.status_code in (200, 503)
        
        if response.status_code == 503:
            assert "unavailable" in response.json()["detail"].lower()
        
        # Cleanup
        requests.delete(f"{API_BASE}/api/videos/{video_id}")


if __name__ == "__main__":
    # Check prerequisites
    print("Checking prerequisites for integration tests...")
    print(f"  Redis: {'✅' if check_redis_available() else '❌'}")
    print(f"  API: {'✅' if check_api_available() else '❌'}")
    print(f"  Celery Worker: {'✅' if check_celery_worker_available() else '❌'}")
    print(f"  Test Video: {'✅' if Path(TEST_VIDEO).exists() else '❌'}")
    print()
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])
