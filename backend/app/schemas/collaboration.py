"""Collaboration schemas — project members, comments, and activity feed."""

from datetime import datetime

from pydantic import BaseModel, Field

# ── Project Members ──────────────────────────────────────────────────────


class ProjectMemberCreate(BaseModel):
    email: str
    role: str = Field(
        default="viewer", pattern="^(owner|editor|viewer)$"
    )


class ProjectMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str = ""
    display_name: str = ""
    role: str
    invited_at: datetime
    accepted_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProjectMemberListResponse(BaseModel):
    members: list[ProjectMemberResponse]
    total: int


# ── Comments ─────────────────────────────────────────────────────────────


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    component_ref: str | None = None


class CommentResponse(BaseModel):
    id: str
    content: str
    component_ref: str | None = None
    user_id: str
    display_name: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]
    total: int


# ── Activity Feed ────────────────────────────────────────────────────────


class ActivityEntry(BaseModel):
    type: str
    user_id: str
    description: str
    timestamp: datetime


class ActivityFeedResponse(BaseModel):
    activities: list[ActivityEntry]
