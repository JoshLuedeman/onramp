"""Drift detection models — baselines, events, and scan results."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class DriftBaseline(Base, TimestampMixin):
    """A known-good snapshot of expected resource configuration."""

    __tablename__ = "drift_baselines"
    __table_args__ = (
        Index("ix_drift_baselines_project_status", "project_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    architecture_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baseline_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    captured_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    events: Mapped[list["DriftEvent"]] = relationship(
        "DriftEvent", back_populates="baseline", cascade="all, delete-orphan"
    )
    scan_results: Mapped[list["DriftScanResult"]] = relationship(
        "DriftScanResult", back_populates="baseline", cascade="all, delete-orphan"
    )


class DriftEvent(Base):
    """An individual drift finding detected during a scan."""

    __tablename__ = "drift_events"
    __table_args__ = (
        Index("ix_drift_events_baseline_severity", "baseline_id", "severity"),
        Index("ix_drift_events_resource_detected", "resource_type", "detected_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    baseline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drift_baselines.id"), nullable=False
    )
    scan_result_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("drift_scan_results.id"), nullable=True
    )
    resource_type: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_id: Mapped[str] = mapped_column(Text, nullable=False)
    drift_type: Mapped[str] = mapped_column(String(50), nullable=False)
    expected_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actual_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    baseline: Mapped["DriftBaseline"] = relationship(
        "DriftBaseline", back_populates="events"
    )
    scan_result: Mapped["DriftScanResult | None"] = relationship(
        "DriftScanResult", back_populates="events"
    )


class DriftScanResult(Base):
    """Aggregated result of a single drift scan run."""

    __tablename__ = "drift_scan_results"
    __table_args__ = (
        Index("ix_drift_scan_results_project_started", "project_id", "scan_started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    baseline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drift_baselines.id"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )
    scan_started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scan_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_resources_scanned: Mapped[int] = mapped_column(Integer, default=0)
    drifted_count: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    removed_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    baseline: Mapped["DriftBaseline"] = relationship(
        "DriftBaseline", back_populates="scan_results"
    )
    events: Mapped[list["DriftEvent"]] = relationship(
        "DriftEvent", back_populates="scan_result"
    )
