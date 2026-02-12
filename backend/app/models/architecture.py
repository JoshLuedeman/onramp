"""Architecture model — stores generated landing zone designs."""

from sqlalchemy import String, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Architecture(Base, TimestampMixin):
    __tablename__ = "architectures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="draft")

    # The full architecture definition as structured JSON
    architecture_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Management group hierarchy
    management_groups: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Subscription layout
    subscriptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Network topology
    network_topology: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Policy assignments
    policies: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Compliance frameworks applied
    compliance_frameworks: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # AI reasoning trace
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), unique=True, nullable=False
    )
    project: Mapped["Project"] = relationship("Project", back_populates="architecture")
