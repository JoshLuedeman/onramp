"""Deployment model — tracks deployments to Azure."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Deployment(Base, TimestampMixin):
    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    target_subscription_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_subscription_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Generated Bicep templates
    bicep_templates: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Azure deployment details
    azure_deployment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    azure_deployment_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Deployment results
    deployed_resources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    project: Mapped["Project"] = relationship("Project", back_populates="deployments")

    initiated_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
