"""Drift remediation model — tracks remediation actions and audit trail."""

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class DriftRemediation(Base, TimestampMixin):
    """A remediation action applied to a drift event."""

    __tablename__ = "drift_remediations"
    __table_args__ = (
        Index("ix_drift_remediations_finding", "finding_id"),
        Index("ix_drift_remediations_status", "status"),
        Index("ix_drift_remediations_actor_created", "actor", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drift_events.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    finding: Mapped["DriftEvent"] = relationship(  # noqa: F821
        "DriftEvent", foreign_keys=[finding_id]
    )
