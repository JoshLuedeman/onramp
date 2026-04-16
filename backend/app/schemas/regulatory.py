"""Pydantic models for regulatory gap prediction and framework analysis."""

from enum import Enum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ControlStatus(str, Enum):
    """Status of a compliance control check."""

    satisfied = "satisfied"
    partial = "partial"
    gap = "gap"


# ---------------------------------------------------------------------------
# Core Models
# ---------------------------------------------------------------------------

class PredictedFramework(BaseModel):
    """A regulatory framework predicted to apply to an organization."""

    framework_name: str
    confidence: str = "medium"  # high / medium / low
    reason: str = ""
    applicable_controls: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class ControlGap(BaseModel):
    """Detail for a single control gap within a framework."""

    control_id: str
    control_name: str
    status: ControlStatus
    gap_description: str = ""
    remediation: str = ""

    model_config = {"extra": "allow"}


class FrameworkGapAnalysis(BaseModel):
    """Gap analysis results for a single compliance framework."""

    framework_name: str
    total_controls: int = 0
    satisfied: int = 0
    partial: int = 0
    gaps: int = 0
    gap_details: list[ControlGap] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class Recommendation(BaseModel):
    """A remediation recommendation to close compliance gaps."""

    priority: str = "medium"  # high / medium / low
    description: str = ""
    architecture_changes: str = ""
    frameworks_addressed: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class RegulatoryPredictionRequest(BaseModel):
    """Request body for POST /api/regulatory/predict."""

    industry: str
    geography: str
    data_types: list[str] | None = None
    use_ai: bool = False


class GapAnalysisRequest(BaseModel):
    """Request body for POST /api/regulatory/gaps."""

    architecture: dict
    frameworks: list[str]


class ApplyPoliciesRequest(BaseModel):
    """Request body for POST /api/regulatory/apply-policies."""

    architecture: dict
    frameworks: list[str]


class RegulatoryPredictionResponse(BaseModel):
    """Response body for regulatory prediction endpoints."""

    predicted_frameworks: list[PredictedFramework] = Field(default_factory=list)
    gap_analyses: list[FrameworkGapAnalysis] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)

    model_config = {"extra": "allow"}
