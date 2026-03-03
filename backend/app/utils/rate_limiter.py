"""Per-user per-endpoint rate limiting via Redis."""

from fastapi import HTTPException, Request, status
import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

# Rate limits: (requests, window_seconds)
RATE_LIMITS = {
    "default": (60, 60),            # 60 req/min
    "agent:run": (10, 60),          # 10 agent runs/min
    "trends:refresh": (5, 300),     # 5 refreshes per 5 min
    "ideas:generate": (10, 300),    # 10 generations per 5 min
    "scripts:generate": (5, 300),   # 5 generations per 5 min
    "seo:optimize": (10, 300),      # 10 optimizations per 5 min
    "media_kit:generate": (3, 600), # 3 per 10 min
    "dna:build": (1, 3600),         # 1 per hour
}


async def check_rate_limit(
    redis_client: aioredis.Redis,
    user_id: str,
    endpoint: str = "default",
) -> None:
    """Check and enforce rate limit. Raises HTTPException if exceeded."""
    max_requests, window = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
    key = f"ratelimit:{endpoint}:{user_id}"

    try:
        current = await redis_client.get(key)
        if current is not None and int(current) >= max_requests:
            logger.warning("rate_limit.exceeded", user_id=user_id, endpoint=endpoint)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window}s.",
            )

        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()
    except (aioredis.ConnectionError, aioredis.TimeoutError):
        # If Redis is down, allow the request (fail open)
        logger.warning("rate_limit.redis_unavailable", endpoint=endpoint)
