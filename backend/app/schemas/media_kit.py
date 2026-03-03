"""Media kit Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MediaKitResponse(BaseModel):
    id: UUID
    user_id: UUID
    subscriber_count: Optional[int] = None
    total_views: Optional[int] = None
    avg_views_per_video: Optional[int] = None
    audience_demographics: dict = {}
    growth_30d: Optional[float] = None
    growth_60d: Optional[float] = None
    growth_90d: Optional[float] = None
    avg_likes: Optional[float] = None
    avg_comments: Optional[float] = None
    avg_shares: Optional[float] = None
    engagement_rate: Optional[float] = None
    brand_safety_score: Optional[float] = None
    suggested_cpm: Optional[float] = None
    suggested_flat_rate: Optional[float] = None
    rate_card: dict = {}
    top_videos: list[dict] = []
    collaboration_formats: list[dict] = []
    public_slug: Optional[str] = None
    pdf_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MediaKitGenerateRequest(BaseModel):
    include_rate_card: bool = True
    include_brand_safety: bool = True
    generate_pdf: bool = True
    generate_public_page: bool = True
