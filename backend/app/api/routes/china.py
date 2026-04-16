"""Azure China (21Vianet) API routes.

Provides region registry, Bicep customization, questionnaire extensions,
and data residency endpoints for Azure China deployments.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.schemas.china import (
    ChinaBicepRequest,
    ChinaBicepResponse,
    ChinaConstraintsRequest,
    ChinaConstraintsResponse,
    ChinaQuestionResponse,
    ChinaRegionListResponse,
    ChinaRegionResponse,
    DataResidencyRequirements,
    ICPRequirements,
)
from app.services.china_bicep import china_bicep_service
from app.services.china_questionnaire import china_questionnaire_service
from app.services.china_regions import china_region_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/china", tags=["china"])


# ── Region Routes ────────────────────────────────────────────────────────────


@router.get(
    "/regions",
    response_model=ChinaRegionListResponse,
)
async def list_regions(
    user: dict = Depends(get_current_user),
) -> ChinaRegionListResponse:
    """List all Azure China regions."""
    regions = china_region_service.get_regions()
    return ChinaRegionListResponse(
        regions=[ChinaRegionResponse(**r) for r in regions],
        total=len(regions),
    )


@router.get(
    "/regions/{name}",
    response_model=ChinaRegionResponse,
)
async def get_region(
    name: str,
    user: dict = Depends(get_current_user),
) -> ChinaRegionResponse:
    """Get details for a specific China region."""
    region = china_region_service.get_region(name)
    if region is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown China region: {name}",
        )
    return ChinaRegionResponse(**region)


# ── Bicep Routes ─────────────────────────────────────────────────────────────


@router.post(
    "/bicep/customize",
    response_model=ChinaBicepResponse,
)
async def customize_bicep(
    body: ChinaBicepRequest,
    user: dict = Depends(get_current_user),
) -> ChinaBicepResponse:
    """Customize a Bicep template for Azure China deployment."""
    if not china_region_service.validate_region(body.region):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid China region: {body.region}",
        )

    original = body.bicep_content
    customized = china_bicep_service.customize_for_china(
        original, body.region, body.compliance_level
    )

    # Count endpoint replacements (lines changed)
    orig_lines = set(original.splitlines())
    new_lines = set(customized.splitlines())
    replacements = len(new_lines - orig_lines)

    return ChinaBicepResponse(
        customized_content=customized,
        region=body.region,
        compliance_level=body.compliance_level,
        endpoints_replaced=replacements,
    )


# ── Questionnaire Routes ────────────────────────────────────────────────────


@router.get(
    "/questions",
    response_model=list[ChinaQuestionResponse],
)
async def get_questions(
    user: dict = Depends(get_current_user),
) -> list[ChinaQuestionResponse]:
    """Get China-specific questionnaire questions."""
    questions = china_questionnaire_service.get_china_questions()
    return [ChinaQuestionResponse(**q) for q in questions]


@router.post(
    "/constraints",
    response_model=ChinaConstraintsResponse,
)
async def apply_constraints(
    body: ChinaConstraintsRequest,
    user: dict = Depends(get_current_user),
) -> ChinaConstraintsResponse:
    """Apply China-specific constraints to an architecture."""
    result = china_questionnaire_service.apply_china_constraints(
        body.architecture, body.china_answers
    )
    return ChinaConstraintsResponse(
        architecture=result,
        region=result.get("region", "chinanorth2"),
        compliance_level=result.get("compliance", {}).get("level", "level3"),
        cloud_environment="china",
    )


# ── Data Residency Routes ───────────────────────────────────────────────────


@router.get(
    "/data-residency",
    response_model=DataResidencyRequirements,
)
async def get_data_residency(
    user: dict = Depends(get_current_user),
) -> DataResidencyRequirements:
    """Get China data residency requirements."""
    requirements = china_region_service.get_data_residency_requirements()
    return DataResidencyRequirements(**requirements)


@router.get(
    "/icp-requirements",
    response_model=ICPRequirements,
)
async def get_icp_requirements(
    user: dict = Depends(get_current_user),
) -> ICPRequirements:
    """Get ICP license requirements for a default architecture.

    For architecture-specific ICP analysis, use POST /bicep/customize.
    """
    result = china_bicep_service.get_icp_requirements({"resources": []})
    return ICPRequirements(**result)
