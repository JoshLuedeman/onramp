"""Compliance scoring API routes."""

import logging
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_architect, require_viewer
from app.db.session import get_db
from app.services.compliance_scoring import compliance_scorer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


class ScoreRequest(BaseModel):
    architecture: dict = Field(..., min_length=1)
    frameworks: list[str] = Field(..., min_length=1)
    use_ai: bool = True
    project_id: str = ""


@router.post("/evaluate")
async def evaluate_compliance(
    request: ScoreRequest,
    user: dict = Depends(require_architect),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate an architecture against compliance frameworks."""
    if request.use_ai:
        result = await compliance_scorer.score_architecture_with_ai(
            request.architecture, request.frameworks
        )
    else:
        result = compliance_scorer.score_architecture(request.architecture, request.frameworks)

    # Persist result if project_id provided and DB available
    if request.project_id and db is not None:
        try:
            from app.models import ComplianceResult, Project

            tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
            project_check = await db.execute(
                select(Project.id).where(
                    Project.id == request.project_id,
                    Project.tenant_id == tenant_id,
                )
            )
            if project_check.scalar_one_or_none() is None:
                logger.warning(
                    "Skipping compliance result persist: project %s not found for tenant %s",
                    request.project_id,
                    tenant_id,
                )
            else:
                async with db.begin_nested():
                    await db.execute(
                        delete(ComplianceResult).where(
                            ComplianceResult.project_id == request.project_id
                        )
                    )
                    record = ComplianceResult(
                        id=str(uuid.uuid4()),
                        project_id=request.project_id,
                        scoring_data=result,
                        frameworks_evaluated=request.frameworks,
                        overall_score=result.get("overall_score", 0),
                    )
                    db.add(record)
                    await db.flush()
        except Exception as e:
            logger.warning("Failed to persist compliance result: %s", e)

    return result


@router.get("/project/{project_id}")
async def get_project_compliance_results(
    project_id: str,
    user: dict = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Load persisted compliance results for a project."""
    if db is None:
        return {"results": [], "project_id": project_id}

    from app.models import ComplianceResult, Project

    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
    result = await db.execute(
        select(ComplianceResult)
        .join(Project, ComplianceResult.project_id == Project.id)
        .where(ComplianceResult.project_id == project_id, Project.tenant_id == tenant_id)
    )
    rows = result.scalars().all()
    return {
        "results": [
            {
                "id": r.id,
                "scoring_data": r.scoring_data,
                "frameworks_evaluated": r.frameworks_evaluated,
                "overall_score": r.overall_score,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "project_id": project_id,
    }
