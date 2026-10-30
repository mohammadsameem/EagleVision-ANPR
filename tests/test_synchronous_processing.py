"""
Tests for synchronous video processing (no Redis/Celery required)

These tests verify the fallback processing works without background workers.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, ANY

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.processing import process_video_task
from src.database import crud
from src.database.models import Video


class TestSynchronousProcessing:
    """Test synchronous video processing workflow"""
    
    @patch('src.api.processing.SessionLocal')
    @patch('src.api.processing.crud')
    @patch('src.api.processing.ANPRPipeline')
    def test_process_video_task_success(self, mock_pipeline_class, mock_crud, mock_session_local):
        """Test successful synchronous processing"""
        # Setup mocks
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_video = Mock()
        mock_video.id = 1
        mock_video.filename = "test.mp4"
        mock_video.file_path = str(Path("data/test_videos/test.mp4"))
        mock_video.target_fps = 5.0
        mock_video.status = "pending"
        
        mock_crud.get_video.return_value = mock_video
        mock_crud.update_video_status.return_value = mock_video
        
        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.get_capabilities.return_value = {"vehicle_detection": True}
        mock_pipeline.process_video.return_value = [
            {"frame_index": 0, "vehicle_id": 1, "plate_bbox": [100, 100, 50, 20]},
            {"frame_index": 1, "vehicle_id": 2, "plate_bbox": None},
        ]
        mock_pipeline_class.return_value = mock_pipeline
        
        mock_crud.store_anpr_results.return_value = 2
        
        # Mock file exists
        with patch.object(Path, 'exists', return_value=True):
            result = process_video_task(1)
        
        # Verify result
        assert result["video_id"] == 1
        assert result["status"] == "completed"
        assert result["detections_count"] == 2
        assert result["vehicles_count"] == 2
        assert result["plates_count"] == 1
        
        # Verify database calls
        mock_crud.get_video.assert_called_once_with(mock_db, 1)
        mock_crud.update_video_status.assert_any_call(mock_db, 1, "processing")
        mock_crud.update_video_status.assert_any_call(mock_db, 1, "completed")
        mock_crud.store_anpr_results.assert_called_once_with(mock_db, 1, ANY)
        mock_db.close.assert_called()
    
    @patch('src.api.processing.SessionLocal')
    @patch('src.api.processing.crud')
    def test_process_video_not_found(self, mock_crud, mock_session_local):
        """Test processing non-existent video"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_crud.get_video.return_value = None
        
        with pytest.raises(ValueError, match="Video 999 not found"):
            process_video_task(999)
        
        mock_db.close.assert_called()
    
    @patch('src.api.processing.SessionLocal')
    @patch('src.api.processing.crud')
    def test_process_video_wrong_status(self, mock_crud, mock_session_local):
        """Test processing video in wrong status"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_video = Mock()
        mock_video.id = 1
        mock_video.status = "completed"
        
        mock_crud.get_video.return_value = mock_video
        
        with pytest.raises(ValueError, match="not in pending status"):
            process_video_task(1)
        
        mock_db.close.assert_called()
    
    @patch('src.api.processing.SessionLocal')
    @patch('src.api.processing.crud')
    def test_process_video_file_not_found(self, mock_crud, mock_session_local):
        """Test processing with missing video file"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_video = Mock()
        mock_video.id = 1
        mock_video.file_path = "/missing/file.mp4"
        mock_video.status = "pending"
        
        mock_crud.get_video.return_value = mock_video
        
        with patch.object(Path, 'exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                process_video_task(1)
        
        # Should update status to failed
        mock_crud.update_video_status.assert_called_with(
            mock_db, 1, "failed", error_message=ANY
        )
        mock_db.close.assert_called()
    
    @patch('src.api.processing.SessionLocal')
    @patch('src.api.processing.crud')
    @patch('src.api.processing.ANPRPipeline')
    def test_process_video_pipeline_error(self, mock_pipeline_class, mock_crud, mock_session_local):
        """Test processing with pipeline error"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_video = Mock()
        mock_video.id = 1
        mock_video.file_path = "/uploads/test.mp4"
        mock_video.target_fps = 5.0
        mock_video.status = "pending"
        
        mock_crud.get_video.return_value = mock_video
        
        # Mock pipeline to raise error
        mock_pipeline = Mock()
        mock_pipeline.get_capabilities.return_value = {"vehicle_detection": True}
        mock_pipeline.process_video.side_effect = RuntimeError("Pipeline failed")
        mock_pipeline_class.return_value = mock_pipeline
        
        with patch.object(Path, 'exists', return_value=True):
            with pytest.raises(RuntimeError, match="Pipeline failed"):
                process_video_task(1)
        
        # Should update status to failed
        mock_crud.update_video_status.assert_called()
        calls = [str(call) for call in mock_crud.update_video_status.call_args_list]
        assert any("failed" in call for call in calls)
        mock_db.close.assert_called()


class TestAPIIntegrationWithoutCelery:
    """Test API endpoints work without Celery/Redis"""
    
    def test_celery_imports_gracefully_fail(self):
        """Test that missing Redis doesn't break API startup"""
        # The API should import even if Redis is unavailable
        from src.api import main
        assert main.app is not None
        
        # CELERY_AVAILABLE should be False without Redis
        if not main.CELERY_AVAILABLE:
            assert main.process_video_background is None
    
    def test_synchronous_mode_always_available(self):
        """Test synchronous processing is always available"""
        from src.api.processing import process_video_task
        assert callable(process_video_task)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
