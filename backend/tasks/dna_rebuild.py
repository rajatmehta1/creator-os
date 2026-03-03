"""Periodic Creator DNA fingerprint rebuilds."""

import asyncio

import structlog

from tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="tasks.dna_rebuild.rebuild_all_dna")
def rebuild_all_dna() -> dict:
    """Rebuild DNA fingerprints for all creators with new content.

    Runs weekly via Celery Beat (Sunday 3 AM UTC).
    """
    logger.info("task.dna_rebuild.start")
    result = asyncio.run(_rebuild_all_async())
    logger.info("task.dna_rebuild.complete", **result)
    return result


@celery_app.task(name="tasks.dna_rebuild.rebuild_single_dna")
def rebuild_single_dna(user_id: str) -> dict:
    """Rebuild DNA fingerprint for a single creator."""
    logger.info("task.dna_rebuild.single", user_id=user_id)
    result = asyncio.run(_rebuild_single_async(user_id))
    return result


async def _rebuild_all_async() -> dict:
    """Async implementation of full DNA rebuild."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.models.user import User

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    creators_rebuilt = 0
    errors = 0

    async with session_factory() as db:
        result = await db.execute(
            select(User).where(User.youtube_channel_id.isnot(None))
        )
        users = result.scalars().all()

        for user in users:
            try:
                await _rebuild_user_dna(db, user)
                creators_rebuilt += 1
            except Exception as e:
                logger.error(
                    "task.dna_rebuild.user_error",
                    user_id=str(user.id),
                    error=str(e),
                )
                errors += 1

        await db.commit()

    await engine.dispose()
    return {"creators_rebuilt": creators_rebuilt, "errors": errors}


async def _rebuild_single_async(user_id: str) -> dict:
    """Rebuild DNA for a single user."""
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.services.user_service import get_user_by_id

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        user = await get_user_by_id(db, UUID(user_id))
        if not user:
            return {"status": "error", "message": "User not found"}

        try:
            await _rebuild_user_dna(db, user)
            await db.commit()
            return {"status": "completed", "user_id": user_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    await engine.dispose()


async def _rebuild_user_dna(db, user) -> None:
    """Rebuild DNA fingerprint for a user from their transcripts."""
    from app.creator_dna.analyzer import analyze_transcript
    from app.creator_dna.embeddings import generate_dna_embedding
    from app.creator_dna.fingerprint import build_fingerprint
    from app.services.user_service import get_youtube_tokens, update_user

    tokens = await get_youtube_tokens(user)
    if not tokens:
        logger.warning("task.dna_rebuild.no_tokens", user_id=str(user.id))
        return

    from app.integrations.youtube.client import YouTubeClient

    client = YouTubeClient(access_token=tokens.get("access_token"))

    # Get recent videos (up to 50 for DNA analysis)
    channel_data = await client.get_my_channel()
    items = channel_data.get("items", [])
    if not items:
        return

    channel_id = items[0]["id"]
    videos = await client.list_channel_videos(channel_id, max_results=50)

    # Analyze transcripts (placeholder - would use captions API or Whisper)
    analyses = []
    for video in videos.get("items", [])[:20]:
        video_id = video.get("id", {}).get("videoId", "")
        title = video.get("snippet", {}).get("title", "")
        description = video.get("snippet", {}).get("description", "")

        # In production: fetch actual transcript via Captions API
        # For now: analyze title + description as proxy
        if title and description:
            try:
                analysis = await analyze_transcript(f"{title}\n\n{description}")
                analyses.append(analysis)
            except Exception as e:
                logger.warning(
                    "task.dna_rebuild.analysis_error",
                    video_id=video_id,
                    error=str(e),
                )

    if analyses:
        # Build fingerprint
        fingerprint = build_fingerprint(analyses)

        # Generate embedding
        embedding = await generate_dna_embedding(
            fingerprint.model_dump(),
            creator_id=str(user.id),
        )

        # Update user
        await update_user(
            db,
            user,
            dna_confidence=fingerprint.confidence_score,
            dna_vector_id=str(user.id),
        )

        logger.info(
            "task.dna_rebuild.user_complete",
            user_id=str(user.id),
            videos_analyzed=len(analyses),
            confidence=fingerprint.confidence_score,
        )
