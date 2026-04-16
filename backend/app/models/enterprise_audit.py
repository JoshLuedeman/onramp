"""Enterprise audit event model — immutable, append-only event log."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class EnterpriseAuditEvent(Base):
    """Immutable record of an enterprise-wide auditable event.

    This model is **append-only**: no UPDATE or DELETE operations are
    exposed anywhere in the application.
    """

    __tablename__ = "enterprise_audit_events"
    __table_args__ = (
        Index(
            "ix_ent_audit_tenant_ts",
            "tenant_id",
            "timestamp",
        ),
        Index(
            "ix_ent_audit_actor_ts",
            "actor_id",
            "timestamp",
        ),
        Index(
            "ix_ent_audit_resource",
            "resource_type",
            "resource_id",
        ),
        Index(
            "ix_ent_audit_action",
            "action",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid,
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True,
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True,
    )
    resource_type: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="create | read | update | delete",
    )
    details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
