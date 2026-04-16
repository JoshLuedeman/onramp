"""Tests for cost management — models, schemas, service, and API routes."""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.cost_manager import CostManager

client = TestClient(app)

PROJECT_ID = "proj-test-cost"
SUBSCRIPTION_ID = "sub-12345-test"


# ── Model import & structure tests ───────────────────────────────────────────


class TestCostModelsImportable:
    """Verify cost models load and have correct table names."""

    def test_models_importable(self):
        from app.models import CostAnomaly, CostBudget, CostSnapshot

        assert CostSnapshot.__tablename__ == "cost_snapshots"
        assert CostBudget.__tablename__ == "cost_budgets"
        assert CostAnomaly.__tablename__ == "cost_anomalies"

    def test_models_in_metadata(self):
        from app.models import Base

        table_names = set(Base.metadata.tables.keys())
        assert "cost_snapshots" in table_names
        assert "cost_budgets" in table_names
        assert "cost_anomalies" in table_names

    def test_snapshot_has_expected_columns(self):
        from app.models.cost import CostSnapshot

        cols = {c.name for c in CostSnapshot.__table__.columns}
        expected = {
            "id", "project_id", "tenant_id", "subscription_id",
            "period_start", "period_end", "total_cost", "currency",
            "cost_by_service", "cost_by_resource_group", "created_at", "updated_at",
        }
        assert expected.issubset(cols)

    def test_budget_has_expected_columns(self):
        from app.models.cost import CostBudget

        cols = {c.name for c in CostBudget.__table__.columns}
        expected = {
            "id", "project_id", "tenant_id", "budget_name", "budget_amount",
            "current_spend", "currency", "threshold_percentage",
            "alert_enabled", "created_at", "updated_at",
        }
        assert expected.issubset(cols)

    def test_anomaly_has_expected_columns(self):
        from app.models.cost import CostAnomaly

        cols = {c.name for c in CostAnomaly.__table__.columns}
        expected = {
            "id", "project_id", "cost_snapshot_id", "anomaly_type",
            "description", "previous_cost", "current_cost",
            "percentage_change", "severity", "detected_at",
        }
        assert expected.issubset(cols)

    def test_snapshot_indexes(self):
        from app.models.cost import CostSnapshot

        index_names = {idx.name for idx in CostSnapshot.__table__.indexes}
        assert "ix_cost_snapshots_project_created" in index_names

    def test_budget_indexes(self):
        from app.models.cost import CostBudget

        index_names = {idx.name for idx in CostBudget.__table__.indexes}
        assert "ix_cost_budgets_project_created" in index_names

    def test_anomaly_indexes(self):
        from app.models.cost import CostAnomaly

        index_names = {idx.name for idx in CostAnomaly.__table__.indexes}
        assert "ix_cost_anomalies_project_detected" in index_names

    def test_snapshot_anomaly_relationship(self):
        from app.models.cost import CostSnapshot

        rel_names = {r.key for r in CostSnapshot.__mapper__.relationships}
        assert "anomalies" in rel_names

    def test_anomaly_snapshot_relationship(self):
        from app.models.cost import CostAnomaly

        rel_names = {r.key for r in CostAnomaly.__mapper__.relationships}
        assert "snapshot" in rel_names


# ── Schema tests ─────────────────────────────────────────────────────────────


