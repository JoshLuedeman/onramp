"""RBAC health monitoring API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db.session import get_db
from app.models.rbac_health import RBACFinding, RBACScanResult
from app.schemas.rbac_health import (
    RBACFindingResponse,
    RBACHealthSummary,
    RBACScanRequest,
    RBACScanResultList,
    RBACScanResultResponse,
)
from app.services.rbac_monitor import rbac_monitor

router = APIRouter(prefix="/api/governance/rbac", tags=["rbac"])


# ── Scan trigger ─────────────────────────────────────────────────────────────


@router.post("/scan/{project_id}", response_model=RBACScanResultResponse)
async def trigger_scan(
    project_id: str,
    payload: RBACScanRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an RBAC health scan for a project."""
    result = await rbac_monitor.scan_rbac_health(
        project_id=project_id,
        subscription_id=payload.subscription_id,
        tenant_id=payload.tenant_id,
        db=db,
    )

    now = result.get("scan_timestamp", datetime.now(timezone.utc))
    findings_response = [
        RBACFindingResponse(
            id=str(uuid.uuid4()),
            scan_result_id=result["id"],
            finding_type=f["finding_type"],
            severity=f["severity"],
            principal_id=f["principal_id"],
            principal_name=f.get("principal_name"),
            role_name=f["role_name"],
            scope=f["scope"],
            description=f["description"],
            remediation=f["remediation"],
            created_at=now,
        )
        for f in result.get("findings", [])
    ]

    return RBACScanResultResponse(
        id=result["id"],
        project_id=result["project_id"],
        tenant_id=result.get("tenant_id"),
        subscription_id=result["subscription_id"],
        health_score=result["health_score"],
        total_assignments=result["total_assignments"],
        finding_count=result["finding_count"],
        scan_timestamp=now,
        status=result["status"],
        findings=findings_response,
        created_at=now,
        updated_at=now,
    )


# ── Results ──────────────────────────────────────────────────────────────────


@router.get("/results", response_model=RBACScanResultList)
async def list_results(
    project_id: str = Query(None, description="Filter by project ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List RBAC scan results, optionally filtered by project_id."""
    if db is None:
        return RBACScanResultList(scan_results=[], total=0)

    query = select(RBACScanResult).options(selectinload(RBACScanResult.findings))

    if project_id:
        query = query.where(RBACScanResult.project_id == project_id)

    query = query.order_by(RBACScanResult.scan_timestamp.desc())
    result = await db.execute(query)
    scans = result.scalars().all()
    return RBACScanResultList(scan_results=scans, total=len(scans))


@router.get("/results/{result_id}", response_model=RBACScanResultResponse)
async def get_result(
    result_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get an RBAC scan result with its findings."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    result = await db.execute(
        select(RBACScanResult)
        .options(selectinload(RBACScanResult.findings))
        .where(RBACScanResult.id == result_id)
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan result not found")
    return scan


# ── Summary ──────────────────────────────────────────────────────────────────


@router.get("/summary/{project_id}", response_model=RBACHealthSummary)
async def get_summary(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get RBAC health summary for a project."""
    if db is None:
        return RBACHealthSummary(project_id=project_id)

    # Get the latest scan result for this project
    result = await db.execute(
        select(RBACScanResult)
        .options(selectinload(RBACScanResult.findings))
        .where(RBACScanResult.project_id == project_id)
        .order_by(RBACScanResult.scan_timestamp.desc())
        .limit(1)
    )
    latest_scan = result.scalar_one_or_none()

    if latest_scan is None:
        return RBACHealthSummary(project_id=project_id)

    # Calculate finding counts by type and severity
    findings_by_type: dict[str, int] = {
        "over_permissioned": 0,
        "stale_assignment": 0,
        "custom_role_proliferation": 0,
        "missing_pim": 0,
        "expiring_credential": 0,
    }
    findings_by_severity: dict[str, int] = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for finding in latest_scan.findings:
        if finding.finding_type in findings_by_type:
            findings_by_type[finding.finding_type] += 1
        if finding.severity in findings_by_severity:
            findings_by_severity[finding.severity] += 1

    # Top risks: critical and high findings
    top_risks = sorted(
        latest_scan.findings,
        key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(
            f.severity, 4
        ),
    )[:5]

    return RBACHealthSummary(
        project_id=project_id,
        health_score=latest_scan.health_score,
        total_findings=latest_scan.finding_count,
        findings_by_type=findings_by_type,
        findings_by_severity=findings_by_severity,
        top_risks=top_risks,
        latest_scan_at=latest_scan.scan_timestamp,
    )


# ── Findings ─────────────────────────────────────────────────────────────────


@router.get("/findings", response_model=list[RBACFindingResponse])
async def list_findings(
    finding_type: str = Query(None, description="Filter by finding type"),
    severity: str = Query(None, description="Filter by severity"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List RBAC findings with optional filters."""
    if db is None:
        return []

    query = select(RBACFinding)

    if finding_type:
        query = query.where(RBACFinding.finding_type == finding_type)
    if severity:
        query = query.where(RBACFinding.severity == severity)

    query = query.order_by(RBACFinding.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
