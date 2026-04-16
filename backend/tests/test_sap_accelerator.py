"""Tests for SAP on Azure accelerator services and API routes."""

from starlette.testclient import TestClient

from app.main import app
from app.services.sap_accelerator import (
    SAP_BEST_PRACTICES,
    SAP_CERTIFIED_SKUS,
    SAP_QUESTIONS,
    SAP_REFERENCE_ARCHITECTURES,
    sap_accelerator,
)
from app.services.sap_bicep import sap_bicep_service

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-token"}


# ── Service Unit Tests: Questionnaire ─────────────────────────────────────────


def test_get_questions_returns_list():
    questions = sap_accelerator.get_questions()
    assert isinstance(questions, list)
    assert len(questions) >= 10


def test_get_questions_has_required_fields():
    questions = sap_accelerator.get_questions()
    for q in questions:
        assert "id" in q
        assert "text" in q
        assert "type" in q
        assert "required" in q
        assert "category" in q


def test_questions_have_unique_ids():
    questions = sap_accelerator.get_questions()
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids))


def test_questions_include_sap_product():
    questions = sap_accelerator.get_questions()
    ids = {q["id"] for q in questions}
    assert "sap_product" in ids


def test_questions_include_database():
    questions = sap_accelerator.get_questions()
    ids = {q["id"] for q in questions}
    assert "sap_database" in ids


def test_questions_include_ha_and_dr():
    questions = sap_accelerator.get_questions()
    ids = {q["id"] for q in questions}
    assert "high_availability" in ids
    assert "disaster_recovery" in ids


def test_questions_all_have_category_sap():
    questions = sap_accelerator.get_questions()
    for q in questions:
        assert q["category"] == "sap"


# ── Service Unit Tests: Certified SKUs ────────────────────────────────────────


def test_get_certified_skus_returns_all():
    skus = sap_accelerator.get_certified_skus({})
    assert isinstance(skus, list)
    assert len(skus) == len(SAP_CERTIFIED_SKUS)


def test_certified_skus_have_required_fields():
    skus = sap_accelerator.get_certified_skus({})
    for sku in skus:
        assert "name" in sku
        assert "series" in sku
        assert "vcpus" in sku
        assert "memory_gb" in sku
        assert "saps_rating" in sku
        assert "tier" in sku


def test_filter_skus_by_tier_hana():
    skus = sap_accelerator.get_certified_skus({"tier": "hana"})
    assert all(s["tier"] == "hana" for s in skus)
    assert len(skus) >= 5


def test_filter_skus_by_tier_app():
    skus = sap_accelerator.get_certified_skus({"tier": "app"})
    assert all(s["tier"] == "app" for s in skus)
    assert len(skus) >= 3


def test_filter_skus_by_min_memory():
    skus = sap_accelerator.get_certified_skus({"min_memory_gb": 1024})
    assert all(s["memory_gb"] >= 1024 for s in skus)


def test_filter_skus_by_min_saps():
    skus = sap_accelerator.get_certified_skus({"min_saps": 50_000})
    assert all(s["saps_rating"] >= 50_000 for s in skus)


def test_skus_include_m_series():
    skus = sap_accelerator.get_certified_skus({"series": "M"})
    assert len(skus) >= 1
    assert all(s["series"] == "M" for s in skus)


def test_skus_include_mv2_series():
    skus = sap_accelerator.get_certified_skus({})
    mv2_skus = [s for s in skus if s["series"] == "Mv2"]
    assert len(mv2_skus) >= 1


def test_hana_skus_have_max_hana_memory():
    skus = sap_accelerator.get_certified_skus({"tier": "hana"})
    for sku in skus:
        assert sku["max_hana_memory_gb"] > 0


# ── Service Unit Tests: Architecture Generation ──────────────────────────────


def test_generate_architecture_basic():
    answers = {
        "sap_product": "s4hana",
        "sap_database": "hana",
        "high_availability": "yes",
        "disaster_recovery": "no",
        "data_volume": "medium",
        "saps_rating": "30000",
        "environment_type": "production",
    }
    arch = sap_accelerator.generate_architecture(answers)
    assert "tiers" in arch
    assert "database" in arch["tiers"]
    assert "application" in arch["tiers"]
    assert "ascs" in arch["tiers"]


