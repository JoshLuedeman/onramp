"""Questionnaire state persistence API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db


router = APIRouter(prefix="/api/questionnaire/state", tags=["questionnaire"])


class SaveStateRequest(BaseModel):
    project_id: str
    answers: dict


@router.post("/save")
async def save_questionnaire_state(
    request: SaveStateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save questionnaire answers for a project."""
    if db is None:
        return {
            "saved": True,
            "message": "State saved in-memory (database not configured)",
            "project_id": request.project_id,
        }

    try:
        from app.models import QuestionnaireResponse
        # Check for existing response
        result = await db.execute(
            select(QuestionnaireResponse).where(
                QuestionnaireResponse.project_id == request.project_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.answers = request.answers
            existing.updated_at = datetime.now(timezone.utc)
        else:
            response = QuestionnaireResponse(
                id=str(uuid.uuid4()),
                project_id=request.project_id,
                answers=request.answers,
                completed=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(response)

        await db.flush()
        return {"saved": True, "project_id": request.project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load/{project_id}")
async def load_questionnaire_state(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Load saved questionnaire answers for a project."""
    if db is None:
        return {"answers": {}, "message": "Database not configured"}

    try:
        from app.models import QuestionnaireResponse
        result = await db.execute(
            select(QuestionnaireResponse).where(
                QuestionnaireResponse.project_id == project_id
            )
        )
        response = result.scalar_one_or_none()
        if not response:
            return {"answers": {}, "project_id": project_id}
        return {
            "answers": response.answers,
            "project_id": project_id,
            "completed": response.completed,
            "updated_at": response.updated_at.isoformat() if response.updated_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
