"""Template model — marketplace templates for reusable architectures."""

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class Template(Base, TimestampMixin):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    architecture_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    author_tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(
        String(20), default="private", nullable=False
    )
    download_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    rating_up: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    rating_down: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    __table_args__ = (
        {"comment": "Marketplace templates for reusable architectures"},
    )
