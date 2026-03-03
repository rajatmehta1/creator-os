"""Redis cache decorator and utilities."""

import functools
import hashlib
import json
from typing import Any, Callable, Optional

import redis.asyncio as aioredis
import structlog

from app.config import get_settings

logger = structlog.get_logger()

# Cache TTL configuration (seconds) matching spec
CACHE_TTLS = {
    # Trend data
    "trends:google": 3600,          # 1 hour
    "trends:reddit": 1800,          # 30 min
    "trends:youtube": 7200,         # 2 hours
    "trends:scored": 14400,         # 4 hours
    # YouTube API responses
    "youtube:channel": 86400,       # 24 hours
    "youtube:video": 43200,         # 12 hours
    "youtube:analytics": 21600,     # 6 hours
    "youtube:search": 86400,        # 24 hours
    # Agent outputs
    "agent:ideas": 86400,           # 24 hours
    "agent:seo": 172800,            # 48 hours
    # Creator DNA
    "dna": 604800,                  # 7 days
    # Session
    "session": 3600,                # 1 hour
    "ratelimit": 86400,             # 24 hours
    "youtube_quota": 86400,         # daily
}

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """Get or create the Redis client."""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


def _make_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """Generate a deterministic cache key from arguments."""
    key_data = json.dumps({"args": [str(a) for a in args], "kwargs": kwargs}, sort_keys=True)
    key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
    return f"{prefix}:{key_hash}"


def cached(prefix: str, ttl: Optional[int] = None) -> Callable:
    """Decorator to cache async function results in Redis.

    Usage:
        @cached("youtube:channel", ttl=86400)
        async def get_channel_info(channel_id: str) -> dict:
            ...
    """
    if ttl is None:
        ttl = CACHE_TTLS.get(prefix, 3600)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                client = await get_redis_client()
                cache_key = _make_cache_key(prefix, *args, **kwargs)

                # Try cache first
                cached_value = await client.get(cache_key)
                if cached_value is not None:
                    logger.debug("cache.hit", key=cache_key)
                    return json.loads(cached_value)

                # Cache miss — call function
                logger.debug("cache.miss", key=cache_key)
                result = await func(*args, **kwargs)

                # Store in cache
                if result is not None:
                    await client.setex(cache_key, ttl, json.dumps(result, default=str))

                return result
            except (aioredis.ConnectionError, aioredis.TimeoutError):
                logger.warning("cache.error", prefix=prefix, msg="Redis unavailable, skipping cache")
                return await func(*args, **kwargs)

        return wrapper
    return decorator


async def invalidate_cache(prefix: str, *args: Any, **kwargs: Any) -> None:
    """Invalidate a specific cache entry."""
    try:
        client = await get_redis_client()
        cache_key = _make_cache_key(prefix, *args, **kwargs)
        await client.delete(cache_key)
        logger.debug("cache.invalidated", key=cache_key)
    except (aioredis.ConnectionError, aioredis.TimeoutError):
        logger.warning("cache.invalidate_error", prefix=prefix)


async def invalidate_pattern(pattern: str) -> None:
    """Invalidate all cache entries matching a pattern."""
    try:
        client = await get_redis_client()
        async for key in client.scan_iter(match=pattern):
            await client.delete(key)
        logger.debug("cache.pattern_invalidated", pattern=pattern)
    except (aioredis.ConnectionError, aioredis.TimeoutError):
        logger.warning("cache.pattern_invalidate_error", pattern=pattern)
