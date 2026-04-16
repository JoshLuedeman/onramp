"""AI/ML landing zone accelerator API routes."""

from fastapi import APIRouter, Query

from app.schemas.aiml import (
    AiMlArchitectureRequest,
    AiMlArchitectureResponse,
    AiMlBicepRequest,
    AiMlBicepResponse,
    AiMlSizingRequest,
    AiMlSizingResponse,
    AiMlValidationRequest,
    AiMlValidationResponse,
)
from app.services.aiml_accelerator import aiml_accelerator
from app.services.aiml_bicep import aiml_bicep_service

router = APIRouter(
    prefix="/api/accelerators/aiml", tags=["aiml-accelerator"]
)


@router.get("/questions")
async def get_questions():
    """Return AI/ML-specific questionnaire questions."""
    questions = aiml_accelerator.get_questions()
    return {"questions": questions}


@router.post("/architecture", response_model=AiMlArchitectureResponse)
async def generate_architecture(body: AiMlArchitectureRequest):
    """Generate an AI/ML architecture from questionnaire answers."""
    arch = aiml_accelerator.generate_architecture(body.answers)
    return AiMlArchitectureResponse(architecture=arch)


@router.get("/skus")
async def get_skus(
    gpu_type: str | None = Query(None, description="Filter by GPU type"),
    family: str | None = Query(None, description="Filter by VM family"),
    price_tier: str | None = Query(None, description="Filter by tier"),
):
    """Return recommended AI/ML GPU SKUs."""
    requirements: dict = {}
    if gpu_type:
        requirements["gpu_type"] = gpu_type
    if family:
        requirements["family"] = family
    if price_tier:
        requirements["price_tier"] = price_tier
    skus = aiml_accelerator.get_sku_recommendations(requirements)
    return {"skus": skus, "count": len(skus)}


@router.post("/sizing", response_model=AiMlSizingResponse)
async def estimate_sizing(body: AiMlSizingRequest):
    """Estimate resource sizing for an AI/ML workload."""
    sizing = aiml_accelerator.estimate_sizing(body.requirements)
    return AiMlSizingResponse(sizing=sizing)


@router.get("/best-practices")
async def get_best_practices():
    """Return AI/ML best-practice guidance."""
    practices = aiml_accelerator.get_best_practices()
    return {"best_practices": practices}


@router.post("/bicep", response_model=AiMlBicepResponse)
async def generate_bicep(body: AiMlBicepRequest):
    """Generate Bicep templates for AI/ML resources."""
    ttype = body.template_type
    if ttype == "ml_workspace":
        bicep = aiml_bicep_service.generate_ml_workspace(body.config)
    elif ttype == "compute_cluster":
        bicep = aiml_bicep_service.generate_compute_cluster(body.config)
    else:
        bicep = aiml_bicep_service.generate_full_aiml_stack(body.config)
    return AiMlBicepResponse(bicep=bicep, template_type=ttype)


@router.get("/reference-architectures")
async def get_reference_architectures():
    """Return curated AI/ML reference architectures."""
    archs = aiml_accelerator.get_reference_architectures()
    return {"reference_architectures": archs}


@router.post("/validate", response_model=AiMlValidationResponse)
async def validate_architecture(body: AiMlValidationRequest):
    """Validate an AI/ML architecture for completeness."""
    result = aiml_accelerator.validate_architecture(body.architecture)
    return AiMlValidationResponse(**result)
