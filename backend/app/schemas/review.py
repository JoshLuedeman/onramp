"""Pydantic schemas for architecture review workflow."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────


class ReviewAction(str, Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"


# ── Requests ─────────────────────────────────────────────────────────────


class SubmitForReviewRequest(BaseModel):
    """Request to submit an architecture for review."""

    reviewer_ids: list[str] | None = Field(
        default=None,
        description="Optional list of reviewer user IDs to notify.",
    )


class ReviewActionRequest(BaseModel):
    """Request to perform a review action."""

    action: ReviewAction
    comments: str | None = Field(
        default=None, max_length=5000
    )


class ReviewConfigurationRequest(BaseModel):
    """Request to configure review requirements for a project."""

    required_approvals: int = Field(
        default=1, ge=1, le=10,
        description="Number of approvals required before deployment.",
    )


# ── Responses ────────────────────────────────────────────────────────────


class ReviewResponse(BaseModel):
    """Single review action detail."""

    id: str
    architecture_id: str
    reviewer_id: str
    action: str
    comments: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewHistoryResponse(BaseModel):
    """Full review history for an architecture."""

    reviews: list[ReviewResponse]
    current_status: str
    required_approvals: int
    approvals_received: int


class ReviewStatusResponse(BaseModel):
    """Current review status summary."""

    status: str
    is_locked: bool
    can_deploy: bool
    approvals_needed: int
    approvals_received: int


class ReviewConfigurationResponse(BaseModel):
    """Review configuration for a project."""

    id: str
    project_id: str
    required_approvals: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
