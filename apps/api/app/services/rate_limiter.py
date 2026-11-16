"""Redis-backed sliding-window rate limits for expensive API operations."""
from __future__ import annotations

import logging
import time
import uuid

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)

_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = math.ceil((tonumber(oldest[2]) + window - now) / 1000)
    return {0, math.max(retry_after, 1)}
end

redis.call('ZADD', key, now, member)
redis.call('PEXPIRE', key, window)
return {1, limit - count - 1}
"""


async def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> None:
    if limit < 1 or window_seconds < 1:
        raise ValueError("Rate-limit count and window must be positive")

    client_host = request.client.host if request.client else "unknown"
    key = f"splitsmart:rate-limit:{bucket}:{client_host}"
    now_ms = time.time_ns() // 1_000_000
    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

    try:
        result = await redis_client.eval(
            _SLIDING_WINDOW_SCRIPT,
            1,
            key,
            now_ms,
            window_seconds * 1000,
            limit,
            uuid.uuid4().hex,
        )
    except RedisError as exc:
        logger.error("Rate-limit storage unavailable", extra={"bucket": bucket})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Request protection is temporarily unavailable",
        ) from exc
    finally:
        await redis_client.aclose()

    if not isinstance(result, (list, tuple)) or len(result) != 2:
        raise RuntimeError("Rate-limit storage returned an invalid decision")

    allowed, retry_after = int(result[0]), int(result[1])
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


async def enforce_ai_rate_limit(request: Request) -> None:
    settings = get_settings()
    await enforce_rate_limit(
        request,
        bucket="ai",
        limit=settings.rate_limit_ai_per_minute,
        window_seconds=60,
    )


async def enforce_upload_rate_limit(request: Request) -> None:
    settings = get_settings()
    await enforce_rate_limit(
        request,
        bucket="upload",
        limit=settings.rate_limit_upload_per_hour,
        window_seconds=60 * 60,
    )
