"""Bicep template preview and download API routes."""

import logging
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_architect, require_viewer
from app.db.session import get_db
from app.services.bicep_generator import bicep_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bicep", tags=["bicep"])


class GenerateBicepRequest(BaseModel):
    architecture: dict
    use_ai: bool = True
    project_id: str = ""


@router.get("/templates")
async def list_templates(user: dict = Depends(require_viewer)):
    """List available Bicep template modules."""
    return {"templates": bicep_generator.list_templates()}


@router.get("/templates/{template_name}")
async def get_template(template_name: str, user: dict = Depends(require_viewer)):
    """Preview a specific Bicep template."""
    content = bicep_generator.get_template(f"{template_name}.bicep")
    if content is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
    return {"name": template_name, "content": content}


@router.post("/generate")
async def generate_bicep(
    request: GenerateBicepRequest,
    user: dict = Depends(require_architect),
    db: AsyncSession = Depends(get_db),
):
    """Generate Bicep templates from an architecture definition."""
    if request.use_ai:
        files = await bicep_generator.generate_from_architecture_with_ai(request.architecture)
    else:
        bicep_generator.ai_generated = False
        files = bicep_generator.generate_from_architecture(request.architecture)

    # Persist generated files if project_id provided and DB available
    if request.project_id and db is not None:
        try:
            from app.models import BicepFile, Project

            tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
            project_check = await db.execute(
                select(Project.id).where(
                    Project.id == request.project_id,
                    Project.tenant_id == tenant_id,
                )
            )
            if project_check.scalar_one_or_none() is None:
                logger.warning(
                    "Skipping bicep file persist: project %s not found for tenant %s",
                    request.project_id,
                    tenant_id,
                )
            else:
                async with db.begin_nested():
                    await db.execute(
                        delete(BicepFile).where(BicepFile.project_id == request.project_id)
                    )
                    for name, content in files.items():
                        record = BicepFile(
                            id=str(uuid.uuid4()),
                            project_id=request.project_id,
                            file_name=name,
                            file_path=f"modules/{name}",
                            content=content,
                            size_bytes=len(content),
                        )
                        db.add(record)
                    await db.flush()
        except Exception as e:
            logger.warning("Failed to persist bicep files: %s", e)

    return {
        "files": [
            {"name": name, "content": content, "size_bytes": len(content)}
            for name, content in files.items()
        ],
        "total_files": len(files),
        "ai_generated": bicep_generator.ai_generated,
    }


@router.get("/project/{project_id}")
async def get_project_bicep_files(
    project_id: str,
    user: dict = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Load persisted Bicep files for a project."""
    if db is None:
        return {"files": [], "project_id": project_id}

    from app.models import BicepFile, Project

    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
    result = await db.execute(
        select(BicepFile)
        .join(Project, BicepFile.project_id == Project.id)
        .where(BicepFile.project_id == project_id, Project.tenant_id == tenant_id)
    )
    rows = result.scalars().all()
    return {
        "files": [
            {
                "name": r.file_name,
                "content": r.content,
                "size_bytes": r.size_bytes,
                "file_path": r.file_path,
            }
            for r in rows
        ],
        "project_id": project_id,
    }


@router.post("/download")
async def download_bicep(
    request: GenerateBicepRequest, user: dict = Depends(require_architect)
):
    """Download generated Bicep templates as a combined response."""
    if request.use_ai:
        files = await bicep_generator.generate_from_architecture_with_ai(request.architecture)
    else:
        bicep_generator.ai_generated = False
        files = bicep_generator.generate_from_architecture(request.architecture)

    # Combine all files into a single downloadable text
    combined = []
    for name, content in files.items():
        combined.append(f"// === {name} ===\n")
        combined.append(content)
        combined.append("\n\n")

    return Response(
        content="".join(combined),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=onramp-landing-zone.bicep"},
    )
