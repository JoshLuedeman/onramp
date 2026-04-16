"""Tests for RBAC health monitor — models, schemas, service, and routes."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROJECT_ID = "proj-test-rbac"
SUBSCRIPTION_ID = "sub-00000000-0000-0000-0000-000000000001"


# ── Model import tests ───────────────────────────────────────────────────────


class TestRBACModelsImportable:
    """Verify RBAC models load and have correct table names."""

    def test_models_importable(self):
        from app.models.rbac_health import RBACFinding, RBACScanResult

        assert RBACScanResult.__tablename__ == "rbac_scan_results"
        assert RBACFinding.__tablename__ == "rbac_findings"

    def test_models_in_metadata(self):
        from app.models import Base

        table_names = set(Base.metadata.tables.keys())
        assert "rbac_scan_results" in table_names
        assert "rbac_findings" in table_names

    def test_scan_result_has_expected_columns(self):
        from app.models.rbac_health import RBACScanResult

        cols = {c.name for c in RBACScanResult.__table__.columns}
        expected = {
            "id", "project_id", "tenant_id", "subscription_id",
            "health_score", "total_assignments", "finding_count",
            "scan_timestamp", "status", "created_at", "updated_at",
        }
        assert expected.issubset(cols)

    def test_finding_has_expected_columns(self):
        from app.models.rbac_health import RBACFinding

        cols = {c.name for c in RBACFinding.__table__.columns}
        expected = {
            "id", "scan_result_id", "finding_type", "severity",
            "principal_id", "principal_name", "role_name", "scope",
            "description", "remediation", "created_at",
        }
        assert expected.issubset(cols)

    def test_scan_result_indexes(self):
        from app.models.rbac_health import RBACScanResult

        index_names = {idx.name for idx in RBACScanResult.__table__.indexes}
        assert "ix_rbac_scan_results_project_scan" in index_names

    def test_finding_indexes(self):
        from app.models.rbac_health import RBACFinding

        index_names = {idx.name for idx in RBACFinding.__table__.indexes}
        assert "ix_rbac_findings_result_severity" in index_names

    def test_models_in_all_exports(self):
        from app.models import __all__

        assert "RBACScanResult" in __all__
        assert "RBACFinding" in __all__

    def test_scan_result_primary_key(self):
        from app.models.rbac_health import RBACScanResult

        pk_cols = [c.name for c in RBACScanResult.__table__.columns if c.primary_key]
        assert pk_cols == ["id"]

    def test_finding_primary_key(self):
        from app.models.rbac_health import RBACFinding

        pk_cols = [c.name for c in RBACFinding.__table__.columns if c.primary_key]
        assert pk_cols == ["id"]

    def test_scan_result_foreign_keys(self):
        from app.models.rbac_health import RBACScanResult

        fk_targets = set()
        for col in RBACScanResult.__table__.columns:
            for fk in col.foreign_keys:
                fk_targets.add(fk.target_fullname)
        assert "projects.id" in fk_targets
        assert "tenants.id" in fk_targets

    def test_finding_foreign_keys(self):
        from app.models.rbac_health import RBACFinding

        fk_targets = set()
        for col in RBACFinding.__table__.columns:
            for fk in col.foreign_keys:
                fk_targets.add(fk.target_fullname)
        assert "rbac_scan_results.id" in fk_targets


# ── Schema tests ─────────────────────────────────────────────────────────────


class TestRBACSchemas:
    """Verify RBAC Pydantic schemas validate correctly."""

    def test_enums_importable(self):
        from app.schemas.rbac_health import (
            RBACFindingType,
            RBACScanStatus,
            RBACSeverity,
        )

        assert RBACFindingType.OVER_PERMISSIONED == "over_permissioned"
        assert RBACFindingType.STALE_ASSIGNMENT == "stale_assignment"
        assert RBACFindingType.CUSTOM_ROLE_PROLIFERATION == "custom_role_proliferation"
        assert RBACFindingType.MISSING_PIM == "missing_pim"
        assert RBACFindingType.EXPIRING_CREDENTIAL == "expiring_credential"
        assert RBACSeverity.CRITICAL == "critical"
        assert RBACScanStatus.COMPLETED == "completed"

    def test_health_summary_defaults(self):
        from app.schemas.rbac_health import RBACHealthSummary

        summary = RBACHealthSummary(project_id="p1")
        assert summary.health_score == 100.0
        assert summary.total_findings == 0
        assert summary.findings_by_type["over_permissioned"] == 0
        assert summary.findings_by_severity["critical"] == 0
        assert summary.top_risks == []
        assert summary.latest_scan_at is None

    def test_scan_result_list_schema(self):
        from app.schemas.rbac_health import RBACScanResultList

        result_list = RBACScanResultList(scan_results=[], total=0)
        assert result_list.scan_results == []
        assert result_list.total == 0

    def test_scan_request_schema(self):
        from app.schemas.rbac_health import RBACScanRequest

        req = RBACScanRequest(subscription_id="sub-123", tenant_id="t-1")
        assert req.subscription_id == "sub-123"
        assert req.tenant_id == "t-1"

    def test_scan_request_minimal(self):
        from app.schemas.rbac_health import RBACScanRequest

        req = RBACScanRequest(subscription_id="sub-123")
        assert req.tenant_id is None

    def test_finding_response_schema(self):
        from app.schemas.rbac_health import RBACFindingResponse

        now = datetime.now(timezone.utc)
        finding = RBACFindingResponse(
            id="f1",
            scan_result_id="s1",
            finding_type="over_permissioned",
            severity="critical",
            principal_id="user-001",
            principal_name="admin@contoso.com",
            role_name="Owner",
            scope="/subscriptions/sub-1",
            description="Owner at subscription scope",
            remediation="Reassign to resource group",
            created_at=now,
        )
        assert finding.finding_type == "over_permissioned"
        assert finding.severity == "critical"

    def test_scan_result_response_schema(self):
        from app.schemas.rbac_health import RBACScanResultResponse

        now = datetime.now(timezone.utc)
        result = RBACScanResultResponse(
            id="s1",
            project_id="p1",
            subscription_id="sub-1",
            health_score=85.0,
            total_assignments=10,
            finding_count=3,
            scan_timestamp=now,
            status="completed",
            created_at=now,
            updated_at=now,
        )
        assert result.health_score == 85.0
        assert result.findings == []


# ── Service tests: Mock assignment generation ────────────────────────────────


class TestRBACMonitorAssignments:
    """Test mock assignment generation."""

    @pytest.mark.asyncio
    async def test_get_role_assignments_dev_mode(self):
        from app.services.rbac_monitor import rbac_monitor

        with patch("app.services.rbac_monitor.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            assignments = await rbac_monitor.get_role_assignments(SUBSCRIPTION_ID)

        assert isinstance(assignments, list)
        assert len(assignments) > 0

        # Verify structure of first assignment
        first = assignments[0]
        assert "principal_id" in first
        assert "principal_name" in first
        assert "role_name" in first
        assert "scope" in first
        assert "is_pim" in first

    @pytest.mark.asyncio
    async def test_get_role_assignments_includes_various_types(self):
        from app.services.rbac_monitor import rbac_monitor

        with patch("app.services.rbac_monitor.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            assignments = await rbac_monitor.get_role_assignments(SUBSCRIPTION_ID)

        role_types = {a.get("role_type") for a in assignments}
        assert "BuiltInRole" in role_types
        assert "CustomRole" in role_types

        principal_types = {a.get("principal_type") for a in assignments}
        assert "User" in principal_types
        assert "ServicePrincipal" in principal_types

    @pytest.mark.asyncio
    async def test_get_role_assignments_prod_mode_empty(self):
        from app.services.rbac_monitor import rbac_monitor

        with patch("app.services.rbac_monitor.settings") as mock_settings:
            mock_settings.is_dev_mode = False
            assignments = await rbac_monitor.get_role_assignments(SUBSCRIPTION_ID)

        assert assignments == []


# ── Service tests: Finding detection ─────────────────────────────────────────


class TestRBACMonitorFindings:
    """Test individual finding detection types."""

    @pytest.mark.asyncio
    async def test_detect_over_permissioned_owner(self):
        from app.services.rbac_monitor import rbac_monitor

        assignments = [
            {
                "principal_id": "user-001",
                "principal_name": "admin@contoso.com",
                "role_name": "Owner",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1",
                "is_pim": False,
                "last_activity": datetime.now(timezone.utc).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        over_perm = [f for f in findings if f["finding_type"] == "over_permissioned"]
        assert len(over_perm) >= 1
        assert over_perm[0]["severity"] == "critical"
        assert "Owner" in over_perm[0]["description"]

    @pytest.mark.asyncio
    async def test_detect_over_permissioned_contributor(self):
        from app.services.rbac_monitor import rbac_monitor

        assignments = [
            {
                "principal_id": "user-002",
                "principal_name": "dev@contoso.com",
                "role_name": "Contributor",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1",
                "is_pim": False,
                "last_activity": datetime.now(timezone.utc).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        over_perm = [f for f in findings if f["finding_type"] == "over_permissioned"]
        assert len(over_perm) >= 1
        assert over_perm[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_no_over_permissioned_at_rg_scope(self):
        from app.services.rbac_monitor import rbac_monitor

        assignments = [
            {
                "principal_id": "user-001",
                "principal_name": "admin@contoso.com",
                "role_name": "Owner",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1/resourceGroups/rg-app",
                "is_pim": True,
                "last_activity": datetime.now(timezone.utc).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        over_perm = [f for f in findings if f["finding_type"] == "over_permissioned"]
        assert len(over_perm) == 0

    @pytest.mark.asyncio
    async def test_detect_stale_assignment(self):
        from app.services.rbac_monitor import rbac_monitor

        now = datetime.now(timezone.utc)
        assignments = [
            {
                "principal_id": "user-stale",
                "principal_name": "stale@contoso.com",
                "role_name": "Reader",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1/resourceGroups/rg-1",
                "is_pim": True,
                "last_activity": (now - timedelta(days=100)).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        stale = [f for f in findings if f["finding_type"] == "stale_assignment"]
        assert len(stale) == 1
        assert stale[0]["severity"] == "medium"  # 100 days (< 180)

    @pytest.mark.asyncio
    async def test_detect_stale_assignment_high_severity(self):
        from app.services.rbac_monitor import rbac_monitor

        now = datetime.now(timezone.utc)
        assignments = [
            {
                "principal_id": "user-very-stale",
                "principal_name": "old@contoso.com",
                "role_name": "Contributor",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1/resourceGroups/rg-1",
                "is_pim": True,
                "last_activity": (now - timedelta(days=200)).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        stale = [f for f in findings if f["finding_type"] == "stale_assignment"]
        assert len(stale) == 1
        assert stale[0]["severity"] == "high"  # 200 days (> 180)

    @pytest.mark.asyncio
    async def test_no_stale_for_recent_activity(self):
        from app.services.rbac_monitor import rbac_monitor

        now = datetime.now(timezone.utc)
        assignments = [
            {
                "principal_id": "user-active",
                "principal_name": "active@contoso.com",
                "role_name": "Reader",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1/resourceGroups/rg-1",
                "is_pim": True,
                "last_activity": (now - timedelta(days=30)).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        stale = [f for f in findings if f["finding_type"] == "stale_assignment"]
        assert len(stale) == 0

    @pytest.mark.asyncio
    async def test_detect_missing_pim(self):
        from app.services.rbac_monitor import rbac_monitor

        assignments = [
            {
                "principal_id": "user-no-pim",
                "principal_name": "nopim@contoso.com",
                "role_name": "Owner",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1/resourceGroups/rg-1",
                "is_pim": False,
                "last_activity": datetime.now(timezone.utc).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        pim = [f for f in findings if f["finding_type"] == "missing_pim"]
        assert len(pim) == 1
        assert pim[0]["severity"] == "high"
        assert "PIM" in pim[0]["description"]

    @pytest.mark.asyncio
    async def test_no_missing_pim_with_pim(self):
        from app.services.rbac_monitor import rbac_monitor

        assignments = [
            {
                "principal_id": "user-pim",
                "principal_name": "pim@contoso.com",
                "role_name": "Owner",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1/resourceGroups/rg-1",
                "is_pim": True,
                "last_activity": datetime.now(timezone.utc).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        pim = [f for f in findings if f["finding_type"] == "missing_pim"]
        assert len(pim) == 0

    @pytest.mark.asyncio
    async def test_detect_expiring_credential(self):
        from app.services.rbac_monitor import rbac_monitor

        now = datetime.now(timezone.utc)
        assignments = [
            {
                "principal_id": "sp-001",
                "principal_name": "deploy-pipeline",
                "principal_type": "ServicePrincipal",
                "role_name": "Contributor",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1/resourceGroups/rg-deploy",
                "is_pim": True,
                "last_activity": now.isoformat(),
                "key_expiry": (now + timedelta(days=15)).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        expiring = [f for f in findings if f["finding_type"] == "expiring_credential"]
        assert len(expiring) == 1
        assert expiring[0]["severity"] == "high"  # 15 days (> 7)

    @pytest.mark.asyncio
    async def test_detect_expiring_credential_critical(self):
        from app.services.rbac_monitor import rbac_monitor

        now = datetime.now(timezone.utc)
        assignments = [
            {
                "principal_id": "sp-002",
                "principal_name": "critical-sp",
                "principal_type": "ServicePrincipal",
                "role_name": "Contributor",
                "role_type": "BuiltInRole",
                "scope": "/subscriptions/sub-1/resourceGroups/rg-1",
                "is_pim": True,
                "last_activity": now.isoformat(),
                "key_expiry": (now + timedelta(days=3)).isoformat(),
            },
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        expiring = [f for f in findings if f["finding_type"] == "expiring_credential"]
        assert len(expiring) == 1
        assert expiring[0]["severity"] == "critical"  # 3 days (≤ 7)

    @pytest.mark.asyncio
    async def test_detect_custom_role_proliferation(self):
        from app.services.rbac_monitor import rbac_monitor

        now = datetime.now(timezone.utc)
        assignments = [
            {
                "principal_id": f"user-{i}",
                "principal_name": f"user-{i}@contoso.com",
                "role_name": f"Custom Role {i}",
                "role_type": "CustomRole",
                "scope": f"/subscriptions/sub-1/resourceGroups/rg-{i}",
                "is_pim": True,
                "last_activity": now.isoformat(),
            }
            for i in range(12)
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        proliferation = [
            f for f in findings if f["finding_type"] == "custom_role_proliferation"
        ]
        assert len(proliferation) == 1
        assert proliferation[0]["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_no_custom_role_proliferation_under_threshold(self):
        from app.services.rbac_monitor import rbac_monitor

        now = datetime.now(timezone.utc)
        assignments = [
            {
                "principal_id": f"user-{i}",
                "principal_name": f"user-{i}@contoso.com",
                "role_name": f"Custom Role {i}",
                "role_type": "CustomRole",
                "scope": f"/subscriptions/sub-1/resourceGroups/rg-{i}",
                "is_pim": True,
                "last_activity": now.isoformat(),
            }
            for i in range(8)
        ]
        findings = await rbac_monitor.analyze_findings(assignments)
        proliferation = [
            f for f in findings if f["finding_type"] == "custom_role_proliferation"
        ]
        assert len(proliferation) == 0

    @pytest.mark.asyncio
    async def test_empty_assignments_no_findings(self):
        from app.services.rbac_monitor import rbac_monitor

        findings = await rbac_monitor.analyze_findings([])
        assert findings == []


# ── Service tests: Health score calculation ──────────────────────────────────


class TestRBACHealthScore:
    """Test RBAC health score calculation."""

    @pytest.mark.asyncio
    async def test_perfect_score_no_findings(self):
        from app.services.rbac_monitor import rbac_monitor

        score = await rbac_monitor.get_rbac_score([])
        assert score == 100.0

    @pytest.mark.asyncio
    async def test_score_deduction_critical(self):
        from app.services.rbac_monitor import rbac_monitor

        findings = [{"severity": "critical"}]
        score = await rbac_monitor.get_rbac_score(findings)
        assert score == 85.0  # 100 - 15

    @pytest.mark.asyncio
    async def test_score_deduction_high(self):
        from app.services.rbac_monitor import rbac_monitor

        findings = [{"severity": "high"}]
        score = await rbac_monitor.get_rbac_score(findings)
        assert score == 90.0  # 100 - 10

    @pytest.mark.asyncio
    async def test_score_deduction_medium(self):
        from app.services.rbac_monitor import rbac_monitor

        findings = [{"severity": "medium"}]
        score = await rbac_monitor.get_rbac_score(findings)
        assert score == 95.0  # 100 - 5

    @pytest.mark.asyncio
    async def test_score_deduction_low(self):
        from app.services.rbac_monitor import rbac_monitor

        findings = [{"severity": "low"}]
        score = await rbac_monitor.get_rbac_score(findings)
        assert score == 98.0  # 100 - 2

    @pytest.mark.asyncio
    async def test_score_floor_at_zero(self):
        from app.services.rbac_monitor import rbac_monitor

        # Many critical findings should floor at 0
        findings = [{"severity": "critical"} for _ in range(20)]
        score = await rbac_monitor.get_rbac_score(findings)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_score_mixed_severities(self):
        from app.services.rbac_monitor import rbac_monitor

        findings = [
            {"severity": "critical"},  # -15
            {"severity": "high"},      # -10
            {"severity": "medium"},    # -5
            {"severity": "low"},       # -2
        ]
        score = await rbac_monitor.get_rbac_score(findings)
        assert score == 68.0  # 100 - 32


# ── Service tests: Full scan flow ────────────────────────────────────────────


class TestRBACMonitorScanFlow:
    """Test end-to-end scan flow."""

    @pytest.mark.asyncio
    async def test_scan_rbac_health_dev_mode(self):
        from app.services.rbac_monitor import rbac_monitor

        with patch("app.services.rbac_monitor.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await rbac_monitor.scan_rbac_health(
                project_id=PROJECT_ID,
                subscription_id=SUBSCRIPTION_ID,
            )

        assert result["project_id"] == PROJECT_ID
        assert result["subscription_id"] == SUBSCRIPTION_ID
        assert result["status"] == "completed"
        assert isinstance(result["health_score"], float)
        assert 0 <= result["health_score"] <= 100
        assert result["total_assignments"] > 0
        assert result["finding_count"] > 0
        assert len(result["findings"]) == result["finding_count"]

    @pytest.mark.asyncio
    async def test_scan_rbac_health_result_has_id(self):
        from app.services.rbac_monitor import rbac_monitor

        with patch("app.services.rbac_monitor.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await rbac_monitor.scan_rbac_health(
                project_id=PROJECT_ID,
                subscription_id=SUBSCRIPTION_ID,
            )

        assert "id" in result
        assert len(result["id"]) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_scan_rbac_health_with_tenant(self):
        from app.services.rbac_monitor import rbac_monitor

        with patch("app.services.rbac_monitor.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await rbac_monitor.scan_rbac_health(
                project_id=PROJECT_ID,
                subscription_id=SUBSCRIPTION_ID,
                tenant_id="tenant-1",
            )

        assert result["tenant_id"] == "tenant-1"

    @pytest.mark.asyncio
    async def test_scan_publishes_sse_event(self):
        from app.services.rbac_monitor import rbac_monitor

        with (
            patch("app.services.rbac_monitor.settings") as mock_settings,
            patch("app.services.rbac_monitor.event_stream") as mock_stream,
        ):
            mock_settings.is_dev_mode = True
            mock_stream.publish = AsyncMock(return_value=0)

            result = await rbac_monitor.scan_rbac_health(
                project_id=PROJECT_ID,
                subscription_id=SUBSCRIPTION_ID,
            )

        mock_stream.publish.assert_called_once()
        call_args = mock_stream.publish.call_args
        assert call_args[0][0] == "governance_score_updated"
        event_data = call_args[0][1]
        assert event_data["component"] == "rbac"
        assert event_data["project_id"] == PROJECT_ID

    @pytest.mark.asyncio
    async def test_scan_handles_exception_gracefully(self):
        from app.services.rbac_monitor import rbac_monitor

        with patch.object(
            rbac_monitor, "get_role_assignments", side_effect=RuntimeError("Azure API error")
        ):
            result = await rbac_monitor.scan_rbac_health(
                project_id=PROJECT_ID,
                subscription_id=SUBSCRIPTION_ID,
            )

        assert result["status"] == "failed"
        assert result["health_score"] == 0.0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_scan_dev_mode_finds_all_types(self):
        """Dev mode mock data should trigger all finding types."""
        from app.services.rbac_monitor import rbac_monitor

        with patch("app.services.rbac_monitor.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await rbac_monitor.scan_rbac_health(
                project_id=PROJECT_ID,
                subscription_id=SUBSCRIPTION_ID,
            )

        finding_types = {f["finding_type"] for f in result["findings"]}
        assert "over_permissioned" in finding_types
        assert "stale_assignment" in finding_types
        assert "missing_pim" in finding_types
        assert "expiring_credential" in finding_types
        assert "custom_role_proliferation" in finding_types


# ── Service tests: Singleton and task registration ───────────────────────────


class TestRBACMonitorRegistration:
    """Test singleton and task scheduler registration."""

    def test_singleton_exists(self):
        from app.services.rbac_monitor import rbac_monitor

        assert rbac_monitor is not None
        assert isinstance(rbac_monitor, type(rbac_monitor))

    def test_task_registered_with_scheduler(self):
        from app.services.task_scheduler import task_scheduler

        tasks = task_scheduler.registered_tasks
        assert "rbac_health_scan" in tasks

    def test_task_has_correct_interval(self):
        from app.services.task_scheduler import task_scheduler

        task = task_scheduler.registered_tasks["rbac_health_scan"]
        assert task.interval_seconds == 3600


# ── Service tests: Helpers ───────────────────────────────────────────────────


class TestRBACMonitorHelpers:
    """Test internal helper methods."""

    def test_is_subscription_scope_true(self):
        from app.services.rbac_monitor import RBACMonitor

        assert RBACMonitor._is_subscription_scope("/subscriptions/sub-1")
        assert RBACMonitor._is_subscription_scope("/subscriptions/sub-1/")

    def test_is_subscription_scope_false_rg(self):
        from app.services.rbac_monitor import RBACMonitor

        assert not RBACMonitor._is_subscription_scope(
            "/subscriptions/sub-1/resourceGroups/rg-1"
        )

    def test_is_subscription_scope_false_resource(self):
        from app.services.rbac_monitor import RBACMonitor

        assert not RBACMonitor._is_subscription_scope(
            "/subscriptions/sub-1/resourceGroups/rg-1/providers/Microsoft.Compute/virtualMachines/vm-1"
        )


# ── API route tests (no-DB / mock mode) ─────────────────────────────────────


class TestRBACRoutesNoDB:
    """Test RBAC endpoints when no DB is configured (dev mode)."""

    def test_trigger_scan(self):
        payload = {"subscription_id": SUBSCRIPTION_ID}
        r = client.post(f"/api/governance/rbac/scan/{PROJECT_ID}", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["subscription_id"] == SUBSCRIPTION_ID
        assert data["status"] == "completed"
        assert "health_score" in data
        assert "findings" in data
        assert isinstance(data["findings"], list)

    def test_trigger_scan_with_tenant(self):
        payload = {
            "subscription_id": SUBSCRIPTION_ID,
            "tenant_id": "tenant-abc",
        }
        r = client.post(f"/api/governance/rbac/scan/{PROJECT_ID}", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["tenant_id"] == "tenant-abc"

    def test_trigger_scan_missing_subscription(self):
        r = client.post(f"/api/governance/rbac/scan/{PROJECT_ID}", json={})
        assert r.status_code == 422

    def test_list_results_empty(self):
        r = client.get("/api/governance/rbac/results")
        assert r.status_code == 200
        data = r.json()
        assert data["scan_results"] == []
        assert data["total"] == 0

    def test_list_results_with_project_filter(self):
        r = client.get(
            "/api/governance/rbac/results",
            params={"project_id": PROJECT_ID},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["scan_results"] == []

    def test_get_result_no_db(self):
        r = client.get("/api/governance/rbac/results/non-existent")
        assert r.status_code == 404

    def test_get_summary_no_db(self):
        r = client.get(f"/api/governance/rbac/summary/{PROJECT_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["health_score"] == 100.0
        assert data["total_findings"] == 0

    def test_list_findings_empty(self):
        r = client.get("/api/governance/rbac/findings")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_findings_with_type_filter(self):
        r = client.get(
            "/api/governance/rbac/findings",
            params={"finding_type": "over_permissioned"},
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_list_findings_with_severity_filter(self):
        r = client.get(
            "/api/governance/rbac/findings",
            params={"severity": "critical"},
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_scan_response_has_finding_details(self):
        payload = {"subscription_id": SUBSCRIPTION_ID}
        r = client.post(f"/api/governance/rbac/scan/{PROJECT_ID}", json=payload)
        assert r.status_code == 200
        data = r.json()

        # Should have findings from dev mode mock data
        assert len(data["findings"]) > 0

        # Each finding should have required fields
        for finding in data["findings"]:
            assert "id" in finding
            assert "finding_type" in finding
            assert "severity" in finding
            assert "principal_id" in finding
            assert "role_name" in finding
            assert "description" in finding
            assert "remediation" in finding

    def test_scan_response_score_within_range(self):
        payload = {"subscription_id": SUBSCRIPTION_ID}
        r = client.post(f"/api/governance/rbac/scan/{PROJECT_ID}", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert 0 <= data["health_score"] <= 100


# ── Periodic task callback tests ─────────────────────────────────────────────


class TestPeriodicTaskCallback:
    """Test the periodic task function."""

    @pytest.mark.asyncio
    async def test_periodic_callback_no_project(self):
        from app.services.rbac_monitor import _periodic_rbac_scan

        result = await _periodic_rbac_scan(tenant_id=None, project_id=None)
        assert result is not None
        assert "Skipped" in result["message"]

    @pytest.mark.asyncio
    async def test_periodic_callback_with_project(self):
        from app.services.rbac_monitor import _periodic_rbac_scan

        with patch("app.services.rbac_monitor.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await _periodic_rbac_scan(
                tenant_id=None, project_id=PROJECT_ID
            )

        assert result is not None
        assert "completed" in result["message"]
        assert "health_score" in result
        assert "finding_count" in result
