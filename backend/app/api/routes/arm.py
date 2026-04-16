"""ARM template generation, validation, and download API routes."""

import io
import logging
import zipfile

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.auth import get_current_user
from app.schemas.arm import (
    DownloadARMRequest,
    GenerateARMRequest,
    ValidateARMRequest,
)
from app.services.arm_generator import arm_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/arm", tags=["arm"])


@router.post("/generate")
async def generate_arm(
    request: GenerateARMRequest,
    user: dict = Depends(get_current_user),
):
    """Generate ARM JSON templates from an architecture definition."""
    if request.use_ai:
        files = await arm_generator.generate_from_architecture_with_ai(
            request.architecture
        )
    else:
        arm_generator.ai_generated = False
        files = arm_generator.generate_from_architecture(request.architecture)

    return {
        "files": [
            {"name": name, "content": content, "size_bytes": len(content)}
            for name, content in files.items()
        ],
        "total_files": len(files),
        "ai_generated": arm_generator.ai_generated,
    }


@router.post("/download")
async def download_arm(
    request: DownloadARMRequest,
    user: dict = Depends(get_current_user),
):
    """Download generated ARM templates as a zip archive."""
    if request.use_ai:
        files = await arm_generator.generate_from_architecture_with_ai(
            request.architecture
        )
    else:
        arm_generator.ai_generated = False
        files = arm_generator.generate_from_architecture(request.architecture)

    # Create an in-memory zip file
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=onramp-arm-templates.zip"
        },
    )


@router.post("/validate")
async def validate_arm(
    request: ValidateARMRequest,
    user: dict = Depends(get_current_user),
):
    """Validate an ARM template structure."""
    result = arm_generator.validate_template(request.template)
    return result
