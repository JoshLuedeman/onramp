"""SAP on Azure accelerator API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas.sap import (
    SapArchitectureRequest,
    SapArchitectureResponse,
    SapBestPracticeListResponse,
    SapBicepRequest,
    SapBicepResponse,
    SapQuestionListResponse,
    SapReferenceArchListResponse,
    SapSizingRequest,
    SapSizingResponse,
    SapSkuListResponse,
    SapValidateRequest,
    SapValidateResponse,
)
from app.services.sap_accelerator import sap_accelerator
from app.services.sap_bicep import sap_bicep_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accelerators/sap", tags=["sap"])


# ── Questionnaire ────────────────────────────────────────────────────────────


@router.get("/questions", response_model=SapQuestionListResponse)
async def list_sap_questions(
    user: dict = Depends(get_current_user),
):
    """Return SAP-specific questionnaire questions."""
    questions = sap_accelerator.get_questions()
    return {"questions": questions, "total": len(questions)}


# ── Architecture Generation ──────────────────────────────────────────────────


@router.post("/architecture", response_model=SapArchitectureResponse)
async def generate_sap_architecture(
    request: SapArchitectureRequest,
    user: dict = Depends(get_current_user),
):
    """Generate an SAP landing zone architecture from questionnaire answers."""
    architecture = sap_accelerator.generate_architecture(request.answers)
    return {"architecture": architecture}


# ── Certified SKUs ───────────────────────────────────────────────────────────


@router.get("/skus", response_model=SapSkuListResponse)
async def list_certified_skus(
    tier: str | None = None,
    min_memory_gb: int = 0,
    min_saps: int = 0,
    user: dict = Depends(get_current_user),
):
    """Return SAP-certified VM SKUs, optionally filtered."""
    requirements: dict = {}
    if tier:
        requirements["tier"] = tier
    if min_memory_gb > 0:
        requirements["min_memory_gb"] = min_memory_gb
    if min_saps > 0:
        requirements["min_saps"] = min_saps
    skus = sap_accelerator.get_certified_skus(requirements)
    return {"skus": skus, "total": len(skus)}


# ── Sizing Estimation ────────────────────────────────────────────────────────


@router.post("/sizing", response_model=SapSizingResponse)
async def estimate_sap_sizing(
    request: SapSizingRequest,
    user: dict = Depends(get_current_user),
):
    """Estimate SAP VM sizing based on SAPS, memory, and users."""
    result = sap_accelerator.estimate_sizing(
        {
            "saps": request.saps,
            "data_volume": request.data_volume,
            "concurrent_users": request.concurrent_users,
        }
    )
    return result


# ── Best Practices ───────────────────────────────────────────────────────────


@router.get("/best-practices", response_model=SapBestPracticeListResponse)
async def list_best_practices(
    user: dict = Depends(get_current_user),
):
    """Return the SAP on Azure best-practice checklist."""
    practices = sap_accelerator.get_best_practices()
    return {"best_practices": practices, "total": len(practices)}


# ── Bicep Generation ─────────────────────────────────────────────────────────


@router.post("/bicep", response_model=SapBicepResponse)
async def generate_sap_bicep(
    request: SapBicepRequest,
    user: dict = Depends(get_current_user),
):
    """Generate Bicep template for SAP resources."""
    generators = {
        "hana_vm": sap_bicep_service.generate_hana_vm,
        "app_server": sap_bicep_service.generate_app_server,
        "full_stack": sap_bicep_service.generate_full_sap_stack,
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
        "hana_vm": "SAP HANA database VM with certified SKU",
        "app_server": "SAP application server cluster",
        "full_stack": "Complete SAP on Azure landing zone",
    }
    return {
        "template_type": request.template_type,
        "bicep_template": bicep_template,
        "description": descriptions.get(request.template_type, ""),
    }


# ── Reference Architectures ─────────────────────────────────────────────────


@router.get(
    "/reference-architectures",
    response_model=SapReferenceArchListResponse,
)
async def list_reference_architectures(
    user: dict = Depends(get_current_user),
):
    """Return SAP reference architecture patterns."""
    refs = sap_accelerator.get_reference_architectures()
    return {"reference_architectures": refs, "total": len(refs)}


# ── Architecture Validation ──────────────────────────────────────────────────


@router.post("/validate", response_model=SapValidateResponse)
async def validate_sap_architecture(
    request: SapValidateRequest,
    user: dict = Depends(get_current_user),
):
    """Validate an SAP architecture against best practices."""
    result = sap_accelerator.validate_architecture(request.architecture)
    return result