def test_generate_architecture_has_db_sku():
    answers = {
        "sap_product": "s4hana",
        "sap_database": "hana",
        "high_availability": "no",
        "disaster_recovery": "no",
        "data_volume": "small",
        "saps_rating": "10000",
    }
    arch = sap_accelerator.generate_architecture(answers)
    db_tier = arch["tiers"]["database"]
    assert "vm_sku" in db_tier
    assert db_tier["vm_sku"].startswith("Standard_M")


def test_generate_architecture_ha_enables_hsr():
    answers = {
        "sap_product": "s4hana",
        "sap_database": "hana",
        "high_availability": "yes",
        "disaster_recovery": "no",
        "data_volume": "medium",
        "saps_rating": "30000",
    }
    arch = sap_accelerator.generate_architecture(answers)
    db_tier = arch["tiers"]["database"]
    assert db_tier["vm_count"] == 2
    assert db_tier["hsr_enabled"] is True


def test_generate_architecture_no_ha():
    answers = {
        "sap_product": "ecc",
        "sap_database": "hana",
        "high_availability": "no",
        "disaster_recovery": "no",
        "data_volume": "small",
        "saps_rating": "10000",
    }
    arch = sap_accelerator.generate_architecture(answers)
    db_tier = arch["tiers"]["database"]
    assert db_tier["vm_count"] == 1


def test_generate_architecture_with_dr():
    answers = {
        "sap_product": "s4hana",
        "sap_database": "hana",
        "high_availability": "yes",
        "disaster_recovery": "yes",
        "rpo_rto": "rpo_5_rto_30",
        "data_volume": "medium",
        "saps_rating": "30000",
    }
    arch = sap_accelerator.generate_architecture(answers)
    assert "disaster_recovery" in arch
    assert arch["disaster_recovery"]["enabled"] is True


def test_generate_architecture_web_dispatcher_with_fiori():
    answers = {
        "sap_product": "s4hana",
        "sap_database": "hana",
        "high_availability": "no",
        "disaster_recovery": "no",
        "data_volume": "small",
        "saps_rating": "10000",
        "integration_requirements": ["fiori"],
    }
    arch = sap_accelerator.generate_architecture(answers)
    assert "web_dispatcher" in arch["tiers"]


def test_generate_architecture_has_networking():
    answers = {
        "sap_product": "s4hana",
        "sap_database": "hana",
        "high_availability": "no",
        "disaster_recovery": "no",
        "data_volume": "small",
        "saps_rating": "10000",
    }
    arch = sap_accelerator.generate_architecture(answers)
    assert "networking" in arch
    assert "subnets" in arch["networking"]


def test_generate_architecture_has_shared_services():
    answers = {
        "sap_product": "s4hana",
        "sap_database": "hana",
        "high_availability": "no",
        "disaster_recovery": "no",
        "data_volume": "small",
        "saps_rating": "10000",
    }
    arch = sap_accelerator.generate_architecture(answers)
    shared = arch["shared_services"]
    types = {s["type"] for s in shared}
    assert "azure_netapp_files" in types
    assert "proximity_placement_group" in types


# ── Service Unit Tests: Best Practices ────────────────────────────────────────


def test_get_best_practices_returns_list():
    practices = sap_accelerator.get_best_practices()
    assert isinstance(practices, list)
    assert len(practices) >= 8


def test_best_practices_have_required_fields():
    practices = sap_accelerator.get_best_practices()
    for bp in practices:
        assert "id" in bp
        assert "category" in bp
        assert "title" in bp
        assert "severity" in bp


def test_best_practices_include_critical():
    practices = sap_accelerator.get_best_practices()
    critical = [bp for bp in practices if bp["severity"] == "critical"]
    assert len(critical) >= 3


# ── Service Unit Tests: Sizing ────────────────────────────────────────────────


def test_estimate_sizing_basic():
    result = sap_accelerator.estimate_sizing({
        "saps": 30000,
        "data_volume": "medium",
        "concurrent_users": 500,
    })
    assert "database_sku" in result
    assert "app_server_sku" in result
    assert "app_server_count" in result
    assert result["app_server_count"] >= 2


