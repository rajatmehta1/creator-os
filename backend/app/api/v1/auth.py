"""YouTube OAuth authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.dependencies import DbSession
from app.schemas.user import UserResponse

router = APIRouter()


@router.post("/youtube/connect")
async def youtube_connect(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Initiate YouTube OAuth flow. Returns the authorization URL."""
    from app.integrations.youtube.auth import generate_auth_url

    auth_url = generate_auth_url(settings)
    return {"auth_url": auth_url}


@router.get("/youtube/callback")
async def youtube_callback(
    code: str = Query(...),
    state: str = Query(default=""),
    db: AsyncSession = Depends(),
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> dict[str, str]:
    """Handle YouTube OAuth callback and store tokens."""
    from app.integrations.youtube.auth import exchange_code

    try:
        tokens = await exchange_code(code, settings)
        # TODO: Store tokens, create/update user
        return {"status": "connected", "message": "YouTube channel connected successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}",
        )


@router.post("/youtube/disconnect")
async def youtube_disconnect(
    db: DbSession,
) -> dict[str, str]:
    """Revoke YouTube access and remove stored tokens."""
    # TODO: Implement with current user context
    return {"status": "disconnected"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: DbSession,
) -> UserResponse:
    """Get the current authenticated user's profile."""
    # TODO: Implement with auth middleware
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )
