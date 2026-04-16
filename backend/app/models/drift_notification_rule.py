"""Drift notification rule model — controls when and how drift alerts are sent."""

from sqlalchemy import JSON, Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class DriftNotificationRule(Base, TimestampMixin):
    """A rule that maps drift severity thresholds to notification channels."""

    __tablename__ = "drift_notification_rules"
    __table_args__ = (
        Index("ix_drift_notif_rules_project", "project_id"),
        Index("ix_drift_notif_rules_tenant", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )

    severity_threshold: Mapped[str] = mapped_column(
        String(20), nullable=False, default="high"
    )
    channels: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recipients: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
