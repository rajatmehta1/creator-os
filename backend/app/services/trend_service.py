"""Trend service for saving, querying, refreshing, and scoring trends."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations import google_trends, reddit, news
from app.models.trend import Trend, TrendSource, TrendVelocity

logger = structlog.get_logger()


# ------------------------------------------------------------------
# Save
# ------------------------------------------------------------------

async def save_trend(
    db: AsyncSession,
    *,
    title: str,
    source: TrendSource,
    summary: Optional[str] = None,
    category: Optional[str] = None,
    relevance_score: Optional[float] = None,
    velocity: TrendVelocity = TrendVelocity.EMERGING,
    competition_level: Optional[str] = None,
    raw_data: Optional[dict[str, Any]] = None,
    related_topics: Optional[list[str]] = None,
    niche_angle: Optional[str] = None,
    suggested_content_types: Optional[list[str]] = None,
    time_sensitivity: Optional[str] = None,
) -> Trend:
    """Persist a detected trend to the database.

    Args:
        db: Async database session.
        title: Short trend headline.
        source: Where the trend was detected.
        summary: Optional longer description.
        category: Topic category (e.g. ``"tech"``, ``"gaming"``).
        relevance_score: 0.0 - 1.0 relevance to the creator's niche.
        velocity: Lifecycle phase of the trend.
        competition_level: ``"low"``, ``"medium"``, or ``"high"``.
        raw_data: Raw payload from the source API.
        related_topics: List of related topic strings.
        niche_angle: Suggested creator-specific angle.
        suggested_content_types: e.g. ``["youtube_video", "twitter_thread"]``.
        time_sensitivity: ``"hours"``, ``"days"``, or ``"weeks"``.

    Returns:
        The newly created ``Trend`` row.
    """
    trend = Trend(
        title=title,
        source=source,
        summary=summary,
        category=category,
        relevance_score=relevance_score,
        velocity=velocity,
        competition_level=competition_level,
        detected_at=datetime.now(timezone.utc),
        raw_data=raw_data,
        related_topics=related_topics or [],
        niche_angle=niche_angle,
        suggested_content_types=suggested_content_types or [],
        time_sensitivity=time_sensitivity,
    )
    db.add(trend)
    await db.flush()
    logger.info(
        "trend.saved",
        trend_id=str(trend.id),
        title=title,
        source=source.value,
    )
    return trend


# ------------------------------------------------------------------
# Query
# ------------------------------------------------------------------

async def get_trends_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    source: Optional[TrendSource] = None,
    velocity: Optional[TrendVelocity] = None,
    category: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Trend]:
    """Retrieve trends with optional filters.

    Note: Trends are currently global (not per-user); ``user_id`` is accepted
    for future personalisation and is logged for audit purposes.

    Args:
        db: Async database session.
        user_id: Requesting user (for future personalisation / logging).
        source: Filter by originating source.
        velocity: Filter by lifecycle phase.
        category: Filter by topic category.
        min_score: Only return trends scored >= this value.
        limit: Max results.
        offset: Pagination offset.

    Returns:
        List of ``Trend`` instances, ordered newest first.
    """
    stmt = (
        select(Trend)
        .order_by(Trend.detected_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if source is not None:
        stmt = stmt.where(Trend.source == source)
    if velocity is not None:
        stmt = stmt.where(Trend.velocity == velocity)
    if category is not None:
        stmt = stmt.where(Trend.category == category)
    if min_score is not None:
        stmt = stmt.where(Trend.relevance_score >= min_score)

    result = await db.execute(stmt)
    trends = list(result.scalars().all())
    logger.debug(
        "trend.query",
        user_id=str(user_id),
        filters={"source": source, "velocity": velocity, "category": category},
        count=len(trends),
    )
    return trends


# ------------------------------------------------------------------
# Refresh (pull from integrations)
# ------------------------------------------------------------------

async def refresh_trends(
    db: AsyncSession,
    *,
    sources: Optional[list[str]] = None,
    niche: Optional[str] = None,
    subreddits: Optional[list[str]] = None,
    news_query: Optional[str] = None,
) -> dict[str, int]:
    """Pull fresh trend data from external integrations and persist.

    This is the main entry-point called by the API / scheduler to keep
    the trends table up-to-date.

    Args:
        db: Async database session.
        sources: List of source names to refresh. Defaults to all.
        niche: Optional niche keyword for targeted queries.
        subreddits: Subreddit names for Reddit source.
        news_query: Search query for NewsAPI source.

    Returns:
        Dict mapping source name to the number of trends saved.
    """
    all_sources = sources or ["google_trends", "reddit", "news"]
    counts: dict[str, int] = {}
    query_term = niche or "technology"

    logger.info("trend.refresh_start", sources=all_sources, niche=niche)

    # --- Google Trends ---
    if "google_trends" in all_sources:
        try:
            count = await _refresh_google_trends(db, query_term)
            counts["google_trends"] = count
        except Exception as exc:
            logger.error("trend.refresh_google_error", error=str(exc))
            counts["google_trends"] = 0

    # --- Reddit ---
    if "reddit" in all_sources:
        try:
            target_subs = subreddits or ["technology", "Futurology"]
            count = await _refresh_reddit(db, target_subs)
            counts["reddit"] = count
        except Exception as exc:
            logger.error("trend.refresh_reddit_error", error=str(exc))
            counts["reddit"] = 0

    # --- News ---
    if "news" in all_sources:
        try:
            q = news_query or query_term
            count = await _refresh_news(db, q)
            counts["news"] = count
        except Exception as exc:
            logger.error("trend.refresh_news_error", error=str(exc))
            counts["news"] = 0

    logger.info("trend.refresh_complete", counts=counts)
    return counts


async def _refresh_google_trends(db: AsyncSession, keyword: str) -> int:
    """Pull Google Trends data and persist as Trend rows."""
    trending = await google_trends.get_trending_searches()
    rising = await google_trends.get_rising_queries([keyword])

    saved = 0
    for term in trending[:20]:
        await save_trend(
            db,
            title=str(term),
            source=TrendSource.GOOGLE_TRENDS,
            summary=f"Trending search: {term}",
            velocity=TrendVelocity.EMERGING,
            raw_data={"query": str(term), "type": "trending_search"},
        )
        saved += 1

    for kw, queries in rising.items():
        for q in queries[:10]:
            query_text = q.get("query", "") if isinstance(q, dict) else str(q)
            value = q.get("value", 0) if isinstance(q, dict) else 0
            await save_trend(
                db,
                title=query_text,
                source=TrendSource.GOOGLE_TRENDS,
                summary=f"Rising query for '{kw}' with growth {value}",
                velocity=TrendVelocity.EMERGING,
                raw_data={"keyword": kw, "query": query_text, "value": value},
            )
            saved += 1

    return saved


async def _refresh_reddit(db: AsyncSession, subreddits: list[str]) -> int:
    """Pull Reddit hot/rising posts and persist as Trend rows."""
    saved = 0
    for sub_name in subreddits:
        hot_posts = await reddit.get_hot_posts(sub_name, limit=10)
        rising_posts = await reddit.get_rising_posts(sub_name, limit=10)

        for post in hot_posts + rising_posts:
            velocity = (
                TrendVelocity.EMERGING
                if post.get("score", 0) < 1000
                else TrendVelocity.PEAKING
            )
            await save_trend(
                db,
                title=post.get("title", "Untitled"),
                source=TrendSource.REDDIT,
                summary=post.get("selftext", "")[:300] or None,
                category=sub_name,
                velocity=velocity,
                raw_data=post,
            )
            saved += 1

    return saved


async def _refresh_news(db: AsyncSession, query: str) -> int:
    """Pull news articles and persist as Trend rows."""
    news_data = await news.search_news(query, days=3)
    articles = news_data.get("articles", [])

    saved = 0
    for article in articles[:15]:
        await save_trend(
            db,
            title=article.get("title", "Untitled"),
            source=TrendSource.NEWS,
            summary=article.get("description"),
            velocity=TrendVelocity.EMERGING,
            raw_data=article,
        )
        saved += 1

    return saved


# ------------------------------------------------------------------
# Score (placeholder for agent-based scoring)
# ------------------------------------------------------------------

async def score_trends(
    db: AsyncSession,
    trend_ids: list[UUID],
    *,
    user_niche: Optional[str] = None,
    creator_dna: Optional[dict[str, Any]] = None,
) -> list[Trend]:
    """Score a batch of trends for relevance to a creator's niche.

    This is a placeholder that assigns a simple heuristic score.
    The full implementation will be driven by the Trend Scout agent,
    which uses the creator's DNA profile and content history for
    personalised scoring.

    Args:
        db: Async database session.
        trend_ids: IDs of trends to score.
        user_niche: Creator's declared niche keyword.
        creator_dna: Optional creator DNA vector/profile for scoring.

    Returns:
        List of updated ``Trend`` instances with populated scores.
    """
    logger.info(
        "trend.score_start",
        trend_count=len(trend_ids),
        niche=user_niche,
    )

    stmt = select(Trend).where(Trend.id.in_(trend_ids))
    result = await db.execute(stmt)
    trends = list(result.scalars().all())

    for trend in trends:
        # Placeholder heuristic: base score on velocity
        base_score = {
            TrendVelocity.EMERGING: 0.7,
            TrendVelocity.PEAKING: 0.9,
            TrendVelocity.DECLINING: 0.4,
            TrendVelocity.EXPIRED: 0.1,
        }.get(trend.velocity, 0.5)

        # Tiny boost if niche keyword appears in the title
        if user_niche and user_niche.lower() in (trend.title or "").lower():
            base_score = min(base_score + 0.15, 1.0)

        trend.relevance_score = round(base_score, 4)

    await db.flush()
    logger.info("trend.score_complete", scored=len(trends))
    return trends
