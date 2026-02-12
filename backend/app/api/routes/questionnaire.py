"""Questionnaire API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.services.questionnaire import questionnaire_service

router = APIRouter(prefix="/api/questionnaire", tags=["questionnaire"])


class AnswerSubmission(BaseModel):
    question_id: str
    answer: str | list[str]


class QuestionnaireState(BaseModel):
    answers: dict[str, str | list[str]] = {}


@router.get("/categories")
async def get_categories(user: dict = Depends(get_current_user)):
    """Get all question categories."""
    return {"categories": questionnaire_service.get_categories()}


@router.get("/questions")
async def get_all_questions(user: dict = Depends(get_current_user)):
    """Get all questions."""
    return {"questions": questionnaire_service.get_all_questions()}


@router.get("/questions/{category}")
async def get_questions_by_category(
    category: str, user: dict = Depends(get_current_user)
):
    """Get questions for a specific category."""
    questions = questionnaire_service.get_questions_for_category(category)
    if not questions:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    return {"category": category, "questions": questions}


@router.post("/next")
async def get_next_question(
    state: QuestionnaireState, user: dict = Depends(get_current_user)
):
    """Get the next unanswered question based on current state."""
    org_size = state.answers.get("org_size")
    org_size_str = org_size if isinstance(org_size, str) else None
    next_q = questionnaire_service.get_next_question(state.answers, org_size_str)

    if next_q is None:
        return {"complete": True, "question": None}

    progress = questionnaire_service.get_progress(state.answers)
    return {"complete": False, "question": next_q, "progress": progress}


@router.post("/validate")
async def validate_answer(
    submission: AnswerSubmission, user: dict = Depends(get_current_user)
):
    """Validate an answer for a question."""
    is_valid = questionnaire_service.validate_answer(
        submission.question_id, submission.answer
    )
    return {"valid": is_valid, "question_id": submission.question_id}


@router.post("/progress")
async def get_progress(
    state: QuestionnaireState, user: dict = Depends(get_current_user)
):
    """Get questionnaire completion progress."""
    return questionnaire_service.get_progress(state.answers)
