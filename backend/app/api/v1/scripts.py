"""Script Architect endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession
from app.schemas.content import ContentResponse, ContentUpdate, ScriptGenerateRequest

router = APIRouter()


@router.post("/generate", response_model=ContentResponse)
async def generate_script(
    request: ScriptGenerateRequest,
    db: DbSession,
) -> ContentResponse:
    """Generate a script from an idea using the Script Architect agent."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")


@router.get("", response_model=list[ContentResponse])
async def list_scripts(
    db: DbSession,
    content_type: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ContentResponse]:
    """List all scripts."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")


@router.get("/{script_id}", response_model=ContentResponse)
async def get_script(script_id: UUID, db: DbSession) -> ContentResponse:
    """Get a specific script."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")


@router.put("/{script_id}", response_model=ContentResponse)
async def update_script(
    script_id: UUID,
    data: ContentUpdate,
    db: DbSession,
) -> ContentResponse:
    """Edit a script."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")


@router.post("/{script_id}/variants", response_model=list[ContentResponse])
async def generate_variants(
    script_id: UUID,
    platforms: list[str] = ["blog_post", "twitter_thread", "linkedin_post", "newsletter"],
    db: DbSession = None,
) -> list[ContentResponse]:
    """Generate platform variants of a script."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")
