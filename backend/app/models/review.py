"""Architecture review workflow models — reviews and configuration."""

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class ArchitectureReview(Base, TimestampMixin):
    """A single review action on an architecture."""

    __tablename__ = "architecture_reviews"
    __table_args__ = (
        Index(
            "ix_arch_reviews_arch_created",
            "architecture_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    architecture_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("architectures.id"),
        nullable=False,
    )
    reviewer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # approved | changes_requested | rejected
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    architecture: Mapped["Architecture"] = relationship(
        "Architecture", back_populates="reviews"
    )
    reviewer: Mapped["User"] = relationship("User")


class ReviewConfiguration(Base, TimestampMixin):
    """Per-project review gate configuration."""

    __tablename__ = "review_configurations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        unique=True,
        nullable=False,
    )
    required_approvals: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )

    project: Mapped["Project"] = relationship("Project")
