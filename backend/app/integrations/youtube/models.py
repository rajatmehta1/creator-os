"""YouTube API response data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class YouTubeChannel(BaseModel):
    channel_id: str
    title: str
    description: str
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0
    published_at: Optional[datetime] = None
    country: Optional[str] = None
    keywords: list[str] = []


class YouTubeVideo(BaseModel):
    video_id: str
    title: str
    description: str
    published_at: datetime
    channel_id: str
    thumbnail_url: Optional[str] = None
    tags: list[str] = []
    category_id: Optional[str] = None
    duration: Optional[str] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0


class YouTubeTrending(BaseModel):
    video_id: str
    title: str
    channel_title: str
    category_id: str
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    published_at: datetime
    tags: list[str] = []
