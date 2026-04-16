"""Tests for drift detection models, schemas, and API routes."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROJECT_ID = "proj-test-drift"


# ── Model & schema import tests ──────────────────────────────────────────────


class TestDriftModelsImportable:
    """Verify models load and have correct table names."""

    def test_models_importable(self):
        from app.models import DriftBaseline, DriftEvent, DriftScanResult

        assert DriftBaseline.__tablename__ == "drift_baselines"
        assert DriftEvent.__tablename__ == "drift_events"
        assert DriftScanResult.__tablename__ == "drift_scan_results"

    def test_models_in_metadata(self):
        from app.models import Base

        table_names = set(Base.metadata.tables.keys())
        assert "drift_baselines" in table_names
        assert "drift_events" in table_names
        assert "drift_scan_results" in table_names

    def test_baseline_has_expected_columns(self):
        from app.models.drift import DriftBaseline

        cols = {c.name for c in DriftBaseline.__table__.columns}
        expected = {
            "id", "project_id", "architecture_version", "baseline_data",
            "status", "captured_by", "created_at", "updated_at",
        }
        assert expected.issubset(cols)

    def test_event_has_expected_columns(self):
        from app.models.drift import DriftEvent

        cols = {c.name for c in DriftEvent.__table__.columns}
        expected = {
            "id", "baseline_id", "scan_result_id", "resource_type",
            "resource_id", "drift_type", "expected_value", "actual_value",
            "severity", "detected_at", "resolved_at", "resolution_type",
        }
        assert expected.issubset(cols)

    def test_scan_result_has_expected_columns(self):
        from app.models.drift import DriftScanResult

        cols = {c.name for c in DriftScanResult.__table__.columns}
        expected = {
            "id", "baseline_id", "project_id", "tenant_id",
            "scan_started_at", "scan_completed_at", "total_resources_scanned",
            "drifted_count", "new_count", "removed_count",
            "status", "error_message",
        }
        assert expected.issubset(cols)

    def test_baseline_indexes(self):
        from app.models.drift import DriftBaseline

        index_names = {idx.name for idx in DriftBaseline.__table__.indexes}
        assert "ix_drift_baselines_project_status" in index_names

    def test_event_indexes(self):
        from app.models.drift import DriftEvent

        index_names = {idx.name for idx in DriftEvent.__table__.indexes}
        assert "ix_drift_events_baseline_severity" in index_names
        assert "ix_drift_events_resource_detected" in index_names

    def test_scan_result_indexes(self):
        from app.models.drift import DriftScanResult

        index_names = {idx.name for idx in DriftScanResult.__table__.indexes}
        assert "ix_drift_scan_results_project_started" in index_names


class TestDriftSchemasImportable:
    """Verify schemas load and validate correctly."""

    def test_enums_importable(self):
        from app.schemas.drift import (
            DriftSeverity,
            DriftStatus,
            DriftType,
            ScanStatus,
        )

        assert DriftSeverity.CRITICAL == "critical"
        assert DriftType.ADDED == "added"
        assert DriftStatus.ACTIVE == "active"
        assert ScanStatus.RUNNING == "running"

    def test_baseline_create_schema(self):
        from app.schemas.drift import DriftBaselineCreate

        payload = DriftBaselineCreate(
            project_id="p1",
            baseline_data={"resources": []},
            architecture_version=1,
            captured_by="user@example.com",
        )
        assert payload.project_id == "p1"
        assert payload.baseline_data == {"resources": []}
        assert payload.architecture_version == 1
        assert payload.captured_by == "user@example.com"

    def test_baseline_create_minimal(self):
        from app.schemas.drift import DriftBaselineCreate

        payload = DriftBaselineCreate(
            project_id="p1",
            baseline_data={"resources": []},
        )
        assert payload.architecture_version is None
        assert payload.captured_by is None

    def test_drift_summary_defaults(self):
        from app.schemas.drift import DriftSummary

        summary = DriftSummary(project_id="p1")
        assert summary.total_events == 0
        assert summary.unresolved_events == 0
        assert summary.by_severity["critical"] == 0
        assert summary.by_type["added"] == 0
        assert summary.latest_scan_at is None
        assert summary.active_baseline_id is None

    def test_scan_result_list_schema(self):
        from app.schemas.drift import DriftScanResultList

        result_list = DriftScanResultList(scan_results=[], total=0)
        assert result_list.scan_results == []
        assert result_list.total == 0


# ── API route tests (no-DB / mock mode) ─────────────────────────────────────


class TestBaselineRoutesNoDB:
    """Test baseline endpoints when no DB is configured."""

    def test_create_baseline(self):
        payload = {
            "project_id": PROJECT_ID,
            "baseline_data": {"resources": [{"id": "vm-1", "type": "vm"}]},
            "architecture_version": 2,
            "captured_by": "admin@test.com",
        }
        r = client.post("/api/governance/drift/baselines", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["baseline_data"] == payload["baseline_data"]
        assert data["architecture_version"] == 2
        assert data["status"] == "active"
        assert data["captured_by"] == "admin@test.com"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_baseline_minimal(self):
        payload = {
            "project_id": PROJECT_ID,
            "baseline_data": {"resources": []},
        }
        r = client.post("/api/governance/drift/baselines", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["architecture_version"] is None
        assert data["captured_by"] is None

    def test_create_baseline_missing_data(self):
        payload = {"project_id": PROJECT_ID}
        r = client.post("/api/governance/drift/baselines", json=payload)
        assert r.status_code == 422

    def test_list_baselines_empty(self):
        r = client.get(
            "/api/governance/drift/baselines",
            params={"project_id": PROJECT_ID},
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_list_baselines_requires_project_id(self):
        r = client.get("/api/governance/drift/baselines")
        assert r.status_code == 422

    def test_get_baseline_no_db(self):
        r = client.get("/api/governance/drift/baselines/non-existent")
        assert r.status_code == 404

    def test_supersede_baseline_no_db(self):
        r = client.post(
            "/api/governance/drift/baselines/non-existent/supersede"
        )
        assert r.status_code == 404


class TestScanResultRoutesNoDB:
    """Test scan result endpoints when no DB is configured."""

    def test_list_scan_results_empty(self):
        r = client.get("/api/governance/drift/scan-results")
        assert r.status_code == 200
        data = r.json()
        assert data["scan_results"] == []
        assert data["total"] == 0

    def test_list_scan_results_with_filters(self):
        r = client.get(
            "/api/governance/drift/scan-results",
            params={"project_id": PROJECT_ID, "status": "completed"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["scan_results"] == []
        assert data["total"] == 0

    def test_get_scan_result_no_db(self):
        r = client.get("/api/governance/drift/scan-results/non-existent")
        assert r.status_code == 404


class TestEventRoutesNoDB:
    """Test drift event endpoints when no DB is configured."""

    def test_list_events_empty(self):
        r = client.get("/api/governance/drift/events")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_events_with_filters(self):
        r = client.get(
            "/api/governance/drift/events",
            params={
                "baseline_id": "b-1",
                "severity": "critical",
                "drift_type": "modified",
                "resolved": "false",
            },
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_list_events_resolved_filter(self):
        r = client.get(
            "/api/governance/drift/events",
            params={"resolved": "true"},
        )
        assert r.status_code == 200
        assert r.json() == []


class TestSummaryRoutesNoDB:
    """Test drift summary endpoint when no DB is configured."""

    def test_get_summary_no_db(self):
        r = client.get(f"/api/governance/drift/summary/{PROJECT_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["total_events"] == 0
        assert data["unresolved_events"] == 0
        assert data["by_severity"]["critical"] == 0
        assert data["by_severity"]["high"] == 0
        assert data["by_severity"]["medium"] == 0
        assert data["by_severity"]["low"] == 0
        assert data["by_type"]["added"] == 0
        assert data["by_type"]["removed"] == 0
        assert data["by_type"]["modified"] == 0
        assert data["by_type"]["policy_violation"] == 0
        assert data["latest_scan_at"] is None
        assert data["active_baseline_id"] is None


# ── Router registration test ─────────────────────────────────────────────────


def _make_mock_baseline(**overrides):
    """Create a mock DriftBaseline ORM object."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": str(uuid.uuid4()),
        "project_id": PROJECT_ID,
        "architecture_version": 1,
        "baseline_data": {"resources": []},
        "status": "active",
        "captured_by": "test@example.com",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_mock_event(**overrides):
    """Create a mock DriftEvent ORM object."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": str(uuid.uuid4()),
        "baseline_id": str(uuid.uuid4()),
        "scan_result_id": None,
        "resource_type": "Microsoft.Compute/virtualMachines",
        "resource_id": "/subscriptions/sub1/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm1",
        "drift_type": "modified",
        "expected_value": {"sku": "Standard_B2s"},
        "actual_value": {"sku": "Standard_D4s_v3"},
        "severity": "high",
        "detected_at": now,
        "resolved_at": None,
        "resolution_type": None,
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_mock_scan_result(**overrides):
    """Create a mock DriftScanResult ORM object."""
    now = datetime.now(timezone.utc)
    defaults = {
        "id": str(uuid.uuid4()),
        "baseline_id": str(uuid.uuid4()),
        "project_id": PROJECT_ID,
        "tenant_id": None,
        "scan_started_at": now,
        "scan_completed_at": now,
        "total_resources_scanned": 10,
        "drifted_count": 2,
        "new_count": 1,
        "removed_count": 0,
        "status": "completed",
        "error_message": None,
        "events": [],
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestBaselineRoutesWithDB:
    """Test baseline endpoints with a mocked DB session."""

    def test_create_baseline_with_db(self):
        mock_db = AsyncMock()
        mock_baseline = _make_mock_baseline()

        async def mock_flush():
            pass

        async def mock_refresh(obj):
            # Copy attributes from mock_baseline to obj
            for attr in ["id", "project_id", "architecture_version",
                         "baseline_data", "status", "captured_by",
                         "created_at", "updated_at"]:
                setattr(obj, attr, getattr(mock_baseline, attr))

        mock_db.flush = mock_flush
        mock_db.refresh = mock_refresh
        mock_db.add = MagicMock()

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            payload = {
                "project_id": PROJECT_ID,
                "baseline_data": {"resources": [{"id": "vm-1"}]},
                "architecture_version": 3,
            }
            r = client.post("/api/governance/drift/baselines", json=payload)
            assert r.status_code == 200
            assert mock_db.add.called
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_list_baselines_with_db(self):
        mock_baselines = [
            _make_mock_baseline(status="active"),
            _make_mock_baseline(status="superseded"),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_baselines
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                "/api/governance/drift/baselines",
                params={"project_id": PROJECT_ID},
            )
            assert r.status_code == 200
            data = r.json()
            assert len(data) == 2
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_get_baseline_with_db_found(self):
        mock_baseline = _make_mock_baseline()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_baseline

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(f"/api/governance/drift/baselines/{mock_baseline.id}")
            assert r.status_code == 200
            data = r.json()
            assert data["id"] == mock_baseline.id
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_get_baseline_with_db_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get("/api/governance/drift/baselines/nonexistent")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_supersede_baseline_with_db(self):
        mock_baseline = _make_mock_baseline(status="active")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_baseline

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        async def mock_flush():
            pass

        async def mock_refresh(obj):
            obj.status = "superseded"

        mock_db.flush = mock_flush
        mock_db.refresh = mock_refresh

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.post(
                f"/api/governance/drift/baselines/{mock_baseline.id}/supersede"
            )
            assert r.status_code == 200
            assert mock_baseline.status == "superseded"
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_supersede_baseline_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.post(
                "/api/governance/drift/baselines/nonexistent/supersede"
            )
            assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestScanResultRoutesWithDB:
    """Test scan result endpoints with a mocked DB session."""

    def test_list_scan_results_with_db(self):
        mock_scans = [_make_mock_scan_result()]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_scans
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                "/api/governance/drift/scan-results",
                params={"project_id": PROJECT_ID, "status": "completed"},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_get_scan_result_with_db_found(self):
        mock_scan = _make_mock_scan_result()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_scan

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(f"/api/governance/drift/scan-results/{mock_scan.id}")
            assert r.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_get_scan_result_with_db_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get("/api/governance/drift/scan-results/nonexistent")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestEventRoutesWithDB:
    """Test event endpoints with a mocked DB session."""

    def test_list_events_with_filters(self):
        mock_events = [
            _make_mock_event(severity="critical", drift_type="modified"),
        ]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_events
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                "/api/governance/drift/events",
                params={
                    "baseline_id": "b1",
                    "severity": "critical",
                    "drift_type": "modified",
                    "resolved": "false",
                },
            )
            assert r.status_code == 200
            data = r.json()
            assert len(data) == 1
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_list_events_resolved_true(self):
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(
                "/api/governance/drift/events",
                params={"resolved": "true"},
            )
            assert r.status_code == 200
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestSummaryRouteWithDB:
    """Test summary endpoint with a mocked DB session."""

    def test_summary_no_active_baseline(self):
        """When no active baseline, summary returns zeros."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(f"/api/governance/drift/summary/{PROJECT_ID}")
            assert r.status_code == 200
            data = r.json()
            assert data["total_events"] == 0
            assert data["active_baseline_id"] is None
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_summary_with_events(self):
        """When active baseline has events, summary aggregates correctly."""
        baseline_id = str(uuid.uuid4())
        mock_baseline = _make_mock_baseline(id=baseline_id)

        events = [
            _make_mock_event(
                baseline_id=baseline_id, severity="critical",
                drift_type="modified", resolved_at=None,
            ),
            _make_mock_event(
                baseline_id=baseline_id, severity="high",
                drift_type="added", resolved_at=None,
            ),
            _make_mock_event(
                baseline_id=baseline_id, severity="medium",
                drift_type="removed",
                resolved_at=datetime.now(timezone.utc),
            ),
        ]

        call_count = 0
        latest_scan_time = datetime.now(timezone.utc)

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # First call: find active baseline
                result.scalar_one_or_none.return_value = mock_baseline
            elif call_count == 2:
                # Second call: get events
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = events
                result.scalars.return_value = mock_scalars
            elif call_count == 3:
                # Third call: latest scan timestamp
                result.scalar_one_or_none.return_value = latest_scan_time
            return result

        mock_db = AsyncMock()
        mock_db.execute = mock_execute

        from app.db.session import get_db

        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            r = client.get(f"/api/governance/drift/summary/{PROJECT_ID}")
            assert r.status_code == 200
            data = r.json()
            assert data["total_events"] == 3
            assert data["unresolved_events"] == 2
            assert data["by_severity"]["critical"] == 1
            assert data["by_severity"]["high"] == 1
            assert data["by_severity"]["medium"] == 1
            assert data["by_type"]["modified"] == 1
            assert data["by_type"]["added"] == 1
            assert data["by_type"]["removed"] == 1
            assert data["active_baseline_id"] == baseline_id
            assert data["latest_scan_at"] is not None
        finally:
            app.dependency_overrides.pop(get_db, None)


