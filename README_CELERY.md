# EagleVision ANPR - Background Processing Setup

This guide explains how to set up and use background video processing with Celery and Redis.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   FastAPI   │────▶│    Redis     │◀────│ Celery Worker│
│  (API)      │     │   (Broker)   │     │  (ANPR)      │
└─────────────┘     └──────────────┘     └──────────────┘
       │                                          │
       └──────────┬───────────────────────────────┘
                  │
            ┌─────▼──────┐
            │  SQLite    │
            │ (Database) │
            └────────────┘
```

## Quick Start (Windows)

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Start Redis

Using Docker (recommended):
```powershell
docker-compose -f docker-compose.dev.yml up -d
```

Or install Redis on Windows:
- Download from: https://github.com/microsoftarchive/redis/releases
- Or use WSL2 with Linux Redis

### 3. Start Celery Worker

```powershell
celery -A src.celery_app worker --loglevel=info --pool=solo
```

**Note:** Use `--pool=solo` on Windows since `prefork` pool doesn't work on Windows.

### 4. Start FastAPI

```powershell
uvicorn src.api.main:app --reload --port 8000
```

### 5. Submit a Video for Processing

```powershell
# Upload video
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/videos/upload" `
  -Method POST `
  -Form @{file = Get-Item "path/to/video.mp4"; target_fps = "5"}

$videoId = $response.id

# Trigger background processing
Invoke-RestMethod -Uri "http://localhost:8000/api/videos/$videoId/process?use_celery=true" `
  -Method POST
```

### 6. Check Processing Status

```powershell
# Poll status
Invoke-RestMethod -Uri "http://localhost:8000/api/videos/$videoId/status"
```

## Usage

### Background Processing (Default)

```python
import requests

# Upload
with open("video.mp4", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/videos/upload",
        files={"file": f},
        params={"target_fps": 5}
    )
video_id = response.json()["id"]

# Process in background (returns immediately)
response = requests.post(
    f"http://localhost:8000/api/videos/{video_id}/process",
    params={"use_celery": True}  # Default
)
print(f"Task submitted: {response.json()['task_id']}")

# Poll status
import time
while True:
    status = requests.get(f"http://localhost:8000/api/videos/{video_id}/status").json()
    print(f"Status: {status['status']} - {status['progress_percent']:.1f}%")
    if status["status"] in ("completed", "failed"):
        break
    time.sleep(2)

# Get results
results = requests.get(f"http://localhost:8000/api/videos/{video_id}/results").json()
print(f"Vehicles: {results['statistics']['total_vehicles']}")
print(f"Plates: {results['statistics']['total_plates']}")
```

### Synchronous Processing (Testing)

```python
# Process immediately (blocks until complete)
response = requests.post(
    f"http://localhost:8000/api/videos/{video_id}/process",
    params={"use_celery": False}
)
print(f"Status: {response.json()['status']}")
```

## Configuration

### Environment Variables

```powershell
# Redis URL (default: redis://localhost:6379/0)
$env:REDIS_URL = "redis://localhost:6379/0"

# Database URL (default: sqlite:///./eaglevision_anpr.db)
$env:DATABASE_URL = "sqlite:///./eaglevision_anpr.db"
```

### Celery Settings

Edit `src/celery_app.py` to configure:
- Task retry behavior
- Worker prefetch multiplier
- Result expiration
- Queue routing

## Monitoring

### Redis Commander (Web UI)

Access at http://localhost:8081 to view:
- Task queue depth
- Active workers
- Result keys

### Celery Flower (Optional)

```powershell
pip install flower
celery -A src.celery_app flower --port=5555
```

Access at http://localhost:5555 for:
- Worker status
- Task history
- Real-time monitoring

### Command Line

```powershell
# Check Redis
docker exec eaglevision-redis redis-cli ping

# Check Celery
celery -A src.celery_app inspect active

# Check queue length
celery -A src.celery_app inspect stats
```

## Testing

### Unit Tests (Mocked)

```powershell
pytest tests/test_celery_tasks.py -v
```

### Integration Tests (Requires Redis)

```powershell
# Start Redis
docker-compose -f docker-compose.dev.yml up -d

