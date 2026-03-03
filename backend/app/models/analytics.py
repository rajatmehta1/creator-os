"""Video analytics model for YouTube performance data."""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class VideoAnalytics(UUIDMixin, TimestampMixin, Base):
    """Performance analytics for a single YouTube video."""

    __tablename__ = "video_analytics"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    publish_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Core metrics
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watch_time_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_view_duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_percentage_viewed: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Impressions and CTR
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Engagement
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subscribers_lost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Revenue
    revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Detailed data (stored as JSON)
    traffic_sources: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    audience_retention_curve: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=list
    )
    top_keywords: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)
    demographics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Sync metadata
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="video_analytics")
