"""Deployment API routes with orchestration, tracking, rollback, and audit."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tenant_scope import require_project_tenant
from app.auth import get_current_user, require_architect
from app.db.session import get_db
from app.services.credentials import credential_manager
from app.services.deployment_orchestrator import deployment_orchestrator

router = APIRouter(prefix="/api/deployment", tags=["deployment"])


class ValidationRequest(BaseModel):
    subscription_id: str = Field(..., min_length=1)
    region: str = Field(default="eastus2", min_length=1)


class DeployRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    architecture: dict = Field(..., min_length=1)
    subscription_ids: list[str] = Field(..., min_length=1)


@router.post("/validate")
async def validate_deployment_target(
    request: ValidationRequest, user: dict = Depends(require_architect)
):
    """Validate that a subscription is ready for deployment."""
    cred_result = await credential_manager.validate_credentials(request.subscription_id)
    perm_result = await credential_manager.check_deployment_permissions(request.subscription_id)
    quota_result = await credential_manager.check_subscription_quotas(
        request.subscription_id, request.region
    )

    return {
        "subscription_id": request.subscription_id,
        "credentials_valid": cred_result.is_valid,
        "permissions_sufficient": perm_result["has_permissions"],
        "quotas_sufficient": quota_result["quotas_sufficient"],
        "ready_to_deploy": (
            cred_result.is_valid
            and perm_result["has_permissions"]
            and quota_result["quotas_sufficient"]
        ),
        "details": {
            "credentials": {"valid": cred_result.is_valid, "error": cred_result.error},
            "permissions": perm_result,
            "quotas": quota_result,
        },
    }


@router.post("/create", status_code=201)
async def create_deployment(
    request: DeployRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new deployment plan."""
    if db is not None:
        tenant_id = user.get(
            "tid", user.get("tenant_id", "dev-tenant")
        )
        await require_project_tenant(
            db, request.project_id, tenant_id
        )
    record = deployment_orchestrator.create_deployment(
        request.project_id, request.architecture, request.subscription_ids
    )
    return record.to_dict()


@router.post("/{deployment_id}/start")
async def start_deployment(
    deployment_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start executing a deployment."""
    record = deployment_orchestrator.get_deployment(deployment_id)
    if not record:
        raise HTTPException(
            status_code=404, detail="Deployment not found"
        )
    if db is not None:
        tenant_id = user.get(
            "tid", user.get("tenant_id", "dev-tenant")
        )
        await require_project_tenant(
            db, record.project_id, tenant_id
        )
    result = deployment_orchestrator.start_deployment(deployment_id)
    return result.to_dict()


@router.get("/{deployment_id}")
async def get_deployment_status(
    deployment_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get deployment status and progress."""
    record = deployment_orchestrator.get_deployment(deployment_id)
    if not record:
        raise HTTPException(
            status_code=404, detail="Deployment not found"
        )
    if db is not None:
        tenant_id = user.get(
            "tid", user.get("tenant_id", "dev-tenant")
        )
        await require_project_tenant(
            db, record.project_id, tenant_id
        )
    return record.to_dict()


@router.post("/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rollback a deployment."""
    record = deployment_orchestrator.get_deployment(deployment_id)
    if not record:
        raise HTTPException(
            status_code=404, detail="Deployment not found"
        )
    if db is not None:
        tenant_id = user.get(
            "tid", user.get("tenant_id", "dev-tenant")
        )
        await require_project_tenant(
            db, record.project_id, tenant_id
        )
    result = deployment_orchestrator.rollback_deployment(deployment_id)
    return result.to_dict()


@router.get("/{deployment_id}/audit")
async def get_audit_log(
    deployment_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get deployment audit log."""
    record = deployment_orchestrator.get_deployment(deployment_id)
    if not record:
        raise HTTPException(
            status_code=404, detail="Deployment not found"
        )
    if db is not None:
        tenant_id = user.get(
            "tid", user.get("tenant_id", "dev-tenant")
        )
        await require_project_tenant(
            db, record.project_id, tenant_id
        )
    log = deployment_orchestrator.get_audit_log(deployment_id)
    if not log:
        raise HTTPException(
            status_code=404, detail="Deployment not found"
        )
    return {"deployment_id": deployment_id, "entries": log}


@router.get("/")
async def list_deployments(
    project_id: str = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all deployments."""
    if project_id is not None and db is not None:
        tenant_id = user.get(
            "tid", user.get("tenant_id", "dev-tenant")
        )
        await require_project_tenant(
            db, project_id, tenant_id
        )
    records = deployment_orchestrator.list_deployments(project_id)
    return {"deployments": [r.to_dict() for r in records]}
