"""Creator profile and DNA fingerprint endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DbSession
from app.schemas.user import CreatorDNAResponse, UserProfile, UserUpdate

router = APIRouter()


@router.get("", response_model=UserProfile)
async def get_profile(db: DbSession) -> UserProfile:
    """Get the current creator's profile."""
    # TODO: Implement with auth
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 3")


@router.put("", response_model=UserProfile)
async def update_profile(data: UserUpdate, db: DbSession) -> UserProfile:
    """Update creator profile settings."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 3")


@router.post("/dna/build")
async def build_dna(db: DbSession) -> dict[str, str]:
    """Trigger a Creator DNA fingerprint build from YouTube content."""
    return {"status": "queued", "message": "DNA fingerprint build has been queued"}


@router.get("/dna", response_model=CreatorDNAResponse)
async def get_dna(db: DbSession) -> CreatorDNAResponse:
    """Get the current Creator DNA fingerprint."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 2")


@router.get("/dna/status")
async def get_dna_status(db: DbSession) -> dict[str, str]:
    """Get the DNA fingerprint build progress."""
    return {"status": "not_started", "progress": 0.0, "message": "No build in progress"}
