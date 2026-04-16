"""Tenant lifecycle management API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import RoleChecker
from app.db.session import get_db
from app.schemas.tenant_lifecycle import (
    TenantOffboardRequest,
    TenantOffboardResponse,
    TenantProvisionRequest,
    TenantSettingsResponse,
    TenantSettingsUpdate,
)
from app.services.tenant_service import TenantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tenants", tags=["tenant-lifecycle"])

_require_admin = RoleChecker(["admin"])


@router.post(
    "/provision",
    response_model=TenantSettingsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_tenant(
    body: TenantProvisionRequest,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Provision a new tenant with resource limits."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )

    svc = TenantService(db)
    result = await svc.provision_tenant(body)
    return result


@router.get(
    "/{tenant_id}/settings",
    response_model=TenantSettingsResponse,
)
async def get_tenant_settings(
    tenant_id: str,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get tenant settings and resource limits."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )

    svc = TenantService(db)
    result = await svc.get_tenant_settings(tenant_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return result


@router.put(
    "/{tenant_id}/settings",
    response_model=TenantSettingsResponse,
)
async def update_tenant_settings(
    tenant_id: str,
    body: TenantSettingsUpdate,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update tenant resource limits and feature flags."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )

    svc = TenantService(db)
    result = await svc.update_tenant_settings(tenant_id, body)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return result


@router.post(
    "/{tenant_id}/offboard",
    response_model=TenantOffboardResponse,
)
async def offboard_tenant(
    tenant_id: str,
    body: TenantOffboardRequest,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Offboard a tenant — deactivate and optionally archive."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )

    svc = TenantService(db)
    result = await svc.offboard_tenant(
        tenant_id,
        archive=body.archive,
        retention_days=body.retention_days,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return result
