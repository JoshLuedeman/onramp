"""Azure Confidential Computing API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas.confidential import (
    AttestationConfigResponse,
    ConfidentialArchitectureRequest,
    ConfidentialArchitectureResponse,
    ConfidentialBicepRequest,
    ConfidentialBicepResponse,
    ConfidentialOptionsListResponse,
    ConfidentialRecommendRequest,
    ConfidentialRecommendResponse,
    ConfidentialRegionListResponse,
    ConfidentialVmSkuListResponse,
)
from app.services.confidential_bicep import confidential_bicep_service
from app.services.confidential_computing import confidential_computing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/confidential", tags=["confidential"])


# ── Information Endpoints ────────────────────────────────────────────────────


@router.get("/options", response_model=ConfidentialOptionsListResponse)
async def list_confidential_options(user: dict = Depends(get_current_user)):
    """List all confidential computing options."""
    options = confidential_computing_service.get_confidential_options()
    return {"options": options, "total": len(options)}


@router.get("/vm-skus", response_model=ConfidentialVmSkuListResponse)
async def list_vm_skus(user: dict = Depends(get_current_user)):
    """List all confidential computing-capable VM SKUs."""
    skus = confidential_computing_service.get_vm_skus()
    return {"skus": skus, "total": len(skus)}


@router.get("/regions", response_model=ConfidentialRegionListResponse)
async def list_supported_regions(user: dict = Depends(get_current_user)):
    """List regions with confidential computing support."""
    regions = confidential_computing_service.get_supported_regions()
    return {"regions": regions, "total": len(regions)}


# ── Recommendation & Architecture ────────────────────────────────────────────


@router.post("/recommend", response_model=ConfidentialRecommendResponse)
async def recommend_config(
    request: ConfidentialRecommendRequest,
    user: dict = Depends(get_current_user),
):
    """Recommend a confidential computing configuration for a workload."""
    result = confidential_computing_service.recommend_confidential_config(
        request.workload_type, request.requirements
    )
    return result


@router.post("/architecture", response_model=ConfidentialArchitectureResponse)
async def generate_architecture(
    request: ConfidentialArchitectureRequest,
    user: dict = Depends(get_current_user),
):
    """Generate a confidential computing-enhanced architecture."""
    enhanced = confidential_computing_service.generate_confidential_architecture(
        request.base_architecture, request.cc_options
    )
    return {"architecture": enhanced, "cc_enabled": True}


# ── Bicep Generation ─────────────────────────────────────────────────────────


@router.post("/bicep", response_model=ConfidentialBicepResponse)
async def generate_bicep(
    request: ConfidentialBicepRequest,
    user: dict = Depends(get_current_user),
):
    """Generate Bicep template for confidential computing resources."""
    generators = {
        "confidential_vm": confidential_bicep_service.generate_confidential_vm,
        "confidential_aks": confidential_bicep_service.generate_confidential_aks,
        "attestation_provider": confidential_bicep_service.generate_attestation_provider,
        "confidential_sql": confidential_bicep_service.generate_confidential_sql,
        "full_stack": confidential_bicep_service.generate_full_confidential_stack,
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
        "confidential_vm": "Confidential VM with hardware-based TEE encryption",
        "confidential_aks": "Confidential AKS cluster with TEE-backed node pools",
        "attestation_provider": "Azure Attestation provider for TEE verification",
        "confidential_sql": "Always Encrypted SQL Database with secure enclaves",
        "full_stack": "Complete confidential computing landing zone",
    }
    return {
        "template_type": request.template_type,
        "bicep_template": bicep_template,
        "description": descriptions.get(request.template_type, ""),
    }


# ── Attestation ──────────────────────────────────────────────────────────────


@router.get("/attestation/{cc_type}", response_model=AttestationConfigResponse)
async def get_attestation_config(
    cc_type: str, user: dict = Depends(get_current_user)
):
    """Get attestation configuration for a confidential computing type."""
    config = confidential_computing_service.get_attestation_config(cc_type)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"No attestation config found for '{cc_type}'.",
        )
    return config
