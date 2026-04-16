"""Workload extensions API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.workload_extensions import workload_registry

router = APIRouter(prefix="/api/workloads/extensions", tags=["workload-extensions"])


class SizingRequest(BaseModel):
    requirements: dict = Field(default_factory=dict)


class ValidateRequest(BaseModel):
    architecture: dict


@router.get("/")
async def list_extensions():
    """List all registered workload extensions."""
    return {"extensions": workload_registry.list_extensions()}


@router.get("/{workload_type}")
async def get_extension(workload_type: str):
    """Get details for a specific workload extension."""
    ext = workload_registry.get_extension(workload_type)
    if ext is None:
        raise HTTPException(status_code=404, detail=f"Workload type not found: {workload_type}")
    return {
        "workload_type": ext.workload_type,
        "display_name": ext.display_name,
        "description": ext.description,
        "questions": ext.get_questions(),
        "best_practices": ext.get_best_practices(),
    }


@router.get("/{workload_type}/questions")
async def get_questions(workload_type: str):
    """Get workload-specific questionnaire questions."""
    ext = workload_registry.get_extension(workload_type)
    if ext is None:
        raise HTTPException(status_code=404, detail=f"Workload type not found: {workload_type}")
    return {"workload_type": workload_type, "questions": ext.get_questions()}


@router.get("/{workload_type}/best-practices")
async def get_best_practices(workload_type: str):
    """Get workload-specific best practices."""
    ext = workload_registry.get_extension(workload_type)
    if ext is None:
        raise HTTPException(status_code=404, detail=f"Workload type not found: {workload_type}")
    return {"workload_type": workload_type, "best_practices": ext.get_best_practices()}


@router.post("/{workload_type}/validate")
async def validate_architecture(workload_type: str, body: ValidateRequest):
    """Validate an architecture against workload requirements."""
    result = workload_registry.validate_for_workload(workload_type, body.architecture)
    return {"workload_type": workload_type, **result}


@router.post("/{workload_type}/sizing")
async def estimate_sizing(workload_type: str, body: SizingRequest):
    """Estimate resource sizing for a workload."""
    ext = workload_registry.get_extension(workload_type)
    if ext is None:
        raise HTTPException(status_code=404, detail=f"Workload type not found: {workload_type}")
    return {"workload_type": workload_type, "sizing": ext.estimate_sizing(body.requirements)}
