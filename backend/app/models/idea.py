"""Idea model for generated content ideas."""

import enum
from typing import Optional
import uuid

from sqlalchemy import Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class IdeaStatus(str, enum.Enum):
    GENERATED = "generated"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class IdeaDifficulty(str, enum.Enum):
    QUICK_WIN = "quick_win"
    STANDARD = "standard"
    DEEP_DIVE = "deep_dive"


class Idea(UUIDMixin, TimestampMixin, Base):
    """A generated content idea, potentially linked to a trend."""

    __tablename__ = "ideas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    trend_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trends.id"), nullable=True
    )

    # Core idea
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    hook: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    angle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    secondary_types: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)

    # Scoring
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_performance: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[Optional[IdeaDifficulty]] = mapped_column(
        Enum(IdeaDifficulty), nullable=True
    )

    # Details
    key_points: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)
    differentiation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_audience_segment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    suggested_publish_window: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trend_connection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[IdeaStatus] = mapped_column(
        Enum(IdeaStatus), default=IdeaStatus.GENERATED, nullable=False, index=True
    )

    # Relationships
    user = relationship("User", back_populates="ideas")
    trend = relationship("Trend")
    content = relationship("Content", back_populates="idea", uselist=False)
