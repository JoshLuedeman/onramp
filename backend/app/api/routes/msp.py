"""MSP (Managed Service Provider) dashboard API routes.

All endpoints require the ``msp_admin`` (or ``admin``) role.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import RoleChecker
from app.db.session import get_db
from app.schemas.msp import (
    ComplianceSummaryResponse,
    MSPOverviewResponse,
    TenantHealthResponse,
)
from app.services.msp_service import MSPService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/msp", tags=["msp"])

# Role gate — only admin or msp_admin may access
_require_msp_admin = RoleChecker(["admin", "msp_admin"])


@router.get("/overview", response_model=MSPOverviewResponse)
async def get_msp_overview(
    user: dict = Depends(_require_msp_admin),
    db: AsyncSession = Depends(get_db),
) -> MSPOverviewResponse:
    """Return aggregated overview across all managed tenants."""
    svc = MSPService(db)
    overview = await svc.get_overview()
    logger.info(
        "MSP overview requested by %s", user.get("email", "unknown")
    )
    return overview


@router.get(
    "/tenants/{tenant_id}/health",
    response_model=TenantHealthResponse,
)
async def get_tenant_health(
    tenant_id: str,
    user: dict = Depends(_require_msp_admin),
    db: AsyncSession = Depends(get_db),
) -> TenantHealthResponse:
    """Return detailed health for a specific tenant."""
    svc = MSPService(db)
    health = await svc.get_tenant_health(tenant_id)
    if health is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return health


@router.get(
    "/compliance-summary",
    response_model=ComplianceSummaryResponse,
)
async def get_compliance_summary(
    user: dict = Depends(_require_msp_admin),
    db: AsyncSession = Depends(get_db),
) -> ComplianceSummaryResponse:
    """Return aggregated compliance scores across all tenants."""
    svc = MSPService(db)
    summary = await svc.get_compliance_summary()
    return summary
