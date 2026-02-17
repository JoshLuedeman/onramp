"""Bicep template preview and download API routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import get_current_user
from app.services.bicep_generator import bicep_generator

router = APIRouter(prefix="/api/bicep", tags=["bicep"])


class GenerateBicepRequest(BaseModel):
    architecture: dict
    use_ai: bool = True


@router.get("/templates")
async def list_templates(user: dict = Depends(get_current_user)):
    """List available Bicep template modules."""
    return {"templates": bicep_generator.list_templates()}


@router.get("/templates/{template_name}")
async def get_template(template_name: str, user: dict = Depends(get_current_user)):
    """Preview a specific Bicep template."""
    content = bicep_generator.get_template(f"{template_name}.bicep")
    if content is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
    return {"name": template_name, "content": content}


@router.post("/generate")
async def generate_bicep(
    request: GenerateBicepRequest, user: dict = Depends(get_current_user)
):
    """Generate Bicep templates from an architecture definition."""
    if request.use_ai:
        files = await bicep_generator.generate_from_architecture_with_ai(request.architecture)
    else:
        bicep_generator.ai_generated = False
        files = bicep_generator.generate_from_architecture(request.architecture)
    return {
        "files": [
            {"name": name, "content": content, "size_bytes": len(content)}
            for name, content in files.items()
        ],
        "total_files": len(files),
        "ai_generated": bicep_generator.ai_generated,
    }


@router.post("/download")
async def download_bicep(
    request: GenerateBicepRequest, user: dict = Depends(get_current_user)
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
