"""Architecture generation API routes."""

import uuid
from datetime import datetime, timezone

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
    if request.use_ai:
        from app.services.ai_foundry import ai_client
        architecture = await ai_client.generate_architecture(request.answers)
    else:
        architecture = get_archetype_for_answers(request.answers)

    # Persist if project_id provided and DB available
    if request.project_id and db is not None:
        try:
            from app.models import Architecture as ArchModel
            arch_record = ArchModel(
                id=str(uuid.uuid4()),
                project_id=request.project_id,
                archetype=architecture.get("organization_size", ""),
                definition=architecture,
                ai_generated=request.use_ai,
                version=1,
                created_at=datetime.now(timezone.utc),
            )
            db.add(arch_record)
            await db.flush()
        except Exception as e:
            import logging
            logging.getLogger("onramp").warning(f"Failed to persist architecture: {e}")

    return {"architecture": architecture}
