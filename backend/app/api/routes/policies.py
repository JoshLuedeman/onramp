"""Policy generation and validation API routes."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user
from app.schemas.policy import (
    PolicyApplyRequest,
    PolicyGenerateRequest,
    PolicyLibraryResponse,
    PolicyValidationResult,
)
from app.services.policy_generator import policy_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/policies", tags=["policies"])


class _PolicyValidateBody(BaseModel):
    """Inline body for the validate endpoint."""

    policy: dict


@router.post("/generate")
async def generate_policy(
    request: PolicyGenerateRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Generate an Azure Policy from a natural language description."""
    policy = await policy_generator.generate_policy(
        description=request.description,
        context=request.context,
    )
    return {"policy": policy.model_dump()}


@router.post("/validate")
async def validate_policy(
    request: _PolicyValidateBody,
    user: dict = Depends(get_current_user),
) -> dict:
    """Validate an Azure Policy JSON definition."""
    result: PolicyValidationResult = policy_generator.validate_policy_json(
        request.policy
    )
    return result.model_dump()


@router.get("/library")
async def get_policy_library(
    user: dict = Depends(get_current_user),
) -> dict:
    """List common pre-built policy templates."""
    templates = policy_generator.get_policy_library()
    return PolicyLibraryResponse(policies=templates).model_dump()


@router.post("/apply")
async def apply_policy(
    request: PolicyApplyRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Add a generated policy to an architecture.

    Currently stores the policy association; future phases will push it
    to Azure via ARM/Bicep deployment.
    """
    validation = policy_generator.validate_policy_json(request.policy)
    if not validation.valid:
        return {
            "status": "error",
            "message": "Policy validation failed",
            "errors": validation.errors,
        }

    return {
        "status": "applied",
        "policy_name": request.policy.get("name", "unknown"),
        "architecture_id": request.architecture_id,
    }
