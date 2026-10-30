"""
Unit tests for Celery tasks (mocked - no Redis required)

These tests verify task logic without requiring a real Redis broker.
For integration tests with real Redis and workers, see test_celery_integration.py
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Mock Celery before importing tasks
with patch('src.celery_tasks.celery_app'):
    from src.celery_tasks import process_video_background


class TestProcessVideoBackgroundMocked:
    """Test process_video_background task with mocked dependencies"""
    
    @patch('src.celery_tasks.SessionLocal')
    @patch('src.celery_tasks.crud')
    @patch('src.celery_tasks.ANPRPipeline')
    def test_successful_processing(self, mock_pipeline_class, mock_crud, mock_session_local):
        """Test successful video processing"""
        # Setup mocks
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_video = Mock()
        mock_video.id = 1
        mock_video.filename = "test.mp4"
        mock_video.file_path = "/uploads/test.mp4"
        mock_video.target_fps = 5.0
        mock_video.status = "pending"
        mock_video.frame_count = 100
        
        mock_crud.get_video.return_value = mock_video
        
        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.get_capabilities.return_value = {"vehicle_detection": True}
        mock_pipeline.process_video.return_value = [
            {"frame_index": 0, "plate_bbox": [100, 100, 50, 20]},
            {"frame_index": 1, "plate_bbox": None},
        ]
        mock_pipeline_class.return_value = mock_pipeline
        
        mock_crud.store_anpr_results.return_value = 2
        
        # Mock file exists
        with patch.object(Path, 'exists', return_value=True):
            # Create mock task with request context
            mock_self = Mock()
            mock_self.request.id = "test-task-id"
            mock_self.request.retries = 0
            mock_self.max_retries = 2
            mock_self.update_state = Mock()
            
            # Execute task
            result = process_video_background(mock_self, 1)
        
        # Verify result
        assert result["video_id"] == 1
        assert result["status"] == "completed"
        assert result["vehicles_count"] == 2
        assert result["plates_count"] == 1
        assert "task_id" in result
        
        # Verify database updates
        mock_crud.update_video_status.assert_any_call(mock_db, 1, "processing")
        mock_crud.update_video_status.assert_any_call(mock_db, 1, "completed")
        mock_crud.store_anpr_results.assert_called_once()
        mock_db.commit.assert_called()
        mock_db.close.assert_called()
    
    @patch('src.celery_tasks.SessionLocal')
    @patch('src.celery_tasks.crud')
    def test_video_not_found(self, mock_crud, mock_session_local):
        """Test handling of non-existent video"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_crud.get_video.return_value = None
        
        mock_self = Mock()
        mock_self.request.retries = 0
        
        with pytest.raises(ValueError, match="Video 999 not found"):
            process_video_background(mock_self, 999)
        
        mock_db.close.assert_called()
    
    @patch('src.celery_tasks.SessionLocal')
    @patch('src.celery_tasks.crud')
    def test_already_completed_idempotent(self, mock_crud, mock_session_local):
        """Test idempotency - already completed video"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_video = Mock()
        mock_video.id = 1
        mock_video.status = "completed"
        mock_video.total_vehicles = 10
        mock_video.total_plates = 5
        
        mock_crud.get_video.return_value = mock_video
        
        mock_self = Mock()
        mock_self.request.retries = 0
        
        result = process_video_background(mock_self, 1)
        
        assert result["status"] == "completed"
        assert result["message"] == "Already processed"
        assert result["detections_count"] == 10
        
        # Should not update status or process again
        mock_crud.update_video_status.assert_not_called()
        mock_db.close.assert_called()
    
    @patch('src.celery_tasks.SessionLocal')
    @patch('src.celery_tasks.crud')
    def test_file_not_found(self, mock_crud, mock_session_local):
        """Test handling of missing video file"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_video = Mock()
        mock_video.id = 1
        mock_video.file_path = "/missing/file.mp4"
        mock_video.status = "pending"
        
        mock_crud.get_video.return_value = mock_video
        
        mock_self = Mock()
        mock_self.request.retries = 0
        
        with patch.object(Path, 'exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                process_video_background(mock_self, 1)
        
        # Should update status to failed
        mock_crud.update_video_status.assert_called_with(
            mock_db, 1, "failed", error_message=pytest.ANY
        )
        mock_db.close.assert_called()
    
    @patch('src.celery_tasks.SessionLocal')
    @patch('src.celery_tasks.crud')
    @patch('src.celery_tasks.ANPRPipeline')
    def test_pipeline_failure_with_retry(self, mock_pipeline_class, mock_crud, mock_session_local):
        """Test pipeline failure triggers retry"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_video = Mock()
        mock_video.id = 1
        mock_video.file_path = "/uploads/test.mp4"
        mock_video.status = "pending"
        
        mock_crud.get_video.return_value = mock_video
        
        # Mock pipeline to raise exception
        mock_pipeline = Mock()
        mock_pipeline.get_capabilities.return_value = {"vehicle_detection": True}
        mock_pipeline.process_video.side_effect = RuntimeError("Pipeline error")
        mock_pipeline_class.return_value = mock_pipeline
        
        mock_self = Mock()
        mock_self.request.retries = 0
        mock_self.max_retries = 2
        mock_self.retry = Mock(side_effect=Exception("Retry raised"))
        
        with patch.object(Path, 'exists', return_value=True):
            with pytest.raises(Exception):
                process_video_background(mock_self, 1)
        
        # Should update to failed and attempt retry
        mock_crud.update_video_status.assert_called()
        mock_self.retry.assert_called_once()
        mock_db.close.assert_called()
    
    @patch('src.celery_tasks.SessionLocal')
    @patch('src.celery_tasks.crud')
    @patch('src.celery_tasks.ANPRPipeline')
    def test_duplicate_results_prevention(self, mock_pipeline_class, mock_crud, mock_session_local):
        """Test that duplicate results are not inserted"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        # Mock query to show existing vehicles
        mock_query = Mock()
        mock_query.filter.return_value.count.return_value = 10  # Existing results
        mock_db.query.return_value = mock_query
        
        mock_video = Mock()
        mock_video.id = 1
        mock_video.file_path = "/uploads/test.mp4"
        mock_video.status = "pending"
        mock_video.frame_count = 100
        mock_video.target_fps = 5.0
        
        mock_crud.get_video.return_value = mock_video
        
        mock_pipeline = Mock()
        mock_pipeline.get_capabilities.return_value = {"vehicle_detection": True}
        mock_pipeline.process_video.return_value = [
            {"frame_index": 0, "plate_bbox": None}
        ]
        mock_pipeline_class.return_value = mock_pipeline
        
        mock_self = Mock()
        mock_self.request.id = "test-id"
        mock_self.request.retries = 1  # This is a retry
        mock_self.max_retries = 2
        mock_self.update_state = Mock()
        
        with patch.object(Path, 'exists', return_value=True):
            result = process_video_background(mock_self, 1)
        
        # Should NOT call store_anpr_results since results exist
        mock_crud.store_anpr_results.assert_not_called()
        
        # Should still update stats and complete
        assert result["status"] == "completed"
        mock_db.close.assert_called()


class TestCeleryTaskConfiguration:
    """Test Celery task configuration"""
    
    def test_task_registered(self):
        """Test that task is properly registered"""
        # This would require actual Celery app
        # Just verify import doesn't fail
        from src.celery_tasks import process_video_background
        assert callable(process_video_background)
    
    def test_task_has_correct_settings(self):
        """Test task decorator settings"""
        from src.celery_tasks import process_video_background
        
        # Verify task is bound (has self parameter)
        assert process_video_background.__wrapped__.__code__.co_varnames[0] == 'self'


class TestCleanupTask:
    """Test cleanup_old_videos task"""
    
    @patch('src.celery_tasks.SessionLocal')
    @patch('src.celery_tasks.crud')
    def test_cleanup_old_videos(self, mock_crud, mock_session_local):
        """Test old video cleanup"""
        from src.celery_tasks import cleanup_old_videos
        from datetime import datetime, timedelta
        
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        # Mock old videos
        old_video1 = Mock()
        old_video1.file_path = "/uploads/old1.mp4"
        old_video2 = Mock()
        old_video2.file_path = "/uploads/old2.mp4"
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [old_video1, old_video2]
        mock_db.query.return_value = mock_query
        
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'unlink'):
                result = cleanup_old_videos(30)
        
        assert result["deleted"] == 2
        mock_db.delete.assert_called()
        mock_db.commit.assert_called()
        mock_db.close.assert_called()


@pytest.fixture
def mock_celery_app():
    """Fixture to mock Celery app"""
    with patch('src.celery_app.Celery') as mock:
        yield mock


def test_celery_app_configuration(mock_celery_app):
    """Test Celery app is configured correctly"""
    from src.celery_app import celery_app
    
    # Verify app exists
    assert celery_app is not None
    
    # Check configuration
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.timezone == "UTC"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
