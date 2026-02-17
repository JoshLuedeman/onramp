"""Compliance framework models."""

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class ComplianceFramework(Base, TimestampMixin):
    __tablename__ = "compliance_frameworks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    short_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    controls: Mapped[list["ComplianceControl"]] = relationship(
        "ComplianceControl", back_populates="framework", cascade="all, delete-orphan"
    )


class ComplianceControl(Base, TimestampMixin):
    __tablename__ = "compliance_controls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[str] = mapped_column(String(50), default="medium")

    # Azure Policy mapping
    azure_policy_definitions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    framework_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("compliance_frameworks.id"), nullable=False
    )
    framework: Mapped["ComplianceFramework"] = relationship(
        "ComplianceFramework", back_populates="controls"
    )
