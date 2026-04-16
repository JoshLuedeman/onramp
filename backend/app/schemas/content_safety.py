"""Content safety schemas for prompt injection defense and output filtering."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SafetyStrictness(str, Enum):
    """How aggressively the safety system flags content."""

    STRICT = "strict"
    MODERATE = "moderate"
    MINIMAL = "minimal"


# ── Input checking ──────────────────────────────────────────────────


class InputCheckResult(BaseModel):
    """Result of checking user input for prompt injection attempts."""

    safe: bool
    flagged_patterns: list[str] = Field(default_factory=list)
    sanitized_text: str
    risk_level: str = Field(
        default="none",
        description="none | low | medium | high | critical",
    )


class CheckInputRequest(BaseModel):
    """Request body for POST /api/safety/check-input."""

    text: str = Field(..., min_length=1, max_length=32_000)
    strictness: SafetyStrictness = SafetyStrictness.MODERATE


# ── Output checking ─────────────────────────────────────────────────


class OutputCheckResult(BaseModel):
    """Result of checking AI output for harmful content."""

    safe: bool
    flags: list[str] = Field(default_factory=list)
    filtered_text: str | None = None


class CheckOutputRequest(BaseModel):
    """Request body for POST /api/safety/check-output."""

    text: str = Field(..., min_length=1, max_length=64_000)
    feature: str = Field(default="general", description="Feature area: chat, policy, architecture")


# ── Rate limiting ───────────────────────────────────────────────────


class RateLimitStatus(BaseModel):
    """Current rate limit status for a user/tenant."""

    user_calls_remaining: int
    tenant_calls_remaining: int | None = None
    reset_at: datetime


# ── Configuration ───────────────────────────────────────────────────


class ContentSafetyConfig(BaseModel):
    """Configurable safety parameters."""

    strictness: SafetyStrictness = SafetyStrictness.MODERATE
    user_rate_limit: int = Field(default=50, ge=1, le=10_000)
    tenant_rate_limit: int = Field(default=500, ge=1, le=100_000)
