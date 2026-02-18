"""ComplianceResult model — stores compliance scoring results per project."""

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class ComplianceResult(Base, TimestampMixin):
    __tablename__ = "compliance_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    scoring_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    frameworks_evaluated: Mapped[list] = mapped_column(JSON, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="compliance_results")
