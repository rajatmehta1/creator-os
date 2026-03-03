"""Media kit service for generating, querying, and updating creator media kits."""

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.youtube.analytics import YouTubeAnalyticsClient
from app.integrations.youtube.client import YouTubeClient
from app.models.analytics import VideoAnalytics
from app.models.media_kit import MediaKit
from app.services.analytics_service import compute_derived_metrics

logger = structlog.get_logger()


def _generate_slug(length: int = 12) -> str:
    """Generate a URL-safe random slug for public media kit pages."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ------------------------------------------------------------------
# Generate
# ------------------------------------------------------------------

async def generate_media_kit(
    db: AsyncSession,
    user_id: UUID,
    channel_id: str,
    access_token: str,
    *,
    include_rate_card: bool = True,
    include_brand_safety: bool = True,
    generate_public_page: bool = True,
) -> MediaKit:
    """Build a comprehensive media kit from live YouTube data.

    Pulls channel stats, demographics, recent video performance, and
    computes engagement / growth metrics to produce a brand-ready media kit.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        channel_id: YouTube channel ID.
        access_token: Valid OAuth2 access token.
        include_rate_card: Whether to compute suggested pricing.
        include_brand_safety: Whether to compute brand-safety score.
        generate_public_page: Whether to create a public slug.

    Returns:
        The created or updated ``MediaKit`` row.
    """
    logger.info(
        "media_kit.generate_start",
        user_id=str(user_id),
        channel_id=channel_id,
    )

    yt_client = YouTubeClient(access_token=access_token)
    analytics_client = YouTubeAnalyticsClient(access_token)

    # Fetch channel info
    channel_info = await yt_client.get_channel_info(channel_id)
    channel_items = channel_info.get("items", [])
    if not channel_items:
        raise ValueError(f"Channel {channel_id} not found")

    channel_data = channel_items[0]
    channel_stats = channel_data.get("statistics", {})
    subscriber_count = int(channel_stats.get("subscriberCount", 0))
    total_views = int(channel_stats.get("viewCount", 0))
    video_count = int(channel_stats.get("videoCount", 0))
    avg_views_per_video = total_views // max(video_count, 1)

    # Fetch demographics
    demographics_data = await analytics_client.get_demographics(channel_id)

    # Top videos from local DB
    stmt = (
        select(VideoAnalytics)
        .where(VideoAnalytics.user_id == user_id)
        .order_by(VideoAnalytics.views.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    top_video_records = list(result.scalars().all())

    top_videos = [
        {
            "video_id": v.video_id,
            "title": v.title,
            "views": v.views,
            "likes": v.likes,
            "comments": v.comments,
            "ctr": v.ctr,
        }
        for v in top_video_records
    ]

    # Compute average engagement metrics
    if top_video_records:
        avg_likes = sum(v.likes for v in top_video_records) / len(top_video_records)
        avg_comments = sum(v.comments for v in top_video_records) / len(top_video_records)
        avg_shares = sum(v.shares for v in top_video_records) / len(top_video_records)
        total_engagement = sum(
            v.likes + v.comments + v.shares for v in top_video_records
        )
        total_video_views = sum(v.views for v in top_video_records)
        engagement_rate = (
            round(total_engagement / max(total_video_views, 1), 6)
        )
    else:
        avg_likes = 0.0
        avg_comments = 0.0
        avg_shares = 0.0
        engagement_rate = 0.0

    # Growth metrics (placeholder; real growth requires historical snapshots)
    growth_30d = None
    growth_60d = None
    growth_90d = None

    # Rate card estimation
    rate_card: dict[str, Any] = {}
    suggested_cpm: Optional[float] = None
    suggested_flat_rate: Optional[float] = None

    if include_rate_card:
        suggested_cpm = _estimate_cpm(subscriber_count, engagement_rate)
        suggested_flat_rate = _estimate_flat_rate(
            subscriber_count, avg_views_per_video, engagement_rate
        )
        rate_card = {
            "integration_60s": round(suggested_flat_rate * 0.5, 2) if suggested_flat_rate else None,
            "dedicated_video": round(suggested_flat_rate, 2) if suggested_flat_rate else None,
            "shorts": round(suggested_flat_rate * 0.25, 2) if suggested_flat_rate else None,
            "bundle_3_videos": round(suggested_flat_rate * 2.5, 2) if suggested_flat_rate else None,
        }

    # Brand safety score (placeholder heuristic)
    brand_safety_score: Optional[float] = None
    if include_brand_safety:
        brand_safety_score = _estimate_brand_safety(engagement_rate, subscriber_count)

    # Collaboration formats
    collaboration_formats = _suggest_collaboration_formats(subscriber_count)

    # Public slug
    public_slug: Optional[str] = None
    if generate_public_page:
        public_slug = _generate_slug()

    now = datetime.now(timezone.utc)

    # Upsert: check for existing media kit for this user
    stmt_existing = (
        select(MediaKit)
        .where(MediaKit.user_id == user_id)
        .order_by(MediaKit.created_at.desc())
        .limit(1)
    )
    result_existing = await db.execute(stmt_existing)
    media_kit = result_existing.scalar_one_or_none()

    full_data: dict[str, Any] = {
        "channel_id": channel_id,
        "channel_snippet": channel_data.get("snippet", {}),
        "demographics": demographics_data,
        "generated_at": now.isoformat(),
    }

    fields: dict[str, Any] = {
        "user_id": user_id,
        "subscriber_count": subscriber_count,
        "total_views": total_views,
        "avg_views_per_video": avg_views_per_video,
        "audience_demographics": demographics_data,
        "growth_30d": growth_30d,
        "growth_60d": growth_60d,
        "growth_90d": growth_90d,
        "avg_likes": round(avg_likes, 2),
        "avg_comments": round(avg_comments, 2),
        "avg_shares": round(avg_shares, 2),
        "engagement_rate": engagement_rate,
        "brand_safety_score": brand_safety_score,
        "suggested_cpm": suggested_cpm,
        "suggested_flat_rate": suggested_flat_rate,
        "rate_card": rate_card,
        "top_videos": top_videos,
        "collaboration_formats": collaboration_formats,
        "full_data": full_data,
        "generated_at": now,
    }

    if media_kit is None:
        media_kit = MediaKit(**fields, public_slug=public_slug)
        db.add(media_kit)
    else:
        for key, value in fields.items():
            setattr(media_kit, key, value)
        if public_slug and not media_kit.public_slug:
            media_kit.public_slug = public_slug

    await db.flush()
    logger.info(
        "media_kit.generated",
        media_kit_id=str(media_kit.id),
        subscriber_count=subscriber_count,
    )
    return media_kit


# ------------------------------------------------------------------
# Read
# ------------------------------------------------------------------

async def get_media_kit(
    db: AsyncSession,
    media_kit_id: UUID,
) -> Optional[MediaKit]:
    """Fetch a media kit by its primary key.

    Returns:
        ``MediaKit`` instance or ``None``.
    """
    result = await db.execute(select(MediaKit).where(MediaKit.id == media_kit_id))
    return result.scalar_one_or_none()


async def get_public_media_kit(
    db: AsyncSession,
    slug: str,
) -> Optional[MediaKit]:
    """Fetch a media kit by its public slug for brand-facing pages.

    Returns:
        ``MediaKit`` instance or ``None`` if the slug does not match.
    """
    result = await db.execute(
        select(MediaKit).where(MediaKit.public_slug == slug)
    )
    return result.scalar_one_or_none()


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------

async def update_media_kit(
    db: AsyncSession,
    media_kit_id: UUID,
    updates: dict[str, Any],
) -> Optional[MediaKit]:
    """Update specific fields on an existing media kit.

    Useful for manual overrides (e.g. custom rate card, PDF URL).

    Args:
        db: Async database session.
        media_kit_id: Primary key of the media kit.
        updates: Dict of field names to new values.

    Returns:
        Updated ``MediaKit`` or ``None`` if not found.
    """
    media_kit = await get_media_kit(db, media_kit_id)
    if media_kit is None:
        logger.warning("media_kit.not_found", media_kit_id=str(media_kit_id))
        return None

    allowed_fields = {
        "rate_card",
        "collaboration_formats",
        "public_slug",
        "pdf_url",
        "brand_safety_score",
        "suggested_cpm",
        "suggested_flat_rate",
    }

    applied: list[str] = []
    for field, value in updates.items():
        if field in allowed_fields and hasattr(media_kit, field):
            setattr(media_kit, field, value)
            applied.append(field)

    await db.flush()
    logger.info(
        "media_kit.updated",
        media_kit_id=str(media_kit_id),
        fields=applied,
    )
    return media_kit


# ------------------------------------------------------------------
# Private estimation helpers
# ------------------------------------------------------------------

def _estimate_cpm(subscriber_count: int, engagement_rate: float) -> float:
    """Estimate CPM based on channel size and engagement."""
    # Base CPM by tier
    if subscriber_count >= 1_000_000:
        base = 25.0
    elif subscriber_count >= 500_000:
        base = 20.0
    elif subscriber_count >= 100_000:
        base = 15.0
    elif subscriber_count >= 50_000:
        base = 12.0
    elif subscriber_count >= 10_000:
        base = 8.0
    else:
        base = 5.0

    # Engagement multiplier
    if engagement_rate >= 0.08:
        multiplier = 1.4
    elif engagement_rate >= 0.05:
        multiplier = 1.2
    elif engagement_rate >= 0.03:
        multiplier = 1.0
    else:
        multiplier = 0.8

    return round(base * multiplier, 2)


def _estimate_flat_rate(
    subscriber_count: int,
    avg_views: int,
    engagement_rate: float,
) -> float:
    """Estimate a per-video flat sponsorship rate."""
    cpm = _estimate_cpm(subscriber_count, engagement_rate)
    return round((avg_views / 1000) * cpm, 2)


def _estimate_brand_safety(engagement_rate: float, subscriber_count: int) -> float:
    """Heuristic brand-safety score (0.0 - 1.0).

    Higher engagement + larger (established) channels score higher.
    Real implementation would incorporate content analysis.
    """
    score = 0.5
    if engagement_rate >= 0.05:
        score += 0.2
    elif engagement_rate >= 0.03:
        score += 0.1

    if subscriber_count >= 100_000:
        score += 0.2
    elif subscriber_count >= 10_000:
        score += 0.1

    return min(round(score, 2), 1.0)


def _suggest_collaboration_formats(subscriber_count: int) -> list[dict[str, Any]]:
    """Return suggested sponsorship formats based on channel size."""
    formats = [
        {
            "name": "Product Mention",
            "description": "Brief 15-30 second mention within a video",
            "suitable_for": "all sizes",
        },
        {
            "name": "Dedicated Integration",
            "description": "60-90 second sponsored segment within a video",
            "suitable_for": "10K+ subscribers",
        },
    ]

    if subscriber_count >= 50_000:
        formats.append({
            "name": "Dedicated Review Video",
            "description": "Full video focused on the sponsor's product",
            "suitable_for": "50K+ subscribers",
        })

    if subscriber_count >= 100_000:
        formats.extend([
            {
                "name": "Multi-video Campaign",
                "description": "3+ video integration package over 1-2 months",
                "suitable_for": "100K+ subscribers",
            },
            {
                "name": "YouTube Shorts Bundle",
                "description": "3-5 short-form videos highlighting the product",
                "suitable_for": "100K+ subscribers",
            },
        ])

    return formats
