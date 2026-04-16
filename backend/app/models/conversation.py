"""Conversation models for multi-turn AI chat state management."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid

CONVERSATION_STATUSES = ["active", "archived", "deleted"]
MESSAGE_ROLES = ["system", "user", "assistant"]


class Conversation(Base, TimestampMixin):
    """Persistent conversation for multi-turn AI chat."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    model_name: Mapped[str] = mapped_column(String(100), default="gpt-4o")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )

    __table_args__ = (
        Index("ix_conversations_project_created", "project_id", "created_at"),
        Index("ix_conversations_user", "user_id"),
    )


class ConversationMessage(Base):
    """A single message in a conversation (system, user, or assistant)."""

    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    __table_args__ = (
        Index("ix_conv_messages_conv_created", "conversation_id", "created_at"),
    )
