"""CI/CD pipeline generation and download API routes.

Supports both GitHub Actions (issue #23) and Azure DevOps (issue #24) pipeline
formats.  The ``pipeline_format`` field on each request selects the generator.
"""

import io
import logging
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import get_current_user
from app.schemas.pipeline import (
    GeneratePipelineRequest,
    GeneratePipelineResponse,
    PipelineDownloadRequest,
    PipelineFile,
    PipelineFormat,
    PipelineTemplateInfo,
    PipelineTemplateListResponse,
)
from app.services.azure_devops_generator import azure_devops_generator
from app.services.github_actions_generator import github_actions_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_files(request: GeneratePipelineRequest) -> dict[str, str]:
    """Dispatch pipeline generation to the appropriate backend generator."""
    if request.pipeline_format == PipelineFormat.azure_devops:
        return azure_devops_generator.generate_pipeline(
            architecture=request.architecture,
            iac_format=request.iac_format,
            environments=request.environments,
            include_approval_gates=request.include_approval_gates,
            project_name=request.project_name,
            service_connection=request.service_connection,
            variable_group=request.variable_group,
        )
    # Default → GitHub Actions
    return github_actions_generator.generate_workflows(
        architecture=request.architecture,
        iac_format=request.iac_format,
        environments=request.environments,
        include_approval_gates=request.include_approval_gates,
        project_name=request.project_name,
    )


def _download_prefix(pipeline_format: PipelineFormat) -> str:
    """Return the archive path prefix for each pipeline format."""
    if pipeline_format == PipelineFormat.azure_devops:
        return ""  # Azure DevOps files are placed at repo root
    return ".github/workflows/"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/templates", response_model=PipelineTemplateListResponse)
async def list_templates(user: dict = Depends(get_current_user)):
    """List available CI/CD pipeline templates (GitHub Actions + Azure DevOps)."""
    raw = github_actions_generator.list_templates()
    raw.extend(azure_devops_generator.list_templates())
    templates = [PipelineTemplateInfo(**t) for t in raw]
    return PipelineTemplateListResponse(templates=templates)


@router.get("/formats")
async def list_formats(user: dict = Depends(get_current_user)):
    """List supported pipeline formats and their IaC format support."""
    return {
        "pipeline_formats": [pf.value for pf in PipelineFormat],
        "iac_formats": azure_devops_generator.supported_formats(),
    }


@router.post("/generate", response_model=GeneratePipelineResponse)
async def generate_pipeline(
    request: GeneratePipelineRequest,
    user: dict = Depends(get_current_user),
):
    """Generate CI/CD pipeline files from an architecture definition."""
    try:
        files = _generate_files(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    file_list = [
        PipelineFile(
            name=name,
            content=content,
            size_bytes=len(content.encode("utf-8")),
        )
        for name, content in files.items()
    ]
    return GeneratePipelineResponse(
        files=file_list,
        total_files=len(files),
        iac_format=request.iac_format.value,
        pipeline_format=request.pipeline_format.value,
        environments=request.environments,
    )


@router.post("/download")
async def download_pipeline(
    request: PipelineDownloadRequest,
    user: dict = Depends(get_current_user),
):
    """Download generated pipeline files as a zip archive."""
    if request.pipeline_format == PipelineFormat.azure_devops:
        files = azure_devops_generator.generate_pipeline(
            architecture=request.architecture,
            iac_format=request.iac_format,
            environments=request.environments,
            include_approval_gates=request.include_approval_gates,
            project_name=request.project_name,
            service_connection=request.service_connection,
            variable_group=request.variable_group,
        )
    else:
        files = github_actions_generator.generate_workflows(
            architecture=request.architecture,
            iac_format=request.iac_format,
            environments=request.environments,
            include_approval_gates=request.include_approval_gates,
            project_name=request.project_name,
        )

    prefix = _download_prefix(request.pipeline_format)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(f"{prefix}{name}", content)
    buf.seek(0)

    fmt_label = request.pipeline_format.value
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f"attachment; filename=onramp-pipeline-{request.iac_format.value}-{fmt_label}.zip"
            )
        },
    )