# Run integration tests
pytest tests/test_celery_integration.py -v --redis
```

### Manual Testing

```powershell
# Test with existing video
python test_background_processing.py
```

## Troubleshooting

### Celery Won't Start

**Error:** `ImportError: No module named 'celery'`
```powershell
pip install celery==5.4.0 redis==5.2.0
```

**Error:** `kombu.exceptions.OperationalError: Error 111 connecting to localhost:6379`
```powershell
# Check Redis is running
docker ps | Select-String redis

# Or start Redis
docker-compose -f docker-compose.dev.yml up -d
```

### Tasks Not Processing

**Check worker is running:**
```powershell
celery -A src.celery_app inspect active
```

**Check queue:**
```powershell
celery -A src.celery_app inspect registered
```

### API Returns "Background processing unavailable"

**Cause:** Redis not accessible

**Fix:**
1. Ensure Redis is running
2. Check REDIS_URL environment variable
3. Use `use_celery=false` for synchronous processing

### Worker Crashes

**Check logs:**
```powershell
# Worker console output shows errors
celery -A src.celery_app worker --loglevel=debug
```

**Common issues:**
- File not found (check video file path)
- Memory exhaustion (reduce worker concurrency)
- Database locked (check SQLite isn't locked by another process)

## Production Deployment

### Scaling Workers

```powershell
# Multiple workers
celery -A src.celery_app worker -n worker1@%h --loglevel=info
celery -A src.celery_app worker -n worker2@%h --loglevel=info
```

### Systemd Service (Linux)

Create `/etc/systemd/system/eaglevision-worker.service`:
```ini
[Unit]
Description=EagleVision Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=eaglevision
WorkingDirectory=/opt/eaglevision
Environment="REDIS_URL=redis://localhost:6379/0"
ExecStart=/opt/eaglevision/venv/bin/celery -A src.celery_app worker \
  --loglevel=info \
  --pidfile=/var/run/celery/%n.pid \
  --logfile=/var/log/celery/%n.log
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker Production

Use `docker-compose.prod.yml` (create separately) with:
- Redis with persistence
- Multiple Celery workers
- Supervisor for process management
- Health checks

## Task Reference

### process_video_background

**Description:** Process video through ANPR pipeline

**Arguments:**
- `video_id` (int): Database ID of video

**Returns:**
```json
{
  "video_id": 1,
  "status": "completed",
  "detections_count": 47,
  "vehicles_count": 47,
  "plates_count": 21,
  "task_id": "abc123..."
}
```

**Retry:** Up to 2 retries with 30s delay

**Idempotent:** Yes (won't duplicate results)

### cleanup_old_videos (Optional)

**Description:** Delete old completed videos

**Arguments:**
- `days_old` (int): Age threshold in days (default: 30)

**Scheduling:**
```python
from celery import schedules
celery_app.conf.beat_schedule = {
    'cleanup-daily': {
        'task': 'cleanup_old_videos',
        'schedule': schedules.crontab(hour=2, minute=0),  # 2 AM daily
        'args': (30,)
    }
}
```

## Architecture Details

### Task Flow

1. **API** receives upload → creates DB record (status="pending")
2. **API** receives process request → submits Celery task
3. **Celery** picks up task → updates status="processing"
4. **Worker** runs ANPR pipeline → stores results in DB
5. **Worker** updates status="completed" or "failed"
6. **API** polls status → returns current state from DB

### Idempotency

Tasks are idempotent:
- Check video status before processing
- Skip if already completed
- Check for existing results before inserting
- Safe to retry on transient failures

### Failure Handling

- **File not found:** Fail immediately (no retry)
- **Pipeline error:** Retry up to 2 times
- **Database error:** Retry up to 2 times
- **All retries exhausted:** Set status="failed" with error message

## Next Steps

- [ ] Add progress callbacks for real-time updates
- [ ] Implement task prioritization (urgent videos)
- [ ] Add task cancellation endpoint
- [ ] Set up Celery Beat for scheduled cleanup
- [ ] Add worker health monitoring
- [ ] Implement task result webhooks

