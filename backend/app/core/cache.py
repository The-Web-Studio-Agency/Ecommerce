"""Redis connection helper (async client).

Redis backs the readiness probe and the login rate limiter. The client is a
lazily-created process singleton: `redis.asyncio` binds its connection pool to
the running event loop, so it must not be constructed at import time.
"""

from __future__ import annotations

import redis.asyncio as redis

from app.core.config import get_settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return the process-wide async Redis client, creating it on first use."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    """Close the client and drop the singleton (application shutdown, tests)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def redis_healthy() -> bool:
    """Return True when Redis answers PING. Never raises."""
    try:
        return bool(await get_redis().ping())
    except Exception:  # noqa: BLE001 - health probe must not propagate
        return False
