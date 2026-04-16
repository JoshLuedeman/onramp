"""Task execution model — tracks background governance task runs."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid

TASK_STATUSES = [
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
]

TASK_TYPES = [
    "drift_detection",
    "policy_compliance",
    "rbac_health",
    "tagging_compliance",
]


class TaskExecution(Base, TimestampMixin):
    """A single execution of a background governance task."""

    __tablename__ = "task_executions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    task_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tenants.id"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    result_summary: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
