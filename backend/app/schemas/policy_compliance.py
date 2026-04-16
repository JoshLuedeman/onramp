"""Pydantic schemas for the policy compliance monitoring API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────


class ViolationSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceScanStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


# ── Violation schemas ────────────────────────────────────────────────────────


class PolicyViolationResponse(BaseModel):
    """Response for a single policy violation."""

    id: str
    compliance_result_id: str
    resource_id: str
    resource_type: str
    policy_name: str
    policy_description: str | None = None
    severity: str
    framework_control_id: str | None = None
    remediation_suggestion: str | None = None
    detected_at: datetime

    model_config = {"from_attributes": True}


# ── Result schemas ───────────────────────────────────────────────────────────


class PolicyComplianceResultResponse(BaseModel):
    """Response for a policy compliance scan result."""

    id: str
    project_id: str
    tenant_id: str | None = None
    scan_timestamp: datetime
    total_resources: int = 0
    compliant_count: int = 0
    non_compliant_count: int = 0
    status: str
    error_message: str | None = None
    violations: list[PolicyViolationResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PolicyComplianceResultList(BaseModel):
    """Paginated list of compliance results."""

    results: list[PolicyComplianceResultResponse]
    total: int


# ── Summary schemas ──────────────────────────────────────────────────────────


class PolicyComplianceSummary(BaseModel):
    """Aggregate policy compliance statistics for a project."""

    project_id: str
    total_scans: int = 0
    latest_scan_at: datetime | None = None
    total_violations: int = 0
    by_severity: dict[str, int] = Field(
        default_factory=lambda: {
            "critical": 0, "high": 0, "medium": 0, "low": 0
        }
    )
    by_framework: dict[str, int] = Field(default_factory=dict)
    compliance_rate: float = Field(
        default=0.0,
        description="Percentage of compliant resources in the latest scan",
    )
