"""RBAC health monitoring models — scan results and findings."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class RBACScanResult(Base, TimestampMixin):
    """Aggregated result of a single RBAC health scan."""

    __tablename__ = "rbac_scan_results"
    __table_args__ = (
        Index("ix_rbac_scan_results_project_scan", "project_id", "scan_timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )
    subscription_id: Mapped[str] = mapped_column(String(255), nullable=False)
    health_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    total_assignments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scan_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")

    findings: Mapped[list["RBACFinding"]] = relationship(
        "RBACFinding", back_populates="scan_result", cascade="all, delete-orphan"
    )


class RBACFinding(Base):
    """An individual RBAC finding detected during a health scan."""

    __tablename__ = "rbac_findings"
    __table_args__ = (
        Index("ix_rbac_findings_result_severity", "scan_result_id", "severity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    scan_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rbac_scan_results.id"), nullable=False
    )
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    principal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="CURRENT_TIMESTAMP", nullable=False
    )

    scan_result: Mapped["RBACScanResult"] = relationship(
        "RBACScanResult", back_populates="findings"
    )
