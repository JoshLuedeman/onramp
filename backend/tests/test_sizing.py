"""Tests for the right-sizing recommendation engine and API routes."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.sizing import (
    AvailabilitySLA,
    CostEstimate,
    CostPriority,
    SKURecommendation,
    WorkloadProfile,
    WorkloadType,
)
from app.services.pricing import pricing_service
from app.services.sizing import SizingEngine, sizing_engine

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    return SizingEngine()


@pytest.fixture()
def web_profile():
    return WorkloadProfile(
        workload_type=WorkloadType.WEB_APP,
        peak_concurrent_users=500,
        availability=AvailabilitySLA.SLA_999,
        cost_priority=CostPriority.BALANCED,
    )


@pytest.fixture()
def db_profile():
    return WorkloadProfile(
        workload_type=WorkloadType.DATABASE,
        peak_concurrent_users=200,
        availability=AvailabilitySLA.SLA_9995,
        cost_priority=CostPriority.BALANCED,
        data_size_gb=100.0,
    )


@pytest.fixture()
def analytics_profile():
    return WorkloadProfile(
        workload_type=WorkloadType.ANALYTICS,
        peak_concurrent_users=50,
        availability=AvailabilitySLA.SLA_999,
        cost_priority=CostPriority.PERFORMANCE_FIRST,
    )


@pytest.fixture()
def batch_profile():
    return WorkloadProfile(
        workload_type=WorkloadType.BATCH,
        peak_concurrent_users=10,
        availability=AvailabilitySLA.SLA_999,
        cost_priority=CostPriority.COST_OPTIMIZED,
    )


@pytest.fixture()
def api_profile():
    return WorkloadProfile(
        workload_type=WorkloadType.API,
        peak_concurrent_users=1000,
        availability=AvailabilitySLA.SLA_9999,
        cost_priority=CostPriority.BALANCED,
    )


@pytest.fixture()
def microservices_profile():
    return WorkloadProfile(
        workload_type=WorkloadType.MICROSERVICES,
        peak_concurrent_users=3000,
        availability=AvailabilitySLA.SLA_9999,
        cost_priority=CostPriority.PERFORMANCE_FIRST,
    )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestSizingEngineSingleton:
    def test_singleton_exists(self):
        assert sizing_engine is not None
        assert isinstance(sizing_engine, SizingEngine)


# ---------------------------------------------------------------------------
# VM recommendations
# ---------------------------------------------------------------------------


class TestVMRecommendation:
    """VM SKU selection for each workload type and priority combination."""

    def test_web_app_balanced(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.WEB_APP, 500, CostPriority.BALANCED)
        assert vm.series == "D"
        assert vm.sku.startswith("Standard_D")
        assert vm.monthly_cost_estimate > 0

    def test_web_app_cost_optimized_low_traffic(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.WEB_APP, 50, CostPriority.COST_OPTIMIZED)
        assert vm.series == "B"

    def test_web_app_performance_first_high_traffic(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.WEB_APP, 5000, CostPriority.PERFORMANCE_FIRST)
        assert vm.sku == "Standard_D16s_v3"

    def test_database_selects_e_series(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.DATABASE, 500, CostPriority.BALANCED)
        assert vm.series == "E"

    def test_database_cost_optimized(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.DATABASE, 50, CostPriority.COST_OPTIMIZED)
        assert vm.sku == "Standard_E2s_v3"

    def test_database_high_traffic(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.DATABASE, 2000, CostPriority.BALANCED)
        assert vm.sku == "Standard_E8s_v3"

    def test_analytics_performance_first_gets_gpu(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.ANALYTICS, 100, CostPriority.PERFORMANCE_FIRST)
        assert vm.series == "NC"
        assert vm.sku == "Standard_NC6s_v3"

    def test_analytics_balanced_gets_memory(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.ANALYTICS, 500, CostPriority.BALANCED)
        assert vm.series == "E"

    def test_batch_cost_optimized(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.BATCH, 10, CostPriority.COST_OPTIMIZED)
        assert vm.series == "B"  # Low traffic + cost-optimized → burstable B-series

    def test_batch_medium(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.BATCH, 300, CostPriority.BALANCED)
        assert vm.sku == "Standard_D4s_v3"

    def test_batch_large(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.BATCH, 1000, CostPriority.BALANCED)
        assert vm.sku == "Standard_D8s_v3"

    def test_api_small(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.API, 100, CostPriority.BALANCED)
        assert vm.series == "D"
        assert vm.sku == "Standard_D2s_v3"

    def test_api_large(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.API, 1500, CostPriority.BALANCED)
        assert vm.sku == "Standard_D8s_v3"

    def test_microservices_medium(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.MICROSERVICES, 800, CostPriority.BALANCED)
        assert vm.series == "D"

    def test_vm_has_vcpus_and_memory(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.WEB_APP, 100, CostPriority.BALANCED)
        assert vm.vcpus > 0
        assert vm.memory_gb > 0

    def test_vm_has_reasoning(self, engine):
        vm = engine.get_vm_recommendation(WorkloadType.WEB_APP, 100, CostPriority.BALANCED)
        assert len(vm.reasoning) > 0


# ---------------------------------------------------------------------------
# App Service recommendations
# ---------------------------------------------------------------------------


class TestAppServiceRecommendation:
    def test_cost_optimized_low_traffic_free_tier(self, engine):
        rec = engine.get_app_service_recommendation(WorkloadType.WEB_APP, 30, CostPriority.COST_OPTIMIZED)
        assert rec.sku == "F1"
        assert rec.tier == "Free"
        assert rec.monthly_cost_estimate == 0.0

    def test_cost_optimized_moderate_traffic_basic(self, engine):
        rec = engine.get_app_service_recommendation(WorkloadType.WEB_APP, 200, CostPriority.COST_OPTIMIZED)
        assert rec.sku == "B1"

    def test_balanced_small_prod_standard(self, engine):
        rec = engine.get_app_service_recommendation(WorkloadType.WEB_APP, 300, CostPriority.BALANCED)
        assert rec.sku == "S1"
        assert rec.tier == "Standard"

    def test_balanced_high_traffic_premium(self, engine):
        rec = engine.get_app_service_recommendation(WorkloadType.WEB_APP, 1500, CostPriority.BALANCED)
        assert rec.sku == "P1v3"

    def test_very_high_traffic_premium_v2(self, engine):
        rec = engine.get_app_service_recommendation(WorkloadType.WEB_APP, 5000, CostPriority.BALANCED)
        assert rec.sku == "P2v3"

    def test_performance_first_small_still_premium(self, engine):
        rec = engine.get_app_service_recommendation(WorkloadType.API, 300, CostPriority.PERFORMANCE_FIRST)
        assert rec.sku == "P1v3"

    def test_has_reasoning(self, engine):
        rec = engine.get_app_service_recommendation(WorkloadType.WEB_APP, 100, CostPriority.BALANCED)
        assert len(rec.reasoning) > 0


# ---------------------------------------------------------------------------
# Database recommendations
# ---------------------------------------------------------------------------


class TestDatabaseRecommendation:
    def test_cost_optimized_small_basic(self, engine):
        rec = engine.get_database_recommendation(WorkloadType.WEB_APP, 1.0, CostPriority.COST_OPTIMIZED)
        assert rec.sku == "SQL_Basic"
        assert rec.tier == "Basic"

    def test_cost_optimized_larger_standard(self, engine):
        rec = engine.get_database_recommendation(WorkloadType.WEB_APP, 30.0, CostPriority.COST_OPTIMIZED)
        assert rec.sku == "SQL_S0"

    def test_balanced_medium_standard_s2(self, engine):
        rec = engine.get_database_recommendation(WorkloadType.WEB_APP, 100.0, CostPriority.BALANCED)
        assert rec.sku == "SQL_S2"

    def test_performance_first_premium(self, engine):
        rec = engine.get_database_recommendation(WorkloadType.DATABASE, 200.0, CostPriority.PERFORMANCE_FIRST)
        assert rec.sku == "SQL_P1"
        assert rec.tier == "Premium"

    def test_large_data_premium(self, engine):
        rec = engine.get_database_recommendation(WorkloadType.DATABASE, 300.0, CostPriority.BALANCED)
        assert rec.tier == "Premium"

    def test_very_large_data_hyperscale(self, engine):
        rec = engine.get_database_recommendation(WorkloadType.DATABASE, 600.0, CostPriority.BALANCED)
        assert rec.tier == "Hyperscale"
        assert rec.sku == "SQL_Hyperscale_2vCore"

    def test_massive_data_performance_hyperscale_4v(self, engine):
        rec = engine.get_database_recommendation(WorkloadType.ANALYTICS, 2000.0, CostPriority.PERFORMANCE_FIRST)
        assert rec.sku == "SQL_Hyperscale_4vCore"

    def test_max_size_set(self, engine):
        rec = engine.get_database_recommendation(WorkloadType.WEB_APP, 50.0, CostPriority.BALANCED)
        assert rec.max_size_gb > 0


# ---------------------------------------------------------------------------
# Storage recommendations
# ---------------------------------------------------------------------------


class TestStorageRecommendation:
    def test_sla_999_hot_zrs(self, engine):
        rec = engine.get_storage_recommendation(AvailabilitySLA.SLA_999, WorkloadType.WEB_APP)
        assert rec.redundancy == "ZRS"
        assert rec.tier == "Hot"

    def test_sla_999_batch_cool_lrs(self, engine):
        rec = engine.get_storage_recommendation(AvailabilitySLA.SLA_999, WorkloadType.BATCH)
        assert rec.redundancy == "LRS"
        assert rec.tier == "Cool"

    def test_sla_9995_hot_grs(self, engine):
        rec = engine.get_storage_recommendation(AvailabilitySLA.SLA_9995, WorkloadType.WEB_APP)
        assert rec.redundancy == "GRS"
        assert rec.tier == "Hot"

    def test_sla_9995_analytics_cool_grs(self, engine):
        rec = engine.get_storage_recommendation(AvailabilitySLA.SLA_9995, WorkloadType.ANALYTICS)
        assert rec.redundancy == "GRS"
        assert rec.tier == "Cool"

    def test_sla_9999_hot_ragrs(self, engine):
        rec = engine.get_storage_recommendation(AvailabilitySLA.SLA_9999, WorkloadType.WEB_APP)
        assert rec.redundancy == "RA-GRS"
        assert rec.tier == "Hot"

    def test_sla_9999_batch_grs_cool(self, engine):
        rec = engine.get_storage_recommendation(AvailabilitySLA.SLA_9999, WorkloadType.BATCH)
        assert rec.redundancy == "GRS"
        assert rec.tier == "Cool"

    def test_has_reasoning(self, engine):
        rec = engine.get_storage_recommendation(AvailabilitySLA.SLA_999, WorkloadType.WEB_APP)
        assert len(rec.reasoning) > 0

    def test_has_cost_estimate(self, engine):
        rec = engine.get_storage_recommendation(AvailabilitySLA.SLA_999, WorkloadType.WEB_APP)
        assert rec.monthly_cost_estimate >= 0


# ---------------------------------------------------------------------------
# recommend_skus (full pipeline)
# ---------------------------------------------------------------------------


class TestRecommendSkus:
    """Integration tests for the full recommendation pipeline."""

    def test_returns_four_recommendations(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        assert len(recs) == 4

    def test_recommendation_types(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        types = {r.resource_type for r in recs}
        assert "Microsoft.Compute/virtualMachines" in types
        assert "Microsoft.Web/serverFarms" in types
        assert "Microsoft.Sql/servers/databases" in types
        assert "Microsoft.Storage/storageAccounts" in types

    def test_all_have_skus(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        for rec in recs:
            assert rec.recommended_sku != ""

    def test_all_have_costs(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        for rec in recs:
            assert rec.monthly_cost_estimate >= 0

    def test_all_have_alternatives(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        for rec in recs:
            assert isinstance(rec.alternatives, list)
            assert len(rec.alternatives) >= 1

    def test_database_profile_uses_e_series(self, engine, db_profile):
        recs = engine.recommend_skus(db_profile)
        vm_rec = next(r for r in recs if r.resource_type == "Microsoft.Compute/virtualMachines")
        assert "Standard_E" in vm_rec.recommended_sku

    def test_analytics_profile_gpu(self, engine, analytics_profile):
        recs = engine.recommend_skus(analytics_profile)
        vm_rec = next(r for r in recs if r.resource_type == "Microsoft.Compute/virtualMachines")
        assert "NC" in vm_rec.recommended_sku

    def test_batch_profile_cost_optimized(self, engine, batch_profile):
        recs = engine.recommend_skus(batch_profile)
        app_rec = next(r for r in recs if r.resource_type == "Microsoft.Web/serverFarms")
        # Cost optimized with low traffic → free or basic
        assert app_rec.recommended_sku in ("F1", "B1")


# ---------------------------------------------------------------------------
# Cost priority affects SKU selection
# ---------------------------------------------------------------------------


class TestCostPriorityAffectsSKU:
    def test_cost_optimized_cheaper_than_performance(self, engine):
        cheap = engine.recommend_skus(WorkloadProfile(
            workload_type=WorkloadType.WEB_APP,
            peak_concurrent_users=500,
            cost_priority=CostPriority.COST_OPTIMIZED,
        ))
        expensive = engine.recommend_skus(WorkloadProfile(
            workload_type=WorkloadType.WEB_APP,
            peak_concurrent_users=500,
            cost_priority=CostPriority.PERFORMANCE_FIRST,
        ))
        cheap_total = sum(r.monthly_cost_estimate for r in cheap)
        expensive_total = sum(r.monthly_cost_estimate for r in expensive)
        assert cheap_total <= expensive_total

    def test_balanced_between_extremes(self, engine):
        cheap = engine.recommend_skus(WorkloadProfile(
            workload_type=WorkloadType.API,
            peak_concurrent_users=200,
            cost_priority=CostPriority.COST_OPTIMIZED,
        ))
        balanced = engine.recommend_skus(WorkloadProfile(
            workload_type=WorkloadType.API,
            peak_concurrent_users=200,
            cost_priority=CostPriority.BALANCED,
        ))
        expensive = engine.recommend_skus(WorkloadProfile(
            workload_type=WorkloadType.API,
            peak_concurrent_users=200,
            cost_priority=CostPriority.PERFORMANCE_FIRST,
        ))
        cheap_t = sum(r.monthly_cost_estimate for r in cheap)
        bal_t = sum(r.monthly_cost_estimate for r in balanced)
        exp_t = sum(r.monthly_cost_estimate for r in expensive)
        assert cheap_t <= bal_t <= exp_t


# ---------------------------------------------------------------------------
# Availability SLA affects redundancy
# ---------------------------------------------------------------------------


class TestAvailabilitySLAAffectsRedundancy:
    def test_higher_sla_higher_redundancy(self, engine):
        low = engine.recommend_skus(WorkloadProfile(
            workload_type=WorkloadType.WEB_APP,
            peak_concurrent_users=100,
            availability=AvailabilitySLA.SLA_999,
        ))
        high = engine.recommend_skus(WorkloadProfile(
            workload_type=WorkloadType.WEB_APP,
            peak_concurrent_users=100,
            availability=AvailabilitySLA.SLA_9999,
        ))
        low_storage = next(r for r in low if r.resource_type == "Microsoft.Storage/storageAccounts")
        high_storage = next(r for r in high if r.resource_type == "Microsoft.Storage/storageAccounts")
        # Higher SLA should have GRS/RA-GRS, lower should have ZRS/LRS
        assert "GRS" in high_storage.recommended_sku or "RAGRS" in high_storage.recommended_sku
        assert "ZRS" in low_storage.recommended_sku or "LRS" in low_storage.recommended_sku


# ---------------------------------------------------------------------------
# estimate_monthly_cost
# ---------------------------------------------------------------------------


class TestEstimateMonthlyCost:
    def test_returns_cost_estimate(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        estimate = engine.estimate_monthly_cost(recs)
        assert isinstance(estimate, CostEstimate)

    def test_total_matches_sum(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        estimate = engine.estimate_monthly_cost(recs)
        breakdown_sum = sum(item.monthly_cost for item in estimate.breakdown)
        assert estimate.total_monthly == pytest.approx(breakdown_sum, abs=0.02)

    def test_breakdown_length_matches_recs(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        estimate = engine.estimate_monthly_cost(recs)
        assert len(estimate.breakdown) == len(recs)

    def test_regional_pricing(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        eastus_est = engine.estimate_monthly_cost(recs, region="eastus")
        europe_est = engine.estimate_monthly_cost(recs, region="westeurope")
        assert europe_est.total_monthly >= eastus_est.total_monthly

    def test_empty_recommendations(self, engine):
        estimate = engine.estimate_monthly_cost([])
        assert estimate.total_monthly == 0.0

    def test_currency_is_usd(self, engine, web_profile):
        recs = engine.recommend_skus(web_profile)
        estimate = engine.estimate_monthly_cost(recs)
        assert estimate.currency == "USD"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_workload_profile_defaults(self):
        profile = WorkloadProfile(workload_type=WorkloadType.WEB_APP)
        assert profile.peak_concurrent_users == 100
        assert profile.availability == AvailabilitySLA.SLA_999
        assert profile.cost_priority == CostPriority.BALANCED
        assert profile.data_size_gb is None

    def test_workload_profile_all_fields(self):
        profile = WorkloadProfile(
            workload_type=WorkloadType.DATABASE,
            peak_concurrent_users=5000,
            availability=AvailabilitySLA.SLA_9999,
            cost_priority=CostPriority.PERFORMANCE_FIRST,
            data_size_gb=500.0,
        )
        assert profile.data_size_gb == 500.0

    def test_sku_recommendation_model(self):
        rec = SKURecommendation(
            resource_type="VM",
            recommended_sku="Standard_D2s_v3",
            reasoning="Test",
            monthly_cost_estimate=70.08,
            alternatives=["Standard_D4s_v3"],
        )
        assert rec.resource_type == "VM"
        assert len(rec.alternatives) == 1

    def test_workload_type_enum_values(self):
        assert WorkloadType.WEB_APP.value == "web_app"
        assert WorkloadType.DATABASE.value == "database"
        assert WorkloadType.ANALYTICS.value == "analytics"
        assert WorkloadType.BATCH.value == "batch"
        assert WorkloadType.API.value == "api"
        assert WorkloadType.MICROSERVICES.value == "microservices"

    def test_cost_priority_enum_values(self):
        assert CostPriority.COST_OPTIMIZED.value == "cost_optimized"
        assert CostPriority.BALANCED.value == "balanced"
        assert CostPriority.PERFORMANCE_FIRST.value == "performance_first"

    def test_availability_sla_enum_values(self):
        assert AvailabilitySLA.SLA_999.value == "sla_999"
        assert AvailabilitySLA.SLA_9995.value == "sla_9995"
        assert AvailabilitySLA.SLA_9999.value == "sla_9999"


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


AUTH_HEADERS = {"Authorization": "Bearer dev-token"}


class TestRecommendRoute:
    def test_recommend_success(self):
        resp = client.post(
            "/api/sizing/recommend",
            json={
                "workload_type": "web_app",
                "peak_concurrent_users": 500,
                "availability": "sla_999",
                "cost_priority": "balanced",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data
        assert "total_estimate" in data
        assert len(data["recommendations"]) == 4

    def test_recommend_with_data_size(self):
        resp = client.post(
            "/api/sizing/recommend",
            json={
                "workload_type": "database",
                "peak_concurrent_users": 200,
                "cost_priority": "performance_first",
                "data_size_gb": 1000.0,
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        recs = resp.json()["recommendations"]
        db_rec = next(r for r in recs if r["resource_type"] == "Microsoft.Sql/servers/databases")
        assert "Hyperscale" in db_rec["recommended_sku"]

    def test_recommend_all_workload_types(self):
        for wt in WorkloadType:
            resp = client.post(
                "/api/sizing/recommend",
                json={"workload_type": wt.value},
                headers=AUTH_HEADERS,
            )
            assert resp.status_code == 200, f"Failed for workload_type={wt.value}"

    def test_recommend_invalid_workload_type(self):
        resp = client.post(
            "/api/sizing/recommend",
            json={"workload_type": "invalid_type"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_recommend_missing_body(self):
        resp = client.post("/api/sizing/recommend", headers=AUTH_HEADERS)
        assert resp.status_code == 422


class TestEstimateRoute:
    def test_estimate_known_skus(self):
        resp = client.post(
            "/api/sizing/estimate",
            json={"skus": ["Standard_B1s", "F1", "SQL_Basic"]},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_monthly" in data
        assert data["total_monthly"] > 0

    def test_estimate_with_region(self):
        resp = client.post(
            "/api/sizing/estimate",
            json={"skus": ["Standard_D2s_v3"], "region": "westeurope"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200

    def test_estimate_unknown_sku(self):
        resp = client.post(
            "/api/sizing/estimate",
            json={"skus": ["NonExistent_SKU"]},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["total_monthly"] == 0.0

    def test_estimate_empty_skus_rejected(self):
        resp = client.post(
            "/api/sizing/estimate",
            json={"skus": []},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422


class TestSKUListRoute:
    def test_list_skus_default_region(self):
        resp = client.get("/api/sizing/skus", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "skus" in data
        assert data["total"] >= 30

    def test_list_skus_with_region(self):
        resp = client.get("/api/sizing/skus?region=westeurope", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        skus = resp.json()["skus"]
        assert len(skus) > 0

    def test_sku_item_structure(self):
        resp = client.get("/api/sizing/skus", headers=AUTH_HEADERS)
        item = resp.json()["skus"][0]
        assert "sku" in item
        assert "resource_type" in item
        assert "monthly_cost" in item
        assert "region" in item


class TestWorkloadTypesRoute:
    def test_list_workload_types(self):
        resp = client.get("/api/sizing/workload-types", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "workload_types" in data
        assert len(data["workload_types"]) == 6

    def test_workload_type_structure(self):
        resp = client.get("/api/sizing/workload-types", headers=AUTH_HEADERS)
        wt = resp.json()["workload_types"][0]
        assert "name" in wt
        assert "description" in wt
        assert "typical_resources" in wt

    def test_all_enum_values_represented(self):
        resp = client.get("/api/sizing/workload-types", headers=AUTH_HEADERS)
        names = {wt["name"] for wt in resp.json()["workload_types"]}
        for wt in WorkloadType:
            assert wt.value in names


# ---------------------------------------------------------------------------
# Alternatives helpers
# ---------------------------------------------------------------------------


class TestAlternatives:
    def test_vm_alternatives_memory_workload(self, engine):
        alts = engine._vm_alternatives(WorkloadType.DATABASE, CostPriority.BALANCED)
        assert all("Standard_E" in a for a in alts)

    def test_vm_alternatives_cost_optimized(self, engine):
        alts = engine._vm_alternatives(WorkloadType.WEB_APP, CostPriority.COST_OPTIMIZED)
        assert all("Standard_B" in a for a in alts)

    def test_vm_alternatives_general(self, engine):
        alts = engine._vm_alternatives(WorkloadType.API, CostPriority.BALANCED)
        assert all("Standard_D" in a for a in alts)

    def test_app_service_alternatives_cost(self, engine):
        alts = engine._app_service_alternatives(CostPriority.COST_OPTIMIZED)
        assert "F1" in alts

    def test_app_service_alternatives_balanced(self, engine):
        alts = engine._app_service_alternatives(CostPriority.BALANCED)
        assert "P1v3" in alts

    def test_database_alternatives_cost(self, engine):
        alts = engine._database_alternatives(CostPriority.COST_OPTIMIZED)
        assert "SQL_Basic" in alts

    def test_database_alternatives_balanced(self, engine):
        alts = engine._database_alternatives(CostPriority.BALANCED)
        assert "SQL_P1" in alts

    def test_storage_alternatives_high_sla(self, engine):
        alts = engine._storage_alternatives(AvailabilitySLA.SLA_9999)
        assert "Storage_RAGRS_Hot" in alts

    def test_storage_alternatives_low_sla(self, engine):
        alts = engine._storage_alternatives(AvailabilitySLA.SLA_999)
        assert "Storage_LRS_Hot" in alts


# ---------------------------------------------------------------------------
# Embedded pricing data coverage
# ---------------------------------------------------------------------------


class TestEmbeddedPricingData:
    def test_at_least_30_skus(self):
        assert len(pricing_service.EMBEDDED_PRICES) >= 30

    def test_vm_skus_present(self):
        vm_skus = [k for k in pricing_service.EMBEDDED_PRICES if k.startswith("Standard_")]
        assert len(vm_skus) >= 10

    def test_app_service_skus_present(self):
        app_skus = [k for k in pricing_service.EMBEDDED_PRICES if k in {"F1", "B1", "B2", "B3", "S1", "S2", "S3", "P1v3", "P2v3", "P3v3"}]
        assert len(app_skus) >= 5

    def test_sql_skus_present(self):
        sql_skus = [k for k in pricing_service.EMBEDDED_PRICES if k.startswith("SQL_")]
        assert len(sql_skus) >= 5

    def test_storage_skus_present(self):
        storage_skus = [k for k in pricing_service.EMBEDDED_PRICES if k.startswith("Storage_")]
        assert len(storage_skus) >= 4

    def test_all_prices_non_negative(self):
        for sku, price in pricing_service.EMBEDDED_PRICES.items():
            assert price >= 0, f"Negative price for {sku}: {price}"
