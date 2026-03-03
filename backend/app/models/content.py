"""Content model for scripts, posts, and other content pieces."""

import enum
from typing import Optional
import uuid

from sqlalchemy import Enum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ContentStatus(str, enum.Enum):
    IDEA = "idea"
    DRAFT = "draft"
    REVIEW = "review"
    OPTIMIZED = "optimized"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentType(str, enum.Enum):
    YOUTUBE_VIDEO = "youtube_video"
    YOUTUBE_SHORT = "youtube_short"
    BLOG_POST = "blog_post"
    TWITTER_THREAD = "twitter_thread"
    LINKEDIN_POST = "linkedin_post"
    NEWSLETTER = "newsletter"
    PODCAST_OUTLINE = "podcast_outline"


class Content(UUIDMixin, TimestampMixin, Base):
    """Content piece in the creation pipeline."""

    __tablename__ = "content"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType), nullable=False, index=True
    )
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus), default=ContentStatus.IDEA, nullable=False, index=True
    )

    # Content body
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outline: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # SEO metadata
    seo_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    seo_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=list)

    # Relationships and references
    idea_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ideas.id"), nullable=True
    )
    parent_content_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content.id"), nullable=True
    )

    # Extra metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    vector_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="content")
    idea = relationship("Idea", back_populates="content")
    variants = relationship("Content", backref="parent_content", remote_side="Content.id")
