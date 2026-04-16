"""Remediation approval workflow models."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class ApprovalRequest(Base, TimestampMixin):
    """A gated approval request between recommendation and execution."""

    __tablename__ = "approval_requests"
    __table_args__ = (
        Index("ix_approval_requests_status_project", "status", "project_id"),
        Index("ix_approval_requests_tenant_status", "tenant_id", "status"),
        Index("ix_approval_requests_expires", "expires_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    reviewer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