class TestCostSchemasImportable:
    """Verify cost schemas load and validate correctly."""

    def test_enums_importable(self):
        from app.schemas.cost import AnomalySeverity, AnomalyType, CostGranularity

        assert AnomalySeverity.CRITICAL == "critical"
        assert AnomalySeverity.HIGH == "high"
        assert AnomalyType.SPIKE == "spike"
        assert AnomalyType.UNUSUAL_SERVICE == "unusual_service"
        assert AnomalyType.NEW_RESOURCE == "new_resource"
        assert CostGranularity.DAILY == "daily"
        assert CostGranularity.WEEKLY == "weekly"
        assert CostGranularity.MONTHLY == "monthly"

    def test_cost_summary_response(self):
        from app.schemas.cost import CostSummaryResponse

        now = datetime.now(timezone.utc)
        resp = CostSummaryResponse(
            project_id="p1",
            subscription_id="sub-1",
            period_start=now,
            period_end=now,
            total_cost=1234.56,
        )
        assert resp.project_id == "p1"
        assert resp.total_cost == 1234.56
        assert resp.currency == "USD"
        assert resp.cost_by_service == []
        assert resp.cost_by_resource_group == []

    def test_cost_trend_response_defaults(self):
        from app.schemas.cost import CostTrendResponse

        resp = CostTrendResponse(
            project_id="p1",
            subscription_id="sub-1",
            granularity="daily",
            days=30,
        )
        assert resp.data_points == []
        assert resp.total_cost == 0.0
        assert resp.average_daily_cost == 0.0

    def test_budget_create_schema(self):
        from app.schemas.cost import CostBudgetCreate

        budget = CostBudgetCreate(
            project_id="p1",
            budget_name="Monthly Budget",
            budget_amount=5000.0,
        )
        assert budget.project_id == "p1"
        assert budget.budget_name == "Monthly Budget"
        assert budget.budget_amount == 5000.0
        assert budget.currency == "USD"
        assert budget.threshold_percentage == 80.0
        assert budget.alert_enabled is True

    def test_budget_update_schema_optional_fields(self):
        from app.schemas.cost import CostBudgetUpdate

        update = CostBudgetUpdate()
        assert update.budget_name is None
        assert update.budget_amount is None
        assert update.currency is None
        assert update.threshold_percentage is None
        assert update.alert_enabled is None

    def test_budget_status_response(self):
        from app.schemas.cost import BudgetStatusResponse

        resp = BudgetStatusResponse(
            project_id="p1",
            budget_name="Budget",
            budget_amount=10000.0,
            current_spend=6500.0,
            utilization_percentage=65.0,
        )
        assert resp.is_over_threshold is False
        assert resp.is_over_budget is False

    def test_cost_anomaly_response(self):
        from app.schemas.cost import CostAnomalyResponse

        now = datetime.now(timezone.utc)
        resp = CostAnomalyResponse(
            id="a1",
            project_id="p1",
            cost_snapshot_id="s1",
            anomaly_type="spike",
            description="Cost spike detected",
            previous_cost=100.0,
            current_cost=150.0,
            percentage_change=50.0,
            severity="high",
            detected_at=now,
        )
        assert resp.anomaly_type == "spike"
        assert resp.percentage_change == 50.0

    def test_cost_anomaly_list_defaults(self):
        from app.schemas.cost import CostAnomalyList

        resp = CostAnomalyList()
        assert resp.anomalies == []
        assert resp.total == 0

    def test_cost_scan_response(self):
        from app.schemas.cost import CostScanResponse

        resp = CostScanResponse(
            status="completed",
            message="Done",
            project_id="p1",
        )
        assert resp.status == "completed"
        assert resp.scan_id is None


# ── CostManager service tests ───────────────────────────────────────────────


