"""Trend Scout endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession, RedisClient
from app.schemas.trend import TrendRefreshRequest, TrendResponse

router = APIRouter()


@router.get("", response_model=list[TrendResponse])
async def get_trends(
    db: DbSession,
    category: str | None = Query(default=None),
    velocity: str | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[TrendResponse]:
    """Get current trends for the creator's niche."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 3")


@router.post("/refresh")
async def refresh_trends(
    request: TrendRefreshRequest,
    db: DbSession,
    redis: RedisClient,
) -> dict[str, str]:
    """Force refresh trends from all sources."""
    return {"status": "queued", "message": "Trend refresh has been queued"}


@router.get("/history")
async def get_trend_history(
    db: DbSession,
    days: int = Query(default=30, le=90),
) -> list[TrendResponse]:
    """Get historical trend data."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 3")


@router.get("/{trend_id}", response_model=TrendResponse)
async def get_trend_detail(trend_id: UUID, db: DbSession) -> TrendResponse:
    """Get detailed information about a specific trend."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Coming in Sprint 3")
