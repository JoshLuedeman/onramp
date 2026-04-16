"""Pulumi code generation and download API routes."""

import io
import logging
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import get_current_user
from app.schemas.pulumi import GeneratePulumiRequest
from app.services.pulumi_generator import pulumi_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pulumi", tags=["pulumi"])


@router.get("/templates")
async def list_templates(user: dict = Depends(get_current_user)):
    """List available Pulumi templates with supported languages."""
    return {"templates": pulumi_generator.list_templates()}


@router.post("/generate")
async def generate_pulumi(
    request: GeneratePulumiRequest,
    user: dict = Depends(get_current_user),
):
    """Generate Pulumi code from an architecture definition.

    Accepts an optional ``language`` field ('typescript' or 'python').
    """
    try:
        pulumi_generator.validate_language(request.language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if request.use_ai:
        files = await pulumi_generator.generate_from_architecture_with_ai(
            request.architecture, request.language
        )
    else:
        pulumi_generator.ai_generated = False
        files = pulumi_generator.generate_from_architecture(
            request.architecture, request.language
        )

    return {
        "files": [
            {"name": name, "content": content, "size_bytes": len(content)}
            for name, content in files.items()
        ],
        "total_files": len(files),
        "language": request.language,
        "ai_generated": pulumi_generator.ai_generated,
    }


@router.post("/download")
async def download_pulumi(
    request: GeneratePulumiRequest,
    user: dict = Depends(get_current_user),
):
    """Download generated Pulumi code as a zip archive."""
    try:
        pulumi_generator.validate_language(request.language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if request.use_ai:
        files = await pulumi_generator.generate_from_architecture_with_ai(
            request.architecture, request.language
        )
    else:
        pulumi_generator.ai_generated = False
        files = pulumi_generator.generate_from_architecture(
            request.architecture, request.language
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)

    ext = "ts" if request.language == "typescript" else "py"
    filename = f"onramp-pulumi-{ext}.zip"

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
