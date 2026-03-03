"""User service for CRUD operations and token management."""

from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.integrations.youtube.auth import decrypt_tokens, encrypt_tokens
from app.models.user import User

logger = structlog.get_logger()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get a user by their ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get a user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_channel_id(db: AsyncSession, channel_id: str) -> Optional[User]:
    """Get a user by their YouTube channel ID."""
    result = await db.execute(
        select(User).where(User.youtube_channel_id == channel_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    name: str,
    image: Optional[str] = None,
) -> User:
    """Create a new user."""
    user = User(email=email, name=name, image=image)
    db.add(user)
    await db.flush()
    logger.info("user.created", user_id=str(user.id), email=email)
    return user


async def update_user(
    db: AsyncSession,
    user: User,
    **kwargs,
) -> User:
    """Update user fields."""
    for key, value in kwargs.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    await db.flush()
    return user


async def store_youtube_tokens(
    db: AsyncSession,
    user: User,
    tokens: dict,
    channel_id: str,
    channel_name: Optional[str] = None,
) -> User:
    """Encrypt and store YouTube OAuth tokens for a user."""
    settings = get_settings()
    encrypted = encrypt_tokens(tokens, settings.secret_key)
    user.youtube_tokens_encrypted = encrypted
    user.youtube_channel_id = channel_id
    user.youtube_channel_name = channel_name
    await db.flush()
    logger.info("user.youtube_connected", user_id=str(user.id), channel_id=channel_id)
    return user


async def get_youtube_tokens(user: User) -> Optional[dict]:
    """Decrypt and return YouTube OAuth tokens."""
    if not user.youtube_tokens_encrypted:
        return None
    settings = get_settings()
    return decrypt_tokens(user.youtube_tokens_encrypted, settings.secret_key)
