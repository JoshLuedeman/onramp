"""Tagging compliance API routes — policies, scans, and results."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db.session import get_db
from app.models.tagging import TaggingPolicy, TaggingScanResult
from app.schemas.tagging import (
    TaggingPolicyCreate,
    TaggingPolicyResponse,
    TaggingPolicyUpdate,
    TaggingScanResultList,
    TaggingScanResultResponse,
    TaggingSummary,
)

router = APIRouter(prefix="/api/governance/tagging", tags=["tagging"])


# ── Policies ─────────────────────────────────────────────────────────────────


@router.post("/policies", response_model=TaggingPolicyResponse)
async def create_policy(
    payload: TaggingPolicyCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tagging policy."""
    now = datetime.now(timezone.utc)

    if db is None:
        return TaggingPolicyResponse(
            id=str(uuid.uuid4()),
            project_id=payload.project_id,
            tenant_id=payload.tenant_id,
            name=payload.name,
            required_tags=[t.model_dump() for t in payload.required_tags],
            created_at=now,
            updated_at=now,
        )

    policy = TaggingPolicy(
        project_id=payload.project_id,
        tenant_id=payload.tenant_id,
        name=payload.name,
        required_tags=[t.model_dump() for t in payload.required_tags],
    )
    db.add(policy)
    await db.flush()
    await db.refresh(policy)
    return policy


