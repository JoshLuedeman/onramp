"""Governance audit trail API routes — append-only event log."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.governance_audit import (
    GovernanceAuditEntryResponse,
    GovernanceAuditListResponse,
    GovernanceAuditStats,
)
from app.services.governance_audit import governance_audit_service

router = APIRouter(
    prefix="/api/governance/audit", tags=["governance-audit"]
)


@router.get("/", response_model=GovernanceAuditListResponse)
async def list_audit_entries(
    event_type: str | None = Query(None, description="Filter by event type"),
    actor: str | None = Query(None, description="Filter by actor"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    project_id: str | None = Query(None, description="Filter by project"),
    date_from: datetime | None = Query(None, description="Start date filter"),
    date_to: datetime | None = Query(None, description="End date filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit trail entries with filtering and pagination."""
    tenant_id = user.get("tenant_id")
    filters = {}
    if event_type:
        filters["event_type"] = event_type
    if actor:
        filters["actor"] = actor
    if resource_type:
        filters["resource_type"] = resource_type
    if project_id:
        filters["project_id"] = project_id
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to

    result = await governance_audit_service.query_events(
        filters=filters or None,
        page=page,
        page_size=page_size,
        db=db,
    )
    return GovernanceAuditListResponse(**result)


@router.get("/export")
async def export_audit_entries(
    fmt: str = Query("json", alias="format", description="Export format: json or csv"),
    event_type: str | None = Query(None, description="Filter by event type"),
    actor: str | None = Query(None, description="Filter by actor"),
    project_id: str | None = Query(None, description="Filter by project"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export audit entries as JSON or CSV."""
    filters = {}
    if event_type:
        filters["event_type"] = event_type
    if actor:
        filters["actor"] = actor
    if project_id:
        filters["project_id"] = project_id

    content = await governance_audit_service.export_events(
        filters=filters or None,
        fmt=fmt,
        db=db,
    )

    if fmt == "csv":
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=governance_audit.csv"
            },
        )

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=governance_audit.json"
        },
    )


@router.get("/stats", response_model=GovernanceAuditStats)
async def get_audit_stats(
    project_id: str | None = Query(None, description="Filter by project"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get summary statistics for governance audit events."""
    tenant_id = user.get("tenant_id")
    stats = await governance_audit_service.get_stats(
        project_id=project_id,
        tenant_id=tenant_id,
        db=db,
    )
    return GovernanceAuditStats(**stats)


@router.get("/{entry_id}", response_model=GovernanceAuditEntryResponse)
async def get_audit_entry(
    entry_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single audit trail entry."""
    result = await governance_audit_service.get_event(entry_id, db=db)
    if result is None:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return GovernanceAuditEntryResponse(**result)
