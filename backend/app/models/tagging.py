"""Tagging compliance models — policies, scan results, and violations."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class TaggingPolicy(Base, TimestampMixin):
    """A configurable tagging policy defining required tags and validation rules."""

    __tablename__ = "tagging_policies"
    __table_args__ = (
        Index("ix_tagging_policies_project", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    required_tags: Mapped[list] = mapped_column(JSON, nullable=False)

    scan_results: Mapped[list["TaggingScanResult"]] = relationship(
        "TaggingScanResult", back_populates="policy", cascade="all, delete-orphan"
    )


class TaggingScanResult(Base):
    """Aggregated result of a single tagging compliance scan."""

    __tablename__ = "tagging_scan_results"
    __table_args__ = (
        Index(
            "ix_tagging_scan_results_project_timestamp",
            "project_id",
            "scan_timestamp",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tagging_policies.id"), nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )
    total_resources: Mapped[int] = mapped_column(Integer, default=0)
    compliant_count: Mapped[int] = mapped_column(Integer, default=0)
    non_compliant_count: Mapped[int] = mapped_column(Integer, default=0)
    compliance_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    scan_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="CURRENT_TIMESTAMP", nullable=False
    )

    policy: Mapped["TaggingPolicy"] = relationship(
        "TaggingPolicy", back_populates="scan_results"
    )
    violations: Mapped[list["TaggingViolation"]] = relationship(
        "TaggingViolation", back_populates="scan_result", cascade="all, delete-orphan"
    )


class TaggingViolation(Base):
    """An individual tagging violation found during a scan."""

    __tablename__ = "tagging_violations"
    __table_args__ = (
        Index("ix_tagging_violations_scan_result", "scan_result_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    scan_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tagging_scan_results.id"), nullable=False
    )
    resource_id: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    violation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_name: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="CURRENT_TIMESTAMP", nullable=False
    )

    scan_result: Mapped["TaggingScanResult"] = relationship(
        "TaggingScanResult", back_populates="violations"
    )
