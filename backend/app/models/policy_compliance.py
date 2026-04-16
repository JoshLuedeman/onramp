"""Policy compliance monitoring models — scan results and violations."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class PolicyComplianceResult(Base, TimestampMixin):
    """Aggregated result of a single policy compliance scan."""

    __tablename__ = "policy_compliance_results"
    __table_args__ = (
        Index(
            "ix_policy_compliance_results_project_scan",
            "project_id",
            "scan_timestamp",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )
    scan_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_resources: Mapped[int] = mapped_column(Integer, default=0)
    compliant_count: Mapped[int] = mapped_column(Integer, default=0)
    non_compliant_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="completed"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    violations: Mapped[list["PolicyViolation"]] = relationship(
        "PolicyViolation",
        back_populates="compliance_result",
        cascade="all, delete-orphan",
    )


class PolicyViolation(Base):
    """An individual policy violation detected during a compliance scan."""

    __tablename__ = "policy_violations"
    __table_args__ = (
        Index(
            "ix_policy_violations_result_severity",
            "compliance_result_id",
            "severity",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    compliance_result_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("policy_compliance_results.id"),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    framework_control_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("compliance_controls.id"),
        nullable=True,
    )
    remediation_suggestion: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    compliance_result: Mapped["PolicyComplianceResult"] = relationship(
        "PolicyComplianceResult", back_populates="violations"
    )
