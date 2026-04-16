"""Pydantic schemas for AI quality infrastructure.

Covers prompt versioning, human feedback, and token usage tracking.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FeedbackRating(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


# ---------------------------------------------------------------------------
# AI Feedback
# ---------------------------------------------------------------------------


class AIFeedbackCreate(BaseModel):
    """Schema for submitting feedback on an AI output."""

    feature: str
    output_id: str
    rating: FeedbackRating
    comment: str | None = None


class AIFeedbackResponse(BaseModel):
    """Schema returned when reading feedback records."""

    id: str
    feature: str
    output_id: str
    rating: str
    comment: str | None = None
    prompt_version: str
    user_id: str
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackStatsItem(BaseModel):
    """Per-feature feedback statistics."""

    feature: str
    total: int
    positive: int
    negative: int
    positive_rate: float = 0.0


class FeedbackStatsResponse(BaseModel):
    """Aggregated feedback statistics."""

    stats: list[FeedbackStatsItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Token Usage
# ---------------------------------------------------------------------------


class TokenUsageSummary(BaseModel):
    """Aggregate token usage for a given scope / time range."""

    feature: str | None = None
    total_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_estimate: float = 0.0


class TokenUsageByFeature(BaseModel):
    """Breakdown of token usage grouped by AI feature."""

    summaries: list[TokenUsageSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Prompt Versioning
# ---------------------------------------------------------------------------


class PromptVersionResponse(BaseModel):
    """Schema for prompt version information."""

    id: str
    name: str
    version: int
    template: str
    metadata_json: dict | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptListResponse(BaseModel):
    """List of registered prompt versions."""

    prompts: list[PromptVersionResponse] = Field(default_factory=list)
