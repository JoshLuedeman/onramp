"""Terraform HCL generation and download API routes."""

import io
import logging
import zipfile

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.auth import get_current_user
from app.schemas.terraform import (
    TerraformDownloadRequest,
    TerraformFile,
    TerraformGenerateRequest,
    TerraformGenerateResponse,
    TerraformTemplateInfo,
    TerraformTemplateListResponse,
)
from app.services.terraform_generator import terraform_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terraform", tags=["terraform"])


@router.get("/templates", response_model=TerraformTemplateListResponse)
async def list_templates(user: dict = Depends(get_current_user)):
    """List available Terraform module templates."""
    raw = terraform_generator.list_templates()
    templates = [TerraformTemplateInfo(**t) for t in raw]
    return TerraformTemplateListResponse(templates=templates)


@router.post("/generate", response_model=TerraformGenerateResponse)
async def generate_terraform(
    request: TerraformGenerateRequest,
    user: dict = Depends(get_current_user),
):
    """Generate Terraform HCL from an architecture definition."""
    if request.use_ai:
        files = await terraform_generator.generate_from_architecture_with_ai(
            request.architecture
        )
    else:
        terraform_generator.ai_generated = False
        files = terraform_generator.generate_from_architecture(request.architecture)

    file_list = [
        TerraformFile(name=name, content=content, size_bytes=len(content))
        for name, content in files.items()
    ]
    return TerraformGenerateResponse(
        files=file_list,
        total_files=len(files),
        ai_generated=terraform_generator.ai_generated,
    )


@router.post("/download")
async def download_terraform(
    request: TerraformDownloadRequest,
    user: dict = Depends(get_current_user),
):
    """Download generated Terraform configuration as a zip archive."""
    if request.use_ai:
        files = await terraform_generator.generate_from_architecture_with_ai(
            request.architecture
        )
    else:
        terraform_generator.ai_generated = False
        files = terraform_generator.generate_from_architecture(request.architecture)

    # Build a zip archive in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(f"onramp-terraform/{name}", content)
    buf.seek(0)

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=onramp-terraform.zip"
        },
    )
