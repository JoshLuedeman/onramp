"""Drift detection API routes — baselines, events, and scan results."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db.session import get_db
from app.models.drift import DriftBaseline, DriftEvent, DriftScanResult
from app.schemas.drift import (
    DriftBaselineCreate,
    DriftBaselineResponse,
    DriftEventResponse,
    DriftScanResultList,
    DriftScanResultResponse,
    DriftSummary,
)
from app.schemas.drift_remediation import (
    BatchRemediationRequest,
    BatchRemediationResponse,
    RemediationAuditLog,
    RemediationRequest,
    RemediationResponse,
)

router = APIRouter(prefix="/api/governance/drift", tags=["drift"])


# ── Baselines ────────────────────────────────────────────────────────────────


@router.post("/baselines", response_model=DriftBaselineResponse, status_code=201)
async def create_baseline(
    payload: DriftBaselineCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new drift baseline from architecture data."""
    now = datetime.now(timezone.utc)

    if db is None:
        return DriftBaselineResponse(
            id=str(uuid.uuid4()),
            project_id=payload.project_id,
            architecture_version=payload.architecture_version,
            baseline_data=payload.baseline_data,
            status="active",
            captured_by=payload.captured_by,
            created_at=now,
            updated_at=now,
        )

    baseline = DriftBaseline(
        project_id=payload.project_id,
        architecture_version=payload.architecture_version,
        baseline_data=payload.baseline_data,
        status="active",
        captured_by=payload.captured_by,
    )
    db.add(baseline)
    await db.flush()
    await db.refresh(baseline)
    return baseline


