"""Migration wave planning API routes."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db.session import get_db
from app.models.migration_wave import MigrationPlan, MigrationWave, WaveWorkload
from app.models.project import Project
from app.models.workload import Workload
from app.schemas.dependency import DependencyEdge, WorkloadSummary
from app.schemas.migration_wave import (
    MoveWorkloadRequest,
    ValidationWarning,
    WaveExportRequest,
    WaveGenerateRequest,
    WavePlanResponse,
    WaveResponse,
    WaveUpdateRequest,
    WaveWorkloadResponse,
)
from app.services.wave_planner import wave_planner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/migration", tags=["migration"])


def _wave_to_response(
    wave: MigrationWave,
    workload_map: dict[str, Workload] | None = None,
) -> WaveResponse:
    """Convert a MigrationWave ORM object to a WaveResponse."""
    wl_responses: list[WaveWorkloadResponse] = []
    for ww in wave.wave_workloads:
        wl = workload_map.get(ww.workload_id) if workload_map else None
        wl_responses.append(WaveWorkloadResponse(
            id=ww.id,
            workload_id=ww.workload_id,
            name=wl.name if wl else ww.workload_id,
            type=wl.type if wl else "unknown",
            criticality=wl.criticality if wl else "standard",
            migration_strategy=wl.migration_strategy if wl else "unknown",
            position=ww.position,
            dependencies=(wl.dependencies or []) if wl else [],
        ))
    return WaveResponse(
        id=wave.id,
        name=wave.name,
        order=wave.order,
        status=wave.status,
        notes=wave.notes,
        workloads=wl_responses,
        created_at=wave.created_at,
        updated_at=wave.updated_at,
    )


def _build_workload_summaries(
    workloads: list[Workload],
) -> tuple[list[WorkloadSummary], list[DependencyEdge]]:
    """Build summaries and edges from workload ORM objects."""
    summaries = []
    edges = []
    id_set = {w.id for w in workloads}
    for w in workloads:
        summaries.append(WorkloadSummary(
            id=w.id,
            name=w.name,
            criticality=w.criticality,
            migration_strategy=w.migration_strategy,
            project_id=w.project_id,
        ))
        for dep_id in w.dependencies or []:
            if dep_id in id_set:
                edges.append(DependencyEdge(source=dep_id, target=w.id))
    return summaries, edges


@router.post("/waves/generate", response_model=WavePlanResponse)
async def generate_waves(
    payload: WaveGenerateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WavePlanResponse:
    """Auto-generate migration waves from a project's workloads."""
    now = datetime.now(timezone.utc)

    if db is None:
        # Return mock plan with no waves when no DB is available
        plan_id = str(uuid.uuid4())
        return WavePlanResponse(
            id=plan_id,
            project_id=payload.project_id,
            name=payload.plan_name,
            strategy=payload.strategy,
            is_active=True,
            waves=[],
            warnings=[],
            created_at=now,
            updated_at=now,
        )

    try:
        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        proj_result = await db.execute(
            select(Project).where(
                Project.id == payload.project_id,
                Project.tenant_id == tenant_id,
            )
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=403, detail="Project not found or access denied"
            )

        # Load workloads
        wl_result = await db.execute(
            select(Workload).where(
                Workload.project_id == payload.project_id
            )
        )
        workloads = list(wl_result.scalars().all())
        if not workloads:
            plan_id = str(uuid.uuid4())
            return WavePlanResponse(
                id=plan_id,
                project_id=payload.project_id,
                name=payload.plan_name,
                strategy=payload.strategy,
                is_active=True,
                waves=[],
                warnings=[
                    ValidationWarning(
                        type="missing_workload",
                        message="No workloads found for this project",
                    )
                ],
                created_at=now,
                updated_at=now,
            )

        summaries, edges = _build_workload_summaries(workloads)
        wl_map = {w.id: w for w in workloads}

        # Generate waves
        wave_lists = wave_planner.generate_waves(
            summaries, edges, payload.strategy, payload.max_wave_size
        )

        # Persist plan
        plan = MigrationPlan(
            id=str(uuid.uuid4()),
            project_id=payload.project_id,
            name=payload.plan_name,
            strategy=payload.strategy,
            max_wave_size=payload.max_wave_size,
            is_active=True,
        )
        db.add(plan)
        await db.flush()

        wave_responses: list[WaveResponse] = []
        for idx, wave_workloads in enumerate(wave_lists):
            wave = MigrationWave(
                id=str(uuid.uuid4()),
                plan_id=plan.id,
                name=f"Wave {idx + 1}",
                order=idx,
                status="planned",
            )
            db.add(wave)
            await db.flush()

            wl_responses: list[WaveWorkloadResponse] = []
            for pos, ws in enumerate(wave_workloads):
                ww = WaveWorkload(
                    id=str(uuid.uuid4()),
                    wave_id=wave.id,
                    workload_id=ws.id,
                    plan_id=plan.id,
                    position=pos,
                )
                db.add(ww)

                wl = wl_map.get(ws.id)
                wl_responses.append(WaveWorkloadResponse(
                    id=ww.id,
                    workload_id=ws.id,
                    name=ws.name,
                    type=wl.type if wl else "unknown",
                    criticality=ws.criticality,
                    migration_strategy=ws.migration_strategy,
                    position=pos,
                    dependencies=(wl.dependencies or []) if wl else [],
                ))

            wave_responses.append(WaveResponse(
                id=wave.id,
                name=wave.name,
                order=wave.order,
                status=wave.status,
                notes=wave.notes,
                workloads=wl_responses,
                created_at=now,
                updated_at=now,
            ))

        await db.flush()

        return WavePlanResponse(
            id=plan.id,
            project_id=payload.project_id,
            name=plan.name,
            strategy=plan.strategy,
            is_active=plan.is_active,
            waves=wave_responses,
            warnings=[],
            created_at=now,
            updated_at=now,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate waves")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/waves", response_model=WavePlanResponse)
