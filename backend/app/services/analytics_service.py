"""Analytics service for syncing, querying, and computing YouTube metrics."""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.youtube.analytics import YouTubeAnalyticsClient
from app.integrations.youtube.client import YouTubeClient
from app.models.analytics import VideoAnalytics

logger = structlog.get_logger()


# ------------------------------------------------------------------
# Sync video analytics from YouTube
# ------------------------------------------------------------------

async def sync_video_analytics(
    db: AsyncSession,
    user_id: UUID,
    video_id: str,
    access_token: str,
) -> VideoAnalytics:
    """Pull latest analytics from YouTube and upsert into the database.

    If a ``VideoAnalytics`` row already exists for the ``video_id`` it is
    updated in-place; otherwise a new row is created.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        video_id: YouTube video ID.
        access_token: Valid OAuth2 access token.

    Returns:
        The created or updated ``VideoAnalytics`` row.
    """
    logger.info("analytics.sync_start", user_id=str(user_id), video_id=video_id)

    analytics_client = YouTubeAnalyticsClient(access_token)
    video_data = await analytics_client.get_video_analytics(video_id)

    if not video_data.get("found", False):
        logger.warning("analytics.video_not_found", video_id=video_id)
        raise ValueError(f"Video {video_id} not found on YouTube")

    # Fetch traffic sources and retention in parallel-style (sequential here)
    traffic_data = await analytics_client.get_traffic_sources(video_id)
    retention_data = await analytics_client.get_retention_curve(video_id)

    # Look up existing row or create new
    stmt = select(VideoAnalytics).where(VideoAnalytics.video_id == video_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    stats = video_data.get("statistics", {})
    analytics_totals = video_data.get("analytics", {})

    now = datetime.now(timezone.utc)
    published_at_str = video_data.get("published_at", "")
    try:
        published_at = datetime.fromisoformat(
            published_at_str.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        published_at = now

    fields: dict[str, Any] = {
        "user_id": user_id,
        "video_id": video_id,
        "title": video_data.get("title", ""),
        "publish_date": published_at,
        "views": stats.get("views", 0),
        "watch_time_hours": round(
            analytics_totals.get("estimatedMinutesWatched", 0) / 60, 2
        ),
        "average_view_duration": analytics_totals.get("averageViewDuration", 0.0),
        "average_percentage_viewed": analytics_totals.get(
            "averageViewPercentage", 0.0
        ),
        "impressions": analytics_totals.get("impressions", 0),
        "ctr": analytics_totals.get("impressionClickThroughRate", 0.0),
        "likes": stats.get("likes", 0),
        "comments": stats.get("comments", 0),
        "shares": analytics_totals.get("shares", 0),
        "subscribers_gained": analytics_totals.get("subscribersGained", 0),
        "subscribers_lost": analytics_totals.get("subscribersLost", 0),
        "revenue": analytics_totals.get("estimatedRevenue"),
        "traffic_sources": traffic_data.get("sources", {}),
        "audience_retention_curve": retention_data.get("curve", []),
        "last_synced_at": now,
    }

    if record is None:
        record = VideoAnalytics(**fields)
        db.add(record)
    else:
        for key, value in fields.items():
            setattr(record, key, value)

    await db.flush()
    logger.info(
        "analytics.sync_complete",
        video_id=video_id,
        views=fields["views"],
    )
    return record


# ------------------------------------------------------------------
# Channel overview
# ------------------------------------------------------------------

async def get_channel_overview(
    db: AsyncSession,
    user_id: UUID,
    channel_id: str,
    access_token: str,
    days: int = 28,
) -> dict[str, Any]:
    """Build a high-level channel performance overview.

    Combines YouTube Analytics API data with aggregated per-video stats
    stored locally.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        channel_id: YouTube channel ID.
        access_token: Valid OAuth2 access token.
        days: Number of days for the analytics window.

    Returns:
        Dict containing channel-level metrics, period comparison,
        and top-performing videos.
    """
    logger.info(
        "analytics.channel_overview",
        user_id=str(user_id),
        channel_id=channel_id,
        days=days,
    )

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    prev_start = start_date - timedelta(days=days)
    prev_end = start_date - timedelta(days=1)

    analytics_client = YouTubeAnalyticsClient(access_token)

    current = await analytics_client.get_channel_analytics(
        channel_id, start_date, end_date
    )
    previous = await analytics_client.get_channel_analytics(
        channel_id, prev_start, prev_end
    )

    # Channel basics from Data API
    yt_client = YouTubeClient(access_token=access_token)
    channel_info = await yt_client.get_channel_info(channel_id)
    channel_items = channel_info.get("items", [{}])
    channel_stats = channel_items[0].get("statistics", {}) if channel_items else {}

    # Compute period-over-period changes
    current_totals = current.get("totals", {})
    previous_totals = previous.get("totals", {})
    comparison = _compute_period_comparison(current_totals, previous_totals)

    # Top videos from local DB
    stmt = (
        select(VideoAnalytics)
        .where(VideoAnalytics.user_id == user_id)
        .order_by(VideoAnalytics.views.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    top_videos = [
        {
            "video_id": v.video_id,
            "title": v.title,
            "views": v.views,
            "ctr": v.ctr,
            "avg_view_duration": v.average_view_duration,
            "likes": v.likes,
        }
        for v in result.scalars().all()
    ]

    return {
        "channel_id": channel_id,
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days},
        "subscribers": int(channel_stats.get("subscriberCount", 0)),
        "total_views": int(channel_stats.get("viewCount", 0)),
        "total_videos": int(channel_stats.get("videoCount", 0)),
        "current_period": current_totals,
        "previous_period": previous_totals,
        "comparison": comparison,
        "top_videos": top_videos,
    }


# ------------------------------------------------------------------
# Single video performance
# ------------------------------------------------------------------

async def get_video_performance(
    db: AsyncSession,
    video_id: str,
) -> Optional[dict[str, Any]]:
    """Return stored performance data and derived metrics for a video.

    Args:
        db: Async database session.
        video_id: YouTube video ID.

    Returns:
        Dict with raw metrics plus computed engagement rate and growth rate,
        or ``None`` if the video has not been synced yet.
    """
    stmt = select(VideoAnalytics).where(VideoAnalytics.video_id == video_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        return None

    derived = compute_derived_metrics(
        views=record.views,
        likes=record.likes,
        comments=record.comments,
        shares=record.shares,
        subscribers_gained=record.subscribers_gained,
        subscribers_lost=record.subscribers_lost,
        impressions=record.impressions,
        ctr=record.ctr,
        average_view_duration=record.average_view_duration,
        average_percentage_viewed=record.average_percentage_viewed,
    )

    return {
        "video_id": record.video_id,
        "title": record.title,
        "publish_date": record.publish_date.isoformat() if record.publish_date else None,
        "views": record.views,
        "watch_time_hours": record.watch_time_hours,
        "average_view_duration": record.average_view_duration,
        "average_percentage_viewed": record.average_percentage_viewed,
        "impressions": record.impressions,
        "ctr": record.ctr,
        "likes": record.likes,
        "comments": record.comments,
        "shares": record.shares,
        "subscribers_gained": record.subscribers_gained,
        "subscribers_lost": record.subscribers_lost,
        "revenue": record.revenue,
        "traffic_sources": record.traffic_sources,
        "audience_retention_curve": record.audience_retention_curve,
        "last_synced_at": (
            record.last_synced_at.isoformat() if record.last_synced_at else None
        ),
        "derived_metrics": derived,
    }


# ------------------------------------------------------------------
# Derived metrics
# ------------------------------------------------------------------

def compute_derived_metrics(
    *,
    views: int,
    likes: int,
    comments: int,
    shares: int,
    subscribers_gained: int,
    subscribers_lost: int,
    impressions: int,
    ctr: float,
    average_view_duration: float,
    average_percentage_viewed: float,
) -> dict[str, Any]:
    """Compute higher-order metrics from raw YouTube data.

    Derived metrics:
    - **engagement_rate**: (likes + comments + shares) / views
    - **subscriber_conversion**: net subs gained / views
    - **growth_rate**: net subs / views (alias, different denominator possible)
    - **virality_score**: shares / views
    - **retention_quality**: ``"excellent"`` / ``"good"`` / ``"average"`` / ``"poor"``
      based on average percentage viewed.
    - **ctr_quality**: Similar quality label for click-through rate.

    Returns:
        Dict of computed metric values.
    """
    safe_views = max(views, 1)

    engagement_rate = round((likes + comments + shares) / safe_views, 6)
    net_subscribers = subscribers_gained - subscribers_lost
    subscriber_conversion = round(net_subscribers / safe_views, 6)
    virality_score = round(shares / safe_views, 6)
    growth_rate = round(net_subscribers / safe_views, 6)

    # Retention quality thresholds
    if average_percentage_viewed >= 60:
        retention_quality = "excellent"
    elif average_percentage_viewed >= 45:
        retention_quality = "good"
    elif average_percentage_viewed >= 30:
        retention_quality = "average"
    else:
        retention_quality = "poor"

    # CTR quality thresholds (YouTube average ~4-5%)
    if ctr >= 10.0:
        ctr_quality = "excellent"
    elif ctr >= 6.0:
        ctr_quality = "good"
    elif ctr >= 3.0:
        ctr_quality = "average"
    else:
        ctr_quality = "poor"

    return {
        "engagement_rate": engagement_rate,
        "subscriber_conversion": subscriber_conversion,
        "growth_rate": growth_rate,
        "virality_score": virality_score,
        "retention_quality": retention_quality,
        "ctr_quality": ctr_quality,
        "net_subscribers": net_subscribers,
    }


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _compute_period_comparison(
    current: dict[str, Any],
    previous: dict[str, Any],
) -> dict[str, Any]:
    """Compute percentage change between two period totals."""
    comparison: dict[str, Any] = {}
    for metric, current_value in current.items():
        prev_value = previous.get(metric, 0)
        try:
            cv = float(current_value)
            pv = float(prev_value)
        except (TypeError, ValueError):
            continue

        if pv != 0:
            change_pct = round(((cv - pv) / abs(pv)) * 100, 2)
        elif cv > 0:
            change_pct = 100.0
        else:
            change_pct = 0.0

        comparison[metric] = {
            "current": cv,
            "previous": pv,
            "change_percent": change_pct,
            "direction": "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat"),
        }
    return comparison
