"""Architecture version model — tracks version history of generated architectures."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class ArchitectureVersion(Base, TimestampMixin):
    """Immutable snapshot of an architecture at a point in time.

    Each time an architecture is generated, refined, or restored, a new
    version row is appended.  The ``version_number`` auto-increments per
    architecture and the ``architecture_json`` column stores the full
    serialised architecture payload so that any historical state can be
    reconstructed.
    """

    __tablename__ = "architecture_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    architecture_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("architectures.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    architecture_json: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    architecture: Mapped["Architecture"] = relationship(
        "Architecture", backref="versions"
    )
