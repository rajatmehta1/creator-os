"""Trend model for tracked trends from various sources."""

import enum
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import DateTime, Enum, Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TrendVelocity(str, enum.Enum):
    EMERGING = "emerging"
    PEAKING = "peaking"
    DECLINING = "declining"
    EXPIRED = "expired"


class TrendSource(str, enum.Enum):
    GOOGLE_TRENDS = "google_trends"
    REDDIT = "reddit"
    YOUTUBE_TRENDING = "youtube_trending"
    NEWS = "news"
    GOOGLE_SEARCH = "google_search"


class Trend(UUIDMixin, TimestampMixin, Base):
    """A detected trend from one or more data sources."""

    __tablename__ = "trends"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[TrendSource] = mapped_column(Enum(TrendSource), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Scoring
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    velocity: Mapped[TrendVelocity] = mapped_column(
        Enum(TrendVelocity), default=TrendVelocity.EMERGING, nullable=False, index=True
    )
    competition_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timing
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    peak_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Raw data from source
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    related_topics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)

    # Niche targeting
    niche_angle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_content_types: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=list
    )
    time_sensitivity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