async def list_waves(
    project_id: str = Query(..., description="Project ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WavePlanResponse:
    """Get the active wave plan for a project."""
    now = datetime.now(timezone.utc)

    if db is None:
        return WavePlanResponse(
            id="mock-plan",
            project_id=project_id,
            name="Migration Plan",
            strategy="complexity_first",
            is_active=True,
            waves=[],
            warnings=[],
            created_at=now,
            updated_at=now,
        )

    try:
        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        proj_result = await db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.tenant_id == tenant_id,
            )
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=403, detail="Project not found or access denied"
            )

        plan_result = await db.execute(
            select(MigrationPlan)
            .options(
                selectinload(MigrationPlan.waves).selectinload(
                    MigrationWave.wave_workloads
                )
            )
            .where(
                MigrationPlan.project_id == project_id,
                MigrationPlan.is_active.is_(True),
            )
        )
        plan = plan_result.scalar_one_or_none()
        if plan is None:
            return WavePlanResponse(
                id="",
                project_id=project_id,
                name="No Plan",
                strategy="complexity_first",
                is_active=False,
                waves=[],
                warnings=[],
                created_at=now,
                updated_at=now,
            )

        # Load workloads for enrichment
        wl_ids = [
            ww.workload_id
            for wave in plan.waves
            for ww in wave.wave_workloads
        ]
        wl_map: dict[str, Workload] = {}
        if wl_ids:
            wl_result = await db.execute(
                select(Workload).where(Workload.id.in_(wl_ids))
            )
            wl_map = {w.id: w for w in wl_result.scalars().all()}

        wave_responses = [
            _wave_to_response(wave, wl_map) for wave in plan.waves
        ]

        return WavePlanResponse(
            id=plan.id,
            project_id=project_id,
            name=plan.name,
            strategy=plan.strategy,
            is_active=plan.is_active,
            waves=wave_responses,
            warnings=[],
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list waves")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/waves/{wave_id}", response_model=WaveResponse)
async def get_wave(
    wave_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WaveResponse:
    """Get a single wave by ID."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    try:
        result = await db.execute(
            select(MigrationWave)
            .options(selectinload(MigrationWave.wave_workloads))
            .where(MigrationWave.id == wave_id)
        )
        wave = result.scalar_one_or_none()
        if wave is None:
            raise HTTPException(status_code=404, detail="Wave not found")

        wl_ids = [ww.workload_id for ww in wave.wave_workloads]
        wl_map: dict[str, Workload] = {}
        if wl_ids:
            wl_result = await db.execute(
                select(Workload).where(Workload.id.in_(wl_ids))
            )
            wl_map = {w.id: w for w in wl_result.scalars().all()}

        return _wave_to_response(wave, wl_map)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get wave")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/waves/{wave_id}", response_model=WaveResponse)
async def update_wave(
    wave_id: str,
    updates: WaveUpdateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WaveResponse:
    """Update a wave's name, status, or notes."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    try:
        result = await db.execute(
            select(MigrationWave)
            .options(selectinload(MigrationWave.wave_workloads))
            .where(MigrationWave.id == wave_id)
        )
        wave = result.scalar_one_or_none()
        if wave is None:
            raise HTTPException(status_code=404, detail="Wave not found")

        if updates.name is not None:
            wave.name = updates.name
        if updates.status is not None:
            wave.status = updates.status
        if updates.notes is not None:
            wave.notes = updates.notes

        await db.flush()

        wl_ids = [ww.workload_id for ww in wave.wave_workloads]
        wl_map: dict[str, Workload] = {}
        if wl_ids:
            wl_result = await db.execute(
                select(Workload).where(Workload.id.in_(wl_ids))
            )
            wl_map = {w.id: w for w in wl_result.scalars().all()}

        return _wave_to_response(wave, wl_map)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update wave")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/waves/move", response_model=WavePlanResponse)
