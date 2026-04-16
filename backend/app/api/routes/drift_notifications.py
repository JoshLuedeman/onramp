"""Drift notification rule management and notification trigger routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.drift_notification import (
    DriftNotificationRuleCreate,
    DriftNotificationRuleResponse,
    DriftNotificationRuleUpdate,
    DriftNotificationSummary,
)

router = APIRouter(
    prefix="/api/governance/drift",
    tags=["governance-drift-notifications"],
)


# ---------------------------------------------------------------------------
# CRUD — notification rules
# ---------------------------------------------------------------------------


@router.post(
    "/notification-rules",
    response_model=DriftNotificationRuleResponse,
    status_code=201,
)
async def create_notification_rule(
    payload: DriftNotificationRuleCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new drift notification rule for a project."""
    now = datetime.now(timezone.utc)

    if db is None:
        return DriftNotificationRuleResponse(
            id=str(uuid.uuid4()),
            project_id=payload.project_id,
            tenant_id=payload.tenant_id,
            severity_threshold=payload.severity_threshold.value,
            channels=payload.channels,
            recipients=payload.recipients,
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )

    from app.models.drift_notification_rule import DriftNotificationRule

    rule = DriftNotificationRule(
        project_id=payload.project_id,
        tenant_id=payload.tenant_id,
        severity_threshold=payload.severity_threshold.value,
        channels=payload.channels,
        recipients=payload.recipients,
        enabled=payload.enabled,
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.get(
    "/notification-rules",
    response_model=list[DriftNotificationRuleResponse],
)
async def list_notification_rules(
    project_id: str = Query(None, description="Filter by project ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List drift notification rules, optionally filtered by project."""
    if db is None:
        return []

    from app.models.drift_notification_rule import DriftNotificationRule

    query = select(DriftNotificationRule)
    if project_id:
        query = query.where(DriftNotificationRule.project_id == project_id)
    query = query.order_by(DriftNotificationRule.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/notification-rules/{rule_id}",
    response_model=DriftNotificationRuleResponse,
)
async def get_notification_rule(
    rule_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single drift notification rule by ID."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    from app.models.drift_notification_rule import DriftNotificationRule

    result = await db.execute(
        select(DriftNotificationRule).where(DriftNotificationRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Notification rule not found")
    return rule


@router.put(
    "/notification-rules/{rule_id}",
    response_model=DriftNotificationRuleResponse,
)
async def update_notification_rule(
    rule_id: str,
    payload: DriftNotificationRuleUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing drift notification rule."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    from app.models.drift_notification_rule import DriftNotificationRule

    result = await db.execute(
        select(DriftNotificationRule).where(DriftNotificationRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Notification rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "severity_threshold" in update_data and update_data["severity_threshold"] is not None:
        update_data["severity_threshold"] = update_data["severity_threshold"].value

    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(rule)
    return rule


@router.delete("/notification-rules/{rule_id}", status_code=204)
async def delete_notification_rule(
    rule_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a drift notification rule."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    from app.models.drift_notification_rule import DriftNotificationRule

    result = await db.execute(
        select(DriftNotificationRule).where(DriftNotificationRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Notification rule not found")

    await db.delete(rule)
    await db.flush()
    return None


# ---------------------------------------------------------------------------
# Notification trigger & history
# ---------------------------------------------------------------------------


@router.post(
    "/notify/{scan_id}",
    response_model=DriftNotificationSummary,
)
async def trigger_notifications_for_scan(
    scan_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger drift notifications for a completed scan's results."""
    from app.services.drift_notification import drift_notification_service

    # Load scan result and its events
    scan_result, findings = await _load_scan_data(db, scan_id)

    summary = await drift_notification_service.process_scan_results(
        db=db,
        scan_result=scan_result,
        findings=findings,
    )
    return summary


@router.get(
    "/notification-history",
    response_model=list[dict],
)
async def get_notification_history(
    project_id: str = Query(None, description="Filter by project ID"),
    scan_id: str = Query(None, description="Filter by scan ID"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """View drift notification history from the notifications table."""
    if db is None:
        return []

    from app.models.notification import Notification

    query = select(Notification).where(
        Notification.notification_type == "drift_detected"
    )
    if project_id:
        query = query.where(Notification.project_id == project_id)
    if scan_id:
        # Scan ID stored in delivery_metadata is hard to filter in SQL;
        # filter by message content containing the scan_id as a fallback.
        query = query.where(Notification.message.contains(scan_id))

    query = query.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "severity": n.severity,
            "channel": n.channel,
            "status": n.status,
            "project_id": n.project_id,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "delivered_at": n.delivered_at.isoformat() if n.delivered_at else None,
        }
        for n in notifications
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _load_scan_data(
    db: AsyncSession | None, scan_id: str
) -> tuple[dict, list[dict]]:
    """Load scan result and events, returning dicts for the service layer."""
    if db is None:
        # Dev-mode fallback: return stub data
        return (
            {"id": scan_id, "project_id": "dev-project", "tenant_id": None},
            [],
        )

    from sqlalchemy.orm import selectinload

    from app.models.drift import DriftScanResult

    result = await db.execute(
        select(DriftScanResult)
        .options(selectinload(DriftScanResult.events))
        .where(DriftScanResult.id == scan_id)
    )
    scan = result.scalar_one_or_none()

    if scan is None:
        raise HTTPException(status_code=404, detail="Scan result not found")

    scan_dict = {
        "id": scan.id,
        "project_id": scan.project_id,
        "tenant_id": scan.tenant_id,
        "status": scan.status,
        "drifted_count": scan.drifted_count,
    }

    findings = [
        {
            "id": e.id,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "drift_type": e.drift_type,
            "severity": e.severity,
            "expected_value": e.expected_value,
            "actual_value": e.actual_value,
        }
        for e in (scan.events or [])
    ]

    return scan_dict, findings
