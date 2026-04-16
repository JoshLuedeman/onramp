"""Tests for the SKU database service."""

from app.services.sku_database import (
    CLOUD_SKU_RESTRICTIONS,
    COMPUTE_SKUS,
    DATABASE_SKUS,
    NETWORKING_SKUS,
    SKU_REGION_RESTRICTIONS,
    STORAGE_SKUS,
    SkuDatabaseService,
    sku_database_service,
)


# ---------------------------------------------------------------------------
# Static data integrity
# ---------------------------------------------------------------------------


def test_compute_skus_non_empty():
    assert len(COMPUTE_SKUS) >= 10


def test_storage_skus_non_empty():
    assert len(STORAGE_SKUS) >= 4


def test_database_skus_non_empty():
    assert len(DATABASE_SKUS) >= 5


def test_networking_skus_non_empty():
    assert len(NETWORKING_SKUS) >= 5


def test_all_compute_skus_have_required_keys():
    for s in COMPUTE_SKUS:
        assert "id" in s
        assert "name" in s
        assert "family" in s
        assert "vcpus" in s
        assert "ram_gb" in s


def test_all_storage_skus_have_required_keys():
    for s in STORAGE_SKUS:
        assert "id" in s
        assert "name" in s
        assert "tier" in s


def test_compute_families_cover_expected():
    families = {s["family"] for s in COMPUTE_SKUS}
    assert {"B", "D", "E", "F", "H", "L", "M", "N", "G"} <= families


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def test_get_compute_skus_no_filter():
    skus = sku_database_service.get_compute_skus()
    assert len(skus) == len(COMPUTE_SKUS)


def test_get_compute_skus_filter_family():
    skus = sku_database_service.get_compute_skus({"family": "N"})
    assert len(skus) >= 2
    assert all(s["family"] == "N" for s in skus)


def test_get_compute_skus_filter_min_vcpus():
    skus = sku_database_service.get_compute_skus({"min_vcpus": 32})
    assert all(s["vcpus"] >= 32 for s in skus)


def test_get_compute_skus_filter_min_ram():
    skus = sku_database_service.get_compute_skus({"min_ram": 256})
    assert all(s["ram_gb"] >= 256 for s in skus)


def test_get_compute_skus_filter_gpu():
    skus = sku_database_service.get_compute_skus({"gpu": True})
    assert len(skus) >= 2
    assert all(s.get("gpu") is not None for s in skus)


def test_get_compute_skus_filter_price_tier():
    skus = sku_database_service.get_compute_skus({"price_tier": "low"})
    assert all(s["price_tier"] == "low" for s in skus)


def test_get_storage_skus_no_filter():
    skus = sku_database_service.get_storage_skus()
    assert len(skus) == len(STORAGE_SKUS)


def test_get_storage_skus_filter_tier():
    skus = sku_database_service.get_storage_skus({"tier": "premium"})
    assert all(s["tier"] == "premium" for s in skus)


def test_get_storage_skus_filter_media():
    skus = sku_database_service.get_storage_skus({"media": "ssd"})
    assert all(s["media"] == "ssd" for s in skus)


def test_get_database_skus_no_filter():
    skus = sku_database_service.get_database_skus()
    assert len(skus) == len(DATABASE_SKUS)


def test_get_database_skus_filter_service():
    skus = sku_database_service.get_database_skus({"service": "cosmos_db"})
    assert all(s["service"] == "cosmos_db" for s in skus)


def test_get_networking_skus_no_filter():
    skus = sku_database_service.get_networking_skus()
    assert len(skus) == len(NETWORKING_SKUS)


def test_get_networking_skus_filter_service():
    skus = sku_database_service.get_networking_skus({"service": "vpn_gateway"})
    assert all(s["service"] == "vpn_gateway" for s in skus)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


def test_recommend_sku_ai_ml():
    result = sku_database_service.recommend_sku("ai_ml", {"gpu": True})
    assert "recommended_sku" in result
    assert "reason" in result
    assert "alternatives" in result
    assert result["recommended_sku"]["family"] == "N"


def test_recommend_sku_general():
    result = sku_database_service.recommend_sku("general", {})
    assert result["recommended_sku"] is not None


def test_recommend_sku_sap():
    result = sku_database_service.recommend_sku("sap", {"min_ram": 192})
    assert result["recommended_sku"]["family"] in ("M", "E")


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def test_get_sku_comparison_existing():
    skus = sku_database_service.get_sku_comparison(["b2s", "d4s_v5"])
    assert len(skus) == 2
    assert skus[0]["id"] == "b2s"
    assert skus[1]["id"] == "d4s_v5"


def test_get_sku_comparison_missing_id():
    skus = sku_database_service.get_sku_comparison(["b2s", "nonexistent"])
    assert len(skus) == 1


def test_get_sku_comparison_empty():
    skus = sku_database_service.get_sku_comparison([])
    assert skus == []


# ---------------------------------------------------------------------------
# Availability validation
# ---------------------------------------------------------------------------


def test_validate_availability_commercial():
    result = sku_database_service.validate_sku_availability(
        "Standard_D4s_v5", "eastus", "commercial"
    )
    assert result["available"] is True


def test_validate_availability_region_restricted():
    result = sku_database_service.validate_sku_availability(
        "Standard_NC6s_v3", "brazilsouth", "commercial"
    )
    assert result["available"] is False
    assert "region" in result.get("reason", "")


def test_validate_availability_cloud_restricted():
    result = sku_database_service.validate_sku_availability(
        "Standard_ND40rs_v2", "eastus", "government"
    )
    assert result["available"] is False
    assert "government" in result.get("reason", "")


def test_validate_availability_returns_sku_and_region():
    result = sku_database_service.validate_sku_availability(
        "Standard_D4s_v5", "westus", "commercial"
    )
    assert result["sku"] == "Standard_D4s_v5"
    assert result["region"] == "westus"
    assert result["cloud_env"] == "commercial"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_singleton_instance():
    svc = SkuDatabaseService()
    assert svc.get_compute_skus() == sku_database_service.get_compute_skus()
