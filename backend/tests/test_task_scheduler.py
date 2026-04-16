"""Tests for the background task execution framework."""

import asyncio
import importlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.task_execution import (
    TASK_STATUSES,
    TASK_TYPES,
    TaskExecution,
)
from app.schemas.task_execution import (
    TaskExecutionResponse,
    TaskListResponse,
    TaskScheduleRequest,
    TaskStatus,
    TaskType,
)
from app.services.task_scheduler import (
    TaskSchedulerService,
    task_scheduler,
)


# ---------------------------------------------------------------------------
# Unit tests: TaskExecution model
# ---------------------------------------------------------------------------


class TestTaskExecutionModel:
    """Tests for the TaskExecution SQLAlchemy model."""

    def test_table_name(self):
        """Model maps to 'task_executions' table."""
        assert TaskExecution.__tablename__ == "task_executions"

    def test_primary_key_column(self):
        """id is the primary key."""
        cols = TaskExecution.__table__.columns
        pk_cols = [c.name for c in cols if c.primary_key]
        assert pk_cols == ["id"]

    def test_required_columns_exist(self):
        """Model has all required columns."""
        col_names = {
            c.name for c in TaskExecution.__table__.columns
        }
        expected = {
            "id",
            "task_type",
            "tenant_id",
            "project_id",
            "status",
            "started_at",
            "completed_at",
            "result_summary",
            "error_message",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(col_names)

    def test_nullable_columns(self):
        """tenant_id, project_id, started_at, completed_at, result_summary, error_message are nullable."""
        cols = {
            c.name: c for c in TaskExecution.__table__.columns
        }
        for name in [
            "tenant_id",
            "project_id",
            "started_at",
            "completed_at",
            "result_summary",
            "error_message",
        ]:
            assert cols[name].nullable is True, (
                f"{name} should be nullable"
            )

    def test_non_nullable_columns(self):
        """task_type, status, created_at, updated_at are NOT nullable."""
        cols = {
            c.name: c for c in TaskExecution.__table__.columns
        }
        for name in [
            "task_type",
            "status",
            "created_at",
            "updated_at",
        ]:
            assert cols[name].nullable is False, (
                f"{name} should not be nullable"
            )

    def test_foreign_keys(self):
        """tenant_id -> tenants.id, project_id -> projects.id."""
        cols = {
            c.name: c for c in TaskExecution.__table__.columns
        }
        tenant_fks = [
            str(fk.target_fullname)
            for fk in cols["tenant_id"].foreign_keys
        ]
        assert "tenants.id" in tenant_fks

        project_fks = [
            str(fk.target_fullname)
            for fk in cols["project_id"].foreign_keys
        ]
        assert "projects.id" in project_fks

    def test_status_defaults_to_pending(self):
        """status column defaults to 'pending'."""
        cols = {
            c.name: c for c in TaskExecution.__table__.columns
        }
        assert cols["status"].default.arg == "pending"

    def test_task_statuses_constant(self):
        """TASK_STATUSES contains expected values."""
        assert "pending" in TASK_STATUSES
        assert "running" in TASK_STATUSES
        assert "completed" in TASK_STATUSES
        assert "failed" in TASK_STATUSES
        assert "cancelled" in TASK_STATUSES

    def test_task_types_constant(self):
        """TASK_TYPES contains expected governance scan types."""
        assert "drift_detection" in TASK_TYPES
        assert "policy_compliance" in TASK_TYPES
        assert "rbac_health" in TASK_TYPES
        assert "tagging_compliance" in TASK_TYPES


# ---------------------------------------------------------------------------
# Unit tests: Pydantic schemas
# ---------------------------------------------------------------------------


class TestTaskSchemas:
    """Tests for task execution Pydantic schemas."""

    def test_task_status_enum(self):
        """TaskStatus enum contains all statuses."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_task_type_enum(self):
        """TaskType enum contains governance scan types."""
        assert TaskType.DRIFT_DETECTION == "drift_detection"
        assert TaskType.POLICY_COMPLIANCE == "policy_compliance"
        assert TaskType.RBAC_HEALTH == "rbac_health"
        assert TaskType.TAGGING_COMPLIANCE == "tagging_compliance"

    def test_execution_response_from_dict(self):
        """TaskExecutionResponse can be created from a dict."""
        now = datetime.now(timezone.utc)
        resp = TaskExecutionResponse(
            id="test-id",
            task_type="drift_detection",
            status="pending",
            created_at=now,
            updated_at=now,
        )
        assert resp.id == "test-id"
        assert resp.task_type == "drift_detection"
        assert resp.tenant_id is None
        assert resp.project_id is None

    def test_execution_response_with_all_fields(self):
        """TaskExecutionResponse accepts all optional fields."""
        now = datetime.now(timezone.utc)
        resp = TaskExecutionResponse(
            id="test-id",
            task_type="policy_compliance",
            tenant_id="t-1",
            project_id="p-1",
            status="completed",
            started_at=now,
            completed_at=now,
            result_summary={"findings": 3},
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        assert resp.result_summary == {"findings": 3}
        assert resp.tenant_id == "t-1"

    def test_task_list_response(self):
        """TaskListResponse wraps a list of executions."""
        now = datetime.now(timezone.utc)
        item = TaskExecutionResponse(
            id="test-id",
            task_type="rbac_health",
            status="running",
            created_at=now,
            updated_at=now,
        )
        lst = TaskListResponse(tasks=[item], total=1)
        assert lst.total == 1
        assert len(lst.tasks) == 1

    def test_schedule_request_defaults(self):
        """TaskScheduleRequest defaults to None for all fields."""
        req = TaskScheduleRequest()
        assert req.project_id is None
        assert req.tenant_id is None

    def test_schedule_request_with_values(self):
        """TaskScheduleRequest accepts project_id and tenant_id."""
        req = TaskScheduleRequest(
            project_id="p-1", tenant_id="t-1"
        )
        assert req.project_id == "p-1"
        assert req.tenant_id == "t-1"


# ---------------------------------------------------------------------------
# Unit tests: TaskSchedulerService
# ---------------------------------------------------------------------------


class TestTaskSchedulerService:
    """Tests for the TaskSchedulerService class."""

    def test_singleton_exists(self):
        """task_scheduler singleton is available."""
        assert task_scheduler is not None
        assert isinstance(task_scheduler, TaskSchedulerService)

    def test_register_task(self):
        """register_task adds a task to the registry."""
        svc = TaskSchedulerService()
        called = False

        async def my_scan(**kwargs):
            nonlocal called
            called = True
            return {"ok": True}

        svc.register_task(
            "test_scan", my_scan, interval_seconds=60
        )
        assert "test_scan" in svc.registered_tasks
        assert (
            svc.registered_tasks["test_scan"].interval_seconds
            == 60
        )

    def test_periodic_decorator(self):
        """@periodic decorator registers the function."""
        svc = TaskSchedulerService()

        @svc.periodic(
            "decorated_scan",
            interval_seconds=120,
            description="A test scan",
        )
        async def scan_func(**kwargs):
            return {}

        assert "decorated_scan" in svc.registered_tasks
        reg = svc.registered_tasks["decorated_scan"]
        assert reg.description == "A test scan"
        assert reg.interval_seconds == 120

    def test_periodic_decorator_returns_original(self):
        """@periodic returns the original function unchanged."""
        svc = TaskSchedulerService()

        @svc.periodic("passthrough_scan")
        async def original(**kwargs):
            return {"data": 1}

        assert original is not None
        assert asyncio.iscoroutinefunction(original)

    def test_is_running_initially_false(self):
        """Scheduler is not running before start()."""
        svc = TaskSchedulerService()
        assert svc.is_running is False

    @pytest.mark.asyncio
    async def test_start_without_apscheduler(self):
        """start() handles missing apscheduler gracefully."""
        svc = TaskSchedulerService()

        with patch.dict(
            "sys.modules",
            {
                "apscheduler": None,
                "apscheduler.schedulers": None,
                "apscheduler.schedulers.asyncio": None,
                "apscheduler.triggers": None,
                "apscheduler.triggers.interval": None,
            },
        ):
            # Force re-import failure
            await svc.start()
            assert svc.is_running is False

    @pytest.mark.asyncio
    async def test_start_and_shutdown(self):
        """start() and shutdown() manage scheduler lifecycle."""
        svc = TaskSchedulerService()

        mock_scheduler = MagicMock()
        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        with patch(
            "app.services.task_scheduler.AsyncIOScheduler",
            return_value=mock_scheduler,
            create=True,
        ):
            # Mock the apscheduler imports inside start()
            mock_async_sched = MagicMock()
            mock_interval = MagicMock()
            mock_async_mod = MagicMock()
            mock_async_mod.AsyncIOScheduler = (
                lambda: mock_scheduler
            )
            mock_interval_mod = MagicMock()
            mock_interval_mod.IntervalTrigger = MagicMock()

            with patch.dict(
                "sys.modules",
                {
                    "apscheduler": MagicMock(),
                    "apscheduler.schedulers": MagicMock(),
                    "apscheduler.schedulers.asyncio": mock_async_mod,
                    "apscheduler.triggers": MagicMock(),
                    "apscheduler.triggers.interval": mock_interval_mod,
                },
            ):
                await svc.start()
                assert svc.is_running is True

                await svc.shutdown()
                assert svc.is_running is False
                mock_scheduler.shutdown.assert_called_once_with(
                    wait=False
                )

    @pytest.mark.asyncio
    async def test_shutdown_when_not_running(self):
        """shutdown() is safe to call when not running."""
        svc = TaskSchedulerService()
        await svc.shutdown()
        assert svc.is_running is False

    @pytest.mark.asyncio
    async def test_trigger_task_returns_execution(self):
        """trigger_task returns an execution dict."""
        svc = TaskSchedulerService()

        with patch.object(
            svc, "_save_execution", new_callable=AsyncMock
        ) as mock_save:
            mock_save.side_effect = lambda ex: ex

            with patch.object(
                svc,
                "_run_and_record",
                new_callable=AsyncMock,
            ):
                result = await svc.trigger_task(
                    task_type="drift_detection",
                    tenant_id="t-1",
                    project_id="p-1",
                )

        assert result["task_type"] == "drift_detection"
        assert result["status"] == "pending"
        assert result["tenant_id"] == "t-1"
        assert result["project_id"] == "p-1"
        assert "id" in result
        assert len(result["id"]) == 36

    @pytest.mark.asyncio
    async def test_trigger_task_calls_save(self):
        """trigger_task persists the execution record."""
        svc = TaskSchedulerService()

        with patch.object(
            svc, "_save_execution", new_callable=AsyncMock
        ) as mock_save:
            mock_save.side_effect = lambda ex: ex

            with patch.object(
                svc,
                "_run_and_record",
                new_callable=AsyncMock,
            ):
                await svc.trigger_task(
                    task_type="policy_compliance"
                )

        mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_and_record_no_handler(self):
        """_run_and_record completes with message when no handler registered."""
        svc = TaskSchedulerService()

        with patch.object(
            svc,
            "_update_execution",
            new_callable=AsyncMock,
        ) as mock_update:
            await svc._run_and_record(
                "task-1", "unknown_type", None, None
            )

        # Should be called twice: running, then completed
        assert mock_update.call_count == 2
        # First call: status=running
        first_call = mock_update.call_args_list[0]
        assert first_call.kwargs["status"] == "running"
        # Second call: status=completed
        second_call = mock_update.call_args_list[1]
        assert second_call.kwargs["status"] == "completed"
        assert "No handler" in str(
            second_call.kwargs["result_summary"]
        )

    @pytest.mark.asyncio
    async def test_run_and_record_with_handler(self):
        """_run_and_record runs registered handler and records result."""
        svc = TaskSchedulerService()

        async def my_handler(**kwargs):
            return {"findings": 5}

        svc.register_task("test_type", my_handler)

        with patch.object(
            svc,
            "_update_execution",
            new_callable=AsyncMock,
        ) as mock_update:
            await svc._run_and_record(
                "task-2", "test_type", None, None
            )

        assert mock_update.call_count == 2
        second_call = mock_update.call_args_list[1]
        assert second_call.kwargs["status"] == "completed"
        assert second_call.kwargs["result_summary"] == {
            "findings": 5
        }

    @pytest.mark.asyncio
    async def test_run_and_record_handler_failure(self):
        """_run_and_record records failure when handler raises."""
        svc = TaskSchedulerService()

        async def failing_handler(**kwargs):
            raise ValueError("scan broke")

        svc.register_task("fail_type", failing_handler)

        with patch.object(
            svc,
            "_update_execution",
            new_callable=AsyncMock,
        ) as mock_update:
            await svc._run_and_record(
                "task-3", "fail_type", None, None
            )

        assert mock_update.call_count == 2
        second_call = mock_update.call_args_list[1]
        assert second_call.kwargs["status"] == "failed"
        assert "scan broke" in second_call.kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_list_executions_no_db(self):
        """list_executions returns empty list when db is None."""
        svc = TaskSchedulerService()
        result = await svc.list_executions(None)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_execution_no_db(self):
        """get_execution returns None when db is None."""
        svc = TaskSchedulerService()
        result = await svc.get_execution("task-1", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_execution_no_db(self):
        """cancel_execution returns None when db is None."""
        svc = TaskSchedulerService()
        result = await svc.cancel_execution("task-1", None)
        assert result is None


# ---------------------------------------------------------------------------
# Unit tests: Task status transitions
# ---------------------------------------------------------------------------


class TestTaskStatusTransitions:
    """Tests for task execution status transitions."""

    @pytest.mark.asyncio
    async def test_pending_to_running(self):
        """Task transitions from pending to running."""
        svc = TaskSchedulerService()
        updates = []

        async def capture_update(tid, **fields):
            updates.append(fields)

        svc._update_execution = capture_update

        async def slow_handler(**kwargs):
            return {"ok": True}

        svc.register_task("transition_test", slow_handler)

        await svc._run_and_record(
            "t-1", "transition_test", None, None
        )

        assert updates[0]["status"] == "running"
        assert updates[1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_pending_to_failed(self):
        """Task transitions from pending to failed on error."""
        svc = TaskSchedulerService()
        updates = []

        async def capture_update(tid, **fields):
            updates.append(fields)

        svc._update_execution = capture_update

        async def bad_handler(**kwargs):
            raise RuntimeError("boom")

        svc.register_task("fail_test", bad_handler)

        await svc._run_and_record(
            "t-2", "fail_test", None, None
        )

        assert updates[0]["status"] == "running"
        assert updates[1]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self):
        """Cancel transitions pending task to cancelled."""
        svc = TaskSchedulerService()

        mock_execution = MagicMock()
        mock_execution.status = "pending"
        mock_execution.completed_at = None

        mock_db = AsyncMock()

        with patch.object(
            svc,
            "get_execution",
            new_callable=AsyncMock,
            return_value=mock_execution,
        ):
            result = await svc.cancel_execution(
                "task-1", mock_db
            )

        assert result.status == "cancelled"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_completed_task_noop(self):
        """Cancel on a completed task does not change status."""
        svc = TaskSchedulerService()

        mock_execution = MagicMock()
        mock_execution.status = "completed"

        with patch.object(
            svc,
            "get_execution",
            new_callable=AsyncMock,
            return_value=mock_execution,
        ):
            result = await svc.cancel_execution(
                "task-1", AsyncMock()
            )

        assert result.status == "completed"


# ---------------------------------------------------------------------------
# Route integration tests (dev mode — no DB)
# ---------------------------------------------------------------------------


class TestGovernanceTaskRoutes:
    """Integration tests for governance task API routes."""

    @pytest.mark.asyncio
    async def test_list_tasks_returns_200(self):
        """GET /api/governance/tasks/ returns 200."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/governance/tasks/"
            )
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_tasks_empty_in_dev(self):
        """In dev mode without DB, task list is empty."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/governance/tasks/"
            )
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """GET /api/governance/tasks/{id} returns 404 for unknown ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/governance/tasks/nonexistent-id"
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_drift_detection(self):
        """POST /api/governance/tasks/trigger/drift_detection returns 200."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/governance/tasks/trigger/drift_detection",
                json={},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "drift_detection"
        assert data["status"] == "pending"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_trigger_policy_compliance(self):
        """POST trigger for policy_compliance works."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/governance/tasks/trigger/policy_compliance",
                json={"project_id": "p-1"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "policy_compliance"
        assert data["project_id"] == "p-1"

    @pytest.mark.asyncio
    async def test_trigger_rbac_health(self):
        """POST trigger for rbac_health works."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/governance/tasks/trigger/rbac_health",
                json={},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "rbac_health"

    @pytest.mark.asyncio
    async def test_trigger_tagging_compliance(self):
        """POST trigger for tagging_compliance works."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/governance/tasks/trigger/tagging_compliance",
                json={},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "tagging_compliance"

    @pytest.mark.asyncio
    async def test_trigger_invalid_type_returns_422(self):
        """POST trigger for an invalid type returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/governance/tasks/trigger/invalid_type",
                json={},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_trigger_with_tenant_override(self):
        """POST trigger with tenant_id in request body overrides."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/governance/tasks/trigger/drift_detection",
                json={"tenant_id": "override-tenant"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "override-tenant"

    @pytest.mark.asyncio
    async def test_cancel_not_found(self):
        """DELETE /api/governance/tasks/{id} returns 404 for unknown ID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.delete(
                "/api/governance/tasks/nonexistent-id"
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self):
        """GET with query params passes filters through."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/governance/tasks/",
                params={
                    "task_type": "drift_detection",
                    "status": "completed",
                    "project_id": "p-1",
                },
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


class TestTaskExecutionMigration:
    """Tests for the 008 migration file."""

    def test_migration_file_imports(self):
        """Migration 008 can be imported."""
        mod = importlib.import_module(
            "app.db.migrations.versions.008_add_task_executions"
        )
        assert hasattr(mod, "upgrade")
        assert hasattr(mod, "downgrade")

    def test_migration_revision(self):
        """Migration has correct revision chain."""
        mod = importlib.import_module(
            "app.db.migrations.versions.008_add_task_executions"
        )
        assert mod.revision == "008"
        assert mod.down_revision == "007"

    def test_migration_upgrade_callable(self):
        """upgrade() is callable."""
        mod = importlib.import_module(
            "app.db.migrations.versions.008_add_task_executions"
        )
        assert callable(mod.upgrade)

    def test_migration_downgrade_callable(self):
        """downgrade() is callable."""
        mod = importlib.import_module(
            "app.db.migrations.versions.008_add_task_executions"
        )
        assert callable(mod.downgrade)


# ---------------------------------------------------------------------------
# Model registration tests
# ---------------------------------------------------------------------------


class TestModelRegistration:
    """Tests that TaskExecution is registered in the models package."""

    def test_task_execution_in_models_init(self):
        """TaskExecution is importable from app.models."""
        from app.models import TaskExecution as TE

        assert TE is TaskExecution

    def test_task_execution_in_all(self):
        """TaskExecution is listed in __all__."""
        import app.models

        assert "TaskExecution" in app.models.__all__
