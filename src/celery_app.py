"""
Celery application configuration for EagleVision ANPR

Handles asynchronous video processing with Redis broker.
"""
import os
from celery import Celery
from kombu import Queue

# Get Redis URL from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery application
celery_app = Celery(
    "eaglevision",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.celery_tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend settings
    result_backend=REDIS_URL,
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=False,  # Don't persist results (use database instead)
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Reject if worker crashes
    worker_prefetch_multiplier=1,  # One task at a time per worker
    
    # Retry settings
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 2, "countdown": 5},
    
    # Queue settings
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="task.#"),
        Queue("priority", routing_key="priority.#"),
    ),
    
    # Worker settings
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s",
)

if __name__ == "__main__":
    celery_app.start()
