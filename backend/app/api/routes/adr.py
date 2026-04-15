"""ADR generation and export API routes."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.adr import (
    ADRExportRequest,
    ADRGenerateRequest,
    ADRGenerateResponse,
)
from app.services.adr_generator import export_adrs, generate_adrs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/architecture", tags=["architecture"])


@router.post("/adrs/generate", response_model=ADRGenerateResponse)
async def generate_adrs_endpoint(
    request: ADRGenerateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
):
    """Generate Architecture Decision Records from architecture data."""
    logger.info("Generating ADRs for user %s", user.get("name", "unknown"))
    adrs = generate_adrs(
        architecture=request.architecture,
        answers=request.answers,
        use_ai=request.use_ai,
    )
    return ADRGenerateResponse(adrs=adrs, project_id=request.project_id)


@router.post("/adrs/export")
async def export_adrs_endpoint(
    request: ADRExportRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
):
    """Export ADRs as Markdown content."""
    logger.info("Exporting %d ADRs in %s format", len(request.adrs), request.format)
    content = export_adrs(adrs=request.adrs, format=request.format)
    return {"content": content}
