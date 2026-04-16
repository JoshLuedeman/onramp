"""Notification schemas for API request / response validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NotificationSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


# ---------------------------------------------------------------------------
# Notification responses
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    project_id: str | None = None
    user_id: str | None = None
    notification_type: str
    title: str
    message: str
    severity: NotificationSeverity
    channel: NotificationChannel
    status: NotificationStatus
    delivery_metadata: dict | None = None
    created_at: datetime
    delivered_at: datetime | None = None
    read_at: datetime | None = None

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    page: int = 1
    page_size: int = 50


# ---------------------------------------------------------------------------
# Notification preferences
# ---------------------------------------------------------------------------


class NotificationPreferenceCreate(BaseModel):
    notification_type: str = Field(
        ..., description="Notification type pattern, e.g. 'drift_detected' or '*' for all"
    )
    channel: NotificationChannel
    enabled: bool = True
    config: dict | None = None


class NotificationPreferenceResponse(BaseModel):
    id: str
    user_id: str
    tenant_id: str | None = None
    notification_type: str
    channel: NotificationChannel
    enabled: bool
    config: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Utility responses
# ---------------------------------------------------------------------------


class UnreadCountResponse(BaseModel):
    unread_count: int


class TestNotificationRequest(BaseModel):
    title: str = "Test Notification"
    message: str = "This is a test notification from OnRamp."
    severity: NotificationSeverity = NotificationSeverity.INFO
    channel: NotificationChannel = NotificationChannel.IN_APP
