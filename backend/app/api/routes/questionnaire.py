"""Questionnaire API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user
from app.services.archetypes import RECOMMENDED_DEFAULTS
from app.services.questionnaire import questionnaire_service

router = APIRouter(prefix="/api/questionnaire", tags=["questionnaire"])

RECOMMENDATION_REASONS: dict[str, str] = {
    "org_size": "Medium-sized organizations benefit from a balanced CAF landing zone with full management group hierarchy without the complexity of an enterprise deployment.",
    "identity_provider": "Microsoft Entra ID is the native Azure identity provider, offering the deepest integration with Azure RBAC, conditional access, and PIM.",
    "pim_required": "PIM provides just-in-time privileged access, reducing the attack surface for administrative accounts.",
    "mfa_requirement": "MFA for all users is a security baseline recommended by Microsoft and required by most compliance frameworks.",
    "management_group_strategy": "The CAF recommended management group hierarchy provides proven separation of platform and workload concerns.",
    "naming_convention": "The CAF standard naming convention ensures consistency across resources and is widely recognized by Azure practitioners.",
    "network_topology": "Hub-spoke is the most commonly deployed and well-documented Azure network topology, offering a good balance of control and simplicity.",
    "hybrid_connectivity": "VPN provides a cost-effective starting point for hybrid connectivity that can be upgraded to ExpressRoute later.",
    "dns_strategy": "Azure DNS provides native integration with Azure Private DNS zones and virtual network resolution.",
    "security_level": "Standard security provides a strong baseline with Defender for Cloud and essential security controls without the overhead of advanced features.",
    "siem_integration": "Microsoft Sentinel provides native Azure integration for threat detection, investigation, and response.",
    "monitoring_strategy": "Azure Monitor and Log Analytics provide comprehensive native monitoring with minimal setup and direct integration with Azure resources.",
    "backup_dr": "Geo-redundant backup protects against regional outages while maintaining cost efficiency compared to full multi-region DR.",
    "tagging_strategy": "These core tags (environment, cost center, owner, application) cover the most critical governance needs for cost management and accountability.",
    "cost_management": "Treating cost management as critical ensures budgets and alerts are enforced from day one, preventing unexpected spend.",
    "iac_tool": "Bicep is Azure-native, has first-class tooling support, and compiles directly to ARM templates.",
    "cicd_platform": "GitHub Actions offers tight integration with GitHub repositories and a generous free tier with native Azure deployment actions.",
    "primary_region": "East US offers the broadest set of Azure services and availability zones, making it a reliable default primary region.",
}


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


@router.post("/resolve-unsure")
async def resolve_unsure(
    state: QuestionnaireState, user: dict = Depends(get_current_user)
):
    """Resolve '_unsure' answers to recommended defaults with explanations."""
    resolved_answers = dict(state.answers)
    recommendations = []
    for key, value in state.answers.items():
        if value == "_unsure" and key in RECOMMENDED_DEFAULTS:
            recommended = RECOMMENDED_DEFAULTS[key]
            resolved_answers[key] = recommended
            recommendations.append({
                "question_id": key,
                "recommended_value": recommended,
                "reason": RECOMMENDATION_REASONS.get(
                    key, "This is the recommended default based on Azure CAF best practices."
                ),
            })
    return {"resolved_answers": resolved_answers, "recommendations": recommendations}


@router.post("/progress")
async def get_progress(
    state: QuestionnaireState, user: dict = Depends(get_current_user)
):
    """Get questionnaire completion progress."""
    return questionnaire_service.get_progress(state.answers)
