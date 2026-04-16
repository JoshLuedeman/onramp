"""Notification models for multi-channel delivery infrastructure."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class Notification(Base):
    """A notification record dispatched to a user via a specific channel."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_status_created", "user_id", "status", "created_at"),
        Index("ix_notifications_tenant_type", "tenant_id", "notification_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="in_app")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    delivery_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class NotificationPreference(Base, TimestampMixin):
    """Per-user notification routing preferences."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "notification_type", "channel",
            name="uq_user_notif_type_channel",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )

    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
