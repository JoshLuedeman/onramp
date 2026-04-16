"""API routes for Azure Government cloud support.

Exposes Government region registry, Bicep template customization, and
Government-specific questionnaire extensions.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.schemas.government import (
    GovernmentBicepRequest,
    GovernmentBicepResponse,
    GovernmentConstraintsRequest,
    GovernmentConstraintsResponse,
    GovernmentQuestionResponse,
    GovernmentRegionListResponse,
    GovernmentRegionResponse,
)
from app.services.government_bicep import government_bicep_service
from app.services.government_questionnaire import government_questionnaire_service
from app.services.government_regions import government_region_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/government", tags=["government"])


# ── Region Endpoints ─────────────────────────────────────────────────────────


@router.get("/regions", response_model=GovernmentRegionListResponse)
async def list_regions(
    user: dict = Depends(get_current_user),
) -> GovernmentRegionListResponse:
    """List all Azure Government regions."""
    regions = government_region_service.get_regions()
    return GovernmentRegionListResponse(regions=regions, total=len(regions))


@router.get("/regions/dod", response_model=GovernmentRegionListResponse)
async def list_dod_regions(
    user: dict = Depends(get_current_user),
) -> GovernmentRegionListResponse:
    """List DoD-only Azure Government regions."""
    regions = government_region_service.get_dod_regions()
    return GovernmentRegionListResponse(regions=regions, total=len(regions))


@router.get("/regions/{name}", response_model=GovernmentRegionResponse)
async def get_region(
    name: str,
    user: dict = Depends(get_current_user),
) -> GovernmentRegionResponse:
    """Get details for a specific Government region."""
    region = government_region_service.get_region(name)
    if region is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Government region '{name}' not found.",
        )
    return GovernmentRegionResponse(**region)


# ── Bicep Endpoints ──────────────────────────────────────────────────────────


@router.post("/bicep/customize", response_model=GovernmentBicepResponse)
async def customize_bicep(
    request: GovernmentBicepRequest,
    user: dict = Depends(get_current_user),
) -> GovernmentBicepResponse:
    """Customize a Bicep template for Azure Government cloud."""
    if not government_region_service.validate_region(request.region):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Government region: '{request.region}'.",
        )

    customized = government_bicep_service.customize_for_government(
        request.bicep_content,
        request.region,
        request.compliance_level,
    )

    changes: list[str] = []
    if customized != request.bicep_content:
        changes.append("Replaced commercial endpoints with .us equivalents")
        changes.append("Added environment property for AzureUSGovernment")
        changes.append(
            f"Injected FedRAMP {request.compliance_level} compliance tags"
        )
        changes.append("Added diagnostic settings for FedRAMP logging")
        changes.append("Mapped commercial SKUs to Government equivalents")
        changes.append(f"Set location to {request.region}")

    return GovernmentBicepResponse(
        customized_content=customized,
        changes_applied=changes,
    )


# ── Questionnaire Endpoints ─────────────────────────────────────────────────


@router.get(
    "/questions",
    response_model=list[GovernmentQuestionResponse],
)
async def get_government_questions(
    user: dict = Depends(get_current_user),
) -> list[GovernmentQuestionResponse]:
    """Get Government-specific questionnaire questions."""
    questions = government_questionnaire_service.get_government_questions()
    return [GovernmentQuestionResponse(**q) for q in questions]


@router.post("/constraints", response_model=GovernmentConstraintsResponse)
async def apply_constraints(
    request: GovernmentConstraintsRequest,
    user: dict = Depends(get_current_user),
) -> GovernmentConstraintsResponse:
    """Apply Government constraints to an architecture."""
    result = government_questionnaire_service.apply_government_constraints(
        request.architecture,
        request.gov_answers,
    )
    warnings = result.pop("warnings", [])
    return GovernmentConstraintsResponse(
        architecture=result,
        warnings=warnings,
    )
