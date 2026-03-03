"""Content pipeline endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession
from app.schemas.content import ContentCreate, ContentResponse, ContentUpdate

router = APIRouter()


@router.get("", response_model=list[ContentResponse])
async def list_content(
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status"),
    content_type: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ContentResponse]:
    """Get all content with pipeline status."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")


@router.post("", response_model=ContentResponse)
async def create_content(
    data: ContentCreate,
    db: DbSession,
) -> ContentResponse:
    """Create a new content entry."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")


@router.put("/{content_id}/status", response_model=ContentResponse)
async def update_content_status(
    content_id: UUID,
    new_status: str,
    db: DbSession,
) -> ContentResponse:
    """Move content through pipeline stages."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")


@router.get("/{content_id}/variants", response_model=list[ContentResponse])
async def get_content_variants(
    content_id: UUID,
    db: DbSession,
) -> list[ContentResponse]:
    """Get all platform variants of a content piece."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")