def test_estimate_sizing_from_users():
    result = sap_accelerator.estimate_sizing({
        "saps": 0,
        "data_volume": "small",
        "concurrent_users": 200,
    })
    assert result["total_saps"] > 0


def test_estimate_sizing_large_volume():
    result = sap_accelerator.estimate_sizing({
        "saps": 100000,
        "data_volume": "very_large",
        "concurrent_users": 2000,
    })
    assert result["database_sku"]["memory_gb"] >= 2048


# ── Service Unit Tests: Validation ────────────────────────────────────────────


def test_validate_valid_architecture():
    answers = {
        "sap_product": "s4hana",
        "sap_database": "hana",
        "high_availability": "yes",
        "disaster_recovery": "no",
        "data_volume": "medium",
        "saps_rating": "30000",
    }
    arch = sap_accelerator.generate_architecture(answers)
    result = sap_accelerator.validate_architecture(arch)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_missing_db_tier():
    result = sap_accelerator.validate_architecture({
        "tiers": {"application": {"vm_sku": "Standard_E16s_v5"}},
    })
    assert result["valid"] is False
    assert any("database" in e.lower() for e in result["errors"])


def test_validate_missing_app_tier():
    result = sap_accelerator.validate_architecture({
        "tiers": {"database": {"vm_sku": "Standard_M64s"}},
    })
    assert result["valid"] is False
    assert any("application" in e.lower() for e in result["errors"])


def test_validate_uncertified_sku():
    result = sap_accelerator.validate_architecture({
        "tiers": {
            "database": {"vm_sku": "Standard_D4s_v5"},
            "application": {"vm_sku": "Standard_E16s_v5"},
        },
    })
    assert result["valid"] is False
    assert any("certified" in e.lower() for e in result["errors"])


# ── Service Unit Tests: Reference Architectures ──────────────────────────────


def test_get_reference_architectures():
    refs = sap_accelerator.get_reference_architectures()
    assert isinstance(refs, list)
    assert len(refs) == 3


def test_reference_architectures_have_required_fields():
    refs = sap_accelerator.get_reference_architectures()
    for ref in refs:
        assert "id" in ref
        assert "name" in ref
        assert "product" in ref
        assert "components" in ref


def test_reference_architectures_include_s4hana():
    refs = sap_accelerator.get_reference_architectures()
    ids = {r["id"] for r in refs}
    assert "s4hana_ha" in ids


# ── Bicep Service Tests ──────────────────────────────────────────────────────


def test_generate_hana_vm_bicep():
    bicep = sap_bicep_service.generate_hana_vm({
        "name": "testHana",
        "location": "westeurope",
        "vm_sku": "Standard_M128s",
    })
    assert "testHana" in bicep
    assert "westeurope" in bicep
    assert "Standard_M128s" in bicep
    assert "SUSE" in bicep


def test_generate_app_server_bicep():
    bicep = sap_bicep_service.generate_app_server({
        "name": "testApp",
        "vm_count": 3,
        "vm_sku": "Standard_E16s_v5",
    })
    assert "testApp" in bicep
    assert "Standard_E16s_v5" in bicep
    assert "vmCount" in bicep


def test_generate_full_sap_stack_bicep():
    bicep = sap_bicep_service.generate_full_sap_stack({
        "name_prefix": "prod",
        "location": "eastus2",
        "ha_enabled": True,
    })
    assert "prod" in bicep
    assert "eastus2" in bicep
    assert "proximityPlacementGroup" in bicep.lower() or "ppg" in bicep


def test_full_stack_includes_anf():
    bicep = sap_bicep_service.generate_full_sap_stack({
        "include_anf": True,
    })
    assert "NetApp" in bicep


def test_full_stack_includes_backup():
    bicep = sap_bicep_service.generate_full_sap_stack({
        "include_backup": True,
    })
    assert "RecoveryServices" in bicep


def test_full_stack_includes_monitoring():
    bicep = sap_bicep_service.generate_full_sap_stack({
        "include_monitoring": True,
    })
    assert "monitor" in bicep.lower()


