"""User-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: str
    name: str
    image: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    image: Optional[str] = None
    youtube_channel_id: Optional[str] = None
    youtube_channel_name: Optional[str] = None
    niche: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfile(BaseModel):
    id: UUID
    email: str
    name: str
    image: Optional[str] = None
    youtube_channel_id: Optional[str] = None
    youtube_channel_name: Optional[str] = None
    niche: Optional[str] = None
    topics: list[str] = []
    dna_confidence: Optional[float] = None
    settings: dict = {}

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    niche: Optional[str] = None
    topics: Optional[list[str]] = None
    settings: Optional[dict] = None


class CreatorDNAResponse(BaseModel):
    """Creator DNA fingerprint response."""

    # Voice Characteristics
    vocabulary_complexity: Optional[float] = None
    sentence_rhythm: Optional[dict] = None
    filler_words: list[str] = []
    signature_phrases: list[str] = []
    humor_style: Optional[str] = None
    humor_frequency: Optional[float] = None

    # Topic Profile
    topic_clusters: list[dict] = []
    expertise_depth: dict[str, float] = {}

    # Audience Relationship
    formality_level: Optional[float] = None
    audience_address_style: Optional[str] = None
    vulnerability_level: Optional[float] = None
    call_to_action_style: Optional[str] = None

    # Content Structure
    preferred_format_length: dict[str, float] = {}
    hook_style: Optional[str] = None
    pacing_pattern: Optional[str] = None
    storytelling_frequency: Optional[float] = None

    # Meta
    confidence_score: Optional[float] = None
    last_updated: Optional[datetime] = None
    videos_analyzed: int = 0
