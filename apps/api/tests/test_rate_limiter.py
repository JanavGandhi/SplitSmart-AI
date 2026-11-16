from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError

from app.services import rate_limiter
from app.services.rate_limiter import (
    enforce_ai_rate_limit,
    enforce_rate_limit,
    enforce_upload_rate_limit,
)


class FakeRedis:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.eval_args = None
        self.closed = False

    async def eval(self, *args):
        self.eval_args = args
        if self.error:
            raise self.error
        return self.result

    async def aclose(self):
        self.closed = True


def request_from(host: str):
    return SimpleNamespace(client=SimpleNamespace(host=host))


@pytest.mark.asyncio
async def test_sliding_window_allows_request_and_closes_redis(monkeypatch):
    redis = FakeRedis(result=[1, 9])
    monkeypatch.setattr(rate_limiter, "get_settings", lambda: SimpleNamespace(redis_url="redis://test"))
    monkeypatch.setattr(rate_limiter.aioredis, "from_url", lambda *args, **kwargs: redis)

    await enforce_rate_limit(
        request_from("192.0.2.10"),
        bucket="ai",
        limit=10,
        window_seconds=60,
    )

    assert redis.eval_args[2] == "splitsmart:rate-limit:ai:192.0.2.10"
    assert redis.eval_args[4:6] == (60_000, 10)
    assert redis.closed


@pytest.mark.asyncio
async def test_sliding_window_returns_retry_after_when_limit_is_reached(monkeypatch):
    redis = FakeRedis(result=[0, 27])
    monkeypatch.setattr(rate_limiter, "get_settings", lambda: SimpleNamespace(redis_url="redis://test"))
    monkeypatch.setattr(rate_limiter.aioredis, "from_url", lambda *args, **kwargs: redis)

    with pytest.raises(HTTPException) as error:
        await enforce_rate_limit(
            request_from("192.0.2.10"),
            bucket="ai",
            limit=10,
            window_seconds=60,
        )

    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "27"
    assert redis.closed


@pytest.mark.asyncio
async def test_sliding_window_fails_closed_when_redis_is_unavailable(monkeypatch):
    redis = FakeRedis(error=RedisError("offline"))
    monkeypatch.setattr(rate_limiter, "get_settings", lambda: SimpleNamespace(redis_url="redis://test"))
    monkeypatch.setattr(rate_limiter.aioredis, "from_url", lambda *args, **kwargs: redis)

    with pytest.raises(HTTPException) as error:
        await enforce_rate_limit(
            request_from("192.0.2.10"),
            bucket="ai",
            limit=10,
            window_seconds=60,
        )

    assert error.value.status_code == 503
    assert redis.closed


@pytest.mark.asyncio
async def test_endpoint_policies_use_configured_request_ceilings(monkeypatch):
    settings = SimpleNamespace(
        rate_limit_ai_per_minute=10,
        rate_limit_upload_per_hour=20,
    )
    calls = []

    async def record_policy(request, **policy):
        calls.append(policy)

    monkeypatch.setattr(rate_limiter, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limiter, "enforce_rate_limit", record_policy)
    request = request_from("192.0.2.10")

    await enforce_ai_rate_limit(request)
    await enforce_upload_rate_limit(request)

    assert calls == [
        {"bucket": "ai", "limit": 10, "window_seconds": 60},
        {"bucket": "upload", "limit": 20, "window_seconds": 3600},
    ]
