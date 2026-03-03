"""Content-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ContentCreate(BaseModel):
    title: str
    content_type: str
    body: Optional[str] = None
    idea_id: Optional[UUID] = None
    parent_content_id: Optional[UUID] = None


class ContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    tags: Optional[list[str]] = None
    outline: Optional[dict] = None
    metadata_json: Optional[dict] = None


class ContentResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    content_type: str
    status: str
    body: Optional[str] = None
    outline: Optional[dict] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    tags: list[str] = []
    idea_id: Optional[UUID] = None
    parent_content_id: Optional[UUID] = None
    metadata_json: dict = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptGenerateRequest(BaseModel):
    idea_id: UUID
    content_type: str = "youtube_video"
    include_variants: bool = True


class ScriptResponse(BaseModel):
    id: UUID
    title: str
    content_type: str
    body: str
    outline: Optional[dict] = None
    variants: list["ContentResponse"] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class SEOPackage(BaseModel):
    """Full SEO optimization package."""

    # YouTube
    title_options: list[dict] = []
    description: str = ""
    tags: list[str] = []
    hashtags: list[str] = []
    chapters: list[dict] = []
    thumbnail_concepts: list[dict] = []

    # Blog
    meta_title: str = ""
    meta_description: str = ""
    suggested_headers: list[str] = []
    target_word_count: int = 0

    # Twitter
    thread_hooks: list[str] = []
    hashtag_strategy: list[str] = []

    # Newsletter
    subject_lines: list[dict] = []
    preview_text: str = ""

    # Overall
    primary_keyword: str = ""
    secondary_keywords: list[str] = []
    search_visibility_score: float = 0.0
