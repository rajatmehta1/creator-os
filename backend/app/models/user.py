"""User model with YouTube channel connection."""

from typing import Optional

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """Creator user with linked YouTube channel."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # YouTube connection
    youtube_channel_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    youtube_channel_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    youtube_tokens_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Creator settings
    niche: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    topics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # DNA fingerprint reference
    dna_vector_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dna_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Relationships
    content = relationship("Content", back_populates="user", lazy="selectin")
    ideas = relationship("Idea", back_populates="user", lazy="selectin")
    video_analytics = relationship("VideoAnalytics", back_populates="user", lazy="selectin")
    media_kits = relationship("MediaKit", back_populates="user", lazy="selectin")
