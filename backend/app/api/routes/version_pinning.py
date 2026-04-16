"""API routes for IaC provider and API version pinning.

Exposes the centralized version registry so the frontend (and CI pipelines)
can query recommended provider versions, SDK pins, and API version dates.
"""

import logging

from fastapi import APIRouter, HTTPException, Path, Query

from app.schemas.version_pinning import (
    ArmVersionsResponse,
    BicepVersionsResponse,
    PulumiVersionsResponse,
    TerraformVersionsResponse,
    VersionReport,
)
from app.services.version_pinning import (
    STALENESS_THRESHOLD_DAYS,
    version_pinning,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/versions", tags=["versions"])


@router.get("/terraform", response_model=TerraformVersionsResponse)
async def get_terraform_versions():
    """Get recommended Terraform provider versions."""
    providers = version_pinning.get_terraform_providers()
    return TerraformVersionsResponse(
        terraform_version=version_pinning.terraform_cli_version,
        providers=providers,
    )


@router.get("/pulumi/{language}", response_model=PulumiVersionsResponse)
async def get_pulumi_versions(
    language: str = Path(
        ..., description="Target language: typescript or python"
    ),
):
    """Get recommended Pulumi SDK versions for a specific language."""
    lang = language.lower()
    if lang not in ("typescript", "python"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported language '{language}'. "
                "Supported: typescript, python"
            ),
        )
    packages = version_pinning.get_pulumi_versions(lang)  # type: ignore[arg-type]
    return PulumiVersionsResponse(language=lang, packages=packages)


@router.get("/arm", response_model=ArmVersionsResponse)
async def get_arm_versions():
    """Get recommended ARM template API versions."""
    api_versions = version_pinning.get_arm_api_versions()
    return ArmVersionsResponse(
        schema_version=(
            "https://schema.management.azure.com/"
            "schemas/2019-04-01/deploymentTemplate.json#"
        ),
        content_version="1.0.0.0",
        api_versions=api_versions,
    )


@router.get("/bicep", response_model=BicepVersionsResponse)
async def get_bicep_versions():
    """Get recommended Bicep API versions."""
    api_versions = version_pinning.get_bicep_api_versions()
    return BicepVersionsResponse(api_versions=api_versions)


@router.get("/report", response_model=VersionReport)
async def get_version_report(
    threshold_days: int = Query(
        default=STALENESS_THRESHOLD_DAYS,
        ge=1,
        le=3650,
        description="Staleness threshold in days",
    ),
):
    """Generate a full version freshness report across all IaC formats."""
    return version_pinning.get_version_report(threshold_days)
