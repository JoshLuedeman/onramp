"""Cloud configuration API routes.

Exposes sovereign-cloud environment metadata, endpoints, and
service-availability validation.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.models.cloud_environment import CloudEnvironment
from app.schemas.cloud_config import (
    CloudEndpointsResponse,
    CloudEnvironmentResponse,
    EnvironmentValidationRequest,
    EnvironmentValidationResponse,
)
from app.services.cloud_config_service import cloud_config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cloud", tags=["cloud"])


def _resolve_environment(env_name: str) -> CloudEnvironment:
    """Map a path parameter to a :class:`CloudEnvironment` or raise 404."""
    try:
        return CloudEnvironment(env_name.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown cloud environment: {env_name}",
        )


# ── Routes ───────────────────────────────────────────────────────────────


@router.get(
    "/environments",
    response_model=list[CloudEnvironmentResponse],
)
async def list_environments(
    user: dict = Depends(get_current_user),
) -> list[CloudEnvironmentResponse]:
    """List all supported cloud environments."""
    result: list[CloudEnvironmentResponse] = []
    for env in cloud_config_service.get_available_environments():
        meta = cloud_config_service.get_environment_metadata(env)
        result.append(
            CloudEnvironmentResponse(
                name=env.value,
                display_name=meta["display_name"],
                description=meta["description"],
                available_regions=meta["regions"],
            )
        )
    return result


@router.get(
    "/environments/{env_name}",
    response_model=CloudEnvironmentResponse,
)
async def get_environment(
    env_name: str,
    user: dict = Depends(get_current_user),
) -> CloudEnvironmentResponse:
    """Get details for a specific cloud environment."""
    env = _resolve_environment(env_name)
    meta = cloud_config_service.get_environment_metadata(env)
    return CloudEnvironmentResponse(
        name=env.value,
        display_name=meta["display_name"],
        description=meta["description"],
        available_regions=meta["regions"],
    )


@router.get(
    "/environments/{env_name}/endpoints",
    response_model=CloudEndpointsResponse,
)
async def get_endpoints(
    env_name: str,
    user: dict = Depends(get_current_user),
) -> CloudEndpointsResponse:
    """Get the service endpoints for a cloud environment."""
    env = _resolve_environment(env_name)
    endpoints = cloud_config_service.get_endpoints(env)
    return CloudEndpointsResponse(**endpoints.model_dump())


@router.post(
    "/environments/validate",
    response_model=EnvironmentValidationResponse,
)
async def validate_environment(
    body: EnvironmentValidationRequest,
    user: dict = Depends(get_current_user),
) -> EnvironmentValidationResponse:
    """Validate that an environment supports the required services."""
    env = _resolve_environment(body.environment)
    result = cloud_config_service.validate_environment_support(
        env, body.required_services,
    )
    return EnvironmentValidationResponse(**result)
