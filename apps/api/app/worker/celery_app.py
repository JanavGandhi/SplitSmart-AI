"""Celery worker — stub for Stage 3 implementation."""
# Full implementation in Stage 3: Async Vision AI Receipt Pipeline
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "splitsmart",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
)
