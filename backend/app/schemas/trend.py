"""Trend-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class TrendSourceInfo(BaseModel):
    source: str
    url: Optional[str] = None
    raw_score: Optional[float] = None


class TrendResponse(BaseModel):
    id: UUID
    title: str
    summary: Optional[str] = None
    source: str
    category: Optional[str] = None
    relevance_score: Optional[float] = None
    velocity: str
    competition_level: Optional[str] = None
    detected_at: datetime
    niche_angle: Optional[str] = None
    suggested_content_types: list[str] = []
    time_sensitivity: Optional[str] = None
    related_topics: list[str] = []

    model_config = {"from_attributes": True}


class TrendRecommendation(BaseModel):
    """Fully processed trend recommendation from Trend Scout agent."""

    trend_title: str
    trend_summary: str
    relevance_score: float
    velocity: str
    sources: list[TrendSourceInfo] = []
    niche_angle: str
    competition_level: str
    suggested_content_types: list[str] = []
    related_topics: list[str] = []
    time_sensitivity: str


class TrendCluster(BaseModel):
    """A group of semantically related trends."""

    cluster_name: str
    trends: list[TrendRecommendation] = []
    combined_score: float = 0.0


class TrendRefreshRequest(BaseModel):
    sources: list[str] = ["google_trends", "reddit", "youtube_trending", "news"]
    niche_override: Optional[str] = None
