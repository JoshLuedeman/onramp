"""Conversation schemas for multi-turn AI chat."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


# ── Create / Input schemas ──────────────────────────────────────────


class ConversationCreate(BaseModel):
    project_id: str
    title: str | None = None


class ConversationMessageCreate(BaseModel):
    content: str


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=32_000)


# ── Response schemas ─────────────────────────────────────────────────


class ConversationMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    token_count: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: str
    title: str | None = None
    status: str
    model_name: str
    total_tokens: int
    project_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationWithMessages(ConversationResponse):
    messages: list[ConversationMessageResponse] = Field(default_factory=list)


class SendMessageResponse(BaseModel):
    assistant_message: ConversationMessageResponse
    conversation: ConversationResponse
