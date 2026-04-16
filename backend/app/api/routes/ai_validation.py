"""API routes for AI output validation and reference data."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.ai_validation import AIOutputType, ValidationResult
from app.services.ai_validator import ai_validator
from app.services.azure_reference import azure_reference

router = APIRouter(prefix="/api/ai", tags=["ai-validation"])


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------


class ValidateRequest(BaseModel):
    """Request body for POST /api/ai/validate."""

    output_type: AIOutputType
    data: dict = Field(default_factory=dict)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@router.post("/validate", response_model=ValidationResult)
async def validate_ai_output(request: ValidateRequest):
    """Validate arbitrary AI output against a specified schema type."""
    dispatch = {
        AIOutputType.architecture: ai_validator.validate_architecture,
        AIOutputType.policy: ai_validator.validate_policy,
        AIOutputType.sku_recommendation: ai_validator.validate_sku_recommendation,
        AIOutputType.security_finding: ai_validator.validate_security_finding,
        AIOutputType.compliance_gap: ai_validator.validate_compliance_gap,
    }
    handler = dispatch.get(request.output_type)
    if handler is None:
        return ValidationResult(
            success=False,
            errors=[],
            warnings=[f"Unknown output type: {request.output_type}"],
        )
    return handler(request.data)


@router.get("/validation/metrics")
async def get_validation_metrics(feature: str | None = None):
    """Get validation metrics, optionally filtered by feature."""
    metrics = ai_validator.get_metrics(feature)
    return {"metrics": [m.model_dump() for m in metrics]}


@router.get("/reference/resource-types")
async def list_resource_types():
    """List all known valid Azure resource types."""
    return {
        "resource_types": sorted(azure_reference.VALID_RESOURCE_TYPES),
        "count": len(azure_reference.VALID_RESOURCE_TYPES),
    }


@router.get("/reference/regions")
async def list_regions():
    """List all known valid Azure regions."""
    return {
        "regions": sorted(azure_reference.VALID_REGIONS),
        "count": len(azure_reference.VALID_REGIONS),
    }
