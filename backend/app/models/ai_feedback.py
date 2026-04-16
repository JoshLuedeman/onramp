"""AI feedback model for capturing human feedback on AI outputs."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class AIFeedback(Base):
    """Captures human feedback (thumbs up/down) on AI-generated outputs."""

    __tablename__ = "ai_feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    feature: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    output_id: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