@router.get("/policies", response_model=list[TaggingPolicyResponse])
async def list_policies(
    project_id: str = Query(..., description="Project ID to filter policies"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tagging policies for a project."""
    if db is None:
        return []

    result = await db.execute(
        select(TaggingPolicy)
        .where(TaggingPolicy.project_id == project_id)
        .order_by(TaggingPolicy.created_at.desc())
    )
    return result.scalars().all()


@router.get("/policies/{policy_id}", response_model=TaggingPolicyResponse)
async def get_policy(
    policy_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get policy details."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    result = await db.execute(
        select(TaggingPolicy).where(TaggingPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.put("/policies/{policy_id}", response_model=TaggingPolicyResponse)
async def update_policy(
    policy_id: str,
    payload: TaggingPolicyUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a tagging policy."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    result = await db.execute(
        select(TaggingPolicy).where(TaggingPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")

    if payload.name is not None:
        policy.name = payload.name
    if payload.required_tags is not None:
        policy.required_tags = [t.model_dump() for t in payload.required_tags]

    await db.flush()
    await db.refresh(policy)
    return policy


@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a tagging policy."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    result = await db.execute(
        select(TaggingPolicy).where(TaggingPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")

    await db.delete(policy)
    await db.flush()
    return {"detail": "Policy deleted"}


# ── Scans ────────────────────────────────────────────────────────────────────


@router.post("/scan/{project_id}", response_model=TaggingScanResultResponse)
async def trigger_scan(
    project_id: str,
    subscription_id: str = Query("default", description="Azure subscription ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a tagging compliance scan for a project."""
    from app.services.tagging_monitor import tagging_monitor

    result = await tagging_monitor.scan_tagging_compliance(
        project_id=project_id,
        subscription_id=subscription_id,
        db=db,
    )

    # Convert violations to response format for the no-DB case
    if db is None:
        return TaggingScanResultResponse(
            id=result["id"],
            project_id=result["project_id"],
            policy_id=result.get("policy_id") or "no-policy",
            tenant_id=result.get("tenant_id"),
            total_resources=result["total_resources"],
            compliant_count=result["compliant_count"],
            non_compliant_count=result["non_compliant_count"],
            compliance_percentage=result["compliance_percentage"],
            scan_timestamp=result["scan_timestamp"],
            status=result["status"],
            created_at=datetime.now(timezone.utc),
            violations=[],
        )

    # Reload from DB with violations
    db_result = await db.execute(
        select(TaggingScanResult)
        .options(selectinload(TaggingScanResult.violations))
        .where(TaggingScanResult.id == result["id"])
    )
    scan = db_result.scalar_one_or_none()
    if scan is None:
        # Fallback — return the dict as response
        return TaggingScanResultResponse(
            id=result["id"],
            project_id=result["project_id"],
            policy_id=result.get("policy_id") or "no-policy",
            tenant_id=result.get("tenant_id"),
            total_resources=result["total_resources"],
            compliant_count=result["compliant_count"],
            non_compliant_count=result["non_compliant_count"],
            compliance_percentage=result["compliance_percentage"],
            scan_timestamp=result["scan_timestamp"],
            status=result["status"],
            created_at=datetime.now(timezone.utc),
            violations=[],
        )
    return scan


# ── Results ──────────────────────────────────────────────────────────────────


@router.get("/results", response_model=TaggingScanResultList)
async def list_results(
    project_id: str = Query(None, description="Filter by project ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tagging scan results."""
    if db is None:
        return TaggingScanResultList(scan_results=[], total=0)

    query = select(TaggingScanResult).options(
        selectinload(TaggingScanResult.violations)
    )
    if project_id:
        query = query.where(TaggingScanResult.project_id == project_id)
    query = query.order_by(TaggingScanResult.scan_timestamp.desc())

    result = await db.execute(query)
    scans = result.scalars().all()
    return TaggingScanResultList(scan_results=scans, total=len(scans))


@router.get("/results/{result_id}", response_model=TaggingScanResultResponse)
async def get_result(
    result_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a scan result with its violations."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    result = await db.execute(
        select(TaggingScanResult)
        .options(selectinload(TaggingScanResult.violations))
        .where(TaggingScanResult.id == result_id)
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan result not found")
    return scan


# ── Summary ──────────────────────────────────────────────────────────────────


@router.get("/summary/{project_id}", response_model=TaggingSummary)
async def get_tagging_summary(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tagging compliance summary for a project."""
    if db is None:
        return TaggingSummary(project_id=project_id)

    # Get latest scan result
    scan_result_query = await db.execute(
        select(TaggingScanResult)
        .options(selectinload(TaggingScanResult.violations))
        .where(TaggingScanResult.project_id == project_id)
        .order_by(TaggingScanResult.scan_timestamp.desc())
        .limit(1)
    )
    latest_scan = scan_result_query.scalar_one_or_none()

    if latest_scan is None:
        return TaggingSummary(project_id=project_id)

    # Get policy name
    policy_query = await db.execute(
        select(TaggingPolicy).where(TaggingPolicy.id == latest_scan.policy_id)
    )
    policy = policy_query.scalar_one_or_none()

    # Calculate violations by type
    violations_by_type = {
        "missing_tag": 0,
        "invalid_value": 0,
        "naming_violation": 0,
    }
    resource_violation_counts: dict[str, int] = {}

    for violation in latest_scan.violations:
        vtype = violation.violation_type
        if vtype in violations_by_type:
            violations_by_type[vtype] += 1
        resource_id = violation.resource_id
        resource_violation_counts[resource_id] = (
            resource_violation_counts.get(resource_id, 0) + 1
        )

    # Find worst offending resources
    worst_offenders = sorted(
        resource_violation_counts.items(), key=lambda x: x[1], reverse=True
    )[:5]
    worst_offending_resources = [
        {"resource_id": rid, "violation_count": count}
        for rid, count in worst_offenders
    ]

    return TaggingSummary(
        project_id=project_id,
        compliance_percentage=latest_scan.compliance_percentage,
        total_resources=latest_scan.total_resources,
        compliant_count=latest_scan.compliant_count,
        non_compliant_count=latest_scan.non_compliant_count,
        violations_by_type=violations_by_type,
        worst_offending_resources=worst_offending_resources,
        latest_scan_at=latest_scan.scan_timestamp,
        policy_name=policy.name if policy else None,
    )
