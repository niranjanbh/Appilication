from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import redis.asyncio as aioredis

from app.core.config import settings

if TYPE_CHECKING:
    # Redis[str] generic is for type-checkers only; not valid at runtime
    RedisClient = aioredis.Redis[str]
else:
    RedisClient = aioredis.Redis


def get_redis_client() -> Any:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def get_redis() -> AsyncGenerator[Any, None]:
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()
