"""Shared API dependencies for dependency injection."""

import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.db.session import get_db
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


async def get_current_tenant(
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Resolve the current tenant from the request context.

    Resolution order:
        1. JWT ``tid`` claim → lookup by azure_tenant_id
        2. ``X-Tenant-ID`` header → lookup by tenant id
        3. Dev-mode default → auto-create a default tenant

    Returns:
        The resolved :class:`Tenant` ORM instance.

    Raises:
        HTTPException 403: When no tenant can be resolved or the tenant is
            inactive.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Database not configured — cannot resolve tenant",
        )

    tenant: Tenant | None = None

    # 1. Try JWT tid claim
    tid = user.get("tenant_id") or user.get("tid")
    if tid and tid != "dev-tenant":
        result = await db.execute(
            select(Tenant).where(Tenant.azure_tenant_id == tid)
        )
        tenant = result.scalar_one_or_none()
        if tenant:
            logger.debug("Resolved tenant '%s' from JWT tid claim", tenant.name)

    # 2. Try X-Tenant-ID header
    if tenant is None:
        header_tenant_id = request.headers.get("X-Tenant-ID")
        if header_tenant_id:
            result = await db.execute(
                select(Tenant).where(Tenant.id == header_tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                logger.debug("Resolved tenant '%s' from X-Tenant-ID header", tenant.name)

    # 3. Dev-mode default tenant
    if tenant is None and settings.is_dev_mode:
        result = await db.execute(
            select(Tenant).where(Tenant.name == "Default")
        )
        tenant = result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name="Default", is_active=True)
            db.add(tenant)
            await db.flush()
            logger.info("Auto-created default tenant for dev mode (id=%s)", tenant.id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to resolve tenant",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is deactivated",
        )

    return tenant
