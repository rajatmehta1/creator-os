"""Performance analytics endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession

router = APIRouter()


@router.get("/overview")
async def get_analytics_overview(db: DbSession) -> dict:
    """Get channel performance overview."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 5")


@router.get("/videos")
async def get_video_analytics(
    db: DbSession,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="publish_date"),
) -> list[dict]:
    """Get per-video analytics."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 5")


@router.get("/insights")
async def get_insights(db: DbSession) -> list[dict]:
    """Get AI-generated performance insights."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 5")


@router.post("/sync")
async def sync_analytics(db: DbSession) -> dict[str, str]:
    """Force sync analytics from YouTube."""
    return {"status": "queued", "message": "Analytics sync has been queued"}
