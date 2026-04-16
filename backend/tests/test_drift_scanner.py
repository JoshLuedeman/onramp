"""Tests for the configuration drift scanner service."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.drift_scanner import (
    IGNORED_PROPERTIES,
    SECURITY_PROPERTY_KEYWORDS,
    SECURITY_RESOURCE_TYPES,
    DriftScanner,
    _classify_severity,
    _deep_diff,
    _mock_baseline_resources,
    _mock_current_state,
    _severity_summary,
    drift_scanner,
)

client = TestClient(app)

PROJECT_ID = "proj-drift-test"
_BASE_SUB = "/subscriptions/00000000-0000-0000-0000-000000000001"


# ── Unit tests: deep diff ────────────────────────────────────────────────────


class TestDeepDiff:
    """Tests for the recursive dict comparison utility."""

    def test_identical_dicts(self):
        a = {"x": 1, "y": {"z": 2}}
        assert _deep_diff(a, a) == []

    def test_simple_value_change(self):
        a = {"x": 1, "y": 2}
        b = {"x": 1, "y": 3}
        changes = _deep_diff(a, b)
        assert len(changes) == 1
        assert changes[0]["path"] == "y"
        assert changes[0]["expected"] == 2
        assert changes[0]["actual"] == 3

    def test_nested_change(self):
        a = {"outer": {"inner": "old"}}
        b = {"outer": {"inner": "new"}}
        changes = _deep_diff(a, b)
        assert len(changes) == 1
        assert changes[0]["path"] == "outer.inner"

    def test_key_added(self):
        a = {"x": 1}
        b = {"x": 1, "y": 2}
        changes = _deep_diff(a, b)
        assert len(changes) == 1
        assert changes[0]["path"] == "y"
        assert changes[0]["expected"] is None
        assert changes[0]["actual"] == 2

    def test_key_removed(self):
        a = {"x": 1, "y": 2}
        b = {"x": 1}
        changes = _deep_diff(a, b)
        assert len(changes) == 1
        assert changes[0]["path"] == "y"
        assert changes[0]["expected"] == 2
        assert changes[0]["actual"] is None

    def test_ignores_noise_properties(self):
        a = {"etag": "old-etag", "provisioningState": "Succeeded", "value": 1}
        b = {"etag": "new-etag", "provisioningState": "Updating", "value": 1}
        changes = _deep_diff(a, b)
        assert len(changes) == 0

    def test_ignores_timestamp_properties(self):
        a = {"timestamp": "2024-01-01", "lastModifiedTime": "t1", "data": "same"}
        b = {"timestamp": "2024-06-01", "lastModifiedTime": "t2", "data": "same"}
        assert _deep_diff(a, b) == []

    def test_multiple_changes(self):
        a = {"a": 1, "b": 2, "c": 3}
        b = {"a": 10, "b": 2, "c": 30}
        changes = _deep_diff(a, b)
        assert len(changes) == 2
        paths = {c["path"] for c in changes}
        assert paths == {"a", "c"}

    def test_deeply_nested_change(self):
        a = {"l1": {"l2": {"l3": {"l4": "old"}}}}
        b = {"l1": {"l2": {"l3": {"l4": "new"}}}}
        changes = _deep_diff(a, b)
        assert len(changes) == 1
        assert changes[0]["path"] == "l1.l2.l3.l4"

    def test_empty_dicts(self):
        assert _deep_diff({}, {}) == []

    def test_list_value_change(self):
        """Lists are compared as opaque values (not recursively)."""
        a = {"rules": [1, 2]}
        b = {"rules": [1, 2, 3]}
        changes = _deep_diff(a, b)
        assert len(changes) == 1
        assert changes[0]["path"] == "rules"


# ── Unit tests: severity classification ──────────────────────────────────────


class TestClassifySeverity:
    """Tests for severity assignment logic."""

    def test_added_normal_resource(self):
        result = _classify_severity("Microsoft.Compute/virtualMachines", "added")
        assert result == "medium"

    def test_added_security_resource(self):
        result = _classify_severity(
            "Microsoft.Network/networkSecurityGroups", "added"
        )
        assert result == "high"

    def test_removed_normal_resource(self):
        result = _classify_severity("Microsoft.Web/sites", "removed")
        assert result == "medium"

    def test_removed_security_resource(self):
        result = _classify_severity("Microsoft.KeyVault/vaults", "removed")
        assert result == "high"

    def test_modified_tag_only_is_low(self):
        changes = [{"path": "properties.tags.env", "expected": "prod", "actual": "dev"}]
        result = _classify_severity(
            "Microsoft.Storage/storageAccounts", "modified", changes
        )
        assert result == "low"

    def test_modified_security_nsg_is_critical(self):
        changes = [
            {
                "path": "properties.securityRules",
                "expected": [{"name": "old"}],
                "actual": [{"name": "old"}, {"name": "new"}],
            }
        ]
        result = _classify_severity(
            "Microsoft.Network/networkSecurityGroups", "modified", changes
        )
        assert result == "critical"

    def test_modified_security_property_non_security_resource_is_high(self):
        changes = [
            {
                "path": "properties.encryption.enabled",
                "expected": True,
                "actual": False,
            }
        ]
        result = _classify_severity(
            "Microsoft.Storage/storageAccounts", "modified", changes
        )
        assert result == "high"

    def test_modified_config_is_medium(self):
        changes = [
            {
                "path": "properties.sku",
                "expected": "Standard_LRS",
                "actual": "Premium_LRS",
            }
        ]
        result = _classify_severity(
            "Microsoft.Storage/storageAccounts", "modified", changes
        )
        assert result == "medium"

    def test_modified_no_changes_is_medium(self):
        result = _classify_severity(
            "Microsoft.Compute/virtualMachines", "modified", []
        )
        assert result == "medium"

    def test_modified_with_none_changes_is_medium(self):
        result = _classify_severity(
            "Microsoft.Compute/virtualMachines", "modified", None
        )
        assert result == "medium"

    def test_firewall_property_is_high(self):
        changes = [
            {"path": "properties.firewall.enabled", "expected": True, "actual": False}
        ]
        result = _classify_severity("Microsoft.Web/sites", "modified", changes)
        assert result == "high"

    def test_https_only_change_is_high(self):
        changes = [
            {"path": "properties.httpsOnly", "expected": True, "actual": False}
        ]
        result = _classify_severity("Microsoft.Web/sites", "modified", changes)
        assert result == "high"


# ── Unit tests: compare_resources ────────────────────────────────────────────


class TestCompareResources:
    """Tests for the resource comparison logic."""

    @pytest.fixture
    def scanner(self):
        return DriftScanner()

    @pytest.mark.asyncio
    async def test_no_drift_identical(self, scanner):
        baseline = {"res1": {"resource_type": "T", "value": 1}}
        current = {"res1": {"resource_type": "T", "value": 1}}
        events = await scanner.compare_resources(baseline, current)
        assert events == []

    @pytest.mark.asyncio
    async def test_removed_resource(self, scanner):
        baseline = {"res1": {"resource_type": "Microsoft.Compute/virtualMachines"}}
        current = {}
        events = await scanner.compare_resources(baseline, current)
        assert len(events) == 1
        assert events[0]["drift_type"] == "removed"
        assert events[0]["resource_id"] == "res1"
        assert events[0]["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_added_resource(self, scanner):
        baseline = {}
        current = {"res1": {"resource_type": "Microsoft.Cache/redis"}}
        events = await scanner.compare_resources(baseline, current)
        assert len(events) == 1
        assert events[0]["drift_type"] == "added"
        assert events[0]["resource_id"] == "res1"

    @pytest.mark.asyncio
    async def test_modified_resource(self, scanner):
        baseline = {"res1": {"resource_type": "T", "properties": {"sku": "A"}}}
        current = {"res1": {"resource_type": "T", "properties": {"sku": "B"}}}
        events = await scanner.compare_resources(baseline, current)
        assert len(events) == 1
        assert events[0]["drift_type"] == "modified"
        assert "changes" in events[0]
        assert len(events[0]["changes"]) >= 1

    @pytest.mark.asyncio
    async def test_unchanged_resources_produce_no_events(self, scanner):
        res = {"res1": {"resource_type": "T", "x": 1}, "res2": {"resource_type": "T", "x": 2}}
        events = await scanner.compare_resources(res, dict(res))
        assert events == []

    @pytest.mark.asyncio
    async def test_mixed_drift(self, scanner):
        """Simultaneous added, removed, and modified resources."""
        baseline = {
            "keep": {"resource_type": "T", "val": "old"},
            "remove": {"resource_type": "T"},
        }
        current = {
            "keep": {"resource_type": "T", "val": "new"},
            "add": {"resource_type": "T"},
        }
        events = await scanner.compare_resources(baseline, current)
        types = {e["drift_type"] for e in events}
        assert types == {"added", "removed", "modified"}

    @pytest.mark.asyncio
    async def test_empty_baseline_and_current(self, scanner):
        events = await scanner.compare_resources({}, {})
        assert events == []


# ── Unit tests: mock data ────────────────────────────────────────────────────


class TestMockData:
    """Tests for mock baseline and current state generators."""

    def test_mock_baseline_has_10_resources(self):
        baseline = _mock_baseline_resources()
        assert len(baseline) == 10

    def test_mock_baseline_keys_are_azure_resource_ids(self):
        baseline = _mock_baseline_resources()
        for key in baseline:
            assert key.startswith("/subscriptions/")
            assert "/providers/" in key

    def test_mock_baseline_resources_have_type(self):
        baseline = _mock_baseline_resources()
        for resource in baseline.values():
            assert "resource_type" in resource

    def test_mock_current_state_has_drift(self):
        baseline = _mock_baseline_resources()
        current = _mock_current_state()

        baseline_ids = set(baseline.keys())
        current_ids = set(current.keys())

        removed = baseline_ids - current_ids
        added = current_ids - baseline_ids

        assert len(removed) == 1, "Expected exactly 1 removed resource"
        assert len(added) == 1, "Expected exactly 1 added resource"

    def test_mock_current_state_has_modifications(self):
        baseline = _mock_baseline_resources()
        current = _mock_current_state()

        modified_count = 0
        for rid in set(baseline.keys()) & set(current.keys()):
            if baseline[rid] != current[rid]:
                modified_count += 1

        assert modified_count == 2, "Expected exactly 2 modified resources"


# ── Unit tests: severity summary ─────────────────────────────────────────────


class TestSeveritySummary:
    """Tests for the severity summary helper."""

    def test_empty_events(self):
        result = _severity_summary([])
        assert result == {"critical": 0, "high": 0, "medium": 0, "low": 0}

    def test_counts_by_severity(self):
        events = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "low"},
            {"severity": "critical"},
        ]
        result = _severity_summary(events)
        assert result == {"critical": 1, "high": 2, "medium": 0, "low": 1}


# ── Integration test: mock scan flow ─────────────────────────────────────────


class TestMockScanFlow:
    """Tests for the full scan flow in dev/mock mode."""

    @pytest.fixture
    def scanner(self):
        return DriftScanner()

    @pytest.mark.asyncio
    async def test_mock_scan_produces_events(self, scanner):
        """Dev mode scan finds expected drift in mock data."""
        with patch("app.services.drift_scanner.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await scanner.scan_project(PROJECT_ID)

        assert result["status"] == "completed"
        assert result["project_id"] == PROJECT_ID
        assert result["total_resources_scanned"] > 0
        assert result["id"]  # scan_id is set

        # Mock data should produce: 1 removed, 1 added, 2 modified
        assert result["removed_count"] == 1
        assert result["new_count"] == 1
        assert result["drifted_count"] == 2

        # Events list should be populated
        events = result["events"]
        assert len(events) == 4  # 1 removed + 1 added + 2 modified
        event_types = {e["drift_type"] for e in events}
        assert "removed" in event_types
        assert "added" in event_types
        assert "modified" in event_types

    @pytest.mark.asyncio
    async def test_scan_result_has_all_fields(self, scanner):
        with patch("app.services.drift_scanner.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await scanner.scan_project(PROJECT_ID, tenant_id="t-1")

        assert result["baseline_id"]
        assert result["tenant_id"] == "t-1"
        assert result["scan_started_at"] is not None
        assert result["scan_completed_at"] is not None
        assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_scan_publishes_sse_event(self, scanner):
        """Verify that drift_detected SSE event is published."""
        with (
            patch("app.services.drift_scanner.settings") as mock_settings,
            patch("app.services.drift_scanner.event_stream") as mock_es,
        ):
            mock_settings.is_dev_mode = True
            mock_es.publish = AsyncMock(return_value=0)

            await scanner.scan_project(PROJECT_ID)

            mock_es.publish.assert_called_once()
            call_args = mock_es.publish.call_args
            assert call_args[0][0] == "drift_detected"
            event_data = call_args[0][1]
            assert "scan_id" in event_data
            assert "total_drift_events" in event_data
            assert event_data["project_id"] == PROJECT_ID

    @pytest.mark.asyncio
    async def test_scan_no_drift_no_sse(self, scanner):
        """No SSE event when there is no drift."""
        with (
            patch("app.services.drift_scanner.settings") as mock_settings,
            patch("app.services.drift_scanner.event_stream") as mock_es,
            patch.object(
                scanner, "get_current_state", new_callable=AsyncMock
            ) as mock_state,
            patch.object(
                scanner,
                "_get_active_baseline",
                new_callable=AsyncMock,
            ) as mock_baseline,
        ):
            mock_settings.is_dev_mode = True
            mock_es.publish = AsyncMock(return_value=0)
            # Both return the same data → no drift
            resources = {"r1": {"resource_type": "T", "val": 1}}
            mock_baseline.return_value = ("b-1", resources)
            mock_state.return_value = resources

            await scanner.scan_project(PROJECT_ID)

            mock_es.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_scan_handles_error(self, scanner):
        """Scan catches exceptions and marks result as failed."""
        with (
            patch("app.services.drift_scanner.settings") as mock_settings,
            patch.object(
                scanner, "get_current_state", side_effect=RuntimeError("boom")
            ),
        ):
            mock_settings.is_dev_mode = True
            result = await scanner.scan_project(PROJECT_ID)

        assert result["status"] == "failed"
        assert "boom" in result["error_message"]


# ── Integration test: severity in mock scan ──────────────────────────────────


class TestMockScanSeverity:
    """Verify severity levels are correctly assigned in mock scan."""

    @pytest.mark.asyncio
    async def test_mock_scan_security_severity(self):
        """NSG change should be critical, tag change should be low."""
        scanner = DriftScanner()
        with patch("app.services.drift_scanner.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await scanner.scan_project(PROJECT_ID)

        events = result["events"]
        severities = {e["severity"] for e in events}

        # NSG securityRules change → critical
        assert "critical" in severities
        # Tag-only change → low
        assert "low" in severities


# ── Unit tests: get_current_state ────────────────────────────────────────────


class TestGetCurrentState:
    """Tests for the get_current_state method."""

    @pytest.mark.asyncio
    async def test_dev_mode_returns_mock(self):
        scanner = DriftScanner()
        with patch("app.services.drift_scanner.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await scanner.get_current_state(PROJECT_ID)
        assert len(result) > 0
        for key in result:
            assert key.startswith("/subscriptions/")

    @pytest.mark.asyncio
    async def test_prod_mode_returns_empty(self):
        scanner = DriftScanner()
        with patch("app.services.drift_scanner.settings") as mock_settings:
            mock_settings.is_dev_mode = False
            result = await scanner.get_current_state(PROJECT_ID)
        assert result == {}


# ── Unit tests: periodic task registration ───────────────────────────────────


class TestPeriodicRegistration:
    """Tests for task scheduler integration."""

    def test_drift_scan_registered(self):
        from app.services.task_scheduler import task_scheduler

        assert "drift_scan" in task_scheduler.registered_tasks

    def test_drift_scan_interval(self):
        from app.services.task_scheduler import task_scheduler

        task = task_scheduler.registered_tasks["drift_scan"]
        assert task.interval_seconds == 3600


# ── Unit tests: periodic task function ───────────────────────────────────────


class TestPeriodicTaskFunction:
    """Tests for the run_periodic_drift_scan function."""

    @pytest.mark.asyncio
    async def test_skips_without_project_id(self):
        from app.services.drift_scanner import run_periodic_drift_scan

        result = await run_periodic_drift_scan(tenant_id=None, project_id=None)
        assert result["message"] == "skipped"

    @pytest.mark.asyncio
    async def test_runs_with_project_id(self):
        from app.services.drift_scanner import run_periodic_drift_scan

        with patch("app.services.drift_scanner.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await run_periodic_drift_scan(
                tenant_id=None, project_id=PROJECT_ID
            )
        assert result["message"] == "completed"
        assert result["scan_id"]
        assert result["status"] == "completed"


# ── Module-level constants tests ─────────────────────────────────────────────


class TestConstants:
    """Tests for module-level constants."""

    def test_ignored_properties_contains_etag(self):
        assert "etag" in IGNORED_PROPERTIES

    def test_ignored_properties_contains_provisioning_state(self):
        assert "provisioningState" in IGNORED_PROPERTIES

    def test_security_resource_types_contains_nsg(self):
        assert "Microsoft.Network/networkSecurityGroups" in SECURITY_RESOURCE_TYPES

    def test_security_property_keywords_contains_encryption(self):
        assert "encryption" in SECURITY_PROPERTY_KEYWORDS

    def test_singleton_exists(self):
        assert drift_scanner is not None
        assert isinstance(drift_scanner, DriftScanner)


# ── API route test: scan trigger ─────────────────────────────────────────────


class TestScanTriggerRoute:
    """Tests for POST /api/governance/drift/scan/{project_id}."""

    def test_trigger_scan_returns_202(self):
        r = client.post(f"/api/governance/drift/scan/{PROJECT_ID}")
        assert r.status_code == 202
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["status"] == "running"
        assert "id" in data
        assert "baseline_id" in data
        assert "scan_started_at" in data
        assert data["total_resources_scanned"] == 0
        assert data["drifted_count"] == 0
        assert data["new_count"] == 0
        assert data["removed_count"] == 0
        assert data["events"] == []

    def test_trigger_scan_with_tenant_id(self):
        r = client.post(
            f"/api/governance/drift/scan/{PROJECT_ID}",
            params={"tenant_id": "t-123"},
        )
        assert r.status_code == 202
        data = r.json()
        assert data["tenant_id"] == "t-123"

    def test_trigger_scan_response_shape(self):
        """Verify the response matches DriftScanResultResponse schema."""
        r = client.post(f"/api/governance/drift/scan/{PROJECT_ID}")
        data = r.json()
        expected_keys = {
            "id",
            "baseline_id",
            "project_id",
            "tenant_id",
            "scan_started_at",
            "scan_completed_at",
            "total_resources_scanned",
            "drifted_count",
            "new_count",
            "removed_count",
            "status",
            "error_message",
            "events",
        }
        assert set(data.keys()) == expected_keys
