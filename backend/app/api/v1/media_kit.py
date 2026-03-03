"""Media Kit Generator endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DbSession
from app.schemas.media_kit import MediaKitGenerateRequest, MediaKitResponse

router = APIRouter()


@router.get("", response_model=MediaKitResponse)
async def get_media_kit(db: DbSession) -> MediaKitResponse:
    """Get the current media kit data."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 5")


@router.post("/generate", response_model=MediaKitResponse)
async def generate_media_kit(
    request: MediaKitGenerateRequest,
    db: DbSession,
) -> MediaKitResponse:
    """Generate or refresh the media kit."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 5")


@router.get("/pdf")
async def get_media_kit_pdf(db: DbSession) -> dict:
    """Download media kit as PDF."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 5")


@router.get("/public/{slug}")
async def get_public_media_kit(slug: str, db: DbSession) -> dict:
    """Public shareable media kit page."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 5")
