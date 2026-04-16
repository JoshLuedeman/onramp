"""Pydantic schemas for the tagging compliance API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────


class ViolationType(str, Enum):
    MISSING_TAG = "missing_tag"
    INVALID_VALUE = "invalid_value"
    NAMING_VIOLATION = "naming_violation"


# ── Tag rule schemas ─────────────────────────────────────────────────────────


class TagRuleSchema(BaseModel):
    """A single tag rule within a tagging policy."""

    name: str = Field(..., description="Tag name (e.g., 'Environment')")
    required: bool = True
    allowed_values: list[str] | None = Field(
        None, description="List of allowed values (e.g., ['dev', 'staging', 'prod'])"
    )
    pattern: str | None = Field(
        None, description="Regex pattern for tag value validation"
    )


# ── Policy schemas ───────────────────────────────────────────────────────────


class TaggingPolicyCreate(BaseModel):
    """Request to create a tagging policy."""

    project_id: str
    tenant_id: str | None = None
    name: str
    required_tags: list[TagRuleSchema]


class TaggingPolicyUpdate(BaseModel):
    """Request to update a tagging policy."""

    name: str | None = None
    required_tags: list[TagRuleSchema] | None = None


class TaggingPolicyResponse(BaseModel):
    """Response for a tagging policy."""

    id: str
    project_id: str
    tenant_id: str | None = None
    name: str
    required_tags: list[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Violation schemas ────────────────────────────────────────────────────────


class TaggingViolationResponse(BaseModel):
    """Response for a single tagging violation."""

    id: str
    scan_result_id: str
    resource_id: str
    resource_type: str
    resource_name: str | None = None
    violation_type: str
    tag_name: str
    expected_value: str | None = None
    actual_value: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Scan result schemas ──────────────────────────────────────────────────────


class TaggingScanResultResponse(BaseModel):
    """Response for a tagging scan result."""

    id: str
    project_id: str
    policy_id: str
    tenant_id: str | None = None
    total_resources: int = 0
    compliant_count: int = 0
    non_compliant_count: int = 0
    compliance_percentage: float = 0.0
    scan_timestamp: datetime
    status: str
    created_at: datetime
    violations: list[TaggingViolationResponse] = []

    model_config = {"from_attributes": True}


class TaggingScanResultList(BaseModel):
    """Paginated list of tagging scan results."""

    scan_results: list[TaggingScanResultResponse]
    total: int


# ── Summary schemas ──────────────────────────────────────────────────────────


class TaggingSummary(BaseModel):
    """Aggregate tagging compliance statistics for a project."""

    project_id: str
    compliance_percentage: float = 0.0
    total_resources: int = 0
    compliant_count: int = 0
    non_compliant_count: int = 0
    violations_by_type: dict[str, int] = Field(
        default_factory=lambda: {
            "missing_tag": 0,
            "invalid_value": 0,
            "naming_violation": 0,
        }
    )
    worst_offending_resources: list[dict] = Field(default_factory=list)
    latest_scan_at: datetime | None = None
    policy_name: str | None = None
