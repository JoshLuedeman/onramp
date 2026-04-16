"""Background task scheduler for periodic governance scans.

Uses APScheduler's AsyncIOScheduler to run governance tasks
(drift detection, policy compliance, RBAC health, tagging compliance)
on configurable intervals within FastAPI's async event loop.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.models.base import generate_uuid

logger = logging.getLogger(__name__)

# Type alias for async task functions
TaskFunc = Callable[..., Coroutine[Any, Any, dict | None]]


class _RegisteredTask:
    """Metadata for a registered governance task."""

    __slots__ = (
        "name",
        "func",
        "interval_seconds",
        "description",
    )

    def __init__(
        self,
        name: str,
        func: TaskFunc,
        interval_seconds: int,
        description: str,
    ):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.description = description


class TaskSchedulerService:
    """Manages periodic governance task execution.

    Lifecycle:
        1. Register task functions with ``register_task`` or the
           ``@task_scheduler.periodic`` decorator.
        2. Call ``start()`` during FastAPI lifespan startup.
        3. Call ``shutdown()`` during FastAPI lifespan teardown.
    """

    def __init__(self) -> None:
        self._scheduler: Any | None = None
        self._registry: dict[str, _RegisteredTask] = {}
        self._running = False

    # ------------------------------------------------------------------
    # Task registration
    # ------------------------------------------------------------------

    def register_task(
        self,
        name: str,
        func: TaskFunc,
        interval_seconds: int = 3600,
        description: str = "",
    ) -> None:
        """Register an async function as a periodic governance task."""
        self._registry[name] = _RegisteredTask(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            description=description,
        )
        logger.info(
            "Registered task %s (interval=%ds)", name, interval_seconds
        )

    def periodic(
        self,
        name: str,
        interval_seconds: int = 3600,
        description: str = "",
    ) -> Callable[[TaskFunc], TaskFunc]:
        """Decorator to register an async function as a periodic task.

        Usage::

            @task_scheduler.periodic(
                "drift_detection", interval_seconds=3600
            )
            async def scan_drift(**kwargs) -> dict:
                ...
        """

        def decorator(func: TaskFunc) -> TaskFunc:
            self.register_task(
                name=name,
                func=func,
                interval_seconds=interval_seconds,
                description=description,
            )
            return func

        return decorator

    @property
    def registered_tasks(self) -> dict[str, _RegisteredTask]:
        """Read-only view of registered tasks."""
        return dict(self._registry)

    # ------------------------------------------------------------------
    # Scheduler lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the APScheduler and add jobs for registered tasks."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        try:
            from apscheduler.schedulers.asyncio import (
                AsyncIOScheduler,
            )
            from apscheduler.triggers.interval import (
                IntervalTrigger,
            )
        except ImportError:
            logger.warning(
                "apscheduler not installed — scheduler disabled"
            )
            return

        self._scheduler = AsyncIOScheduler()

        # In dev mode, double the intervals to reduce noise
        multiplier = 2 if settings.is_dev_mode else 1

        for name, task in self._registry.items():
            interval = task.interval_seconds * multiplier
            self._scheduler.add_job(
                self._execute_task,
                trigger=IntervalTrigger(seconds=interval),
                args=[name],
                id=f"governance_{name}",
                name=f"Governance: {name}",
                replace_existing=True,
            )
            logger.info(
                "Scheduled %s every %ds", name, interval
            )

        self._scheduler.start()
        self._running = True
        logger.info(
            "Task scheduler started with %d tasks",
            len(self._registry),
        )

    async def shutdown(self) -> None:
        """Gracefully shut down the scheduler."""
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Task scheduler shut down")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    async def trigger_task(
        self,
        task_type: str,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        """Manually trigger a task and record the execution.

        Returns a dict with the execution metadata (id, status, etc.).
        The actual scan runs in the background.
        """
        task_id = generate_uuid()
        now = datetime.now(timezone.utc)

        execution = {
            "id": task_id,
            "task_type": task_type,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "result_summary": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }

        # Persist via DB if available
        saved = await self._save_execution(execution)

        # Run the task in the background
        asyncio.create_task(
            self._run_and_record(task_id, task_type, tenant_id, project_id)
        )

        return saved

    async def _execute_task(self, task_name: str) -> None:
        """Scheduler callback — trigger a registered task."""
        logger.info("Scheduler firing task: %s", task_name)
        await self.trigger_task(task_name)

    async def _run_and_record(
        self,
        task_id: str,
        task_type: str,
        tenant_id: str | None,
        project_id: str | None,
    ) -> None:
        """Execute the task function and record results."""
        now = datetime.now(timezone.utc)

        # Mark as running
        await self._update_execution(
            task_id, status="running", started_at=now
        )

        registered = self._registry.get(task_type)
        if registered is None:
            # No handler registered — mark completed with note
            await self._update_execution(
                task_id,
                status="completed",
                completed_at=datetime.now(timezone.utc),
                result_summary={
                    "message": (
                        f"No handler registered for '{task_type}'. "
                        "Task recorded as placeholder."
                    ),
                },
            )
            return

        try:
            result = await registered.func(
                tenant_id=tenant_id, project_id=project_id
            )
            await self._update_execution(
                task_id,
                status="completed",
                completed_at=datetime.now(timezone.utc),
                result_summary=result or {"message": "completed"},
            )
        except Exception as exc:
            logger.exception("Task %s (%s) failed", task_type, task_id)
            await self._update_execution(
                task_id,
                status="failed",
                completed_at=datetime.now(timezone.utc),
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def _save_execution(self, execution: dict) -> dict:
        """Persist a new TaskExecution row if DB is available."""
        from app.db.session import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return execution

        try:
            from app.models.task_execution import TaskExecution

            async with factory() as session:
                row = TaskExecution(
                    id=execution["id"],
                    task_type=execution["task_type"],
                    tenant_id=execution["tenant_id"],
                    project_id=execution["project_id"],
                    status=execution["status"],
                )
                session.add(row)
                await session.commit()
        except Exception:
            logger.exception("Failed to persist task execution")

        return execution

    async def _update_execution(
        self, task_id: str, **fields: Any
    ) -> None:
        """Update an existing TaskExecution row."""
        from app.db.session import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return

        try:
            from sqlalchemy import update

            from app.models.task_execution import TaskExecution

            async with factory() as session:
                stmt = (
                    update(TaskExecution)
                    .where(TaskExecution.id == task_id)
                    .values(**fields)
                )
                await session.execute(stmt)
                await session.commit()
        except Exception:
            logger.exception(
                "Failed to update task execution %s", task_id
            )

    # ------------------------------------------------------------------
    # Query helpers (used by routes)
    # ------------------------------------------------------------------

    async def list_executions(
        self,
        db: Any | None,
        task_type: str | None = None,
        status: str | None = None,
        project_id: str | None = None,
    ) -> list[dict]:
        """List task executions with optional filters."""
        if db is None:
            return []

        from sqlalchemy import select

        from app.models.task_execution import TaskExecution

        stmt = select(TaskExecution).order_by(
            TaskExecution.created_at.desc()
        )
        if task_type:
            stmt = stmt.where(TaskExecution.task_type == task_type)
        if status:
            stmt = stmt.where(TaskExecution.status == status)
        if project_id:
            stmt = stmt.where(
                TaskExecution.project_id == project_id
            )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_execution(
        self, task_id: str, db: Any | None
    ) -> Any | None:
        """Get a single task execution by ID."""
        if db is None:
            return None

        from sqlalchemy import select

        from app.models.task_execution import TaskExecution

        result = await db.execute(
            select(TaskExecution).where(
                TaskExecution.id == task_id
            )
        )
        return result.scalar_one_or_none()

    async def cancel_execution(
        self, task_id: str, db: Any | None
    ) -> Any | None:
        """Cancel a pending or running task execution."""
        if db is None:
            return None

        execution = await self.get_execution(task_id, db)
        if execution is None:
            return None

        if execution.status not in ("pending", "running"):
            return execution

        execution.status = "cancelled"
        execution.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return execution


# Singleton
task_scheduler = TaskSchedulerService()
