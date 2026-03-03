"""Media kit model for auto-generated creator media kits."""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class MediaKit(UUIDMixin, TimestampMixin, Base):
    """Auto-generated media kit for brand partnerships."""

    __tablename__ = "media_kits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Channel stats snapshot
    subscriber_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    total_views: Mapped[Optional[int]] = mapped_column(nullable=True)
    avg_views_per_video: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Audience demographics
    audience_demographics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Growth metrics
    growth_30d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    growth_60d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    growth_90d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Engagement
    avg_likes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_comments: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_shares: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    engagement_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Brand safety & pricing
    brand_safety_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    suggested_cpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    suggested_flat_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rate_card: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Top content
    top_videos: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)
    collaboration_formats: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=list
    )

    # Output
    public_slug: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    full_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="media_kits")
