"""Pydantic schemas for the drift detection API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────

class DriftSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DriftType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    POLICY_VIOLATION = "policy_violation"


class DriftStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class ScanStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Baseline schemas ─────────────────────────────────────────────────────────

class DriftBaselineCreate(BaseModel):
    """Request to create a new drift baseline."""

    project_id: str
    architecture_version: int | None = None
    baseline_data: dict = Field(
        ..., description="Snapshot of expected resource configuration"
    )
    captured_by: str | None = None


class DriftBaselineResponse(BaseModel):
    """Response for a drift baseline."""

    id: str
    project_id: str
    architecture_version: int | None = None
    baseline_data: dict
    status: str
    captured_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Event schemas ────────────────────────────────────────────────────────────

class DriftEventResponse(BaseModel):
    """Response for a single drift event."""

    id: str
    baseline_id: str
    scan_result_id: str | None = None
    resource_type: str
    resource_id: str
    drift_type: str
    expected_value: dict | None = None
    actual_value: dict | None = None
    severity: str
    detected_at: datetime
    resolved_at: datetime | None = None
    resolution_type: str | None = None

    model_config = {"from_attributes": True}


# ── Scan result schemas ──────────────────────────────────────────────────────

class DriftScanResultResponse(BaseModel):
    """Response for a drift scan result."""

    id: str
    baseline_id: str
    project_id: str
    tenant_id: str | None = None
    scan_started_at: datetime
    scan_completed_at: datetime | None = None
    total_resources_scanned: int = 0
    drifted_count: int = 0
    new_count: int = 0
    removed_count: int = 0
    status: str
    error_message: str | None = None
    events: list[DriftEventResponse] = []

    model_config = {"from_attributes": True}


class DriftScanResultList(BaseModel):
    """Paginated list of drift scan results."""

    scan_results: list[DriftScanResultResponse]
    total: int


# ── Summary schemas ──────────────────────────────────────────────────────────

class DriftSummary(BaseModel):
    """Aggregate drift statistics for a project."""

    project_id: str
    total_events: int = 0
    unresolved_events: int = 0
    by_severity: dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0}
    )
    by_type: dict[str, int] = Field(
        default_factory=lambda: {
            "added": 0, "removed": 0, "modified": 0, "policy_violation": 0,
        }
    )
    latest_scan_at: datetime | None = None
    active_baseline_id: str | None = None
