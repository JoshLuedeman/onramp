"""Architecture generation API routes."""

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
