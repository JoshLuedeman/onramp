"""API routes for architecture version history, diffing, and restore."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.version import (
    ArchitectureVersionResponse,
    RestoreVersionRequest,
    VersionDiffResponse,
    VersionListResponse,
)
from app.services import version_service

router = APIRouter(
    prefix="/api/architectures/{arch_id}/versions",
    tags=["architecture-versions"],
)


@router.get("", response_model=VersionListResponse)
async def list_versions(
    arch_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionListResponse:
    """List all versions for an architecture, newest first."""
    versions = await version_service.list_versions(db, arch_id)
    return VersionListResponse(
        versions=[
            ArchitectureVersionResponse.model_validate(v) for v in versions
        ],
        total=len(versions),
    )


@router.get("/diff", response_model=VersionDiffResponse)
async def diff_versions(
    arch_id: str,
    from_version: int = Query(..., alias="from", ge=1),
    to_version: int = Query(..., alias="to", ge=1),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionDiffResponse:
    """Compute a diff between two architecture versions."""
    ver_a = await version_service.get_version(db, arch_id, from_version)
    if ver_a is None:
        raise HTTPException(status_code=404, detail=f"Version {from_version} not found")

    ver_b = await version_service.get_version(db, arch_id, to_version)
    if ver_b is None:
        raise HTTPException(status_code=404, detail=f"Version {to_version} not found")

    diff = version_service.diff_versions(ver_a.architecture_json, ver_b.architecture_json)
    diff.from_version = from_version
    diff.to_version = to_version
    return diff


@router.get("/{version_number}", response_model=ArchitectureVersionResponse)
async def get_version(
    arch_id: str,
    version_number: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureVersionResponse:
    """Retrieve a specific architecture version."""
    version = await version_service.get_version(db, arch_id, version_number)
    if version is None:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found")
    return ArchitectureVersionResponse.model_validate(version)


@router.post("/{version_number}/restore", response_model=ArchitectureVersionResponse)
async def restore_version(
    arch_id: str,
    version_number: int,
    body: RestoreVersionRequest | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchitectureVersionResponse:
    """Restore a historical version, creating a new version from it."""
    user_id = user.get("oid", user.get("sub"))
    change_summary = body.change_summary if body else None

    restored = await version_service.restore_version(
        db=db,
        architecture_id=arch_id,
        version_number=version_number,
        created_by=user_id,
        change_summary=change_summary,
    )
    if restored is None:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found")

    return ArchitectureVersionResponse.model_validate(restored)
