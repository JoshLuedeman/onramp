"""Tests for the embedded pricing service."""

import pytest

from app.schemas.sizing import CostEstimate, CostLineItem
from app.services.pricing import PricingService, pricing_service


# ── Singleton / instantiation ────────────────────────────────────────────────


class TestPricingServiceInit:
    """Verify the module-level singleton and basic construction."""

    def test_singleton_exists(self):
        assert pricing_service is not None
        assert isinstance(pricing_service, PricingService)

    def test_new_instance_has_prices(self):
        svc = PricingService()
        assert len(svc.EMBEDDED_PRICES) >= 30

    def test_new_instance_has_regional_multipliers(self):
        svc = PricingService()
        assert "eastus" in svc.REGIONAL_MULTIPLIERS
        assert svc.REGIONAL_MULTIPLIERS["eastus"] == 1.0


# ── get_price ────────────────────────────────────────────────────────────────


class TestGetPrice:
    """Unit tests for PricingService.get_price()."""

    @pytest.fixture()
    def svc(self):
        return PricingService()

    def test_known_vm_sku(self, svc):
        price = svc.get_price("Standard_B1s")
        assert price == 7.59

    def test_known_app_service_sku(self, svc):
        price = svc.get_price("F1")
        assert price == 0.0

    def test_known_sql_sku(self, svc):
        price = svc.get_price("SQL_Basic")
        assert price == pytest.approx(4.9, abs=0.01)

    def test_known_storage_sku(self, svc):
        price = svc.get_price("Storage_LRS_Hot")
        assert price == pytest.approx(20.80, abs=0.01)

    def test_unknown_sku_returns_zero(self, svc):
        assert svc.get_price("NonExistent_SKU_XYZ") == 0.0

    def test_default_region_is_eastus(self, svc):
        assert svc.get_price("Standard_B1s") == svc.get_price("Standard_B1s", "eastus")

    def test_regional_multiplier_applied(self, svc):
        eastus = svc.get_price("Standard_D2s_v3", "eastus")
        europe = svc.get_price("Standard_D2s_v3", "westeurope")
        assert europe > eastus

    def test_unknown_region_uses_multiplier_1(self, svc):
        base = svc.get_price("Standard_B2s", "eastus")
        unknown = svc.get_price("Standard_B2s", "unknownregion123")
        assert base == unknown

    def test_price_is_rounded(self, svc):
        price = svc.get_price("Standard_D2s_v3", "westeurope")
        # 70.08 * 1.10 = 77.088 → rounded to 77.09
        assert price == round(price, 2)


# ── estimate_total ───────────────────────────────────────────────────────────


class TestEstimateTotal:
    """Unit tests for PricingService.estimate_total()."""

    @pytest.fixture()
    def svc(self):
        return PricingService()

    def test_single_recommendation(self, svc):
        recs = [{"recommended_sku": "Standard_B1s", "resource_type": "VM"}]
        estimate = svc.estimate_total(recs)
        assert isinstance(estimate, CostEstimate)
        assert estimate.total_monthly == pytest.approx(7.59, abs=0.01)
        assert estimate.currency == "USD"
        assert len(estimate.breakdown) == 1

    def test_multiple_recommendations(self, svc):
        recs = [
            {"recommended_sku": "Standard_B1s", "resource_type": "VM"},
            {"recommended_sku": "F1", "resource_type": "App Service"},
        ]
        estimate = svc.estimate_total(recs)
        assert estimate.total_monthly == pytest.approx(7.59, abs=0.01)
        assert len(estimate.breakdown) == 2

    def test_empty_list_returns_zero(self, svc):
        estimate = svc.estimate_total([])
        assert estimate.total_monthly == 0.0
        assert estimate.breakdown == []

    def test_unknown_sku_in_list(self, svc):
        recs = [{"recommended_sku": "Fake_SKU", "resource_type": "VM"}]
        estimate = svc.estimate_total(recs)
        assert estimate.total_monthly == 0.0

    def test_regional_pricing_in_estimate(self, svc):
        recs = [{"recommended_sku": "Standard_B1s", "resource_type": "VM"}]
        eastus_est = svc.estimate_total(recs, region="eastus")
        brazil_est = svc.estimate_total(recs, region="brazilsouth")
        assert brazil_est.total_monthly > eastus_est.total_monthly

    def test_breakdown_contains_correct_skus(self, svc):
        recs = [
            {"recommended_sku": "SQL_S0", "resource_type": "DB"},
            {"recommended_sku": "Storage_LRS_Hot", "resource_type": "Storage"},
        ]
        estimate = svc.estimate_total(recs)
        skus = [item.sku for item in estimate.breakdown]
        assert "SQL_S0" in skus
        assert "Storage_LRS_Hot" in skus


# ── list_all_skus ────────────────────────────────────────────────────────────


class TestListAllSkus:
    """Tests for the SKU catalog listing."""

    @pytest.fixture()
    def svc(self):
        return PricingService()

    def test_returns_all_skus(self, svc):
        items = svc.list_all_skus()
        assert len(items) == len(svc.EMBEDDED_PRICES)

    def test_each_item_has_required_keys(self, svc):
        items = svc.list_all_skus()
        for item in items:
            assert "sku" in item
            assert "resource_type" in item
            assert "monthly_cost" in item
            assert "region" in item

    def test_classify_vm_sku(self, svc):
        assert svc._classify_sku("Standard_B1s") == "Microsoft.Compute/virtualMachines"

    def test_classify_sql_sku(self, svc):
        assert svc._classify_sku("SQL_Basic") == "Microsoft.Sql/servers/databases"

    def test_classify_storage_sku(self, svc):
        assert svc._classify_sku("Storage_LRS_Hot") == "Microsoft.Storage/storageAccounts"

    def test_classify_app_service_sku(self, svc):
        assert svc._classify_sku("F1") == "Microsoft.Web/serverFarms"
        assert svc._classify_sku("P1v3") == "Microsoft.Web/serverFarms"

    def test_classify_unknown_sku(self, svc):
        assert svc._classify_sku("SomethingWeird") == "unknown"
