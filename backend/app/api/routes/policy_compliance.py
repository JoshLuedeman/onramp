"""Policy compliance monitoring API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db.session import get_db
from app.models.policy_compliance import PolicyComplianceResult, PolicyViolation
from app.schemas.policy_compliance import (
    PolicyComplianceResultList,
    PolicyComplianceResultResponse,
    PolicyComplianceSummary,
    PolicyViolationResponse,
)
from app.services.policy_monitor import policy_monitor

router = APIRouter(
    prefix="/api/governance/policy-compliance",
    tags=["policy-compliance"],
)


# ── Scan trigger ─────────────────────────────────────────────────────────────


@router.post("/scan/{project_id}", response_model=PolicyComplianceResultResponse)
async def trigger_scan(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a policy compliance scan for a project."""
    result = await policy_monitor.check_compliance(
        project_id=project_id,
        db=db,
    )

    now = datetime.now(timezone.utc)

    # Build violation responses
    violations = [
        PolicyViolationResponse(
            id=v["id"],
            compliance_result_id=result["id"],
            resource_id=v["resource_id"],
            resource_type=v["resource_type"],
            policy_name=v["policy_name"],
            policy_description=v.get("policy_description"),
            severity=v["severity"],
            framework_control_id=v.get("framework_control_id"),
            remediation_suggestion=v.get("remediation_suggestion"),
            detected_at=v["detected_at"],
        )
        for v in result.get("violations", [])
    ]

    return PolicyComplianceResultResponse(
        id=result["id"],
        project_id=result["project_id"],
        tenant_id=result.get("tenant_id"),
        scan_timestamp=result["scan_timestamp"],
        total_resources=result["total_resources"],
        compliant_count=result["compliant_count"],
        non_compliant_count=result["non_compliant_count"],
        status=result["status"],
        error_message=result.get("error_message"),
        violations=violations,
        created_at=now,
        updated_at=now,
    )


# ── Result listing ───────────────────────────────────────────────────────────


@router.get("/results", response_model=PolicyComplianceResultList)
async def list_results(
    project_id: str = Query(None, description="Filter by project ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List policy compliance scan results."""
    if db is None:
        return PolicyComplianceResultList(results=[], total=0)

    query = select(PolicyComplianceResult).options(
        selectinload(PolicyComplianceResult.violations)
    )
    if project_id:
        query = query.where(PolicyComplianceResult.project_id == project_id)

    query = query.order_by(PolicyComplianceResult.scan_timestamp.desc())
    result = await db.execute(query)
    rows = result.scalars().all()
    return PolicyComplianceResultList(results=rows, total=len(rows))


@router.get("/results/{result_id}", response_model=PolicyComplianceResultResponse)
async def get_result(
    result_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific compliance result with its violations."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    result = await db.execute(
        select(PolicyComplianceResult)
        .options(selectinload(PolicyComplianceResult.violations))
        .where(PolicyComplianceResult.id == result_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return row


# ── Summary ──────────────────────────────────────────────────────────────────


@router.get("/summary/{project_id}", response_model=PolicyComplianceSummary)
async def get_summary(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated policy compliance summary for a project."""
    if db is None:
        return PolicyComplianceSummary(project_id=project_id)

    # Count scans
    scan_count_result = await db.execute(
        select(func.count()).select_from(PolicyComplianceResult).where(
            PolicyComplianceResult.project_id == project_id
        )
    )
    total_scans = scan_count_result.scalar() or 0

    # Latest scan timestamp
    latest_result = await db.execute(
        select(func.max(PolicyComplianceResult.scan_timestamp)).where(
            PolicyComplianceResult.project_id == project_id
        )
    )
    latest_scan_at = latest_result.scalar_one_or_none()

    # Get all violations for this project via join
    violation_query = (
        select(PolicyViolation)
        .join(PolicyComplianceResult)
        .where(PolicyComplianceResult.project_id == project_id)
    )
    violation_result = await db.execute(violation_query)
    violations = violation_result.scalars().all()

    # Aggregate by severity
    by_severity: dict[str, int] = {
        "critical": 0, "high": 0, "medium": 0, "low": 0
    }
    for v in violations:
        if v.severity in by_severity:
            by_severity[v.severity] += 1

    # Aggregate by framework (from policy → control mapping)
    by_framework: dict[str, int] = {}
    for v in violations:
        # Use the framework_mapping from the service to count by framework
        # For DB-persisted violations, count by policy_name mapping
        from app.services.compliance_data import COMPLIANCE_FRAMEWORKS

        for fw in COMPLIANCE_FRAMEWORKS:
            for ctrl in fw["controls"]:
                if v.policy_name in ctrl.get("azure_policies", []):
                    fw_name = fw["short_name"]
                    by_framework[fw_name] = by_framework.get(fw_name, 0) + 1

    # Compliance rate from latest scan
    compliance_rate = 0.0
    if latest_scan_at is not None:
        latest_scan_result = await db.execute(
            select(PolicyComplianceResult)
            .where(
                PolicyComplianceResult.project_id == project_id,
                PolicyComplianceResult.scan_timestamp == latest_scan_at,
            )
        )
        latest_scan = latest_scan_result.scalar_one_or_none()
        if latest_scan and latest_scan.total_resources > 0:
            compliance_rate = round(
                (latest_scan.compliant_count / latest_scan.total_resources)
                * 100,
                1,
            )

    return PolicyComplianceSummary(
        project_id=project_id,
        total_scans=total_scans,
        latest_scan_at=latest_scan_at,
        total_violations=len(violations),
        by_severity=by_severity,
        by_framework=by_framework,
        compliance_rate=compliance_rate,
    )


# ── Violations listing ───────────────────────────────────────────────────────


@router.get("/violations", response_model=list[PolicyViolationResponse])
async def list_violations(
    project_id: str = Query(None, description="Filter by project ID"),
    severity: str = Query(None, description="Filter by severity"),
    framework: str = Query(None, description="Filter by framework short name"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List policy violations with optional filters."""
    if db is None:
        return []

    query = select(PolicyViolation).join(PolicyComplianceResult)

    if project_id:
        query = query.where(
            PolicyComplianceResult.project_id == project_id
        )
    if severity:
        query = query.where(PolicyViolation.severity == severity)
    if framework:
        # Filter by policy names that belong to the specified framework
        from app.services.compliance_data import get_framework_by_short_name

        fw = get_framework_by_short_name(framework)
        if fw:
            policy_names = set()
            for ctrl in fw["controls"]:
                policy_names.update(ctrl.get("azure_policies", []))
            if policy_names:
                query = query.where(
                    PolicyViolation.policy_name.in_(policy_names)
                )
            else:
                return []
        else:
            return []

    query = query.order_by(PolicyViolation.detected_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
