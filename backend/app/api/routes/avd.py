"""Azure Virtual Desktop accelerator API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas.avd import (
    AvdArchitectureRequest,
    AvdArchitectureResponse,
    AvdBestPracticeResponse,
    AvdBicepRequest,
    AvdBicepResponse,
    AvdQuestionResponse,
    AvdReferenceArchResponse,
    AvdSizingRequest,
    AvdSizingResponse,
    AvdSkuListResponse,
    AvdSkuRequest,
    AvdValidationRequest,
    AvdValidationResponse,
)
from app.services.avd_accelerator import avd_accelerator
from app.services.avd_bicep import avd_bicep_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/accelerators/avd", tags=["avd"]
)

# ── Questionnaire ────────────────────────────────────────────────────────────


@router.get(
    "/questions",
    response_model=list[AvdQuestionResponse],
)
async def get_questions(
    user: dict = Depends(get_current_user),
):
    """Return AVD-specific questionnaire questions."""
    return avd_accelerator.get_questions()


# ── SKU Recommendations ──────────────────────────────────────────────────────


@router.post(
    "/sku-recommendations",
    response_model=AvdSkuListResponse,
)
async def get_sku_recommendations(
    request: AvdSkuRequest,
    user: dict = Depends(get_current_user),
):
    """Return VM SKU recommendations for the given workload."""
    skus = avd_accelerator.get_sku_recommendations(
        request.user_type, request.application_type
    )
    return {"skus": skus, "total": len(skus)}


# ── Architecture ─────────────────────────────────────────────────────────────


@router.post(
    "/architecture",
    response_model=AvdArchitectureResponse,
)
async def generate_architecture(
    request: AvdArchitectureRequest,
    user: dict = Depends(get_current_user),
):
    """Generate an AVD landing-zone architecture."""
    arch = avd_accelerator.generate_architecture(request.answers)
    return {"architecture": arch}


# ── Best Practices ───────────────────────────────────────────────────────────


@router.get(
    "/best-practices",
    response_model=list[AvdBestPracticeResponse],
)
async def get_best_practices(
    user: dict = Depends(get_current_user),
):
    """Return AVD deployment best practices."""
    return avd_accelerator.get_best_practices()


# ── Sizing ───────────────────────────────────────────────────────────────────


@router.post(
    "/sizing",
    response_model=AvdSizingResponse,
)
async def estimate_sizing(
    request: AvdSizingRequest,
    user: dict = Depends(get_current_user),
):
    """Estimate session-host sizing from requirements."""
    return avd_accelerator.estimate_sizing(request.requirements)


# ── Validation ───────────────────────────────────────────────────────────────


@router.post(
    "/validate",
    response_model=AvdValidationResponse,
)
async def validate_architecture(
    request: AvdValidationRequest,
    user: dict = Depends(get_current_user),
):
    """Validate an AVD architecture dict."""
    return avd_accelerator.validate_architecture(
        request.architecture
    )


# ── Reference Architectures ─────────────────────────────────────────────────


@router.get(
    "/reference-architectures",
    response_model=list[AvdReferenceArchResponse],
)
async def get_reference_architectures(
    user: dict = Depends(get_current_user),
):
    """Return pre-built AVD reference architectures."""
    return avd_accelerator.get_reference_architectures()


# ── Bicep Generation ─────────────────────────────────────────────────────────


@router.post(
    "/bicep",
    response_model=AvdBicepResponse,
)
async def generate_bicep(
    request: AvdBicepRequest,
    user: dict = Depends(get_current_user),
):
    """Generate Bicep template for AVD resources."""
    generators = {
        "host_pool": avd_bicep_service.generate_host_pool,
        "session_hosts": avd_bicep_service.generate_session_hosts,
        "workspace": avd_bicep_service.generate_workspace,
        "app_group": avd_bicep_service.generate_app_group,
        "storage": avd_bicep_service.generate_storage,
        "networking": avd_bicep_service.generate_networking,
        "full_stack": avd_bicep_service.generate_full_avd_stack,
    }
    generator = generators.get(request.template_type)
    if generator is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown template_type '{request.template_type}'."
                f" Valid types: {', '.join(generators.keys())}"
            ),
        )
    bicep_template = generator(request.config)
    descriptions = {
        "host_pool": "AVD host pool resource",
        "session_hosts": "AVD session host virtual machines",
        "workspace": "AVD workspace resource",
        "app_group": "AVD application group resource",
        "storage": "FSLogix profile storage (Azure Files Premium)",
        "networking": "AVD networking (VNet, subnets, NSG)",
        "full_stack": "Complete AVD landing zone",
    }
    return {
        "template_type": request.template_type,
        "bicep_template": bicep_template,
        "description": descriptions.get(
            request.template_type, ""
        ),
    }
