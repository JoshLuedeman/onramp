"""Pydantic schemas for the real-time governance scorecard API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────


class CategoryStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


# ── Category score ───────────────────────────────────────────────────────────


class CategoryScore(BaseModel):
    """Score for a single governance category."""

    name: str
    score: float = Field(ge=0, le=100, description="Category score 0-100")
    status: CategoryStatus
    finding_count: int = 0


# ── Overall scorecard ────────────────────────────────────────────────────────


class GovernanceScoreResponse(BaseModel):
    """Aggregated governance scorecard for a project."""

    overall_score: float = Field(ge=0, le=100, description="Weighted overall score 0-100")
    categories: list[CategoryScore] = []
    executive_summary: str = ""
    last_updated: datetime | None = None


# ── Score trend ──────────────────────────────────────────────────────────────


class ScoreTrendPoint(BaseModel):
    """A single data point in the score trend."""

    timestamp: datetime
    overall_score: float = Field(ge=0, le=100)
    category_scores: dict[str, float] = Field(default_factory=dict)


class ScoreTrendResponse(BaseModel):
    """Historical score trend for a project."""

    project_id: str
    data_points: list[ScoreTrendPoint] = []
