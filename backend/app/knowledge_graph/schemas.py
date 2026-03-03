"""Pydantic models for Neo4j knowledge graph node types.

Each schema mirrors the properties stored on the corresponding Neo4j node
label and is used for validation on both the ingestion and query paths.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Base
# ------------------------------------------------------------------


class GraphNodeBase(BaseModel):
    """Common fields present on every node in the knowledge graph."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Creator
# ------------------------------------------------------------------


class CreatorNode(GraphNodeBase):
    """Represents a content creator (maps to :Creator label in Neo4j).

    The ``creator_id`` is the UUID primary key from the relational ``users``
    table, stored as a string in Neo4j for indexing.
    """

    creator_id: str = Field(..., description="UUID of the creator from the users table")
    name: str
    niche: Optional[str] = None
    primary_topics: list[str] = Field(default_factory=list)
    youtube_channel_id: Optional[str] = None
    authority_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Aggregated authority score across all topics (0-100)",
    )
    content_count: int = Field(default=0, ge=0)


# ------------------------------------------------------------------
# Content
# ------------------------------------------------------------------


class ContentNode(GraphNodeBase):
    """Represents a piece of content (maps to :Content label).

    Linked to its creator via ``CREATED_BY`` and to topics via ``COVERS``.
    """

    content_id: str = Field(..., description="UUID of the content from the content table")
    title: str
    content_type: str = Field(
        ...,
        description="E.g. youtube_video, blog_post, twitter_thread",
    )
    status: str = Field(default="draft")
    published_at: Optional[datetime] = None
    word_count: int = Field(default=0, ge=0)
    performance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Normalised performance metric (0-100)",
    )
    vector_id: Optional[str] = Field(
        default=None,
        description="ID in ChromaDB for the embedding of this content",
    )
    url: Optional[str] = None


# ------------------------------------------------------------------
# Topic
# ------------------------------------------------------------------


class TopicNode(GraphNodeBase):
    """A topic or subject area (maps to :Topic label).

    Topics form a hierarchical graph via ``SUBTOPIC_OF`` relationships.
    """

    name: str = Field(..., description="Canonical lower-cased topic name")
    display_name: str = Field(default="", description="Human-friendly display name")
    category: Optional[str] = None
    depth: int = Field(
        default=0,
        ge=0,
        description="Depth in the topic hierarchy (0 = root topic)",
    )
    content_count: int = Field(default=0, ge=0)
    authority_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Creator-specific authority on this topic (0-100)",
    )
    trend_velocity: Optional[str] = Field(
        default=None,
        description="Current trend velocity: emerging | peaking | declining | stable",
    )


# ------------------------------------------------------------------
# Keyword
# ------------------------------------------------------------------


class KeywordNode(GraphNodeBase):
    """An SEO / search keyword (maps to :Keyword label).

    Keywords are linked to topics (``KEYWORD_OF``) and to content
    (``TARGETS``).
    """

    name: str = Field(..., description="The keyword phrase, lower-cased")
    search_volume: Optional[int] = Field(default=None, ge=0)
    competition: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Competition index 0-1 (0 = low, 1 = high)",
    )
    cpc: Optional[float] = Field(default=None, ge=0.0, description="Cost per click in USD")
    intent: Optional[str] = Field(
        default=None,
        description="Search intent: informational | navigational | transactional | commercial",
    )


# ------------------------------------------------------------------
# Trend
# ------------------------------------------------------------------


class TrendNode(GraphNodeBase):
    """A detected trend (maps to :Trend label).

    Trends are linked to topics (``RELATED_TO``) and optionally to content
    ideas (``INSPIRED``).
    """

    trend_id: str = Field(..., description="UUID of the trend from the trends table")
    title: str
    source: str = Field(
        ...,
        description="Origin: google_trends | reddit | youtube_trending | news",
    )
    velocity: str = Field(
        default="emerging",
        description="emerging | peaking | declining | expired",
    )
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    peak_at: Optional[datetime] = None
    category: Optional[str] = None
    time_sensitivity: Optional[str] = Field(
        default=None,
        description="hours | days | weeks | evergreen",
    )


# ------------------------------------------------------------------
# Audience Segment
# ------------------------------------------------------------------


class AudienceSegmentNode(GraphNodeBase):
    """An audience segment (maps to :AudienceSegment label).

    Creators ``TARGETS`` audience segments; content ``RESONATES_WITH``
    audience segments.
    """

    name: str = Field(..., description="Segment name, e.g. 'beginner python developers'")
    description: Optional[str] = None
    size_estimate: Optional[str] = Field(
        default=None,
        description="Rough size bucket: small | medium | large | massive",
    )
    demographics: Optional[dict[str, str]] = Field(default=None)
    psychographics: Optional[list[str]] = Field(default=None)
    engagement_level: Optional[str] = Field(
        default=None,
        description="low | medium | high",
    )


# ------------------------------------------------------------------
# Idea
# ------------------------------------------------------------------


class IdeaNode(GraphNodeBase):
    """A content idea (maps to :Idea label).

    Ideas can be ``INSPIRED_BY`` trends, ``COVERS`` topics, and are
    ``PROPOSED_FOR`` a creator.
    """

    idea_id: str = Field(..., description="UUID of the idea from the ideas table")
    title: str
    hook: Optional[str] = None
    angle: Optional[str] = None
    content_type: str = Field(default="youtube_video")
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    difficulty: Optional[str] = Field(
        default=None,
        description="quick_win | standard | deep_dive",
    )
    status: str = Field(default="generated")
    target_audience_segment: Optional[str] = None


# ------------------------------------------------------------------
# Relationship payloads (used when creating edges with properties)
# ------------------------------------------------------------------


class CoversRelationship(BaseModel):
    """Properties on a :COVERS edge between Content and Topic."""

    relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    is_primary: bool = False
    mentioned_count: int = Field(default=1, ge=0)


class AuthorityRelationship(BaseModel):
    """Properties on a :HAS_AUTHORITY edge between Creator and Topic."""

    score: float = Field(default=0.0, ge=0.0, le=100.0)
    content_count: int = Field(default=0, ge=0)
    first_covered_at: datetime = Field(default_factory=datetime.utcnow)
    last_covered_at: datetime = Field(default_factory=datetime.utcnow)
