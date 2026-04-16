"""Event stream schemas for real-time SSE updates."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Standard event types for real-time updates."""

    GOVERNANCE_SCORE_UPDATED = "governance_score_updated"
    DRIFT_DETECTED = "drift_detected"
    DRIFT_RESOLVED = "drift_resolved"
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    COMPLIANCE_CHANGED = "compliance_changed"
    NOTIFICATION_NEW = "notification_new"
    COST_ALERT = "cost_alert"


class EventStreamEvent(BaseModel):
    """Schema for an event delivered via SSE."""

    event_type: str
    data: dict = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    project_id: str | None = None
    tenant_id: str | None = None
