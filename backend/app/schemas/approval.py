"""Pydantic schemas for the remediation approval workflow API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequestType(str, Enum):
    DRIFT_REMEDIATION = "drift_remediation"
    POLICY_EXCEPTION = "policy_exception"
    COST_OVERRIDE = "cost_override"


# ── Request schemas ──────────────────────────────────────────────────────────


class ApprovalRequestCreate(BaseModel):
    """Create a new approval request."""

    request_type: ApprovalRequestType
    resource_id: str = Field(..., description="ID of the resource needing approval")
    details: dict = Field(default_factory=dict, description="Context about the request")
    project_id: str | None = None


class ApprovalDecision(BaseModel):
    """Approve or reject an approval request."""

    status: ApprovalStatus = Field(
        ..., description="Must be 'approved' or 'rejected'"
    )
    reason: str = Field(default="", description="Reason for the decision")


# ── Response schemas ─────────────────────────────────────────────────────────


class ApprovalRequestResponse(BaseModel):
    """Full approval request with timestamps."""

    id: str
    request_type: str
    resource_id: str
    requested_by: str
    requested_at: datetime
    status: str
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    review_reason: str | None = None
    details: dict | None = None
    tenant_id: str | None = None
    project_id: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApprovalRequestListResponse(BaseModel):
    """Paginated list of approval requests."""

    requests: list[ApprovalRequestResponse]
    total: int


class PendingCountResponse(BaseModel):
    """Count of pending approval requests."""

    pending_count: int