async def move_workload(
    payload: MoveWorkloadRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WavePlanResponse:
    """Move a workload to a different wave."""
    now = datetime.now(timezone.utc)

    if db is None:
        return WavePlanResponse(
            id="mock-plan",
            project_id="",
            name="Migration Plan",
            strategy="complexity_first",
            is_active=True,
            waves=[],
            warnings=[],
            created_at=now,
            updated_at=now,
        )

    try:
        # Find the target wave and its plan
        target_result = await db.execute(
            select(MigrationWave).where(
                MigrationWave.id == payload.target_wave_id
            )
        )
        target_wave = target_result.scalar_one_or_none()
        if target_wave is None:
            raise HTTPException(
                status_code=404, detail="Target wave not found"
            )

        # Find the wave-workload entry
        ww_result = await db.execute(
            select(WaveWorkload).where(
                WaveWorkload.workload_id == payload.workload_id,
                WaveWorkload.plan_id == target_wave.plan_id,
            )
        )
        ww = ww_result.scalar_one_or_none()
        if ww is None:
            raise HTTPException(
                status_code=404,
                detail="Workload not found in plan",
            )

        ww.wave_id = payload.target_wave_id
        ww.position = payload.position
        await db.flush()

        # Return full plan
        plan_result = await db.execute(
            select(MigrationPlan)
            .options(
                selectinload(MigrationPlan.waves).selectinload(
                    MigrationWave.wave_workloads
                )
            )
            .where(MigrationPlan.id == target_wave.plan_id)
        )
        plan = plan_result.scalar_one()

        wl_ids = [
            ww2.workload_id
            for w in plan.waves
            for ww2 in w.wave_workloads
        ]
        wl_map: dict[str, Workload] = {}
        if wl_ids:
            wl_result = await db.execute(
                select(Workload).where(Workload.id.in_(wl_ids))
            )
            wl_map = {w.id: w for w in wl_result.scalars().all()}

        return WavePlanResponse(
            id=plan.id,
            project_id=plan.project_id,
            name=plan.name,
            strategy=plan.strategy,
            is_active=plan.is_active,
            waves=[_wave_to_response(w, wl_map) for w in plan.waves],
            warnings=[],
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to move workload")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/waves/validate", response_model=WavePlanResponse)
async def validate_plan(
    payload: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WavePlanResponse:
    """Validate the current wave plan for dependency violations."""
    now = datetime.now(timezone.utc)
    project_id = payload.get("project_id", "")

    if db is None:
        return WavePlanResponse(
            id="mock-plan",
            project_id=project_id,
            name="Migration Plan",
            strategy="complexity_first",
            is_active=True,
            waves=[],
            warnings=[],
            created_at=now,
            updated_at=now,
        )

    try:
        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        proj_result = await db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.tenant_id == tenant_id,
            )
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=403, detail="Project not found or access denied"
            )

        plan_result = await db.execute(
            select(MigrationPlan)
            .options(
                selectinload(MigrationPlan.waves).selectinload(
                    MigrationWave.wave_workloads
                )
            )
            .where(
                MigrationPlan.project_id == project_id,
                MigrationPlan.is_active.is_(True),
            )
        )
        plan = plan_result.scalar_one_or_none()
        if plan is None:
            return WavePlanResponse(
                id="",
                project_id=project_id,
                name="No Plan",
                strategy="complexity_first",
                is_active=False,
                waves=[],
                warnings=[],
                created_at=now,
                updated_at=now,
            )

        # Load workloads
        wl_result = await db.execute(
            select(Workload).where(
                Workload.project_id == project_id
            )
        )
        workloads = list(wl_result.scalars().all())
        wl_map_orm = {w.id: w for w in workloads}

        summaries, edges = _build_workload_summaries(workloads)
        summary_map = {s.id: s for s in summaries}

        # Build wave dicts for validation
        wave_dicts = []
        for wave in plan.waves:
            wave_dicts.append({
                "id": wave.id,
                "name": wave.name,
                "order": wave.order,
                "workload_ids": [
                    ww.workload_id for ww in wave.wave_workloads
                ],
            })

        warnings_raw = wave_planner.validate_waves(
            wave_dicts, summary_map, edges, plan.max_wave_size
        )

        warnings = [
            ValidationWarning(**w) for w in warnings_raw
        ]

        wave_responses = [
            _wave_to_response(w, wl_map_orm) for w in plan.waves
        ]

        return WavePlanResponse(
            id=plan.id,
            project_id=project_id,
            name=plan.name,
            strategy=plan.strategy,
            is_active=plan.is_active,
            waves=wave_responses,
            warnings=warnings,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to validate plan")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/waves/export")
