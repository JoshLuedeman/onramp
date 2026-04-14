"""Discovery models — track Azure environment discovery scans."""

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class DiscoveryScan(Base, TimestampMixin):
    """A single discovery scan of an Azure subscription."""

    __tablename__ = "discovery_scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=False
    )
    subscription_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    scan_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship("Project")
    tenant: Mapped["Tenant"] = relationship("Tenant")
    resources: Mapped[list["DiscoveredResource"]] = relationship(
        "DiscoveredResource", back_populates="scan", cascade="all, delete-orphan"
    )


class DiscoveredResource(Base, TimestampMixin):
    """A resource, policy, RBAC assignment, or network entity found during discovery."""

    __tablename__ = "discovered_resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("discovery_scans.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_id: Mapped[str] = mapped_column(Text, nullable=False)
    resource_group: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    scan: Mapped["DiscoveryScan"] = relationship(
        "DiscoveryScan", back_populates="resources"
    )
