"""Pydantic schemas for architecture comparison mode.

Defines the request / response models used by the ``/api/architecture/compare``
endpoints.  Each variant is a full architecture annotated with cost and
complexity metadata so the frontend can render a side-by-side view.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ArchitectureVariant(BaseModel):
    """A single architecture variant with comparison metadata."""

    name: str
    description: str
    architecture: dict = Field(default_factory=dict)
    resource_count: int = 0
    estimated_monthly_cost_min: float = 0.0
    estimated_monthly_cost_max: float = 0.0
    complexity: Literal["simple", "moderate", "complex"] = "moderate"
    compliance_scores: dict[str, float] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class ComparisonResult(BaseModel):
    """Result of comparing multiple architecture variants."""

    variants: list[ArchitectureVariant] = Field(default_factory=list)
    tradeoff_analysis: str = ""
    recommended_index: int = 1  # default to balanced (index 1)

    model_config = {"extra": "allow"}


class CompareRequest(BaseModel):
    """Request body for the compare endpoint."""

    answers: dict[str, str | list[str]]
    options: dict | None = None
