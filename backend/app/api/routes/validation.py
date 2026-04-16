"""Architecture validation API routes."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.architecture_validator import architecture_validator_service

router = APIRouter(prefix="/api/validation", tags=["validation"])


class FullValidationRequest(BaseModel):
    architecture: dict
    workload_type: str | None = None
    cloud_env: str = "commercial"


class SkuValidationRequest(BaseModel):
    architecture: dict
    region: str = "eastus"


class ComplianceValidationRequest(BaseModel):
    architecture: dict
    framework: str


class NetworkingValidationRequest(BaseModel):
    architecture: dict


@router.post("/architecture")
async def validate_architecture(body: FullValidationRequest):
    """Run full architecture validation."""
    result = architecture_validator_service.validate_full(
        body.architecture,
        workload_type=body.workload_type,
        cloud_env=body.cloud_env,
    )
    return result


@router.post("/skus")
async def validate_skus(body: SkuValidationRequest):
    """Validate SKU availability in an architecture."""
    return architecture_validator_service.validate_skus(body.architecture, body.region)


@router.post("/compliance")
async def validate_compliance(body: ComplianceValidationRequest):
    """Validate architecture against a compliance framework."""
    return architecture_validator_service.validate_compliance(
        body.architecture, body.framework
    )


@router.post("/networking")
async def validate_networking(body: NetworkingValidationRequest):
    """Validate networking configuration."""
    return architecture_validator_service.validate_networking(body.architecture)


@router.get("/rules")
async def list_validation_rules():
    """List all validation rules."""
    return {"rules": architecture_validator_service.get_validation_rules()}