# ── Router registration test ─────────────────────────────────────────────────


class TestRouterRegistration:
    """Verify the drift router is registered with the correct prefix."""

    def test_drift_routes_exist(self):
        routes = [r.path for r in app.routes]
        assert "/api/governance/drift/baselines" in routes
        assert "/api/governance/drift/baselines/{baseline_id}" in routes
        assert "/api/governance/drift/baselines/{baseline_id}/supersede" in routes
        assert "/api/governance/drift/scan-results" in routes
        assert "/api/governance/drift/scan-results/{scan_id}" in routes
        assert "/api/governance/drift/events" in routes
        assert "/api/governance/drift/summary/{project_id}" in routes


# ── Enum coverage tests ──────────────────────────────────────────────────────


class TestEnumValues:
    """Ensure all enum values are accessible."""

    def test_severity_values(self):
        from app.schemas.drift import DriftSeverity

        values = [e.value for e in DriftSeverity]
        assert values == ["critical", "high", "medium", "low"]

    def test_drift_type_values(self):
        from app.schemas.drift import DriftType

        values = [e.value for e in DriftType]
        assert values == ["added", "removed", "modified", "policy_violation"]

    def test_drift_status_values(self):
        from app.schemas.drift import DriftStatus

        values = [e.value for e in DriftStatus]
        assert values == ["active", "superseded"]

    def test_scan_status_values(self):
        from app.schemas.drift import ScanStatus

        values = [e.value for e in ScanStatus]
        assert values == ["running", "completed", "failed"]


