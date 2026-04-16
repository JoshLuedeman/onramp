"""Governance task execution API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.task_execution import (
    TaskExecutionResponse,
    TaskListResponse,
    TaskScheduleRequest,
    TaskType,
)
from app.services.task_scheduler import task_scheduler

router = APIRouter(
    prefix="/api/governance/tasks", tags=["governance-tasks"]
)


@router.get("/", response_model=TaskListResponse)
async def list_task_executions(
    task_type: str | None = None,
    status: str | None = None,
    project_id: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List governance task executions with optional filters."""
    tasks = await task_scheduler.list_executions(
        db, task_type=task_type, status=status, project_id=project_id
    )
    return TaskListResponse(tasks=tasks, total=len(tasks))


@router.get("/{task_id}", response_model=TaskExecutionResponse)
async def get_task_execution(
    task_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific task execution."""
    execution = await task_scheduler.get_execution(task_id, db)
    if execution is None:
        raise HTTPException(
            status_code=404, detail="Task execution not found"
        )
    return execution


@router.post(
    "/trigger/{task_type}",
    response_model=TaskExecutionResponse,
)
async def trigger_task(
    task_type: TaskType,
    request: TaskScheduleRequest | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a governance scan task."""
    tenant_id = user.get("tenant_id")
    project_id = (
        request.project_id if request else None
    )
    # Allow request to override tenant_id if provided
    if request and request.tenant_id:
        tenant_id = request.tenant_id

    execution = await task_scheduler.trigger_task(
        task_type=task_type.value,
        tenant_id=tenant_id,
        project_id=project_id,
    )
    return execution


@router.delete(
    "/{task_id}", response_model=TaskExecutionResponse
)
async def cancel_task_execution(
    task_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending or running task execution."""
    execution = await task_scheduler.cancel_execution(
        task_id, db
    )
    if execution is None:
        raise HTTPException(
            status_code=404, detail="Task execution not found"
        )
    return execution
