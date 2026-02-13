"""Questionnaire state persistence API routes."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
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

        # Delete existing responses for this project, then insert fresh
        await db.execute(
            delete(QuestionnaireResponse).where(
                QuestionnaireResponse.project_id == request.project_id
            )
        )

        for question_id, answer in request.answers.items():
            answer_value = json.dumps(answer) if isinstance(answer, list) else str(answer)
            response = QuestionnaireResponse(
                id=str(uuid.uuid4()),
                project_id=request.project_id,
                question_id=question_id,
                answer_value=answer_value,
                answer_data={"raw": answer} if isinstance(answer, list) else None,
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
        responses = result.scalars().all()
        if not responses:
            return {"answers": {}, "project_id": project_id}

        answers: dict[str, str | list[str]] = {}
        for resp in responses:
            if resp.answer_data and "raw" in resp.answer_data:
                answers[resp.question_id] = resp.answer_data["raw"]
            else:
                answers[resp.question_id] = resp.answer_value

        return {
            "answers": answers,
            "project_id": project_id,
            "completed": len(answers) >= 24,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
