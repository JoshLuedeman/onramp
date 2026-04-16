"""Pydantic schemas for drift remediation actions and audit logging."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────


class RemediationAction(str, Enum):
    ACCEPT = "accept"
    REVERT = "revert"
    SUPPRESS = "suppress"


class RemediationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Request schemas ──────────────────────────────────────────────────────────


class RemediationRequest(BaseModel):
    """Request to remediate a single drift finding."""

    finding_id: str = Field(..., description="ID of the drift event to remediate")
    action: RemediationAction
    justification: str | None = Field(
        None, description="Reason for the remediation action"
    )
    expiration_days: int | None = Field(
        None,
        description="Suppression expiration in days (30, 60, 90, or None for permanent)",
    )


class BatchRemediationRequest(BaseModel):
    """Request to remediate multiple drift findings at once."""

    finding_ids: list[str] = Field(
        ..., min_length=1, description="IDs of drift events to remediate"
    )
    action: RemediationAction
    justification: str | None = Field(
        None, description="Reason for the batch remediation"
    )
    expiration_days: int | None = Field(
        None,
        description="Suppression expiration in days (30, 60, 90, or None for permanent)",
    )


# ── Response schemas ─────────────────────────────────────────────────────────


class RemediationResponse(BaseModel):
    """Response for a remediation action."""

    id: str
    finding_id: str
    action: str
    status: str
    result_details: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchRemediationResponse(BaseModel):
    """Response for a batch remediation action."""

    results: list[RemediationResponse]
    total: int
    succeeded: int
    failed: int


# ── Audit schemas ────────────────────────────────────────────────────────────


class RemediationAuditEntry(BaseModel):
    """Audit log entry for a remediation action."""

    id: str
    actor: str
    action: str
    finding_id: str
    justification: str | None = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class RemediationAuditLog(BaseModel):
    """Paginated list of remediation audit entries."""

    entries: list[RemediationAuditEntry]
    total: int
