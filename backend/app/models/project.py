"""Project model — represents a landing zone design project."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

PROJECT_STATUSES = [
    "draft",
    "questionnaire_complete",
    "architecture_generated",
    "compliance_scored",
    "bicep_ready",
    "deploying",
    "deployed",
    "failed",
]


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="projects")

    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_by_user: Mapped["User"] = relationship("User", back_populates="projects")

    questionnaire_responses: Mapped[list["QuestionnaireResponse"]] = relationship(
        "QuestionnaireResponse", back_populates="project", cascade="all, delete-orphan"
    )
    architecture: Mapped["Architecture | None"] = relationship(
        "Architecture", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    deployments: Mapped[list["Deployment"]] = relationship(
        "Deployment", back_populates="project", cascade="all, delete-orphan"
    )
