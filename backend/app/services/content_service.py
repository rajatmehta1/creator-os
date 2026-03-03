"""Content CRUD service with state-machine status transitions."""

from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content, ContentStatus, ContentType
from app.schemas.content import ContentCreate, ContentUpdate

logger = structlog.get_logger()

# ------------------------------------------------------------------
# Valid status transitions (state machine)
# ------------------------------------------------------------------

_VALID_TRANSITIONS: dict[ContentStatus, list[ContentStatus]] = {
    ContentStatus.IDEA: [ContentStatus.DRAFT, ContentStatus.ARCHIVED],
    ContentStatus.DRAFT: [ContentStatus.REVIEW, ContentStatus.ARCHIVED],
    ContentStatus.REVIEW: [ContentStatus.DRAFT, ContentStatus.OPTIMIZED, ContentStatus.ARCHIVED],
    ContentStatus.OPTIMIZED: [ContentStatus.REVIEW, ContentStatus.PUBLISHED, ContentStatus.ARCHIVED],
    ContentStatus.PUBLISHED: [ContentStatus.ARCHIVED],
    ContentStatus.ARCHIVED: [ContentStatus.IDEA, ContentStatus.DRAFT],
}


class InvalidStatusTransitionError(Exception):
    """Raised when a content status transition is not allowed."""

    def __init__(self, current: ContentStatus, target: ContentStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot transition from '{current.value}' to '{target.value}'. "
            f"Allowed targets: {[s.value for s in _VALID_TRANSITIONS.get(current, [])]}"
        )


# ------------------------------------------------------------------
# Create
# ------------------------------------------------------------------

async def create_content(
    db: AsyncSession,
    user_id: UUID,
    data: ContentCreate,
) -> Content:
    """Create a new content piece in IDEA status.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        data: Validated creation payload.

    Returns:
        The newly created ``Content`` instance (flushed, not yet committed).
    """
    content = Content(
        user_id=user_id,
        title=data.title,
        content_type=ContentType(data.content_type),
        status=ContentStatus.IDEA,
        body=data.body,
        idea_id=data.idea_id,
        parent_content_id=data.parent_content_id,
    )
    db.add(content)
    await db.flush()
    logger.info(
        "content.created",
        content_id=str(content.id),
        user_id=str(user_id),
        content_type=data.content_type,
    )
    return content


# ------------------------------------------------------------------
# Read
# ------------------------------------------------------------------

async def get_content(
    db: AsyncSession,
    content_id: UUID,
) -> Optional[Content]:
    """Fetch a single content piece by its ID.

    Returns:
        ``Content`` instance or ``None`` if not found.
    """
    result = await db.execute(select(Content).where(Content.id == content_id))
    return result.scalar_one_or_none()


async def list_content_by_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    status: Optional[ContentStatus] = None,
    content_type: Optional[ContentType] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Content]:
    """List content pieces for a user with optional filters.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        status: Optional status filter.
        content_type: Optional content-type filter.
        limit: Maximum number of results.
        offset: Pagination offset.

    Returns:
        List of ``Content`` instances ordered by most recently updated.
    """
    stmt = (
        select(Content)
        .where(Content.user_id == user_id)
        .order_by(Content.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if status is not None:
        stmt = stmt.where(Content.status == status)
    if content_type is not None:
        stmt = stmt.where(Content.content_type == content_type)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_content_variants(
    db: AsyncSession,
    content_id: UUID,
) -> list[Content]:
    """Return all variant children of a parent content piece.

    Args:
        db: Async database session.
        content_id: Parent content ID.

    Returns:
        List of ``Content`` variants linked via ``parent_content_id``.
    """
    stmt = (
        select(Content)
        .where(Content.parent_content_id == content_id)
        .order_by(Content.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------

async def update_content(
    db: AsyncSession,
    content_id: UUID,
    data: ContentUpdate,
) -> Optional[Content]:
    """Update mutable fields on a content piece.

    This does **not** change the status; use ``update_content_status`` for
    state-machine transitions.

    Returns:
        Updated ``Content`` instance or ``None`` if not found.
    """
    content = await get_content(db, content_id)
    if content is None:
        logger.warning("content.not_found", content_id=str(content_id))
        return None

    update_fields = data.model_dump(exclude_unset=True, exclude={"status"})
    for field, value in update_fields.items():
        if hasattr(content, field):
            setattr(content, field, value)

    await db.flush()
    logger.info("content.updated", content_id=str(content_id), fields=list(update_fields.keys()))
    return content


# ------------------------------------------------------------------
# Status transitions (state machine)
# ------------------------------------------------------------------

async def update_content_status(
    db: AsyncSession,
    content_id: UUID,
    new_status: ContentStatus,
) -> Content:
    """Transition content to a new status following the state machine.

    Valid transitions::

        idea -> draft -> review -> optimized -> published -> archived
                  ^        |          |
                  +--------+          |
                  +-------------------+
        archived -> idea | draft  (re-open)

    Args:
        db: Async database session.
        content_id: The content piece to transition.
        new_status: Target status.

    Raises:
        ValueError: If the content is not found.
        InvalidStatusTransitionError: If the transition is not allowed.

    Returns:
        The content piece with its updated status.
    """
    content = await get_content(db, content_id)
    if content is None:
        raise ValueError(f"Content {content_id} not found")

    current_status = content.status
    allowed = _VALID_TRANSITIONS.get(current_status, [])

    if new_status not in allowed:
        raise InvalidStatusTransitionError(current_status, new_status)

    content.status = new_status
    await db.flush()

    logger.info(
        "content.status_changed",
        content_id=str(content_id),
        from_status=current_status.value,
        to_status=new_status.value,
    )
    return content
