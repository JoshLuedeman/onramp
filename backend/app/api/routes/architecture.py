"""Architecture generation API routes."""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.concurrency import check_version, increment_version
from app.api.tenant_scope import require_project_tenant
from app.auth import get_current_user, require_architect
from app.db.session import get_db
from app.services.archetypes import get_archetype_for_answers, list_archetypes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/architecture", tags=["architecture"])


class GenerateRequest(BaseModel):
    answers: dict[str, str | list[str]]
    use_ai: bool = False
    use_archetype: bool = False
    project_id: str = ""


class CostEstimateRequest(BaseModel):
    architecture: dict


@router.get("/archetypes")
async def get_archetypes(user: dict = Depends(get_current_user)):
    """List available landing zone archetypes."""
    return {"archetypes": list_archetypes()}


@router.post("/generate")
async def generate_architecture(
    request: GenerateRequest,
    user: dict = Depends(require_architect),
    db: AsyncSession = Depends(get_db),
):
    """Generate a landing zone architecture from questionnaire answers."""
    if request.use_archetype and not request.use_ai:
        architecture = get_archetype_for_answers(request.answers)
        used_ai = False
    else:
        from app.services.ai_foundry import ai_client
        architecture = await ai_client.generate_architecture(
            request.answers,
        )
        used_ai = True

    # Persist if project_id provided and DB available
    if request.project_id and db is not None:
        tenant_id = user.get(
            "tid", user.get("tenant_id", "dev-tenant")
        )
        await require_project_tenant(
            db, request.project_id, tenant_id
        )
        try:
            from app.models import Architecture as ArchModel
            arch_record = ArchModel(
                id=str(uuid.uuid4()),
                project_id=request.project_id,
                architecture_data=architecture,
                management_groups=architecture.get(
                    "management_groups",
                ),
                subscriptions=architecture.get("subscriptions"),
                network_topology=architecture.get(
                    "network_topology",
                ),
                policies=architecture.get("policies"),
                ai_reasoning=(
                    "AI-generated" if used_ai else "Archetype-based"
                ),
                version=1,
                status="draft",
            )
            db.add(arch_record)
            await db.flush()
        except Exception as e:
            logger.warning("Failed to persist architecture: %s", e)

    return {"architecture": architecture}


@router.get("/project/{project_id}")
async def get_project_architecture(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Load the persisted architecture for a project."""
    if db is None:
        return {"architecture": None, "project_id": project_id}

    from sqlalchemy import desc, select

    from app.models import Architecture as ArchModel
    from app.models import Project

    tenant_id = user.get(
        "tid", user.get("tenant_id", "dev-tenant")
    )
    query = (
        select(ArchModel)
        .join(Project, ArchModel.project_id == Project.id)
        .where(
            ArchModel.project_id == project_id,
            Project.tenant_id == tenant_id,
        )
        .order_by(
            desc(ArchModel.updated_at), desc(ArchModel.created_at),
        )
    )
    result = await db.execute(query)
    arch = result.scalars().first()
    if not arch:
        return {"architecture": None, "project_id": project_id}

    return {
        "architecture": arch.architecture_data,
        "project_id": project_id,
        "version": arch.version,
    }


@router.post("/estimate-costs")
async def estimate_costs(
    request: CostEstimateRequest,
    user: dict = Depends(get_current_user),
):
    """Estimate monthly Azure costs for an architecture."""
    from app.services.ai_foundry import ai_client

    result = await ai_client.estimate_costs(request.architecture)
    return result


class CompareRequest(BaseModel):
    answers: dict[str, str | list[str]]
    options: dict | None = None


@router.post("/compare")
async def compare_architectures(
    request: CompareRequest,
    user: dict = Depends(get_current_user),
):
    """Generate and compare three architecture variants side-by-side."""
    from app.services.architecture_comparator import (
        architecture_comparator,
    )

    variants = architecture_comparator.generate_variants(
        request.answers, request.options,
    )
    result = architecture_comparator.compare_variants(variants)
    return result.model_dump()


@router.post("/compare/tradeoffs")
async def compare_tradeoffs(
    request: CompareRequest,
    user: dict = Depends(get_current_user),
):
    """Return an AI-generated trade-off analysis for variants."""
    from app.services.architecture_comparator import (
        architecture_comparator,
    )

    variants = architecture_comparator.generate_variants(
        request.answers, request.options,
    )
    analysis = architecture_comparator.generate_tradeoff_analysis(
        variants,
    )
    return {"tradeoff_analysis": analysis}


class RefineRequest(BaseModel):
    architecture: dict
    message: str
    architecture_id: str | None = None
    version: int | None = None


@router.post("/refine")
async def refine_architecture(
    request: RefineRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    if_match: str | None = Header(None, alias="If-Match"),
):
    """Refine a landing zone architecture via conversational AI."""
    # Optimistic concurrency check
    submitted_version = (
        int(if_match) if if_match
        else request.version
    )
    if (
        submitted_version is not None
        and request.architecture_id
        and db is not None
    ):
        from app.models import Architecture as ArchModel
        instance = await check_version(
            db, ArchModel, request.architecture_id,
            submitted_version,
        )
        increment_version(instance)

    from app.services.ai_foundry import ai_client
    from app.services.prompts import ARCHITECTURE_REFINEMENT_PROMPT

    if not ai_client.is_configured:
        return {
            "response": (
                f"I've noted your request: \"{request.message}\". "
                "AI refinement is not configured in dev mode, "
                "but your feedback has been acknowledged."
            ),
            "updated_architecture": None,
        }

    user_prompt = (
        f"Current architecture:\n"
        f"{json.dumps(request.architecture, indent=2)}\n\n"
        f"User request: {request.message}"
    )
    raw = await ai_client.generate_completion_async(
        ARCHITECTURE_REFINEMENT_PROMPT, user_prompt,
    )

    # Try to parse as JSON (updated architecture)
    updated_architecture: dict | None = None
    response_text = raw
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            updated_architecture = parsed
            response_text = parsed.pop(
                "explanation",
                "Architecture updated based on your request.",
            )
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "response": response_text,
        "updated_architecture": updated_architecture,
    }


class UpdateArchitectureRequest(BaseModel):
    """Request to update architecture data with concurrency control."""
    architecture_data: dict
    architecture_id: str
    version: int | None = None


@router.put("/project/{project_id}")
async def update_project_architecture(
    project_id: str,
    request: UpdateArchitectureRequest,
    user: dict = Depends(require_architect),
    db: AsyncSession = Depends(get_db),
    if_match: str | None = Header(None, alias="If-Match"),
):
    """Update architecture with optimistic concurrency control."""
    if db is None:
        return {"architecture": None, "project_id": project_id}

    from app.models import Architecture as ArchModel

    submitted_version = (
        int(if_match) if if_match else request.version
    )
    if submitted_version is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Version required: provide If-Match header or "
            "version in request body.",
        )

    instance = await check_version(
        db, ArchModel, request.architecture_id, submitted_version,
    )
    new_version = increment_version(instance)

    instance.architecture_data = request.architecture_data
    instance.management_groups = request.architecture_data.get(
        "management_groups",
    )
    instance.subscriptions = request.architecture_data.get(
        "subscriptions",
    )
    instance.network_topology = request.architecture_data.get(
        "network_topology",
    )
    instance.policies = request.architecture_data.get("policies")

    return {
        "architecture": instance.architecture_data,
        "project_id": project_id,
        "version": new_version,
    }
