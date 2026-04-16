"""Pydantic schemas for drift notification rules and summaries."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SeverityThreshold(str, Enum):
    """Minimum drift severity that triggers a notification."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ALL = "all"


# Ordered from most to least severe for threshold comparison
SEVERITY_ORDER: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "all": 0,
}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class DriftNotificationRuleCreate(BaseModel):
    """Request to create a new drift notification rule."""

    project_id: str = Field(..., description="Project this rule applies to")
    tenant_id: str | None = Field(None, description="Optional tenant scope")
    severity_threshold: SeverityThreshold = Field(
        SeverityThreshold.HIGH,
        description="Minimum severity that triggers notification",
    )
    channels: list[str] = Field(
        default_factory=lambda: ["in_app"],
        description="Notification channels (in_app, email, webhook)",
    )
    recipients: list[str] = Field(
        default_factory=list,
        description="Email addresses or webhook URLs",
    )
    enabled: bool = True


class DriftNotificationRuleUpdate(BaseModel):
    """Request to update an existing drift notification rule."""

    severity_threshold: SeverityThreshold | None = None
    channels: list[str] | None = None
    recipients: list[str] | None = None
    enabled: bool | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DriftNotificationRuleResponse(BaseModel):
    """Full drift notification rule with timestamps."""

    id: str
    project_id: str
    tenant_id: str | None = None
    severity_threshold: str
    channels: list[str]
    recipients: list[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DriftNotificationSummary(BaseModel):
    """Summary of notifications sent for a scan."""

    scan_id: str
    total_findings: int = 0
    notified_findings: int = 0
    rules_evaluated: int = 0
    notifications_sent: int = 0
    by_channel: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
