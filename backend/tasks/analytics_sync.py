"""Periodic YouTube analytics sync for all creators."""

import asyncio

import structlog

from tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="tasks.analytics_sync.sync_all_analytics")
def sync_all_analytics() -> dict:
    """Sync YouTube analytics for all active creators.

    Runs every 6 hours via Celery Beat.
    """
    logger.info("task.analytics_sync.start")
    result = asyncio.run(_sync_all_async())
    logger.info("task.analytics_sync.complete", **result)
    return result


async def _sync_all_async() -> dict:
    """Async implementation of analytics sync."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.models.user import User
    from app.services import user_service

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    creators_synced = 0
    videos_synced = 0
    errors = 0

    async with session_factory() as db:
        result = await db.execute(
            select(User).where(User.youtube_channel_id.isnot(None))
        )
        users = result.scalars().all()

        for user in users:
            try:
                tokens = await user_service.get_youtube_tokens(user)
                if not tokens:
                    continue

                from app.integrations.youtube.client import YouTubeClient

                client = YouTubeClient(access_token=tokens.get("access_token"))
                channel_data = await client.get_my_channel()
                items = channel_data.get("items", [])

                if items:
                    channel_id = items[0]["id"]
                    # Get recent videos
                    videos = await client.list_channel_videos(channel_id, max_results=20)
                    video_items = videos.get("items", [])

                    for video in video_items:
                        video_id = video.get("id", {}).get("videoId", "")
                        if video_id:
                            from app.services.analytics_service import sync_video_analytics
                            await sync_video_analytics(
                                db=db,
                                user_id=user.id,
                                video_id=video_id,
                                access_token=tokens.get("access_token", ""),
                            )
                            videos_synced += 1

                    creators_synced += 1
            except Exception as e:
                logger.error(
                    "task.analytics_sync.user_error",
                    user_id=str(user.id),
                    error=str(e),
                )
                errors += 1

        await db.commit()

    await engine.dispose()
    return {
        "creators_synced": creators_synced,
        "videos_synced": videos_synced,
        "errors": errors,
    }
