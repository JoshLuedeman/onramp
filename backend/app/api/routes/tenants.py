"""Tenant management API routes.

All mutating operations (create / update / delete) require the ``admin`` role.
Read operations also require ``admin`` so that only privileged users can
enumerate tenants.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import RoleChecker
from app.db.session import get_db
from app.schemas.tenant import (
    TenantCreate,
    TenantListResponse,
    TenantResponse,
    TenantUpdate,
)
from app.services.tenant_service import TenantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tenants", tags=["tenants"])

# Role gates
_require_admin = RoleChecker(["admin"])


@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant(
    body: TenantCreate,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Create a new tenant (admin only)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )

    svc = TenantService(db)
    tenant = await svc.create_tenant(body)
    return TenantResponse.model_validate(tenant)


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> TenantListResponse:
    """List all tenants with pagination (admin only)."""
    if db is None:
        return TenantListResponse(tenants=[], total=0)

    svc = TenantService(db)
    tenants, total = await svc.list_tenants(skip=skip, limit=limit)
    return TenantListResponse(
        tenants=[TenantResponse.model_validate(t) for t in tenants],
        total=total,
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Get a single tenant by ID (admin only)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )

    svc = TenantService(db)
    tenant = await svc.get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return TenantResponse.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Update a tenant (admin only)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )

    svc = TenantService(db)
    tenant = await svc.update_tenant(tenant_id, body)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return TenantResponse.model_validate(tenant)


@router.delete("/{tenant_id}", response_model=TenantResponse)
async def delete_tenant(
    tenant_id: str,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Soft-delete a tenant by deactivating it (admin only)."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )

    svc = TenantService(db)
    tenant = await svc.deactivate_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return TenantResponse.model_validate(tenant)
