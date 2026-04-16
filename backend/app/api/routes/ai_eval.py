"""API routes for the AI evaluation framework.

Provides endpoints to:
- Run the full evaluation suite
- Run evaluation for a specific feature
- Get the latest evaluation results
- List available golden tests
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas.ai_eval import (
    EvalFeature,
    EvaluationReport,
    FullEvaluationReport,
)
from app.services.ai_eval.evaluator import ai_evaluator
from app.services.ai_eval.golden_datasets import ALL_GOLDEN_TESTS

router = APIRouter(prefix="/api/ai/eval", tags=["ai-eval"])


@router.post("/run", response_model=FullEvaluationReport)
async def run_full_evaluation(
    user: dict = Depends(get_current_user),
):
    """Run the full evaluation suite across all AI features."""
    report = ai_evaluator.run_full_evaluation()
    return report


@router.post("/feature/{feature}", response_model=EvaluationReport)
async def run_feature_evaluation(
    feature: EvalFeature,
    user: dict = Depends(get_current_user),
):
    """Run evaluation for a specific AI feature."""
    tests = ALL_GOLDEN_TESTS.get(feature.value)
    if not tests:
        raise HTTPException(
            status_code=404,
            detail=f"No golden tests found for feature '{feature.value}'",
        )
    report = ai_evaluator.evaluate_feature(feature.value, tests)
    return report


@router.get("/results", response_model=FullEvaluationReport | None)
async def get_latest_results(
    user: dict = Depends(get_current_user),
):
    """Get the latest evaluation results (or null if none have been run)."""
    report = ai_evaluator.latest_report
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No evaluation results available. Run an evaluation first.",
        )
    return report


@router.get("/golden-tests")
async def list_golden_tests(
    user: dict = Depends(get_current_user),
):
    """List all available golden tests grouped by feature."""
    result: dict[str, list[dict]] = {}
    for feature, tests in ALL_GOLDEN_TESTS.items():
        result[feature] = [t.model_dump() for t in tests]
    return {"features": result, "total": sum(len(t) for t in ALL_GOLDEN_TESTS.values())}
