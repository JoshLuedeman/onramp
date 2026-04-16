"""Cost management models — snapshots, budgets, and anomalies."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

ANOMALY_TYPES = ["spike", "unusual_service", "new_resource"]
ANOMALY_SEVERITIES = ["critical", "high", "medium", "low"]


class CostSnapshot(Base, TimestampMixin):
    """A point-in-time capture of cost data for a subscription."""

    __tablename__ = "cost_snapshots"
    __table_args__ = (
        Index("ix_cost_snapshots_project_created", "project_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )
    subscription_id: Mapped[str] = mapped_column(String(255), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    cost_by_service: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cost_by_resource_group: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    anomalies: Mapped[list["CostAnomaly"]] = relationship(
        "CostAnomaly", back_populates="snapshot", cascade="all, delete-orphan"
    )


class CostBudget(Base, TimestampMixin):
    """A budget definition for cost tracking and alerting."""

    __tablename__ = "cost_budgets"
    __table_args__ = (
        Index("ix_cost_budgets_project_created", "project_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )
    budget_name: Mapped[str] = mapped_column(String(255), nullable=False)
    budget_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_spend: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    threshold_percentage: Mapped[float] = mapped_column(
        Float, nullable=False, default=80.0
    )
    alert_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CostAnomaly(Base):
    """A detected cost anomaly linked to a snapshot."""

    __tablename__ = "cost_anomalies"
    __table_args__ = (
        Index("ix_cost_anomalies_project_detected", "project_id", "detected_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    cost_snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cost_snapshots.id"), nullable=False
    )
    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    previous_cost: Mapped[float] = mapped_column(Float, nullable=False)
    current_cost: Mapped[float] = mapped_column(Float, nullable=False)
    percentage_change: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    snapshot: Mapped["CostSnapshot"] = relationship(
        "CostSnapshot", back_populates="anomalies"
    )
