"""YouTube API daily quota tracker (10,000 units/day)."""

from datetime import date

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

# YouTube API quota costs per operation
QUOTA_COSTS = {
    "search.list": 100,
    "videos.list": 1,
    "channels.list": 1,
    "playlists.list": 1,
    "playlistItems.list": 1,
    "captions.list": 50,
    "captions.download": 200,
    "commentThreads.list": 1,
    "activities.list": 1,
}

DAILY_QUOTA_LIMIT = 10000


async def check_quota(
    redis_client: aioredis.Redis,
    operation: str,
) -> bool:
    """Check if we have enough YouTube API quota remaining.

    Returns True if the operation can proceed, False if quota is exhausted.
    """
    cost = QUOTA_COSTS.get(operation, 1)
    key = f"youtube_quota:{date.today().isoformat()}"

    try:
        current = await redis_client.get(key)
        current_usage = int(current) if current else 0

        if current_usage + cost > DAILY_QUOTA_LIMIT:
            logger.warning(
                "youtube_quota.exhausted",
                current=current_usage,
                cost=cost,
                limit=DAILY_QUOTA_LIMIT,
            )
            return False

        return True
    except (aioredis.ConnectionError, aioredis.TimeoutError):
        logger.warning("youtube_quota.redis_unavailable")
        return True  # Fail open


async def consume_quota(
    redis_client: aioredis.Redis,
    operation: str,
) -> None:
    """Record quota consumption for a YouTube API call."""
    cost = QUOTA_COSTS.get(operation, 1)
    key = f"youtube_quota:{date.today().isoformat()}"

    try:
        pipe = redis_client.pipeline()
        pipe.incrby(key, cost)
        pipe.expire(key, 86400)
        await pipe.execute()

        logger.debug("youtube_quota.consumed", operation=operation, cost=cost)
    except (aioredis.ConnectionError, aioredis.TimeoutError):
        logger.warning("youtube_quota.track_error", operation=operation)


async def get_quota_remaining(redis_client: aioredis.Redis) -> int:
    """Get remaining YouTube API quota for today."""
    key = f"youtube_quota:{date.today().isoformat()}"
    try:
        current = await redis_client.get(key)
        return DAILY_QUOTA_LIMIT - (int(current) if current else 0)
    except (aioredis.ConnectionError, aioredis.TimeoutError):
        return DAILY_QUOTA_LIMIT
