"""Pydantic schemas for the RBAC health monitoring API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────


class RBACFindingType(str, Enum):
    OVER_PERMISSIONED = "over_permissioned"
    STALE_ASSIGNMENT = "stale_assignment"
    CUSTOM_ROLE_PROLIFERATION = "custom_role_proliferation"
    MISSING_PIM = "missing_pim"
    EXPIRING_CREDENTIAL = "expiring_credential"


class RBACSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RBACScanStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Finding schemas ──────────────────────────────────────────────────────────


class RBACFindingResponse(BaseModel):
    """Response for a single RBAC finding."""

    id: str
    scan_result_id: str
    finding_type: str
    severity: str
    principal_id: str
    principal_name: str | None = None
    role_name: str
    scope: str
    description: str
    remediation: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Scan result schemas ──────────────────────────────────────────────────────


class RBACScanResultResponse(BaseModel):
    """Response for an RBAC scan result."""

    id: str
    project_id: str
    tenant_id: str | None = None
    subscription_id: str
    health_score: float
    total_assignments: int = 0
    finding_count: int = 0
    scan_timestamp: datetime
    status: str
    findings: list[RBACFindingResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RBACScanResultList(BaseModel):
    """Paginated list of RBAC scan results."""

    scan_results: list[RBACScanResultResponse]
    total: int


# ── Summary schemas ──────────────────────────────────────────────────────────


class RBACHealthSummary(BaseModel):
    """Aggregate RBAC health statistics for a project."""

    project_id: str
    health_score: float = 100.0
    total_findings: int = 0
    findings_by_type: dict[str, int] = Field(
        default_factory=lambda: {
            "over_permissioned": 0,
            "stale_assignment": 0,
            "custom_role_proliferation": 0,
            "missing_pim": 0,
            "expiring_credential": 0,
        }
    )
    findings_by_severity: dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0}
    )
    top_risks: list[RBACFindingResponse] = []
    latest_scan_at: datetime | None = None


# ── Request schemas ──────────────────────────────────────────────────────────


class RBACScanRequest(BaseModel):
    """Request to trigger an RBAC health scan."""

    subscription_id: str
    tenant_id: str | None = None
