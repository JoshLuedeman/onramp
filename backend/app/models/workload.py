"""Workload model — represents a workload to be migrated."""

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid

WORKLOAD_TYPES = ["vm", "database", "web-app", "container", "other"]

SOURCE_PLATFORMS = ["vmware", "hyperv", "physical", "aws", "gcp", "other"]

CRITICALITY_LEVELS = [
    "mission-critical",
    "business-critical",
    "standard",
    "dev-test",
]

MIGRATION_STRATEGIES = [
    "rehost",
    "refactor",
    "rearchitect",
    "rebuild",
    "replace",
    "unknown",
]


class Workload(Base, TimestampMixin):
    __tablename__ = "workloads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="other")
    source_platform: Mapped[str] = mapped_column(String(50), default="other")

    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    storage_gb: Mapped[float | None] = mapped_column(Float, nullable=True)

    os_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    criticality: Mapped[str] = mapped_column(String(50), default="standard")

    # JSON arrays
    compliance_requirements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    dependencies: Mapped[list | None] = mapped_column(JSON, nullable=True)

    migration_strategy: Mapped[str] = mapped_column(String(50), default="unknown")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Mapping fields — populated by workload mapper service
    target_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mapping_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
