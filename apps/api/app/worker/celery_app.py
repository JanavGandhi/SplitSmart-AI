"""
Celery application instance — importable by workers and the FastAPI app.

Start the worker with:
    celery -A app.worker.celery_app worker --loglevel=info
"""
from app.worker.tasks import celery_app

__all__ = ["celery_app"]
