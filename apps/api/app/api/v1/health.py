"""Health check router — GET /api/v1/health"""
import time

import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text

from app.database import engine
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint verifying DB and Redis connectivity.
    Returns 200 OK with connection statuses.
    """
    settings = get_settings()
    result = {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": time.time(),
        "db": "disconnected",
        "redis": "disconnected",
        "ocr_mode": "mock" if settings.use_mock_ocr else "gemini",
    }

    # Check PostgreSQL
    try:
        if engine is not None:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            result["db"] = "connected"
        else:
            result["db"] = "not_initialized"
    except Exception as e:
        result["db"] = f"error: {str(e)[:100]}"
        result["status"] = "degraded"

    # Check Redis
    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pong = await redis_client.ping()
        await redis_client.aclose()
        result["redis"] = "connected" if pong else "no_pong"
    except Exception as e:
        result["redis"] = f"error: {str(e)[:100]}"
        result["status"] = "degraded"

    return result
