"""Idea Generator endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession
from app.schemas.idea import IdeaGenerateRequest, IdeaResponse, IdeaUpdateRequest

router = APIRouter()


@router.post("/generate", response_model=list[IdeaResponse])
async def generate_ideas(
    request: IdeaGenerateRequest,
    db: DbSession,
) -> list[IdeaResponse]:
    """Generate content ideas using the Idea Generator agent."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 3")


@router.get("", response_model=list[IdeaResponse])
async def list_ideas(
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status"),
    content_type: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[IdeaResponse]:
    """List saved ideas."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 3")


@router.get("/{idea_id}", response_model=IdeaResponse)
async def get_idea(idea_id: UUID, db: DbSession) -> IdeaResponse:
    """Get idea details."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 3")


@router.put("/{idea_id}", response_model=IdeaResponse)
async def update_idea(
    idea_id: UUID,
    data: IdeaUpdateRequest,
    db: DbSession,
) -> IdeaResponse:
    """Update, approve, or reject an idea."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 3")


@router.post("/{idea_id}/to-script")
async def idea_to_script(idea_id: UUID, db: DbSession) -> dict[str, str]:
    """Send an approved idea to the Script Architect agent."""
    return {"status": "queued", "message": "Script generation queued"}
