"""Regulatory gap predictor API routes."""

import logging

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.schemas.regulatory import (
    ApplyPoliciesRequest,
    GapAnalysisRequest,
    RegulatoryPredictionRequest,
    RegulatoryPredictionResponse,
)
from app.services.regulatory_predictor import regulatory_predictor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/regulatory", tags=["regulatory"])


@router.post("/predict")
async def predict_frameworks(
    request: RegulatoryPredictionRequest,
    user: dict = Depends(get_current_user),
):
    """Predict applicable regulatory frameworks for an industry and geography."""
    if request.use_ai:
        result = await regulatory_predictor.predict_with_ai(
            industry=request.industry,
            geography=request.geography,
            data_types=request.data_types,
        )
        return result

    predictions = regulatory_predictor.predict_frameworks(
        industry=request.industry,
        geography=request.geography,
        data_types=request.data_types,
    )

    # Optionally run gap analysis if we can
    gap_analyses = []
    recommendations = []

    return RegulatoryPredictionResponse(
        predicted_frameworks=predictions,
        gap_analyses=gap_analyses,
        recommendations=recommendations,
    ).model_dump()


@router.post("/gaps")
async def analyze_gaps(
    request: GapAnalysisRequest,
    user: dict = Depends(get_current_user),
):
    """Analyse architecture against specified compliance frameworks."""
    gap_analyses = regulatory_predictor.analyze_gaps(
        architecture=request.architecture,
        frameworks=request.frameworks,
    )
    recommendations = regulatory_predictor.get_remediation_recommendations(gap_analyses)

    return {
        "gap_analyses": [g.model_dump() for g in gap_analyses],
        "recommendations": [r.model_dump() for r in recommendations],
    }


@router.get("/frameworks")
async def list_frameworks(
    user: dict = Depends(get_current_user),
):
    """List all supported regulatory frameworks with descriptions."""
    frameworks = [
        {"name": name, "description": desc}
        for name, desc in regulatory_predictor.FRAMEWORK_DESCRIPTIONS.items()
    ]
    return {"frameworks": frameworks, "total": len(frameworks)}


@router.post("/apply-policies")
async def apply_policies(
    request: ApplyPoliciesRequest,
    user: dict = Depends(get_current_user),
):
    """Auto-add framework-specific Azure Policy assignments to architecture."""
    updated = regulatory_predictor.auto_apply_policies(
        architecture=request.architecture,
        frameworks=request.frameworks,
    )
    return {"architecture": updated}
