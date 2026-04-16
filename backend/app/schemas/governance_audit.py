"""Pydantic schemas for the governance audit trail API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────


class GovernanceEventType(str, Enum):
    DRIFT_DETECTED = "drift_detected"
    SCAN_COMPLETED = "scan_completed"
    REMEDIATION_APPLIED = "remediation_applied"
    NOTIFICATION_SENT = "notification_sent"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    POLICY_VIOLATION = "policy_violation"
    COST_ALERT = "cost_alert"


# ── Response schemas ─────────────────────────────────────────────────────────


class GovernanceAuditEntryResponse(BaseModel):
    """Single audit trail entry."""

    id: str
    event_type: str
    resource_type: str | None = None
    resource_id: str | None = None
    actor: str | None = None
    details: dict | None = None
    tenant_id: str | None = None
    project_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GovernanceAuditListResponse(BaseModel):
    """Paginated list of audit entries."""

    entries: list[GovernanceAuditEntryResponse]
    total: int
    page: int
    page_size: int
    has_more: bool = False


# ── Filter schema ────────────────────────────────────────────────────────────


class GovernanceAuditFilter(BaseModel):
    """Filter criteria for audit queries."""

    event_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    actor: str | None = None
    resource_type: str | None = None
    project_id: str | None = None
    tenant_id: str | None = None


# ── Stats ────────────────────────────────────────────────────────────────────


class GovernanceAuditStats(BaseModel):
    """Summary statistics for audit events."""

    total_events: int = 0
    events_by_type: dict[str, int] = Field(default_factory=dict)
    recent_actors: list[str] = Field(default_factory=list)