@router.get("/baselines", response_model=list[DriftBaselineResponse])
async def list_baselines(
    project_id: str = Query(..., description="Project ID to filter baselines"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List baselines for a project."""
    if db is None:
        return []

    result = await db.execute(
        select(DriftBaseline)
        .where(DriftBaseline.project_id == project_id)
        .order_by(DriftBaseline.created_at.desc())
    )
    return result.scalars().all()


@router.get("/baselines/{baseline_id}", response_model=DriftBaselineResponse)
async def get_baseline(
    baseline_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get baseline details."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    result = await db.execute(
        select(DriftBaseline).where(DriftBaseline.id == baseline_id)
    )
    baseline = result.scalar_one_or_none()
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return baseline


@router.post(
    "/baselines/{baseline_id}/supersede", response_model=DriftBaselineResponse
)
async def supersede_baseline(
    baseline_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a baseline as superseded."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    result = await db.execute(
        select(DriftBaseline).where(DriftBaseline.id == baseline_id)
    )
    baseline = result.scalar_one_or_none()
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")

    baseline.status = "superseded"
    await db.flush()
    await db.refresh(baseline)
    return baseline


# ── Scan results ─────────────────────────────────────────────────────────────


@router.get("/scan-results", response_model=DriftScanResultList)
async def list_scan_results(
    project_id: str = Query(None, description="Filter by project ID"),
    status: str = Query(None, description="Filter by scan status"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List scan results, filterable by project_id and status."""
    if db is None:
        return DriftScanResultList(scan_results=[], total=0)

    query = select(DriftScanResult).options(selectinload(DriftScanResult.events))

    if project_id:
        query = query.where(DriftScanResult.project_id == project_id)
    if status:
        query = query.where(DriftScanResult.status == status)

    query = query.order_by(DriftScanResult.scan_started_at.desc())
    result = await db.execute(query)
    scans = result.scalars().all()
    return DriftScanResultList(scan_results=scans, total=len(scans))


@router.get("/scan-results/{scan_id}", response_model=DriftScanResultResponse)
async def get_scan_result(
    scan_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a scan result with its events."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    result = await db.execute(
        select(DriftScanResult)
        .options(selectinload(DriftScanResult.events))
        .where(DriftScanResult.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan result not found")
    return scan


# ── Events ───────────────────────────────────────────────────────────────────


@router.get("/events", response_model=list[DriftEventResponse])
async def list_events(
    baseline_id: str = Query(None, description="Filter by baseline ID"),
    severity: str = Query(None, description="Filter by severity"),
    drift_type: str = Query(None, description="Filter by drift type"),
    resolved: bool = Query(None, description="Filter by resolved status"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List drift events with optional filters."""
    if db is None:
        return []

    query = select(DriftEvent)

    if baseline_id:
        query = query.where(DriftEvent.baseline_id == baseline_id)
    if severity:
        query = query.where(DriftEvent.severity == severity)
    if drift_type:
        query = query.where(DriftEvent.drift_type == drift_type)
    if resolved is not None:
        if resolved:
            query = query.where(DriftEvent.resolved_at.isnot(None))
        else:
            query = query.where(DriftEvent.resolved_at.is_(None))

    query = query.order_by(DriftEvent.detected_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


# ── Summary ──────────────────────────────────────────────────────────────────


@router.get("/summary/{project_id}", response_model=DriftSummary)
async def get_drift_summary(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get drift summary stats for a project."""
    if db is None:
        return DriftSummary(project_id=project_id)

    # Find the active baseline for this project
    baseline_result = await db.execute(
        select(DriftBaseline).where(
            DriftBaseline.project_id == project_id,
            DriftBaseline.status == "active",
        )
    )
    active_baseline = baseline_result.scalar_one_or_none()

    if active_baseline is None:
        return DriftSummary(project_id=project_id)

    # Get all events for this baseline
    events_result = await db.execute(
        select(DriftEvent).where(DriftEvent.baseline_id == active_baseline.id)
    )
    events = events_result.scalars().all()

    # Calculate by_severity and by_type counts
    by_severity: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    by_type: dict[str, int] = {
        "added": 0, "removed": 0, "modified": 0, "policy_violation": 0,
    }
    unresolved = 0

    for event in events:
        if event.severity in by_severity:
            by_severity[event.severity] += 1
        if event.drift_type in by_type:
            by_type[event.drift_type] += 1
        if event.resolved_at is None:
            unresolved += 1

    # Get latest scan timestamp
    scan_result = await db.execute(
        select(func.max(DriftScanResult.scan_started_at)).where(
            DriftScanResult.project_id == project_id
        )
    )
    latest_scan_at = scan_result.scalar_one_or_none()

    return DriftSummary(
        project_id=project_id,
        total_events=len(events),
        unresolved_events=unresolved,
        by_severity=by_severity,
        by_type=by_type,
        latest_scan_at=latest_scan_at,
        active_baseline_id=active_baseline.id,
    )


# ── Scan trigger ─────────────────────────────────────────────────────────────


@router.post(
    "/scan/{project_id}",
    response_model=DriftScanResultResponse,
    status_code=202,
)
async def trigger_drift_scan(
    project_id: str,
    background_tasks: BackgroundTasks,
    tenant_id: str = Query(None, description="Optional tenant ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a drift scan for a project.

    Creates a DriftScanResult immediately (status=running) and runs
    the full scan asynchronously in the background.
    Returns 202 Accepted with the scan result stub.
    """
    from app.services.drift_scanner import drift_scanner

    now = datetime.now(timezone.utc)
    scan_id = str(uuid.uuid4())
    baseline_id = str(uuid.uuid4())

    # If DB is available, look up the active baseline
    if db is not None:
        result = await db.execute(
            select(DriftBaseline).where(
                DriftBaseline.project_id == project_id,
                DriftBaseline.status == "active",
            )
        )
        active_baseline = result.scalar_one_or_none()
        if active_baseline is not None:
            baseline_id = active_baseline.id

        # Persist initial scan result
        scan_row = DriftScanResult(
            id=scan_id,
            baseline_id=baseline_id,
            project_id=project_id,
            tenant_id=tenant_id,
            scan_started_at=now,
            status="running",
        )
        db.add(scan_row)
        await db.flush()
        await db.refresh(scan_row)

    # Schedule the background scan
    async def _run_scan():
        await drift_scanner.scan_project(
            project_id=project_id,
            tenant_id=tenant_id,
        )

    background_tasks.add_task(_run_scan)

    # Return the initial scan result (status=running)
    return DriftScanResultResponse(
        id=scan_id,
        baseline_id=baseline_id,
        project_id=project_id,
        tenant_id=tenant_id,
        scan_started_at=now,
        status="running",
        total_resources_scanned=0,
        drifted_count=0,
        new_count=0,
        removed_count=0,
        events=[],
    )


# ── Remediation ──────────────────────────────────────────────────────────────


@router.post("/remediate", response_model=RemediationResponse)
async def remediate_finding(
    payload: RemediationRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remediate a single drift finding (accept, revert, or suppress)."""
    from app.services.drift_remediator import drift_remediator

    return await drift_remediator.remediate_finding(
        finding_id=payload.finding_id,
        action=payload.action.value,
        actor=user.get("name", user.get("sub", "unknown")),
        justification=payload.justification,
        expiration_days=payload.expiration_days,
        db=db,
    )


@router.post("/remediate/batch", response_model=BatchRemediationResponse)
async def remediate_batch(
    payload: BatchRemediationRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remediate multiple drift findings with the same action."""
    from app.services.drift_remediator import drift_remediator

    return await drift_remediator.remediate_batch(
        finding_ids=payload.finding_ids,
        action=payload.action.value,
        actor=user.get("name", user.get("sub", "unknown")),
        justification=payload.justification,
        expiration_days=payload.expiration_days,
        db=db,
    )


@router.get("/remediation/history", response_model=RemediationAuditLog)
async def get_remediation_history(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the remediation audit log."""
    from app.services.drift_remediator import drift_remediator

    return await drift_remediator.get_remediation_history(db=db)


@router.get("/remediation/{remediation_id}", response_model=RemediationResponse)
async def get_remediation(
    remediation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the status of a remediation action."""
    from app.services.drift_remediator import drift_remediator

    result = await drift_remediator.get_remediation(remediation_id, db=db)
    if result is None:
        raise HTTPException(status_code=404, detail="Remediation not found")
    return result