# ── API Route Tests ──────────────────────────────────────────────────────────


def test_api_get_questions():
    resp = client.get(
        "/api/accelerators/sap/questions", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "questions" in data
    assert data["total"] >= 10


def test_api_get_skus():
    resp = client.get(
        "/api/accelerators/sap/skus", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "skus" in data
    assert data["total"] >= 10


def test_api_get_skus_filtered():
    resp = client.get(
        "/api/accelerators/sap/skus?tier=hana",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(s["tier"] == "hana" for s in data["skus"])


def test_api_generate_architecture():
    resp = client.post(
        "/api/accelerators/sap/architecture",
        headers=AUTH_HEADERS,
        json={
            "answers": {
                "sap_product": "s4hana",
                "sap_database": "hana",
                "high_availability": "yes",
                "disaster_recovery": "no",
                "data_volume": "medium",
                "saps_rating": "30000",
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "architecture" in data


def test_api_estimate_sizing():
    resp = client.post(
        "/api/accelerators/sap/sizing",
        headers=AUTH_HEADERS,
        json={
            "saps": 30000,
            "data_volume": "medium",
            "concurrent_users": 500,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "database_sku" in data
    assert "app_server_count" in data


def test_api_get_best_practices():
    resp = client.get(
        "/api/accelerators/sap/best-practices",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "best_practices" in data
    assert data["total"] >= 8


def test_api_generate_bicep():
    resp = client.post(
        "/api/accelerators/sap/bicep",
        headers=AUTH_HEADERS,
        json={
            "template_type": "hana_vm",
            "config": {"name": "myHana", "vm_sku": "Standard_M64s"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_type"] == "hana_vm"
    assert "bicep_template" in data
    assert "myHana" in data["bicep_template"]


def test_api_generate_bicep_invalid_type():
    resp = client.post(
        "/api/accelerators/sap/bicep",
        headers=AUTH_HEADERS,
        json={"template_type": "invalid", "config": {}},
    )
    assert resp.status_code == 400


def test_api_get_reference_architectures():
    resp = client.get(
        "/api/accelerators/sap/reference-architectures",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reference_architectures" in data
    assert data["total"] == 3


def test_api_validate_architecture():
    resp = client.post(
        "/api/accelerators/sap/validate",
        headers=AUTH_HEADERS,
        json={
            "architecture": {
                "tiers": {
                    "database": {
                        "vm_sku": "Standard_M64s",
                        "vm_count": 2,
                        "hsr_enabled": True,
                        "accelerated_networking": True,
                    },
                    "application": {
                        "vm_sku": "Standard_E16s_v5",
                        "accelerated_networking": True,
                    },
                    "ascs": {
                        "accelerated_networking": True,
                    },
                },
                "shared_services": [
                    {"type": "proximity_placement_group"},
                    {"type": "standard_load_balancer"},
                ],
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True


# ── Module-Level Constants Tests ─────────────────────────────────────────────


def test_sap_questions_constant():
    assert isinstance(SAP_QUESTIONS, list)
    assert len(SAP_QUESTIONS) >= 10


def test_sap_certified_skus_constant():
    assert isinstance(SAP_CERTIFIED_SKUS, list)
    assert len(SAP_CERTIFIED_SKUS) >= 10


def test_sap_best_practices_constant():
    assert isinstance(SAP_BEST_PRACTICES, list)
    assert len(SAP_BEST_PRACTICES) >= 8


def test_sap_reference_architectures_constant():
    assert isinstance(SAP_REFERENCE_ARCHITECTURES, list)
    assert len(SAP_REFERENCE_ARCHITECTURES) == 3


def test_sap_accelerator_singleton():
    assert sap_accelerator is not None
    assert hasattr(sap_accelerator, "get_questions")
    assert hasattr(sap_accelerator, "generate_architecture")


def test_sap_bicep_service_singleton():
    assert sap_bicep_service is not None
    assert hasattr(sap_bicep_service, "generate_hana_vm")
    assert hasattr(sap_bicep_service, "generate_full_sap_stack")
