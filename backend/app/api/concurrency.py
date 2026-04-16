"""Optimistic concurrency control utilities for architecture mutations.

Provides helpers that compare a client-submitted version against the
current database row and raise 409 Conflict when they diverge.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ConflictError(HTTPException):
    """HTTP 409 Conflict with structured conflict payload."""

    def __init__(
        self,
        *,
        current_version: int,
        submitted_version: int,
        current_data: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> None:
        detail = {
            "current_version": current_version,
            "submitted_version": submitted_version,
            "current_data": current_data or {},
            "message": message or (
                f"Version conflict: you submitted version "
                f"{submitted_version} but the current version is "
                f"{current_version}. Reload and retry."
            ),
        }
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


async def check_version(
    db: AsyncSession,
    model_class: type,
    record_id: str,
    submitted_version: int,
) -> Any:
    """Verify *submitted_version* matches the current DB row version.

    Args:
        db: Async database session.
        model_class: SQLAlchemy model with ``id`` and ``version`` columns.
        record_id: Primary key of the row to check.
        submitted_version: Version the client believes is current.

    Returns:
        The current database instance if versions match.

    Raises:
        ConflictError: When submitted_version != current row version.
        HTTPException 404: When the record does not exist.
    """
    result = await db.execute(
        select(model_class).where(model_class.id == record_id)
    )
    instance = result.scalars().first()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model_class.__name__} {record_id} not found",
        )

    current_version: int = instance.version
    if current_version != submitted_version:
        # Build current_data from architecture_data if available
        current_data: dict[str, Any] = {}
        if hasattr(instance, "architecture_data") and instance.architecture_data:
            current_data = instance.architecture_data

        logger.info(
            "Version conflict on %s %s: submitted=%d current=%d",
            model_class.__name__,
            record_id,
            submitted_version,
            current_version,
        )
        raise ConflictError(
            current_version=current_version,
            submitted_version=submitted_version,
            current_data=current_data,
        )

    return instance


def increment_version(instance: Any) -> int:
    """Bump the version field on *instance* after a successful update.

    Args:
        instance: A SQLAlchemy model instance with a ``version`` attribute.

    Returns:
        The new version number.
    """
    current: int = getattr(instance, "version", 0)
    new_version = current + 1
    instance.version = new_version
    logger.debug(
        "Incremented version on %s to %d",
        type(instance).__name__,
        new_version,
    )
    return new_version
