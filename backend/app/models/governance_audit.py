"""Governance audit trail model — append-only event log."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class GovernanceAuditEntry(Base):
    """Immutable record of a governance event.

    Append-only: no UPDATE or DELETE operations are exposed.
    """

    __tablename__ = "governance_audit_entries"
    __table_args__ = (
        Index(
            "ix_gov_audit_event_type_created",
            "event_type",
            "created_at",
        ),
        Index(
            "ix_gov_audit_project_created",
            "project_id",
            "created_at",
        ),
        Index(
            "ix_gov_audit_tenant_created",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_gov_audit_actor",
            "actor",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    resource_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