async def export_plan(
    payload: WaveExportRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Export the wave plan as CSV or Markdown."""
    if db is None:
        # Return empty export
        if payload.format == "csv":
            header = (
                "Wave,Wave Status,Workload,Type,"
                "Criticality,Strategy,Dependencies\r\n"
            )
            return PlainTextResponse(
                content=header, media_type="text/csv"
            )
        return PlainTextResponse(
            content="# Migration Wave Plan\n\n*No waves generated*\n",
            media_type="text/markdown",
        )

    try:
        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        proj_result = await db.execute(
            select(Project).where(
                Project.id == payload.project_id,
                Project.tenant_id == tenant_id,
            )
        )
        if proj_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=403, detail="Project not found or access denied"
            )

        plan_result = await db.execute(
            select(MigrationPlan)
            .options(
                selectinload(MigrationPlan.waves).selectinload(
                    MigrationWave.wave_workloads
                )
            )
            .where(
                MigrationPlan.project_id == payload.project_id,
                MigrationPlan.is_active.is_(True),
            )
        )
        plan = plan_result.scalar_one_or_none()
        if plan is None:
            if payload.format == "csv":
                return PlainTextResponse(
                    content="No plan found\r\n",
                    media_type="text/csv",
                )
            return PlainTextResponse(
                content="# Migration Wave Plan\n\n*No plan found*\n",
                media_type="text/markdown",
            )

        # Build export data
        wl_ids = [
            ww.workload_id
            for wave in plan.waves
            for ww in wave.wave_workloads
        ]
        wl_map: dict[str, Workload] = {}
        if wl_ids:
            wl_result = await db.execute(
                select(Workload).where(Workload.id.in_(wl_ids))
            )
            wl_map = {w.id: w for w in wl_result.scalars().all()}

        waves_data = []
        for wave in plan.waves:
            wl_data = []
            for ww in wave.wave_workloads:
                wl = wl_map.get(ww.workload_id)
                wl_data.append({
                    "name": wl.name if wl else ww.workload_id,
                    "type": wl.type if wl else "unknown",
                    "criticality": (
                        wl.criticality if wl else "standard"
                    ),
                    "migration_strategy": (
                        wl.migration_strategy if wl else "unknown"
                    ),
                    "dependencies": (
                        (wl.dependencies or []) if wl else []
                    ),
                })
            waves_data.append({
                "name": wave.name,
                "status": wave.status,
                "workloads": wl_data,
            })

        if payload.format == "csv":
            content = wave_planner.export_csv(waves_data)
            return PlainTextResponse(
                content=content, media_type="text/csv"
            )
        else:
            content = wave_planner.export_markdown(waves_data)
            return PlainTextResponse(
                content=content, media_type="text/markdown"
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to export plan")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/waves/{wave_id}")
async def delete_wave(
    wave_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a wave from a plan."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    try:
        result = await db.execute(
            select(MigrationWave).where(MigrationWave.id == wave_id)
        )
        wave = result.scalar_one_or_none()
        if wave is None:
            raise HTTPException(status_code=404, detail="Wave not found")

        await db.delete(wave)
        await db.flush()
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete wave")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
