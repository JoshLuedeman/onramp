"""Workload API routes — import, list, create, update, delete, map."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.workload import Workload
from app.schemas.workload import (
    WorkloadCreate,
    WorkloadImportResult,
    WorkloadResponse,
    WorkloadUpdate,
)
from app.schemas.workload_mapping import MappingOverride, MappingRequest, MappingResponse
from app.services.workload_importer import detect_format, parse_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workloads", tags=["workloads"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _to_response(workload: Workload) -> WorkloadResponse:
    return WorkloadResponse(
        id=workload.id,
        project_id=workload.project_id,
        name=workload.name,
        type=workload.type,
        source_platform=workload.source_platform,
        cpu_cores=workload.cpu_cores,
        memory_gb=workload.memory_gb,
        storage_gb=workload.storage_gb,
        os_type=workload.os_type,
        os_version=workload.os_version,
        criticality=workload.criticality,
        compliance_requirements=workload.compliance_requirements or [],
        dependencies=workload.dependencies or [],
        migration_strategy=workload.migration_strategy,
        notes=workload.notes,
        target_subscription_id=workload.target_subscription_id,
        mapping_reasoning=workload.mapping_reasoning,
        created_at=workload.created_at,
        updated_at=workload.updated_at,
    )


@router.post("/import", response_model=WorkloadImportResult)
async def import_workloads(
    file: UploadFile = File(...),
    project_id: str = Query(..., description="Target project ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkloadImportResult:
    """Parse an uploaded CSV or JSON file and bulk-insert workloads."""
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    filename = file.filename or "upload.csv"
    fmt = detect_format(filename, content)
    logger.info("Importing workloads from %s (format: %s, size: %d)", filename, fmt, len(content))

    # Tenant/project scoping — only enforced when a real DB is available
    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
    if db is not None:
        proj_result = await db.execute(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Project not found or access denied")

    # Parse file — collect row-level errors instead of aborting entirely
    try:
        parsed, errors = parse_file(content, filename, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not parsed and not errors:
        return WorkloadImportResult(
            imported_count=0, failed_count=0, errors=[], workloads=[]
        )

    # Persist to DB (or return mock if no DB)
    created: list[WorkloadResponse] = []
    now = datetime.now(timezone.utc)

    if db is None:
        for wl in parsed:
            mock = WorkloadResponse(
                id=str(uuid.uuid4()),
                project_id=wl.project_id,
                name=wl.name,
                type=wl.type,
                source_platform=wl.source_platform,
                cpu_cores=wl.cpu_cores,
                memory_gb=wl.memory_gb,
                storage_gb=wl.storage_gb,
                os_type=wl.os_type,
                os_version=wl.os_version,
                criticality=wl.criticality,
                compliance_requirements=wl.compliance_requirements,
                dependencies=wl.dependencies,
                migration_strategy=wl.migration_strategy,
                notes=wl.notes,
                created_at=now,
                updated_at=now,
            )
            created.append(mock)
    else:
        try:
            db_workloads = [
                Workload(
                    id=str(uuid.uuid4()),
                    project_id=wl.project_id,
                    name=wl.name,
                    type=wl.type,
                    source_platform=wl.source_platform,
                    cpu_cores=wl.cpu_cores,
                    memory_gb=wl.memory_gb,
                    storage_gb=wl.storage_gb,
                    os_type=wl.os_type,
                    os_version=wl.os_version,
                    criticality=wl.criticality,
                    compliance_requirements=wl.compliance_requirements,
                    dependencies=wl.dependencies,
                    migration_strategy=wl.migration_strategy,
                    notes=wl.notes,
                    created_at=now,
                    updated_at=now,
                )
                for wl in parsed
            ]
            for row in db_workloads:
                db.add(row)
            await db.flush()
            created = [_to_response(row) for row in db_workloads]
        except Exception as exc:
            logger.exception("DB error during workload import")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info(
        "Import complete: %d imported, %d failed", len(created), len(errors)
    )
    return WorkloadImportResult(
        imported_count=len(created),
        failed_count=len(errors),
        errors=errors,
        workloads=created,
    )


@router.get("", response_model=dict)
async def list_workloads(
    project_id: str = Query(..., description="Project ID to filter by"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all workloads for a given project."""
    if db is None:
        return {"workloads": [], "total": 0}

    try:
        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        proj_result = await db.execute(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Project not found or access denied")

        result = await db.execute(
            select(Workload).where(Workload.project_id == project_id)
        )
        workloads = result.scalars().all()
        return {
            "workloads": [_to_response(w) for w in workloads],
            "total": len(workloads),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list workloads")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("", response_model=WorkloadResponse)
async def create_workload(
    payload: WorkloadCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkloadResponse:
    """Create a single workload (manual entry)."""
    now = datetime.now(timezone.utc)

    if db is None:
        return WorkloadResponse(
            id=str(uuid.uuid4()),
            project_id=payload.project_id,
            name=payload.name,
            type=payload.type,
            source_platform=payload.source_platform,
            cpu_cores=payload.cpu_cores,
            memory_gb=payload.memory_gb,
            storage_gb=payload.storage_gb,
            os_type=payload.os_type,
            os_version=payload.os_version,
            criticality=payload.criticality,
            compliance_requirements=payload.compliance_requirements,
            dependencies=payload.dependencies,
            migration_strategy=payload.migration_strategy,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )

    try:
        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        proj_result = await db.execute(
            select(Project).where(Project.id == payload.project_id, Project.tenant_id == tenant_id)
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Project not found or access denied")

        workload = Workload(
            id=str(uuid.uuid4()),
            project_id=payload.project_id,
            name=payload.name,
            type=payload.type,
            source_platform=payload.source_platform,
            cpu_cores=payload.cpu_cores,
            memory_gb=payload.memory_gb,
            storage_gb=payload.storage_gb,
            os_type=payload.os_type,
            os_version=payload.os_version,
            criticality=payload.criticality,
            compliance_requirements=payload.compliance_requirements,
            dependencies=payload.dependencies,
            migration_strategy=payload.migration_strategy,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        db.add(workload)
        await db.flush()
        return _to_response(workload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create workload")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/{workload_id}", response_model=WorkloadResponse)
async def update_workload(
    workload_id: str,
    updates: WorkloadUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkloadResponse:
    """Update a workload by ID."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    try:
        result = await db.execute(
            select(Workload).where(Workload.id == workload_id)
        )
        workload = result.scalar_one_or_none()
        if not workload:
            raise HTTPException(status_code=404, detail="Workload not found")

        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        proj_result = await db.execute(
            select(Project).where(Project.id == workload.project_id, Project.tenant_id == tenant_id)
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Project not found or access denied")

        update_data = updates.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] is None:
            raise HTTPException(status_code=422, detail="name cannot be null")
        for field, value in update_data.items():
            setattr(workload, field, value)
        workload.updated_at = datetime.now(timezone.utc)

        await db.flush()
        return _to_response(workload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update workload %s", workload_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{workload_id}")
async def delete_workload(
    workload_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a workload by ID."""
    if db is None:
        return {"deleted": True, "message": "Database not configured"}

    try:
        result = await db.execute(
            select(Workload).where(Workload.id == workload_id)
        )
        workload = result.scalar_one_or_none()
        if not workload:
            raise HTTPException(status_code=404, detail="Workload not found")

        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        proj_result = await db.execute(
            select(Project).where(Project.id == workload.project_id, Project.tenant_id == tenant_id)
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Project not found or access denied")

        await db.delete(workload)
        return {"deleted": True, "id": workload_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete workload %s", workload_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# POST /api/workloads/map — generate workload-to-subscription mappings
# ---------------------------------------------------------------------------

@router.post("/map", response_model=MappingResponse)
async def map_workloads(
    payload: MappingRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MappingResponse:
    """Generate AI-powered workload-to-subscription mappings for a project."""
    from app.services.workload_mapper import generate_mapping, validate_mappings

    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))

    # Fetch workloads for project
    if db is None:
        return MappingResponse(mappings=[], warnings=["Database not configured"])

    try:
        proj_result = await db.execute(
            select(Project).where(Project.id == payload.project_id, Project.tenant_id == tenant_id)
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Project not found or access denied")

        wl_result = await db.execute(
            select(Workload).where(Workload.project_id == payload.project_id)
        )
        workloads = wl_result.scalars().all()

        if not workloads:
            return MappingResponse(mappings=[], warnings=["No workloads found for this project"])

        # Fetch architecture for subscription list
        architecture: dict = {}
        if payload.architecture_id:
            from app.models import Architecture as ArchModel
            # Scope the architecture lookup to the tenant via the project relationship
            arch_result = await db.execute(
                select(ArchModel)
                .join(Project, ArchModel.project_id == Project.id)
                .where(
                    ArchModel.id == payload.architecture_id,
                    ArchModel.project_id == payload.project_id,
                    Project.tenant_id == tenant_id,
                )
            )
            arch_record = arch_result.scalar_one_or_none()
            if arch_record:
                architecture = arch_record.architecture_data or {}
        else:
            # Try to load the project's architecture — already scoped to the tenant's project
            from app.models import Architecture as ArchModel
            arch_result = await db.execute(
                select(ArchModel)
                .join(Project, ArchModel.project_id == Project.id)
                .where(
                    ArchModel.project_id == payload.project_id,
                    Project.tenant_id == tenant_id,
                )
            )
            arch_record = arch_result.scalar_one_or_none()
            if arch_record:
                architecture = arch_record.architecture_data or {}

        workloads_dicts = [
            {
                "id": w.id,
                "name": w.name,
                "type": w.type,
                "criticality": w.criticality,
                "compliance_requirements": w.compliance_requirements or [],
                "dependencies": w.dependencies or [],
            }
            for w in workloads
        ]

        ai_client = None
        if payload.use_ai:
            from app.services.ai_foundry import ai_client as _ai_client
            ai_client = _ai_client

        mappings = await generate_mapping(workloads_dicts, architecture, ai_client)
        global_warnings = validate_mappings(mappings, workloads_dicts)

        # Surface a user-visible warning when no subscriptions are in the architecture
        if not mappings and not (architecture.get("subscriptions") or []):
            global_warnings.insert(
                0,
                "No subscriptions found in the project architecture. "
                "Generate an architecture first, then retry mapping.",
            )

        logger.info(
            "Generated %d mappings for project %s (%d warnings)",
            len(mappings),
            payload.project_id,
            len(global_warnings),
        )
        return MappingResponse(mappings=mappings, warnings=global_warnings)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate mappings for project %s", payload.project_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# PATCH /api/workloads/{workload_id}/mapping — persist manual override
# ---------------------------------------------------------------------------

@router.patch("/{workload_id}/mapping", response_model=WorkloadResponse)
async def override_workload_mapping(
    workload_id: str,
    override: MappingOverride,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkloadResponse:
    """Manually override the AI-recommended subscription for a workload."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    try:
        result = await db.execute(
            select(Workload).where(Workload.id == workload_id)
        )
        workload = result.scalar_one_or_none()
        if not workload:
            raise HTTPException(status_code=404, detail="Workload not found")

        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        proj_result = await db.execute(
            select(Project).where(
                Project.id == workload.project_id, Project.tenant_id == tenant_id
            )
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Project not found or access denied")

        workload.target_subscription_id = override.target_subscription_id
        workload.mapping_reasoning = override.reasoning
        workload.updated_at = datetime.now(timezone.utc)

        await db.flush()
        logger.info("Overrode mapping for workload %s → %s", workload_id, override.target_subscription_id)
        return _to_response(workload)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to override mapping for workload %s", workload_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
