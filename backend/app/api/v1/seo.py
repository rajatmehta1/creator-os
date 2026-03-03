"""SEO Optimizer endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DbSession
from app.schemas.content import SEOPackage

router = APIRouter()


@router.post("/optimize", response_model=SEOPackage)
async def optimize_seo(
    content_id: UUID,
    db: DbSession,
) -> SEOPackage:
    """Generate an SEO package for content."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")


@router.get("/{content_id}", response_model=SEOPackage)
async def get_seo_package(content_id: UUID, db: DbSession) -> SEOPackage:
    """Get the SEO package for a content piece."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")


@router.post("/{content_id}/refresh", response_model=SEOPackage)
async def refresh_seo(content_id: UUID, db: DbSession) -> SEOPackage:
    """Regenerate SEO package for content."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 4")
