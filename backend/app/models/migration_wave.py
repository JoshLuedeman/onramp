"""Migration wave planning models."""

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

WAVE_STATUSES = ["planned", "in_progress", "completed"]


class MigrationPlan(Base, TimestampMixin):
    """A migration plan contains ordered waves for a project."""

    __tablename__ = "migration_plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), default="Migration Plan")
    strategy: Mapped[str] = mapped_column(String(50), default="complexity_first")
    max_wave_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    waves: Mapped[list["MigrationWave"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="MigrationWave.order",
    )


class MigrationWave(Base, TimestampMixin):
    """A single wave within a migration plan."""

    __tablename__ = "migration_waves"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("migration_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="planned")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan: Mapped["MigrationPlan"] = relationship(back_populates="waves")
    wave_workloads: Mapped[list["WaveWorkload"]] = relationship(
        back_populates="wave",
        cascade="all, delete-orphan",
        order_by="WaveWorkload.position",
    )


class WaveWorkload(Base):
    """Association between a wave and a workload with ordering."""

    __tablename__ = "wave_workloads"
    __table_args__ = (
        UniqueConstraint("workload_id", "plan_id", name="uq_workload_per_plan"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    wave_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("migration_waves.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workload_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workloads.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("migration_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, default=0)

    wave: Mapped["MigrationWave"] = relationship(back_populates="wave_workloads")
