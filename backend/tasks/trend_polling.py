"""Scheduled trend fetching for all active creators."""

import asyncio

import structlog

from tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="tasks.trend_polling.poll_trends")
def poll_trends() -> dict:
    """Poll trends from all sources for all active creators.

    Runs every 2 hours via Celery Beat.
    """
    logger.info("task.poll_trends.start")
    result = asyncio.run(_poll_trends_async())
    logger.info("task.poll_trends.complete", **result)
    return result


async def _poll_trends_async() -> dict:
    """Async implementation of trend polling."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.models.user import User
    from app.services.trend_service import refresh_trends

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    creators_polled = 0
    trends_found = 0

    async with session_factory() as db:
        # Get all users with connected YouTube channels
        result = await db.execute(
            select(User).where(User.youtube_channel_id.isnot(None))
        )
        users = result.scalars().all()

        for user in users:
            try:
                niche = user.niche or "general"
                topics = user.topics or []
                subreddits = [f"r/{t.lower()}" for t in topics[:5]]

                counts = await refresh_trends(
                    db=db,
                    sources=["google_trends", "reddit", "news"],
                    niche=niche,
                    subreddits=subreddits,
                    news_query=niche,
                )
                creators_polled += 1
                trends_found += sum(counts.values())
            except Exception as e:
                logger.error("task.poll_trends.user_error", user_id=str(user.id), error=str(e))

        await db.commit()

    await engine.dispose()
    return {"creators_polled": creators_polled, "trends_found": trends_found}
