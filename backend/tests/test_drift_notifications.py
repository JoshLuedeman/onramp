"""Tests for drift notification system.

Covers:
- DriftNotificationRule model import and table registration
- Drift notification schemas (CRUD, enums, severity order)
- DriftNotificationService (severity threshold, content formatting, processing)
- Route-level tests (CRUD, trigger, history)
- Integration with existing notification service
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app

client = TestClient(app)


# ===================================================================
# Model import tests
# ===================================================================


class TestDriftNotificationRuleModel:
    def test_model_importable(self):
        from app.models.drift_notification_rule import DriftNotificationRule

        assert DriftNotificationRule.__tablename__ == "drift_notification_rules"

    def test_model_registered_in_init(self):
        from app.models import DriftNotificationRule

        assert DriftNotificationRule.__tablename__ == "drift_notification_rules"

    def test_model_in_metadata(self):
        from app.models import Base

        table_names = set(Base.metadata.tables.keys())
        assert "drift_notification_rules" in table_names

    def test_model_has_expected_columns(self):
        from app.models.drift_notification_rule import DriftNotificationRule

        mapper = DriftNotificationRule.__mapper__
        column_names = {c.key for c in mapper.columns}
        expected = {
            "id", "project_id", "tenant_id", "severity_threshold",
            "channels", "recipients", "enabled", "created_at", "updated_at",
        }
        assert expected.issubset(column_names)

    def test_model_default_values(self):
        from app.models.drift_notification_rule import DriftNotificationRule

        rule = DriftNotificationRule(
            project_id="proj-1",
        )
        assert rule.project_id == "proj-1"
        # default=True is applied at DB insert time; verify column default exists
        col = DriftNotificationRule.__table__.columns["enabled"]
        assert col.default.arg is True

    def test_model_id_generation(self):
        from app.models.drift_notification_rule import DriftNotificationRule

        rule = DriftNotificationRule(project_id="proj-1")
        # default=generate_uuid is set in the column definition
        col = DriftNotificationRule.__table__.columns["id"]
        assert col.default is not None


# ===================================================================
# Schema tests
# ===================================================================


class TestSeverityThresholdEnum:
    def test_all_values(self):
        from app.schemas.drift_notification import SeverityThreshold

        assert SeverityThreshold.CRITICAL == "critical"
        assert SeverityThreshold.HIGH == "high"
        assert SeverityThreshold.MEDIUM == "medium"
        assert SeverityThreshold.LOW == "low"
        assert SeverityThreshold.ALL == "all"

    def test_severity_order_ranking(self):
        from app.schemas.drift_notification import SEVERITY_ORDER

        assert SEVERITY_ORDER["critical"] > SEVERITY_ORDER["high"]
        assert SEVERITY_ORDER["high"] > SEVERITY_ORDER["medium"]
        assert SEVERITY_ORDER["medium"] > SEVERITY_ORDER["low"]
        assert SEVERITY_ORDER["low"] > SEVERITY_ORDER["all"]


class TestRuleCreateSchema:
    def test_minimal_create(self):
        from app.schemas.drift_notification import DriftNotificationRuleCreate

        rule = DriftNotificationRuleCreate(project_id="proj-1")
        assert rule.project_id == "proj-1"
        assert rule.severity_threshold.value == "high"
        assert rule.channels == ["in_app"]
        assert rule.recipients == []
        assert rule.enabled is True

    def test_full_create(self):
        from app.schemas.drift_notification import DriftNotificationRuleCreate

        rule = DriftNotificationRuleCreate(
            project_id="proj-1",
            tenant_id="tenant-1",
            severity_threshold="critical",
            channels=["email", "webhook"],
            recipients=["admin@example.com", "https://hooks.example.com/drift"],
            enabled=False,
        )
        assert rule.severity_threshold.value == "critical"
        assert len(rule.channels) == 2
        assert len(rule.recipients) == 2
        assert rule.enabled is False

    def test_invalid_severity_rejected(self):
        from pydantic import ValidationError

        from app.schemas.drift_notification import DriftNotificationRuleCreate

        with pytest.raises(ValidationError):
            DriftNotificationRuleCreate(
                project_id="proj-1",
                severity_threshold="invalid",
            )


class TestRuleUpdateSchema:
    def test_all_optional(self):
        from app.schemas.drift_notification import DriftNotificationRuleUpdate

        update = DriftNotificationRuleUpdate()
        assert update.severity_threshold is None
        assert update.channels is None
        assert update.recipients is None
        assert update.enabled is None

    def test_partial_update(self):
        from app.schemas.drift_notification import DriftNotificationRuleUpdate

        update = DriftNotificationRuleUpdate(enabled=False)
        data = update.model_dump(exclude_unset=True)
        assert data == {"enabled": False}

    def test_severity_threshold_update(self):
        from app.schemas.drift_notification import DriftNotificationRuleUpdate

        update = DriftNotificationRuleUpdate(severity_threshold="critical")
        assert update.severity_threshold.value == "critical"


class TestRuleResponseSchema:
    def test_from_dict(self):
        from app.schemas.drift_notification import DriftNotificationRuleResponse

        now = datetime.now(timezone.utc)
        resp = DriftNotificationRuleResponse(
            id="rule-1",
            project_id="proj-1",
            severity_threshold="high",
            channels=["in_app"],
            recipients=[],
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        assert resp.id == "rule-1"
        assert resp.severity_threshold == "high"

    def test_from_attributes_config(self):
        from app.schemas.drift_notification import DriftNotificationRuleResponse

        assert DriftNotificationRuleResponse.model_config.get("from_attributes") is True


class TestNotificationSummarySchema:
    def test_defaults(self):
        from app.schemas.drift_notification import DriftNotificationSummary

        summary = DriftNotificationSummary(scan_id="scan-1")
        assert summary.total_findings == 0
        assert summary.notified_findings == 0
        assert summary.rules_evaluated == 0
        assert summary.notifications_sent == 0
        assert summary.by_channel == {}
        assert summary.by_severity == {}
        assert summary.errors == []

    def test_populated_summary(self):
        from app.schemas.drift_notification import DriftNotificationSummary

        summary = DriftNotificationSummary(
            scan_id="scan-1",
            total_findings=5,
            notified_findings=3,
            rules_evaluated=2,
            notifications_sent=4,
            by_channel={"in_app": 2, "email": 2},
            by_severity={"critical": 1, "high": 2},
        )
        assert summary.notifications_sent == 4
        assert summary.by_channel["email"] == 2


# ===================================================================
# Service — severity threshold tests
# ===================================================================


class TestSeverityThresholdCheck:
    def setup_method(self):
        from app.services.drift_notification import DriftNotificationService

        self.service = DriftNotificationService()

    def test_critical_meets_critical_threshold(self):
        assert self.service.check_severity_threshold("critical", "critical") is True

    def test_high_does_not_meet_critical_threshold(self):
        assert self.service.check_severity_threshold("high", "critical") is False

    def test_critical_meets_high_threshold(self):
        assert self.service.check_severity_threshold("critical", "high") is True

    def test_high_meets_high_threshold(self):
        assert self.service.check_severity_threshold("high", "high") is True

    def test_medium_does_not_meet_high_threshold(self):
        assert self.service.check_severity_threshold("medium", "high") is False

    def test_low_meets_all_threshold(self):
        assert self.service.check_severity_threshold("low", "all") is True

    def test_critical_meets_all_threshold(self):
        assert self.service.check_severity_threshold("critical", "all") is True

    def test_medium_meets_medium_threshold(self):
        assert self.service.check_severity_threshold("medium", "medium") is True

    def test_low_meets_low_threshold(self):
        assert self.service.check_severity_threshold("low", "low") is True

    def test_case_insensitive(self):
        assert self.service.check_severity_threshold("CRITICAL", "HIGH") is True

    def test_unknown_severity_treated_as_zero(self):
        assert self.service.check_severity_threshold("unknown", "low") is False


# ===================================================================
# Service — content formatting tests
# ===================================================================


class TestContentFormatting:
    def setup_method(self):
        from app.services.drift_notification import DriftNotificationService

        self.service = DriftNotificationService()

    def test_basic_format_with_findings(self):
        scan = {"id": "scan-1", "project_id": "proj-1"}
        findings = [
            {"resource_type": "NSG", "resource_id": "nsg-1", "drift_type": "modified", "severity": "critical"},
            {"resource_type": "VM", "resource_id": "vm-1", "drift_type": "added", "severity": "medium"},
        ]
        result = self.service.format_notification_content(scan, findings)
        assert "2 drift findings detected" in result["title"]
        assert "proj-1" in result["title"]
        assert "1 Critical" in result["message"]
        assert "1 Medium" in result["message"]

    def test_single_finding_no_plural(self):
        scan = {"id": "scan-1", "project_id": "proj-1"}
        findings = [
            {"resource_type": "NSG", "resource_id": "nsg-1", "drift_type": "modified", "severity": "high"},
        ]
        result = self.service.format_notification_content(scan, findings)
        assert "1 drift finding detected" in result["title"]
        assert "findings" not in result["title"]

    def test_project_name_override(self):
        scan = {"id": "scan-1", "project_id": "proj-1"}
        findings = [
            {"resource_type": "VM", "resource_id": "vm-1", "drift_type": "added", "severity": "low"},
        ]
        result = self.service.format_notification_content(
            scan, findings, project_name="Production West"
        )
        assert "Production West" in result["title"]

    def test_top_findings_limited_to_5(self):
        scan = {"id": "scan-1", "project_id": "proj-1"}
        findings = [
            {"resource_type": f"Res-{i}", "resource_id": f"id-{i}", "drift_type": "modified", "severity": "medium"}
            for i in range(10)
        ]
        result = self.service.format_notification_content(scan, findings)
        assert "and 5 more" in result["message"]

    def test_link_to_drift_page_included(self):
        scan = {"id": "scan-123", "project_id": "proj-1"}
        findings = [
            {"resource_type": "VM", "resource_id": "vm-1", "drift_type": "added", "severity": "low"},
        ]
        result = self.service.format_notification_content(scan, findings)
        assert "/governance/drift/scan-results/scan-123" in result["message"]

    def test_empty_findings_still_formats(self):
        scan = {"id": "scan-1", "project_id": "proj-1"}
        result = self.service.format_notification_content(scan, [])
        assert "0 drift findings" in result["title"]

    def test_severity_breakdown_order(self):
        scan = {"id": "scan-1", "project_id": "proj-1"}
        findings = [
            {"resource_type": "A", "resource_id": "a", "drift_type": "modified", "severity": "low"},
            {"resource_type": "B", "resource_id": "b", "drift_type": "modified", "severity": "critical"},
            {"resource_type": "C", "resource_id": "c", "drift_type": "modified", "severity": "high"},
        ]
        result = self.service.format_notification_content(scan, findings)
        message = result["message"]
        # Critical should appear before High, High before Low
        crit_idx = message.index("Critical")
        high_idx = message.index("High")
        low_idx = message.index("Low")
        assert crit_idx < high_idx < low_idx

    def test_finding_bullet_format(self):
        scan = {"id": "scan-1", "project_id": "proj-1"}
        findings = [
            {"resource_type": "NSG", "resource_id": "nsg-prod", "drift_type": "modified", "severity": "high"},
        ]
        result = self.service.format_notification_content(scan, findings)
        assert "[HIGH]" in result["message"]
        assert "NSG" in result["message"]
        assert "nsg-prod" in result["message"]


# ===================================================================
# Service — process_scan_results tests
# ===================================================================


class TestProcessScanResults:
    @pytest.mark.asyncio
    async def test_no_findings_returns_empty_summary(self):
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()
        result = await service.process_scan_results(
            db=None,
            scan_result={"id": "scan-1", "project_id": "proj-1"},
            findings=[],
        )
        assert result["total_findings"] == 0
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_no_rules_returns_zero_sent(self):
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()
        # db=None means _load_rules returns []
        result = await service.process_scan_results(
            db=None,
            scan_result={"id": "scan-1", "project_id": "proj-1"},
            findings=[
                {"resource_type": "NSG", "resource_id": "nsg-1", "drift_type": "modified", "severity": "critical"},
            ],
        )
        assert result["total_findings"] == 1
        assert result["rules_evaluated"] == 0
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_process_with_matching_rules(self):
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()

        mock_rules = [
            {
                "id": "rule-1",
                "project_id": "proj-1",
                "tenant_id": None,
                "severity_threshold": "high",
                "channels": ["in_app"],
                "recipients": [],
                "enabled": True,
            }
        ]

        with patch.object(service, "_load_rules", new_callable=AsyncMock, return_value=mock_rules):
            with patch.object(service, "_send_via_channel", new_callable=AsyncMock):
                result = await service.process_scan_results(
                    db=MagicMock(),
                    scan_result={"id": "scan-1", "project_id": "proj-1", "tenant_id": None},
                    findings=[
                        {"resource_type": "NSG", "resource_id": "nsg-1", "drift_type": "modified", "severity": "critical"},
                        {"resource_type": "VM", "resource_id": "vm-1", "drift_type": "added", "severity": "low"},
                    ],
                )
        assert result["total_findings"] == 2
        assert result["notified_findings"] == 1  # Only critical meets "high" threshold
        assert result["notifications_sent"] == 1
        assert result["by_channel"]["in_app"] == 1

    @pytest.mark.asyncio
    async def test_disabled_rule_skipped(self):
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()

        mock_rules = [
            {
                "id": "rule-1", "project_id": "proj-1", "tenant_id": None,
                "severity_threshold": "all", "channels": ["in_app"],
                "recipients": [], "enabled": False,
            }
        ]

        with patch.object(service, "_load_rules", new_callable=AsyncMock, return_value=mock_rules):
            result = await service.process_scan_results(
                db=MagicMock(),
                scan_result={"id": "scan-1", "project_id": "proj-1"},
                findings=[
                    {"resource_type": "VM", "resource_id": "vm-1", "drift_type": "added", "severity": "critical"},
                ],
            )
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_multiple_channels_per_rule(self):
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()

        mock_rules = [
            {
                "id": "rule-1", "project_id": "proj-1", "tenant_id": None,
                "severity_threshold": "all", "channels": ["in_app", "email", "webhook"],
                "recipients": ["admin@test.com"], "enabled": True,
            }
        ]

        with patch.object(service, "_load_rules", new_callable=AsyncMock, return_value=mock_rules):
            with patch.object(service, "_send_via_channel", new_callable=AsyncMock):
                result = await service.process_scan_results(
                    db=MagicMock(),
                    scan_result={"id": "scan-1", "project_id": "proj-1"},
                    findings=[
                        {"resource_type": "VM", "resource_id": "vm-1", "drift_type": "added", "severity": "medium"},
                    ],
                )
        assert result["notifications_sent"] == 3
        assert result["by_channel"]["in_app"] == 1
        assert result["by_channel"]["email"] == 1
        assert result["by_channel"]["webhook"] == 1

    @pytest.mark.asyncio
    async def test_send_failure_recorded_in_errors(self):
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()

        mock_rules = [
            {
                "id": "rule-1", "project_id": "proj-1", "tenant_id": None,
                "severity_threshold": "all", "channels": ["webhook"],
                "recipients": [], "enabled": True,
            }
        ]

        with patch.object(service, "_load_rules", new_callable=AsyncMock, return_value=mock_rules):
            with patch.object(
                service, "_send_via_channel",
                new_callable=AsyncMock,
                side_effect=Exception("webhook down"),
            ):
                result = await service.process_scan_results(
                    db=MagicMock(),
                    scan_result={"id": "scan-1", "project_id": "proj-1"},
                    findings=[
                        {"resource_type": "VM", "resource_id": "vm-1", "drift_type": "added", "severity": "medium"},
                    ],
                )
        assert result["notifications_sent"] == 0
        assert len(result["errors"]) == 1
        assert "webhook" in result["errors"][0].lower()

    @pytest.mark.asyncio
    async def test_threshold_filters_findings_correctly(self):
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()

        mock_rules = [
            {
                "id": "rule-1", "project_id": "proj-1", "tenant_id": None,
                "severity_threshold": "critical",
                "channels": ["in_app"],
                "recipients": [], "enabled": True,
            }
        ]

        with patch.object(service, "_load_rules", new_callable=AsyncMock, return_value=mock_rules):
            with patch.object(service, "_send_via_channel", new_callable=AsyncMock):
                result = await service.process_scan_results(
                    db=MagicMock(),
                    scan_result={"id": "scan-1", "project_id": "proj-1"},
                    findings=[
                        {"resource_type": "A", "resource_id": "a", "drift_type": "modified", "severity": "high"},
                        {"resource_type": "B", "resource_id": "b", "drift_type": "modified", "severity": "medium"},
                        {"resource_type": "C", "resource_id": "c", "drift_type": "modified", "severity": "low"},
                    ],
                )
        # None meet "critical" threshold
        assert result["notifications_sent"] == 0


# ===================================================================
# Service — _send_via_channel integration
# ===================================================================


class TestSendViaChannel:
    @pytest.mark.asyncio
    async def test_send_via_channel_calls_notification_service(self):
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()
        mock_db = MagicMock()

        with patch("app.services.notification_service.notification_service") as mock_ns:
            mock_ns.send = AsyncMock(return_value=[{"status": "delivered"}])
            with patch("app.services.drift_notification.settings") as mock_settings:
                mock_settings.is_dev_mode = False

                await service._send_via_channel(
                    db=mock_db,
                    channel="in_app",
                    content={"title": "Drift Alert", "message": "3 critical findings"},
                    scan_result={"id": "scan-1", "project_id": "proj-1", "tenant_id": "t-1"},
                    recipients=[],
                    rule={"tenant_id": "t-1"},
                )

            mock_ns.send.assert_awaited_once()
            call_kwargs = mock_ns.send.call_args
            assert call_kwargs[1]["notification_type"] == "drift_detected"
            assert call_kwargs[1]["channel"] == "in_app"

    @pytest.mark.asyncio
    async def test_dev_mode_no_db_logs_only(self):
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()

        with patch("app.services.drift_notification.settings") as mock_settings:
            mock_settings.is_dev_mode = True

            # Should not raise, just log
            await service._send_via_channel(
                db=None,
                channel="in_app",
                content={"title": "Test", "message": "Test message"},
                scan_result={"id": "s-1", "project_id": "p-1"},
                recipients=[],
                rule={},
            )


# ===================================================================
# Route tests — sync TestClient (no DB)
# ===================================================================


class TestCreateRuleRoute:
    def test_create_rule_no_db(self):
        resp = client.post(
            "/api/governance/drift/notification-rules",
            json={
                "project_id": "proj-1",
                "severity_threshold": "high",
                "channels": ["in_app"],
                "recipients": [],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["project_id"] == "proj-1"
        assert data["severity_threshold"] == "high"
        assert data["enabled"] is True
        assert "id" in data

    def test_create_rule_with_all_fields(self):
        resp = client.post(
            "/api/governance/drift/notification-rules",
            json={
                "project_id": "proj-2",
                "tenant_id": "tenant-1",
                "severity_threshold": "critical",
                "channels": ["email", "webhook"],
                "recipients": ["admin@example.com"],
                "enabled": False,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["severity_threshold"] == "critical"
        assert data["enabled"] is False
        assert len(data["channels"]) == 2

    def test_create_rule_invalid_severity(self):
        resp = client.post(
            "/api/governance/drift/notification-rules",
            json={
                "project_id": "proj-1",
                "severity_threshold": "not_a_level",
            },
        )
        assert resp.status_code == 422


class TestListRulesRoute:
    def test_list_rules_no_db(self):
        resp = client.get("/api/governance/drift/notification-rules")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_rules_with_project_filter(self):
        resp = client.get(
            "/api/governance/drift/notification-rules",
            params={"project_id": "proj-1"},
        )
        assert resp.status_code == 200


class TestGetRuleRoute:
    def test_get_rule_no_db_returns_404(self):
        resp = client.get("/api/governance/drift/notification-rules/nonexistent")
        assert resp.status_code == 404

    def test_get_rule_error_message(self):
        resp = client.get("/api/governance/drift/notification-rules/fake-id")
        assert "not configured" in resp.json()["detail"].lower() or "not found" in resp.json()["detail"].lower()


class TestUpdateRuleRoute:
    def test_update_rule_no_db_returns_404(self):
        resp = client.put(
            "/api/governance/drift/notification-rules/nonexistent",
            json={"enabled": False},
        )
        assert resp.status_code == 404


class TestDeleteRuleRoute:
    def test_delete_rule_no_db_returns_404(self):
        resp = client.delete("/api/governance/drift/notification-rules/nonexistent")
        assert resp.status_code == 404


class TestTriggerNotifyRoute:
    def test_trigger_notify_no_db(self):
        resp = client.post("/api/governance/drift/notify/scan-123")
        # With no DB, _load_scan_data returns stub with no findings
        assert resp.status_code == 200
        data = resp.json()
        assert data["scan_id"] == "scan-123"
        assert data["total_findings"] == 0


class TestNotificationHistoryRoute:
    def test_history_no_db(self):
        resp = client.get("/api/governance/drift/notification-history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_with_project_filter(self):
        resp = client.get(
            "/api/governance/drift/notification-history",
            params={"project_id": "proj-1"},
        )
        assert resp.status_code == 200

    def test_history_with_limit(self):
        resp = client.get(
            "/api/governance/drift/notification-history",
            params={"limit": 10},
        )
        assert resp.status_code == 200


# ===================================================================
# Async route tests
# ===================================================================


class TestAsyncRoutes:
    @pytest.mark.asyncio
    async def test_create_rule_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/governance/drift/notification-rules",
                json={
                    "project_id": "proj-async",
                    "severity_threshold": "medium",
                    "channels": ["in_app"],
                    "recipients": [],
                },
            )
        assert resp.status_code == 201
        assert resp.json()["project_id"] == "proj-async"

    @pytest.mark.asyncio
    async def test_list_rules_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/governance/drift/notification-rules")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_trigger_notify_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/governance/drift/notify/scan-async")
        assert resp.status_code == 200
        assert resp.json()["scan_id"] == "scan-async"

    @pytest.mark.asyncio
    async def test_notification_history_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/governance/drift/notification-history")
        assert resp.status_code == 200


# ===================================================================
# Singleton tests
# ===================================================================


class TestSingleton:
    def test_drift_notification_service_singleton_exists(self):
        from app.services.drift_notification import drift_notification_service

        assert drift_notification_service is not None

    def test_singleton_is_same_instance(self):
        from app.services.drift_notification import (
            DriftNotificationService,
            drift_notification_service,
        )

        assert isinstance(drift_notification_service, DriftNotificationService)


# ===================================================================
# Migration file tests
# ===================================================================


class TestMigration:
    def test_migration_file_importable(self):
        import importlib

        m = importlib.import_module(
            "app.db.migrations.versions.016_add_drift_notification_rules"
        )
        assert m.revision == "016"
        assert m.down_revision == "013"

    def test_migration_has_upgrade_and_downgrade(self):
        import importlib

        m = importlib.import_module(
            "app.db.migrations.versions.016_add_drift_notification_rules"
        )
        assert callable(m.upgrade)
        assert callable(m.downgrade)


# ===================================================================
# Integration — DriftNotificationService + NotificationService
# ===================================================================


class TestIntegrationWithNotificationService:
    @pytest.mark.asyncio
    async def test_end_to_end_notification_dispatch(self):
        """Verify that process_scan_results calls notification_service.send."""
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()

        mock_rules = [
            {
                "id": "rule-1", "project_id": "proj-1", "tenant_id": "t-1",
                "severity_threshold": "all", "channels": ["in_app"],
                "recipients": [], "enabled": True,
            }
        ]

        mock_db = MagicMock()

        with patch.object(service, "_load_rules", new_callable=AsyncMock, return_value=mock_rules):
            with patch("app.services.notification_service.notification_service") as mock_ns:
                mock_ns.send = AsyncMock(return_value=[{"status": "delivered"}])
                with patch("app.services.drift_notification.settings") as mock_settings:
                    mock_settings.is_dev_mode = False

                    result = await service.process_scan_results(
                        db=mock_db,
                        scan_result={"id": "scan-1", "project_id": "proj-1", "tenant_id": "t-1"},
                        findings=[
                            {"resource_type": "NSG", "resource_id": "nsg-1", "drift_type": "modified", "severity": "high"},
                        ],
                    )

                mock_ns.send.assert_awaited_once()
                assert result["notifications_sent"] == 1

    @pytest.mark.asyncio
    async def test_severity_extracted_from_content(self):
        """Verify severity is extracted from the message content."""
        from app.services.drift_notification import DriftNotificationService

        service = DriftNotificationService()

        mock_rules = [
            {
                "id": "rule-1", "project_id": "proj-1", "tenant_id": None,
                "severity_threshold": "all", "channels": ["in_app"],
                "recipients": [], "enabled": True,
            }
        ]

        mock_db = MagicMock()

        with patch.object(service, "_load_rules", new_callable=AsyncMock, return_value=mock_rules):
            with patch("app.services.notification_service.notification_service") as mock_ns:
                mock_ns.send = AsyncMock(return_value=[{"status": "delivered"}])
                with patch("app.services.drift_notification.settings") as mock_settings:
                    mock_settings.is_dev_mode = False

                    await service.process_scan_results(
                        db=mock_db,
                        scan_result={"id": "scan-1", "project_id": "proj-1"},
                        findings=[
                            {"resource_type": "FW", "resource_id": "fw-1", "drift_type": "modified", "severity": "critical"},
                        ],
                    )

                call_kwargs = mock_ns.send.call_args[1]
                assert call_kwargs["severity"] == "critical"
