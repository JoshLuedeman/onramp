"""Sovereign compliance & service availability API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas.sovereign import (
    ArchitectureCompatibilityRequest,
    ArchitectureCompatibilityResponse,
    EvaluateComplianceRequest,
    ServiceAvailabilityMatrixResponse,
    ServiceAvailabilityResponse,
    SovereignComplianceResult,
    SovereignFrameworkListResponse,
    SovereignFrameworkResponse,
)
from app.services.service_availability import service_availability_service
from app.services.sovereign_compliance import sovereign_compliance_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sovereign", tags=["sovereign"])


# ── Framework Endpoints ──────────────────────────────────────────────────────


@router.get("/frameworks", response_model=SovereignFrameworkListResponse)
async def list_frameworks(user: dict = Depends(get_current_user)):
    """List all sovereign compliance frameworks."""
    frameworks = sovereign_compliance_service.get_sovereign_frameworks()
    return {"frameworks": frameworks, "total": len(frameworks)}


@router.get("/frameworks/{short_name}", response_model=SovereignFrameworkResponse)
async def get_framework(short_name: str, user: dict = Depends(get_current_user)):
    """Get details for a specific sovereign compliance framework."""
    fw = sovereign_compliance_service.get_framework(short_name)
    if fw is None:
        raise HTTPException(status_code=404, detail=f"Framework '{short_name}' not found.")
    return fw


@router.get("/frameworks/{short_name}/controls")
async def get_framework_controls(
    short_name: str, user: dict = Depends(get_current_user)
):
    """Get control families for a specific sovereign compliance framework."""
    fw = sovereign_compliance_service.get_framework(short_name)
    if fw is None:
        raise HTTPException(status_code=404, detail=f"Framework '{short_name}' not found.")
    controls = sovereign_compliance_service.get_framework_controls(short_name)
    return {"framework": short_name, "controls": controls}


@router.post(
    "/frameworks/{short_name}/evaluate",
    response_model=SovereignComplianceResult,
)
async def evaluate_compliance(
    short_name: str,
    request: EvaluateComplianceRequest,
    user: dict = Depends(get_current_user),
):
    """Evaluate an architecture against a sovereign compliance framework."""
    result = sovereign_compliance_service.evaluate_sovereign_compliance(
        request.architecture, short_name
    )
    return result


# ── Service Availability Endpoints ───────────────────────────────────────────


@router.get("/services/matrix", response_model=ServiceAvailabilityMatrixResponse)
async def get_availability_matrix(user: dict = Depends(get_current_user)):
    """Get the full service availability matrix."""
    return service_availability_service.get_availability_matrix()


@router.get("/services", response_model=list[ServiceAvailabilityResponse])
async def list_services(user: dict = Depends(get_current_user)):
    """List all tracked Azure services with availability information."""
    return service_availability_service.get_all_services()


@router.get("/services/{service_name}", response_model=ServiceAvailabilityResponse)
async def get_service(service_name: str, user: dict = Depends(get_current_user)):
    """Get availability details for a specific Azure service."""
    svc = service_availability_service.get_service(service_name)
    if svc is None:
        raise HTTPException(
            status_code=404, detail=f"Service '{service_name}' not found."
        )
    return svc


@router.post(
    "/services/check-compatibility",
    response_model=ArchitectureCompatibilityResponse,
)
async def check_compatibility(
    request: ArchitectureCompatibilityRequest,
    user: dict = Depends(get_current_user),
):
    """Check if an architecture's services are available in the target environment."""
    result = service_availability_service.check_architecture_compatibility(
        request.architecture, request.target_environment
    )
    return result