class TestCostManagerMockData:
    """Test the CostManager mock data generation (dev mode)."""

    @pytest.fixture(autouse=True)
    def _manager(self):
        self.manager = CostManager()

    @pytest.mark.asyncio
    async def test_get_cost_summary_returns_expected_fields(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await self.manager.get_cost_summary(
                PROJECT_ID, SUBSCRIPTION_ID
            )

        assert result["project_id"] == PROJECT_ID
        assert result["subscription_id"] == SUBSCRIPTION_ID
        assert "total_cost" in result
        assert result["total_cost"] > 0
        assert result["currency"] == "USD"
        assert "period_start" in result
        assert "period_end" in result

    @pytest.mark.asyncio
    async def test_cost_summary_has_10_services(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await self.manager.get_cost_summary(
                PROJECT_ID, SUBSCRIPTION_ID
            )

        services = result["cost_by_service"]
        assert len(services) == 10
        for svc in services:
            assert "service_name" in svc
            assert "cost" in svc
            assert "percentage" in svc
            assert svc["cost"] > 0

    @pytest.mark.asyncio
    async def test_cost_summary_has_resource_groups(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await self.manager.get_cost_summary(
                PROJECT_ID, SUBSCRIPTION_ID
            )

        rgs = result["cost_by_resource_group"]
        assert len(rgs) > 0
        for rg in rgs:
            assert "resource_group" in rg
            assert "cost" in rg
            assert "percentage" in rg

    @pytest.mark.asyncio
    async def test_get_cost_trend_daily_30_days(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await self.manager.get_cost_trend(
                PROJECT_ID, SUBSCRIPTION_ID, "daily", 30
            )

        assert result["project_id"] == PROJECT_ID
        assert result["granularity"] == "daily"
        assert result["days"] == 30
        assert len(result["data_points"]) == 30
        assert result["total_cost"] > 0
        assert result["average_daily_cost"] > 0

    @pytest.mark.asyncio
    async def test_get_cost_trend_weekly(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await self.manager.get_cost_trend(
                PROJECT_ID, SUBSCRIPTION_ID, "weekly", 28
            )

        assert result["granularity"] == "weekly"
        assert len(result["data_points"]) == 4  # 28 / 7

    @pytest.mark.asyncio
    async def test_get_cost_trend_data_points_structure(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await self.manager.get_cost_trend(
                PROJECT_ID, SUBSCRIPTION_ID, "daily", 7
            )

        for dp in result["data_points"]:
            assert "date" in dp
            assert "cost" in dp
            assert "currency" in dp
            assert dp["cost"] > 0

    @pytest.mark.asyncio
    async def test_get_budget_status_65_pct_utilization(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await self.manager.get_budget_status(
                PROJECT_ID, SUBSCRIPTION_ID
            )

        assert result["project_id"] == PROJECT_ID
        assert result["budget_name"] == "Monthly Cloud Budget"
        assert result["budget_amount"] == 10000.0
        assert result["current_spend"] == 6500.0
        assert result["utilization_percentage"] == 65.0
        assert result["is_over_threshold"] is False
        assert result["is_over_budget"] is False

    @pytest.mark.asyncio
    async def test_check_cost_anomalies_detects_spike(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            # Patch event_stream to avoid real SSE publishing
            with patch(
                "app.services.cost_manager.cost_manager._publish_cost_alert",
                new_callable=AsyncMock,
            ):
                result = await self.manager.check_cost_anomalies(
                    PROJECT_ID, SUBSCRIPTION_ID
                )

        assert result["total"] == 1
        anomaly = result["anomalies"][0]
        assert anomaly["anomaly_type"] == "spike"
        assert anomaly["previous_cost"] == 120.0
        assert anomaly["current_cost"] == 168.0
        # 40% increase > 20% threshold
        assert anomaly["percentage_change"] == 40.0
        assert anomaly["severity"] == "high"
        assert "project_id" in anomaly
        assert "detected_at" in anomaly


class TestCostManagerCaching:
    """Test the in-memory cache with TTL."""

    @pytest.fixture(autouse=True)
    def _manager(self):
        self.manager = CostManager()

    @pytest.mark.asyncio
    async def test_cache_returns_same_result(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result1 = await self.manager.get_cost_summary(
                PROJECT_ID, SUBSCRIPTION_ID
            )
            result2 = await self.manager.get_cost_summary(
                PROJECT_ID, SUBSCRIPTION_ID
            )

        # Cached — should be identical objects
        assert result1 is result2

    @pytest.mark.asyncio
    async def test_cache_different_keys(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result1 = await self.manager.get_cost_summary(
                "proj-a", SUBSCRIPTION_ID
            )
            result2 = await self.manager.get_cost_summary(
                "proj-b", SUBSCRIPTION_ID
            )

        # Different keys — different data
        assert result1["project_id"] == "proj-a"
        assert result2["project_id"] == "proj-b"

    def test_clear_cache(self):
        self.manager._set_cached("test-key", {"data": True})
        assert self.manager._get_cached("test-key") is not None
        self.manager.clear_cache()
        assert self.manager._get_cached("test-key") is None

    def test_cache_ttl_expiry(self):
        """Verify cache entries expire after TTL."""
        # Set with a very short TTL by manipulating the cache entry directly
        self.manager._cache["expired-key"] = (
            time.monotonic() - 1,  # Already expired
            {"data": True},
        )
        assert self.manager._get_cached("expired-key") is None

    def test_cache_key_generation(self):
        key = self.manager._cache_key("summary", "proj-1", "sub-1", "last_30_days")
        assert key == "summary:proj-1:sub-1:last_30_days"


class TestCostManagerSSE:
    """Test SSE event publication on anomaly detection."""

    @pytest.fixture(autouse=True)
    def _manager(self):
        self.manager = CostManager()

    @pytest.mark.asyncio
    async def test_anomaly_publishes_cost_alert(self):
        with patch("app.services.cost_manager.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            with patch(
                "app.services.event_stream.event_stream.publish",
                new_callable=AsyncMock,
            ) as mock_publish:
                await self.manager.check_cost_anomalies(
                    PROJECT_ID, SUBSCRIPTION_ID
                )

                mock_publish.assert_called_once()
                call_args = mock_publish.call_args
                assert call_args[0][0] == "cost_alert"
                assert "anomaly_count" in call_args[0][1]
                assert call_args[1]["project_id"] == PROJECT_ID


class TestCostManagerPeriodicTask:
    """Test periodic task registration."""

    def test_cost_anomaly_check_registered(self):
        from app.services.task_scheduler import task_scheduler

        registered = task_scheduler.registered_tasks
        assert "cost_anomaly_check" in registered


# ── API route tests (no-DB / mock mode) ─────────────────────────────────────


class TestCostSummaryRoutes:
    """Test cost summary endpoint."""

    def test_get_cost_summary(self):
        r = client.get(
            f"/api/governance/cost/summary/{PROJECT_ID}",
            params={"subscription_id": SUBSCRIPTION_ID},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["subscription_id"] == SUBSCRIPTION_ID
        assert "total_cost" in data
        assert "cost_by_service" in data
        assert "cost_by_resource_group" in data
        assert data["currency"] == "USD"

    def test_get_cost_summary_default_subscription(self):
        r = client.get(f"/api/governance/cost/summary/{PROJECT_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["subscription_id"] == "dev-subscription"

    def test_get_cost_summary_with_time_range(self):
        r = client.get(
            f"/api/governance/cost/summary/{PROJECT_ID}",
            params={
                "subscription_id": SUBSCRIPTION_ID,
                "time_range": "last_7_days",
            },
        )
        assert r.status_code == 200


class TestCostTrendRoutes:
    """Test cost trend endpoint."""

    def test_get_cost_trend_daily(self):
        r = client.get(
            f"/api/governance/cost/trend/{PROJECT_ID}",
            params={
                "subscription_id": SUBSCRIPTION_ID,
                "granularity": "daily",
                "days": 30,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["granularity"] == "daily"
        assert data["days"] == 30
        assert "data_points" in data
        assert len(data["data_points"]) == 30
        assert data["total_cost"] > 0
        assert data["average_daily_cost"] > 0

    def test_get_cost_trend_weekly(self):
        r = client.get(
            f"/api/governance/cost/trend/{PROJECT_ID}",
            params={"granularity": "weekly", "days": 14},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["granularity"] == "weekly"
        assert len(data["data_points"]) == 2

    def test_get_cost_trend_default_params(self):
        r = client.get(f"/api/governance/cost/trend/{PROJECT_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["granularity"] == "daily"
        assert data["days"] == 30

    def test_get_cost_trend_data_point_structure(self):
        r = client.get(
            f"/api/governance/cost/trend/{PROJECT_ID}",
            params={"days": 7},
        )
        assert r.status_code == 200
        data = r.json()
        for dp in data["data_points"]:
            assert "date" in dp
            assert "cost" in dp
            assert "currency" in dp


class TestBudgetRoutes:
    """Test budget status and creation endpoints."""

    def test_get_budget_status(self):
        r = client.get(
            f"/api/governance/cost/budget/{PROJECT_ID}",
            params={"subscription_id": SUBSCRIPTION_ID},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert "budget_name" in data
        assert "budget_amount" in data
        assert "current_spend" in data
        assert "utilization_percentage" in data
        assert "is_over_threshold" in data
        assert "is_over_budget" in data

    def test_create_budget(self):
        payload = {
            "project_id": PROJECT_ID,
            "budget_name": "Test Budget",
            "budget_amount": 5000.0,
            "currency": "USD",
            "threshold_percentage": 75.0,
            "alert_enabled": True,
        }
        r = client.post("/api/governance/cost/budget", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["budget_name"] == "Test Budget"
        assert data["budget_amount"] == 5000.0
        assert data["current_spend"] == 0.0
        assert data["utilization_percentage"] == 0.0
        assert data["is_over_threshold"] is False
        assert data["is_over_budget"] is False

    def test_create_budget_missing_required_field(self):
        payload = {"project_id": PROJECT_ID}
        r = client.post("/api/governance/cost/budget", json=payload)
        assert r.status_code == 422

    def test_create_budget_defaults(self):
        payload = {
            "project_id": PROJECT_ID,
            "budget_name": "Default Budget",
            "budget_amount": 1000.0,
        }
        r = client.post("/api/governance/cost/budget", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["currency"] == "USD"
        assert data["alert_enabled"] is True


class TestAnomalyRoutes:
    """Test cost anomaly listing endpoint."""

    def test_list_anomalies(self):
        r = client.get(
            f"/api/governance/cost/anomalies/{PROJECT_ID}",
            params={"subscription_id": SUBSCRIPTION_ID},
        )
        assert r.status_code == 200
        data = r.json()
        assert "anomalies" in data
        assert "total" in data

    def test_list_anomalies_default_subscription(self):
        r = client.get(f"/api/governance/cost/anomalies/{PROJECT_ID}")
        assert r.status_code == 200


class TestCostScanRoutes:
    """Test cost scan trigger endpoint."""

    def test_trigger_cost_scan(self):
        r = client.post(
            f"/api/governance/cost/scan/{PROJECT_ID}",
            params={"subscription_id": SUBSCRIPTION_ID},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"
        assert data["project_id"] == PROJECT_ID
        assert "message" in data
        assert "scan_id" in data

    def test_trigger_cost_scan_default_subscription(self):
        r = client.post(f"/api/governance/cost/scan/{PROJECT_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"


# ── Router registration test ────────────────────────────────────────────────


class TestCostRouterRegistered:
    """Verify the cost router is registered on the main app."""

    def test_cost_routes_registered(self):
        route_paths = [route.path for route in app.routes]
        assert "/api/governance/cost/summary/{project_id}" in route_paths
        assert "/api/governance/cost/trend/{project_id}" in route_paths
        assert "/api/governance/cost/budget/{project_id}" in route_paths
        assert "/api/governance/cost/budget" in route_paths
        assert "/api/governance/cost/anomalies/{project_id}" in route_paths
        assert "/api/governance/cost/scan/{project_id}" in route_paths