# ── Relationship tests ───────────────────────────────────────────────────────


class TestModelRelationships:
    """Verify ORM relationships are correctly defined."""

    def test_baseline_has_events_relationship(self):
        from app.models.drift import DriftBaseline

        assert hasattr(DriftBaseline, "events")

    def test_baseline_has_scan_results_relationship(self):
        from app.models.drift import DriftBaseline

        assert hasattr(DriftBaseline, "scan_results")

    def test_event_has_baseline_relationship(self):
        from app.models.drift import DriftEvent

        assert hasattr(DriftEvent, "baseline")

    def test_event_has_scan_result_relationship(self):
        from app.models.drift import DriftEvent

        assert hasattr(DriftEvent, "scan_result")

    def test_scan_result_has_baseline_relationship(self):
        from app.models.drift import DriftScanResult

        assert hasattr(DriftScanResult, "baseline")

    def test_scan_result_has_events_relationship(self):
        from app.models.drift import DriftScanResult

        assert hasattr(DriftScanResult, "events")


# ── Foreign key tests ────────────────────────────────────────────────────────


class TestForeignKeys:
    """Verify foreign key constraints are set correctly."""

    def test_baseline_fk_to_projects(self):
        from app.models.drift import DriftBaseline

        col = DriftBaseline.__table__.c.project_id
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "projects.id" in fk_targets

    def test_event_fk_to_baseline(self):
        from app.models.drift import DriftEvent

        col = DriftEvent.__table__.c.baseline_id
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "drift_baselines.id" in fk_targets

    def test_event_fk_to_scan_result(self):
        from app.models.drift import DriftEvent

        col = DriftEvent.__table__.c.scan_result_id
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "drift_scan_results.id" in fk_targets

    def test_scan_result_fk_to_baseline(self):
        from app.models.drift import DriftScanResult

        col = DriftScanResult.__table__.c.baseline_id
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "drift_baselines.id" in fk_targets

    def test_scan_result_fk_to_projects(self):
        from app.models.drift import DriftScanResult

        col = DriftScanResult.__table__.c.project_id
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "projects.id" in fk_targets

    def test_scan_result_fk_to_tenants(self):
        from app.models.drift import DriftScanResult

        col = DriftScanResult.__table__.c.tenant_id
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "tenants.id" in fk_targets


# ── Migration script test ────────────────────────────────────────────────────


class TestMigrationScript:
    """Verify migration file is valid."""

    def test_migration_importable(self):
        import importlib

        m = importlib.import_module(
            "app.db.migrations.versions.009_add_drift_tables"
        )

        assert m.revision == "009"
        assert m.down_revision == "007"
        assert callable(m.upgrade)
        assert callable(m.downgrade)
