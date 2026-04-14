"""Architecture generation API routes."""

import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_architect
from app.db.session import get_db
from app.services.archetypes import get_archetype_for_answers, list_archetypes

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
    request: GenerateRequest, user: dict = Depends(require_architect),
    db: AsyncSession = Depends(get_db),
):
    """Generate a landing zone architecture from questionnaire answers."""
    # Use AI by default; fall back to static archetypes only when explicitly requested
    if request.use_archetype and not request.use_ai:
        architecture = get_archetype_for_answers(request.answers)
        used_ai = False
    else:
        from app.services.ai_foundry import ai_client
        architecture = await ai_client.generate_architecture(request.answers)
        used_ai = True

    # Persist if project_id provided and DB available
    if request.project_id and db is not None:
        try:
            from app.models import Architecture as ArchModel
            arch_record = ArchModel(
                id=str(uuid.uuid4()),
                project_id=request.project_id,
                architecture_data=architecture,
                management_groups=architecture.get("management_groups"),
                subscriptions=architecture.get("subscriptions"),
                network_topology=architecture.get("network_topology"),
                policies=architecture.get("policies"),
                ai_reasoning="AI-generated" if used_ai else "Archetype-based",
                version=1,
                status="draft",
            )
            db.add(arch_record)
            await db.flush()
        except Exception as e:
            import logging
            logging.getLogger("onramp").warning(f"Failed to persist architecture: {e}")

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

    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
    query = (
        select(ArchModel)
        .join(Project, ArchModel.project_id == Project.id)
        .where(ArchModel.project_id == project_id, Project.tenant_id == tenant_id)
        .order_by(desc(ArchModel.updated_at), desc(ArchModel.created_at))
    )
    result = await db.execute(query)
    arch = result.scalars().first()
    if not arch:
        return {"architecture": None, "project_id": project_id}

    return {"architecture": arch.architecture_data, "project_id": project_id}


@router.post("/estimate-costs")
async def estimate_costs(
    request: CostEstimateRequest, user: dict = Depends(get_current_user),
):
    """Estimate monthly Azure costs for an architecture."""
    from app.services.ai_foundry import ai_client

    result = await ai_client.estimate_costs(request.architecture)
    return result


class RefineRequest(BaseModel):
    architecture: dict
    message: str


@router.post("/refine")
async def refine_architecture(
    request: RefineRequest, user: dict = Depends(get_current_user),
):
    """Refine a landing zone architecture via conversational AI."""
    from app.services.ai_foundry import ai_client
    from app.services.prompts import ARCHITECTURE_REFINEMENT_PROMPT

    if not ai_client.is_configured:
        return {
            "response": f"I've noted your request: \"{request.message}\". "
            "AI refinement is not configured in dev mode, but your feedback has been acknowledged.",
            "updated_architecture": None,
        }

    user_prompt = (
        f"Current architecture:\n{json.dumps(request.architecture, indent=2)}\n\n"
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
            response_text = parsed.pop("explanation", "Architecture updated based on your request.")
    except (json.JSONDecodeError, TypeError):
        pass

    return {"response": response_text, "updated_architecture": updated_architecture}
