"""Pydantic schemas for the AI evaluation framework.

Covers golden test definitions, output scoring, evaluation reports,
and regression detection results.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum  # noqa: TC003

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EvalFeature(str, Enum):
    """AI features that can be evaluated."""

    architecture = "architecture"
    policy = "policy"
    sizing = "sizing"
    security = "security"
    regulatory = "regulatory"


# ---------------------------------------------------------------------------
# Golden Test
# ---------------------------------------------------------------------------


class GoldenTest(BaseModel):
    """A single golden-test case: known input → expected output patterns."""

    name: str
    input_data: dict = Field(default_factory=dict)
    expected_patterns: dict = Field(default_factory=dict)
    feature: str


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


class OutputScore(BaseModel):
    """Multi-dimensional score for a single AI output."""

    structural: float = 0.0
    azure_validity: float = 0.0
    completeness: float = 0.0
    security: float = 0.0
    overall: float = 0.0


class IndividualResult(BaseModel):
    """Result of evaluating one golden test case."""

    test_name: str
    passed: bool
    score: OutputScore = Field(default_factory=OutputScore)
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class EvaluationReport(BaseModel):
    """Evaluation report for a single AI feature."""

    feature: str
    test_count: int = 0
    passed: int = 0
    failed: int = 0
    avg_score: OutputScore = Field(default_factory=OutputScore)
    individual_results: list[IndividualResult] = Field(default_factory=list)


class FullEvaluationReport(BaseModel):
    """Aggregate evaluation across all AI features."""

    features: dict[str, EvaluationReport] = Field(default_factory=dict)
    overall_score: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


class RegressionItem(BaseModel):
    """A single metric regression for a feature."""

    feature: str
    metric: str
    baseline: float
    current: float
    delta: float


class RegressionResult(BaseModel):
    """Result of comparing current scores against a baseline."""

    has_regression: bool = False
    regressions: list[RegressionItem] = Field(default_factory=list)
