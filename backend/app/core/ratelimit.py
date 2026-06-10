from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from fastapi import Depends, Request

from app.core.config import settings
from app.core.exceptions import RateLimitedError
from app.db.redis import get_redis

logger = structlog.get_logger(__name__)


def rate_limit(
    scope: str, *, limit: int, window_seconds: int = 60
) -> Callable[..., Awaitable[None]]:
    """Per-IP fixed-window rate limiter as a router dependency.

    Counters live in Redis with a TTL (rule 13: Redis holds rate limits, not
    business state). Fails open on Redis outage — an unreachable Redis must
    not lock every user out of auth.
    """

    async def dependency(
        request: Request, redis: Any = Depends(get_redis)
    ) -> None:
        if not settings.rate_limit_enabled:
            return
        ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{scope}:{ip}"
        try:
            async with redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, window_seconds, nx=True)
                count, _ = await pipe.execute()
        except Exception:
            logger.warning("rate_limit_redis_unavailable", scope=scope)
            return
        if int(count) > limit:
            logger.warning("rate_limit_exceeded", scope=scope)
            raise RateLimitedError()

    return dependency
