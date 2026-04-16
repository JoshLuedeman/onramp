"""Reusable tenant-scoping utilities for row-level isolation.

Provides helper functions that verify a resource belongs to the
current tenant before allowing access.  Also includes an
audit-logged bypass mechanism for admin / cross-tenant operations.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.architecture import Architecture
from app.models.project import Project

logger = logging.getLogger(__name__)


async def require_project_tenant(
    db: AsyncSession,
    project_id: str,
    tenant_id: str,
) -> Project:
    """Verify *project_id* belongs to *tenant_id* and return it.

    Raises:
        HTTPException 404 when the project does not exist **or**
        belongs to a different tenant (prevents enumeration).
    """
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_id == tenant_id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def require_architecture_tenant(
    db: AsyncSession,
    architecture_id: str,
    tenant_id: str,
) -> Architecture:
    """Verify *architecture_id* belongs to *tenant_id* via project.

    Raises:
        HTTPException 404 when the architecture does not exist or
        belongs to a different tenant.
    """
    result = await db.execute(
        select(Architecture)
        .join(Project, Architecture.project_id == Project.id)
        .where(
            Architecture.id == architecture_id,
            Project.tenant_id == tenant_id,
        )
    )
    architecture = result.scalar_one_or_none()
    if architecture is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Architecture not found",
        )
    return architecture


@asynccontextmanager
async def bypass_tenant_filter(
    *,
    operation: str,
    user_id: str,
    tenant_id: str,
) -> AsyncIterator[None]:
    """Log and allow a tenant-filter bypass for admin operations.

    Usage::

        async with bypass_tenant_filter(
            operation="list_all_tenants",
            user_id=user["sub"],
            tenant_id=tenant.id,
        ):
            ...  # queries run without tenant scope
    """
    logger.warning(
        "TENANT_BYPASS: operation=%s user_id=%s tenant_id=%s",
        operation,
        user_id,
        tenant_id,
    )
    yield
