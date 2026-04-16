"""Tests for policy compliance monitor — models, schemas, service, and routes."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROJECT_ID = "proj-test-policy"


# ── Model & schema import tests ──────────────────────────────────────────────


class TestPolicyComplianceModelsImportable:
    """Verify models load and have correct table names."""

    def test_models_importable(self):
        from app.models import PolicyComplianceResult, PolicyViolation

        assert PolicyComplianceResult.__tablename__ == "policy_compliance_results"
        assert PolicyViolation.__tablename__ == "policy_violations"

    def test_models_in_metadata(self):
        from app.models import Base

        table_names = set(Base.metadata.tables.keys())
        assert "policy_compliance_results" in table_names
        assert "policy_violations" in table_names

    def test_result_has_expected_columns(self):
        from app.models.policy_compliance import PolicyComplianceResult

        cols = {c.name for c in PolicyComplianceResult.__table__.columns}
        expected = {
            "id", "project_id", "tenant_id", "scan_timestamp",
            "total_resources", "compliant_count", "non_compliant_count",
            "status", "error_message", "created_at", "updated_at",
        }
        assert expected.issubset(cols)

    def test_violation_has_expected_columns(self):
        from app.models.policy_compliance import PolicyViolation

        cols = {c.name for c in PolicyViolation.__table__.columns}
        expected = {
            "id", "compliance_result_id", "resource_id", "resource_type",
            "policy_name", "policy_description", "severity",
            "framework_control_id", "remediation_suggestion", "detected_at",
        }
        assert expected.issubset(cols)

    def test_result_indexes(self):
        from app.models.policy_compliance import PolicyComplianceResult

        index_names = {idx.name for idx in PolicyComplianceResult.__table__.indexes}
        assert "ix_policy_compliance_results_project_scan" in index_names

    def test_violation_indexes(self):
        from app.models.policy_compliance import PolicyViolation

        index_names = {idx.name for idx in PolicyViolation.__table__.indexes}
        assert "ix_policy_violations_result_severity" in index_names


class TestPolicyComplianceSchemasImportable:
    """Verify schemas load and validate correctly."""

    def test_enums_importable(self):
        from app.schemas.policy_compliance import (
            ComplianceScanStatus,
            ViolationSeverity,
        )

        assert ViolationSeverity.CRITICAL == "critical"
        assert ViolationSeverity.HIGH == "high"
        assert ViolationSeverity.MEDIUM == "medium"
        assert ViolationSeverity.LOW == "low"
        assert ComplianceScanStatus.COMPLETED == "completed"
        assert ComplianceScanStatus.FAILED == "failed"

    def test_violation_response_schema(self):
        from app.schemas.policy_compliance import PolicyViolationResponse

        now = datetime.now(timezone.utc)
        v = PolicyViolationResponse(
            id="v1",
            compliance_result_id="r1",
            resource_id="/subscriptions/sub/rg/providers/type/name",
            resource_type="Microsoft.Compute/virtualMachines",
            policy_name="require-tls",
            policy_description="TLS 1.2 required",
            severity="high",
            framework_control_id=None,
            remediation_suggestion="Enable TLS 1.2",
            detected_at=now,
        )
        assert v.resource_type == "Microsoft.Compute/virtualMachines"
        assert v.severity == "high"

    def test_result_response_schema(self):
        from app.schemas.policy_compliance import PolicyComplianceResultResponse

        now = datetime.now(timezone.utc)
        r = PolicyComplianceResultResponse(
            id="r1",
            project_id="p1",
            scan_timestamp=now,
            total_resources=20,
            compliant_count=17,
            non_compliant_count=3,
            status="completed",
            violations=[],
            created_at=now,
            updated_at=now,
        )
        assert r.total_resources == 20
        assert r.non_compliant_count == 3
        assert r.status == "completed"
        assert r.violations == []

    def test_result_list_schema(self):
        from app.schemas.policy_compliance import PolicyComplianceResultList

        result_list = PolicyComplianceResultList(results=[], total=0)
        assert result_list.results == []
        assert result_list.total == 0

    def test_summary_defaults(self):
        from app.schemas.policy_compliance import PolicyComplianceSummary

        summary = PolicyComplianceSummary(project_id="p1")
        assert summary.total_scans == 0
        assert summary.total_violations == 0
        assert summary.latest_scan_at is None
        assert summary.by_severity["critical"] == 0
        assert summary.by_severity["high"] == 0
        assert summary.by_severity["medium"] == 0
        assert summary.by_severity["low"] == 0
        assert summary.by_framework == {}
        assert summary.compliance_rate == 0.0


# ── Service tests ────────────────────────────────────────────────────────────


class TestPolicyMonitorService:
    """Test the PolicyMonitor service methods."""

    @pytest.mark.asyncio
    async def test_get_policy_state_dev_mode(self):
        """In dev mode, get_policy_state returns mock data."""
        from app.services.policy_monitor import policy_monitor

        state = await policy_monitor.get_policy_state("sub-test-123")

        assert "total_resources" in state
        assert "non_compliant_resources" in state
        assert isinstance(state["total_resources"], int)
        assert state["total_resources"] > 0
        assert isinstance(state["non_compliant_resources"], list)
        assert len(state["non_compliant_resources"]) > 0

    @pytest.mark.asyncio
    async def test_get_policy_state_deterministic(self):
        """Mock state is deterministic for the same subscription."""
        from app.services.policy_monitor import policy_monitor

        state1 = await policy_monitor.get_policy_state("sub-deterministic")
        state2 = await policy_monitor.get_policy_state("sub-deterministic")

        assert state1["total_resources"] == state2["total_resources"]
        assert len(state1["non_compliant_resources"]) == len(
            state2["non_compliant_resources"]
        )

    @pytest.mark.asyncio
    async def test_get_policy_state_varies_by_subscription(self):
        """Different subscriptions can produce different results."""
        from app.services.policy_monitor import policy_monitor

        state_a = await policy_monitor.get_policy_state("sub-alpha")
        state_b = await policy_monitor.get_policy_state("sub-beta")

        # At minimum, both should return valid structure
        assert state_a["total_resources"] > 0
        assert state_b["total_resources"] > 0

    @pytest.mark.asyncio
    async def test_mock_violations_have_required_fields(self):
        """Each mock violation should have all required fields."""
        from app.services.policy_monitor import policy_monitor

        state = await policy_monitor.get_policy_state("sub-fields-check")
        for v in state["non_compliant_resources"]:
            assert "resource_id" in v
            assert "resource_type" in v
            assert "policy_name" in v
            assert "policy_description" in v
            assert "severity" in v
            assert "remediation" in v

    @pytest.mark.asyncio
    async def test_map_violations_to_frameworks_basic(self):
        """Violations with known policy names get mapped to frameworks."""
        from app.services.policy_monitor import policy_monitor

        violations = [
            {
                "resource_id": "/sub/rg/type/res1",
                "resource_type": "Microsoft.Network/networkSecurityGroups",
                "policy_name": "require-nsg",
                "policy_description": "NSGs required",
                "severity": "high",
                "remediation": "Add NSG",
            },
            {
                "resource_id": "/sub/rg/type/res2",
                "resource_type": "Microsoft.Storage/storageAccounts",
                "policy_name": "require-encryption-at-rest",
                "policy_description": "Encryption required",
                "severity": "high",
                "remediation": "Enable encryption",
            },
        ]

        mapped = await policy_monitor.map_violations_to_frameworks(
            violations, architecture_data={}
        )

        assert len(mapped) == 2

        # First violation should map to frameworks that reference require-nsg
        v1 = mapped[0]
        assert v1["policy_name"] == "require-nsg"
        assert v1["framework_mapping"] is not None
        assert "framework" in v1["framework_mapping"]
        assert "control_id" in v1["framework_mapping"]

    @pytest.mark.asyncio
    async def test_map_violations_unknown_policy(self):
        """Violations with unknown policy names get no framework mapping."""
        from app.services.policy_monitor import policy_monitor

        violations = [
            {
                "resource_id": "/sub/rg/type/res1",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "policy_name": "unknown-policy-xyz",
                "policy_description": "Unknown policy",
                "severity": "low",
                "remediation": "N/A",
            },
        ]

        mapped = await policy_monitor.map_violations_to_frameworks(
            violations, architecture_data={}
        )

        assert len(mapped) == 1
        assert mapped[0]["framework_mapping"] is None

    @pytest.mark.asyncio
    async def test_map_violations_empty_list(self):
        """Empty violations list returns empty mapped list."""
        from app.services.policy_monitor import policy_monitor

        mapped = await policy_monitor.map_violations_to_frameworks(
            [], architecture_data={}
        )
        assert mapped == []

    @pytest.mark.asyncio
    async def test_check_compliance_full_scan(self):
        """Full check_compliance flow returns correct structure."""
        from app.services.policy_monitor import policy_monitor

        with patch.object(
            policy_monitor, "_publish_event", new_callable=AsyncMock
        ) as mock_publish:
            result = await policy_monitor.check_compliance(
                project_id=PROJECT_ID,
                tenant_id="tenant-1",
            )

        assert result["project_id"] == PROJECT_ID
        assert result["tenant_id"] == "tenant-1"
        assert result["status"] == "completed"
        assert result["total_resources"] > 0
        assert result["non_compliant_count"] > 0
        assert result["compliant_count"] >= 0
        assert isinstance(result["violations"], list)
        assert len(result["violations"]) == result["non_compliant_count"]
        assert "id" in result
        assert "scan_timestamp" in result

        # SSE event should have been published
        mock_publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_compliance_error_handling(self):
        """When get_policy_state raises, check_compliance returns failed."""
        from app.services.policy_monitor import policy_monitor

        with patch.object(
            policy_monitor,
            "get_policy_state",
            side_effect=RuntimeError("Azure API unavailable"),
        ):
            result = await policy_monitor.check_compliance(
                project_id=PROJECT_ID,
            )

        assert result["status"] == "failed"
        assert "Azure API unavailable" in result["error_message"]
        assert result["violations"] == []

    @pytest.mark.asyncio
    async def test_check_compliance_publishes_event(self):
        """check_compliance publishes a compliance_changed SSE event."""
        from app.services.policy_monitor import policy_monitor

        with patch(
            "app.services.event_stream.event_stream"
        ) as mock_stream:
            mock_stream.publish = AsyncMock(return_value=1)

            result = await policy_monitor.check_compliance(
                project_id="proj-sse-test",
            )

        mock_stream.publish.assert_called_once()
        call_args = mock_stream.publish.call_args
        assert call_args[1]["event_type"] == "compliance_changed" or \
            call_args[0][0] == "compliance_changed"


# ── Periodic task registration ───────────────────────────────────────────────


class TestPolicyMonitorTaskRegistration:
    """Verify the policy monitor registers with the task scheduler."""

    def test_registered_as_periodic_task(self):
        from app.services.task_scheduler import task_scheduler

        # Force import so decorator runs
        import app.services.policy_monitor  # noqa: F401

        tasks = task_scheduler.registered_tasks
        assert "policy_compliance" in tasks

    def test_periodic_task_has_correct_interval(self):
        from app.services.task_scheduler import task_scheduler

        import app.services.policy_monitor  # noqa: F401

        task = task_scheduler.registered_tasks["policy_compliance"]
        assert task.interval_seconds == 3600

    @pytest.mark.asyncio
    async def test_periodic_task_skips_without_project_id(self):
        from app.services.policy_monitor import run_periodic_policy_scan

        result = await run_periodic_policy_scan(
            tenant_id="t1", project_id=None
        )
        assert result["message"] == "skipped"
        assert result["reason"] == "no project_id"

    @pytest.mark.asyncio
    async def test_periodic_task_runs_with_project_id(self):
        from app.services.policy_monitor import (
            policy_monitor,
            run_periodic_policy_scan,
        )

        with patch.object(
            policy_monitor, "_publish_event", new_callable=AsyncMock
        ):
            result = await run_periodic_policy_scan(
                tenant_id="t1", project_id="proj-periodic"
            )

        assert result["message"] == "completed"
        assert "scan_id" in result
        assert result["status"] == "completed"


# ── API route tests (no-DB / mock mode) ─────────────────────────────────────


class TestScanRouteNoDB:
    """Test the POST /scan endpoint without a database."""

    def test_trigger_scan_returns_result(self):
        r = client.post(f"/api/governance/policy-compliance/scan/{PROJECT_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["status"] == "completed"
        assert data["total_resources"] > 0
        assert data["non_compliant_count"] > 0
        assert isinstance(data["violations"], list)
        assert len(data["violations"]) > 0
        assert "id" in data
        assert "scan_timestamp" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_trigger_scan_violations_have_fields(self):
        r = client.post(f"/api/governance/policy-compliance/scan/{PROJECT_ID}")
        data = r.json()
        for v in data["violations"]:
            assert "id" in v
            assert "resource_id" in v
            assert "resource_type" in v
            assert "policy_name" in v
            assert "severity" in v
            assert "detected_at" in v

    def test_trigger_scan_different_projects(self):
        r1 = client.post("/api/governance/policy-compliance/scan/project-a")
        r2 = client.post("/api/governance/policy-compliance/scan/project-b")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["project_id"] == "project-a"
        assert r2.json()["project_id"] == "project-b"


class TestResultRoutesNoDB:
    """Test result endpoints when no DB is configured."""

    def test_list_results_empty(self):
        r = client.get("/api/governance/policy-compliance/results")
        assert r.status_code == 200
        data = r.json()
        assert data["results"] == []
        assert data["total"] == 0

    def test_list_results_with_project_filter(self):
        r = client.get(
            "/api/governance/policy-compliance/results",
            params={"project_id": PROJECT_ID},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["results"] == []
        assert data["total"] == 0

    def test_get_result_not_found_no_db(self):
        r = client.get(
            "/api/governance/policy-compliance/results/non-existent"
        )
        assert r.status_code == 404


class TestSummaryRouteNoDB:
    """Test summary endpoint when no DB is configured."""

    def test_get_summary_no_db(self):
        r = client.get(
            f"/api/governance/policy-compliance/summary/{PROJECT_ID}"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["total_scans"] == 0
        assert data["total_violations"] == 0
        assert data["latest_scan_at"] is None
        assert data["by_severity"]["critical"] == 0
        assert data["by_severity"]["high"] == 0
        assert data["by_severity"]["medium"] == 0
        assert data["by_severity"]["low"] == 0
        assert data["by_framework"] == {}
        assert data["compliance_rate"] == 0.0


class TestViolationsRouteNoDB:
    """Test violations endpoint when no DB is configured."""

    def test_list_violations_empty(self):
        r = client.get("/api/governance/policy-compliance/violations")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_violations_with_filters(self):
        r = client.get(
            "/api/governance/policy-compliance/violations",
            params={
                "project_id": PROJECT_ID,
                "severity": "high",
                "framework": "SOC2",
            },
        )
        assert r.status_code == 200
        assert r.json() == []


# ── Router registration ─────────────────────────────────────────────────────


class TestRouterRegistration:
    """Verify the policy compliance router is registered in the app."""

    def test_scan_route_exists(self):
        routes = [r.path for r in app.routes]
        assert "/api/governance/policy-compliance/scan/{project_id}" in routes

    def test_results_route_exists(self):
        routes = [r.path for r in app.routes]
        assert "/api/governance/policy-compliance/results" in routes

    def test_result_detail_route_exists(self):
        routes = [r.path for r in app.routes]
        assert "/api/governance/policy-compliance/results/{result_id}" in routes

    def test_summary_route_exists(self):
        routes = [r.path for r in app.routes]
        assert "/api/governance/policy-compliance/summary/{project_id}" in routes

    def test_violations_route_exists(self):
        routes = [r.path for r in app.routes]
        assert "/api/governance/policy-compliance/violations" in routes


# ── Summary aggregation ──────────────────────────────────────────────────────


class TestSummaryAggregation:
    """Verify the summary logic aggregates correctly."""

    def test_summary_schema_with_data(self):
        from app.schemas.policy_compliance import PolicyComplianceSummary

        summary = PolicyComplianceSummary(
            project_id="p1",
            total_scans=5,
            latest_scan_at=datetime.now(timezone.utc),
            total_violations=12,
            by_severity={"critical": 2, "high": 5, "medium": 3, "low": 2},
            by_framework={"SOC2": 4, "HIPAA": 6, "PCI-DSS": 2},
            compliance_rate=85.0,
        )
        assert summary.total_scans == 5
        assert summary.total_violations == 12
        assert summary.by_severity["critical"] == 2
        assert summary.by_framework["HIPAA"] == 6
        assert summary.compliance_rate == 85.0

    @pytest.mark.asyncio
    async def test_map_returns_framework_info(self):
        """Mapped violations include framework name and control_id."""
        from app.services.policy_monitor import policy_monitor

        violations = [
            {
                "resource_id": "/sub/rg/res",
                "resource_type": "Microsoft.Web/sites",
                "policy_name": "require-mfa",
                "policy_description": "MFA required",
                "severity": "high",
                "remediation": "Enable MFA",
            },
        ]
        mapped = await policy_monitor.map_violations_to_frameworks(
            violations, {}
        )

        assert len(mapped) == 1
        m = mapped[0]
        assert m["framework_mapping"] is not None
        # require-mfa is referenced in SOC2, HIPAA, PCI-DSS, FedRAMP, NIST
        assert m["framework_mapping"]["framework"] in [
            "SOC2", "HIPAA", "PCI-DSS", "FedRAMP", "NIST-800-53",
        ]
        assert m["framework_mapping"]["control_id"] is not None
        assert m["framework_mapping"]["control_title"] is not None


# ── Migration test ───────────────────────────────────────────────────────────


class TestMigration:
    """Verify the Alembic migration script is valid."""

    def test_migration_file_exists(self):
        import importlib

        mod = importlib.import_module(
            "app.db.migrations.versions.011_add_policy_compliance"
        )
        assert mod.revision == "011"
        assert mod.down_revision == "010"

    def test_migration_has_upgrade_and_downgrade(self):
        import importlib

        mod = importlib.import_module(
            "app.db.migrations.versions.011_add_policy_compliance"
        )
        assert callable(mod.upgrade)
        assert callable(mod.downgrade)


# ── Mock DB route tests ─────────────────────────────────────────────────────


def _make_mock_violation(**overrides):
    """Create a mock PolicyViolation ORM-like object."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": str(uuid.uuid4()),
        "compliance_result_id": str(uuid.uuid4()),
        "resource_id": "/subscriptions/sub/rg/providers/type/name",
        "resource_type": "Microsoft.Compute/virtualMachines",
        "policy_name": "require-nsg",
        "policy_description": "NSGs required",
        "severity": "high",
        "framework_control_id": None,
        "remediation_suggestion": "Add NSG to subnet",
        "detected_at": now,
    }
    defaults.update(overrides)

    from unittest.mock import MagicMock

    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_mock_result(**overrides):
    """Create a mock PolicyComplianceResult ORM-like object."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": str(uuid.uuid4()),
        "project_id": PROJECT_ID,
        "tenant_id": None,
        "scan_timestamp": now,
        "total_resources": 20,
        "compliant_count": 17,
        "non_compliant_count": 3,
        "status": "completed",
        "error_message": None,
        "created_at": now,
        "updated_at": now,
        "violations": [],
    }
    defaults.update(overrides)

    from unittest.mock import MagicMock

    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestResultRoutesWithMockDB:
    """Test result endpoints with a mocked database session."""

    def test_list_results_with_db(self):
        """list_results returns results from DB."""
        from unittest.mock import MagicMock

        mock_result = _make_mock_result()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_result]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_execute_result

        from app.api.routes.policy_compliance import list_results
        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get("/api/governance/policy-compliance/results")
            assert r.status_code == 200
            data = r.json()
            assert data["total"] == 1
            assert len(data["results"]) == 1
            assert data["results"][0]["project_id"] == PROJECT_ID
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_get_result_found(self):
        """get_result returns a specific result with violations."""
        from unittest.mock import MagicMock

        violation = _make_mock_violation()
        mock_result = _make_mock_result(violations=[violation])

        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = mock_result
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_scalar

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                f"/api/governance/policy-compliance/results/{mock_result.id}"
            )
            assert r.status_code == 200
            data = r.json()
            assert data["id"] == mock_result.id
            assert len(data["violations"]) == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_get_result_not_found(self):
        """get_result returns 404 when result doesn't exist."""
        from unittest.mock import MagicMock

        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_scalar

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                "/api/governance/policy-compliance/results/non-existent"
            )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestViolationsRoutesWithMockDB:
    """Test violations endpoint with mocked database."""

    def test_list_violations_with_db(self):
        """list_violations returns violations from DB."""
        from unittest.mock import MagicMock

        v1 = _make_mock_violation(severity="high")
        v2 = _make_mock_violation(severity="medium")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [v1, v2]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_execute_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                "/api/governance/policy-compliance/violations",
                params={"project_id": PROJECT_ID},
            )
            assert r.status_code == 200
            data = r.json()
            assert len(data) == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_list_violations_with_severity_filter(self):
        """list_violations respects severity filter."""
        from unittest.mock import MagicMock

        v1 = _make_mock_violation(severity="critical")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [v1]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_execute_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                "/api/governance/policy-compliance/violations",
                params={"severity": "critical"},
            )
            assert r.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_list_violations_framework_filter_nonexistent(self):
        """Unknown framework filter returns empty list."""
        from unittest.mock import MagicMock

        mock_db = AsyncMock()

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                "/api/governance/policy-compliance/violations",
                params={"framework": "NONEXISTENT"},
            )
            assert r.status_code == 200
            assert r.json() == []
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_list_violations_framework_filter_valid(self):
        """Valid framework filter applies policy name filter."""
        from unittest.mock import MagicMock

        v1 = _make_mock_violation(policy_name="require-rbac")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [v1]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_execute_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                "/api/governance/policy-compliance/violations",
                params={"framework": "SOC2"},
            )
            assert r.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestSummaryRouteWithMockDB:
    """Test summary endpoint with mocked database."""

    def test_get_summary_with_scans(self):
        """Summary route aggregates scan data from DB."""
        from unittest.mock import MagicMock

        # Mock scalar responses for count, max, violation list, latest scan
        mock_db = AsyncMock()

        # First call: count scans
        count_result = MagicMock()
        count_result.scalar.return_value = 3

        # Second call: max scan timestamp
        now = datetime.now(timezone.utc)
        max_result = MagicMock()
        max_result.scalar_one_or_none.return_value = now

        # Third call: violations
        v1 = _make_mock_violation(severity="high", policy_name="require-nsg")
        v2 = _make_mock_violation(severity="critical", policy_name="require-mfa")
        violation_scalars = MagicMock()
        violation_scalars.all.return_value = [v1, v2]
        violation_result = MagicMock()
        violation_result.scalars.return_value = violation_scalars

        # Fourth call: latest scan for compliance rate
        latest_scan = MagicMock()
        latest_scan.total_resources = 20
        latest_scan.compliant_count = 17
        latest_scan_result = MagicMock()
        latest_scan_result.scalar_one_or_none.return_value = latest_scan

        mock_db.execute.side_effect = [
            count_result,
            max_result,
            violation_result,
            latest_scan_result,
        ]

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                f"/api/governance/policy-compliance/summary/{PROJECT_ID}"
            )
            assert r.status_code == 200
            data = r.json()
            assert data["project_id"] == PROJECT_ID
            assert data["total_scans"] == 3
            assert data["total_violations"] == 2
            assert data["compliance_rate"] == 85.0
            # by_severity should have counts
            assert data["by_severity"]["high"] >= 0
            assert data["by_severity"]["critical"] >= 0
        finally:
            app.dependency_overrides.pop(get_db, None)
