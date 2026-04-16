"""Enterprise audit log API routes."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import RoleChecker
from app.db.session import get_db
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["audit"])

_require_admin = RoleChecker(["admin"])


@router.get("/events")
async def query_audit_events(
    tenant_id: str | None = Query(None),
    actor_id: str | None = Query(None),
    resource_type: str | None = Query(None),
    action: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Query audit events with optional filters (admin only)."""
    if db is None:
        return {"events": [], "total": 0, "page": 1, "page_size": page_size}

    return await audit_service.query_events(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get("/events/export")
async def export_audit_events(
    tenant_id: str | None = Query(None),
    actor_id: str | None = Query(None),
    resource_type: str | None = Query(None),
    action: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    fmt: str = Query("json", pattern="^(json|csv)$"),
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Export audit events as JSON or CSV (admin only)."""
    if db is None:
        raise HTTPException(
            status_code=503, detail="Database not configured",
        )

    content = await audit_service.export_events(
        db,
        tenant_id=tenant_id,
        fmt=fmt,
        actor_id=actor_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
    )

    if fmt == "csv":
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=audit.csv",
            },
        )
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=audit.json",
        },
    )
