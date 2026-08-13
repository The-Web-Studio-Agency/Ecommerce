"""Redis-backed fixed-window rate limiting.

Argon2 verification costs ~250ms of CPU per attempt, so an unthrottled login
endpoint is both a credential-stuffing target and a cheap denial-of-service
vector. The limiter is applied per (endpoint, client IP, account) so one
attacker cannot lock out an unrelated tenant's users.

Availability trade-off: if Redis is unreachable the limiter FAILS OPEN and logs
a warning. A cache outage degrades brute-force protection rather than taking
authentication down for everyone.
"""

from __future__ import annotations

import hashlib

from app.core.cache import get_redis
from app.core.exceptions import RateLimitedError
from app.core.logging import get_logger

logger = get_logger("rate_limit")

KEY_PREFIX = "ratelimit"


def build_key(scope: str, *parts: str) -> str:
    """Build a namespaced counter key.

    Identifying parts are hashed so that raw emails and IP addresses are never
    written to Redis in the clear.
    """
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"{KEY_PREFIX}:{scope}:{digest}"


async def hit(key: str, *, limit: int, window_seconds: int) -> None:
    """Count one attempt against `key`; raise once the window budget is spent.

    Uses INCR plus an EXPIRE applied only on the first hit of a window, so the
    window starts at the first attempt and does not slide forward on every call.
    """
    if limit <= 0:
        return

    try:
        client = get_redis()
        pipeline = client.pipeline()
        pipeline.incr(key)
        pipeline.ttl(key)
        count, ttl = await pipeline.execute()

        if ttl < 0:
            await client.expire(key, window_seconds)
            ttl = window_seconds
    except RateLimitedError:
        raise
    except Exception as exc:  # noqa: BLE001 - availability over enforcement
        logger.warning("rate_limit.unavailable key=%s error=%s", key, type(exc).__name__)
        return

    if count > limit:
        raise RateLimitedError(retry_after_seconds=max(int(ttl), 1))


async def reset(key: str) -> None:
    """Clear a counter (called after a successful login)."""
    try:
        await get_redis().delete(key)
    except Exception as exc:  # noqa: BLE001 - best effort
        logger.warning("rate_limit.reset_failed key=%s error=%s", key, type(exc).__name__)
