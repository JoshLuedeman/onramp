"""Security posture advisor API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas.security import (
    RemediationStep,
    SecurityAnalysisResult,
    SecurityAnalyzeRequest,
    SecurityCheck,
    SecurityFinding,
)
from app.services.security_analyzer import security_analyzer

router = APIRouter(prefix="/api/security", tags=["security"])


@router.post("/analyze", response_model=SecurityAnalysisResult)
async def analyze_architecture(
    body: SecurityAnalyzeRequest,
    user: dict = Depends(get_current_user),
) -> SecurityAnalysisResult:
    """Analyze an architecture for security issues."""
    result = security_analyzer.analyze(
        architecture=body.architecture,
        use_ai=body.use_ai,
    )
    return result


@router.get("/checks", response_model=list[SecurityCheck])
async def list_checks(
    user: dict = Depends(get_current_user),
) -> list[SecurityCheck]:
    """List all available security checks."""
    return security_analyzer.get_available_checks()


@router.post("/fix", response_model=RemediationStep)
async def apply_fix(
    finding_id: str,
    architecture: dict,
    user: dict = Depends(get_current_user),
) -> RemediationStep:
    """Apply an auto-fix for a specific finding.

    Re-runs analysis to locate the finding by id, then returns the
    remediation step with architecture changes.
    """
    # Re-analyze to get findings
    result = security_analyzer.analyze(architecture=architecture)
    target: SecurityFinding | None = None
    for f in result.findings:
        if f.id == finding_id:
            target = f
            break

    if target is None:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")

    if not target.auto_fixable:
        raise HTTPException(
            status_code=400,
            detail=f"Finding '{finding_id}' is not auto-fixable",
        )

    return security_analyzer.get_remediation(target)
