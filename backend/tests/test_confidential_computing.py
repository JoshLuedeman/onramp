"""Tests for Azure Confidential Computing services and API routes."""

from starlette.testclient import TestClient

from app.main import app
from app.services.confidential_bicep import confidential_bicep_service
from app.services.confidential_computing import (
    ATTESTATION_CONFIGS,
    CONFIDENTIAL_OPTIONS,
    CONFIDENTIAL_VM_SKUS,
    SUPPORTED_REGIONS,
    confidential_computing_service,
)

client = TestClient(app)


# ── Service Unit Tests: Confidential Options ─────────────────────────────────


def test_get_confidential_options_returns_list():
    options = confidential_computing_service.get_confidential_options()
    assert isinstance(options, list)
    assert len(options) >= 6


def test_get_confidential_options_has_required_fields():
    options = confidential_computing_service.get_confidential_options()
    for opt in options:
        assert "id" in opt
        assert "name" in opt
        assert "category" in opt
        assert "tee_types" in opt
        assert "description" in opt


def test_confidential_options_include_all_categories():
    options = confidential_computing_service.get_confidential_options()
    categories = {o["category"] for o in options}
    assert "compute" in categories
    assert "data" in categories
    assert "security" in categories


def test_confidential_options_include_containers():
    options = confidential_computing_service.get_confidential_options()
    categories = {o["category"] for o in options}
    assert "containers" in categories


def test_confidential_options_have_unique_ids():
    options = confidential_computing_service.get_confidential_options()
    ids = [o["id"] for o in options]
    assert len(ids) == len(set(ids))


# ── Service Unit Tests: VM SKUs ──────────────────────────────────────────────


def test_get_vm_skus_returns_list():
    skus = confidential_computing_service.get_vm_skus()
    assert isinstance(skus, list)
    assert len(skus) >= 10


def test_vm_skus_have_required_fields():
    skus = confidential_computing_service.get_vm_skus()
    for sku in skus:
        assert "name" in sku
        assert "series" in sku
        assert "vcpus" in sku
        assert "memory_gb" in sku
        assert "tee_type" in sku
        assert "vendor" in sku


def test_vm_skus_include_sev_snp():
    skus = confidential_computing_service.get_vm_skus()
    sev_skus = [s for s in skus if s["tee_type"] == "SEV-SNP"]
    assert len(sev_skus) >= 5


def test_vm_skus_include_sgx():
    skus = confidential_computing_service.get_vm_skus()
    sgx_skus = [s for s in skus if s["tee_type"] == "SGX"]
    assert len(sgx_skus) >= 3


def test_vm_skus_have_positive_specs():
    skus = confidential_computing_service.get_vm_skus()
    for sku in skus:
        assert sku["vcpus"] > 0
        assert sku["memory_gb"] > 0


def test_vm_skus_sgx_have_enclave_memory():
    skus = confidential_computing_service.get_vm_skus()
    sgx_skus = [s for s in skus if s["tee_type"] == "SGX"]
    for sku in sgx_skus:
        assert "enclave_memory_mb" in sku
        assert sku["enclave_memory_mb"] > 0


# ── Service Unit Tests: Regions ──────────────────────────────────────────────


def test_get_supported_regions_returns_list():
    regions = confidential_computing_service.get_supported_regions()
    assert isinstance(regions, list)
    assert len(regions) >= 5


def test_regions_have_required_fields():
    regions = confidential_computing_service.get_supported_regions()
    for r in regions:
        assert "name" in r
        assert "display_name" in r
        assert "tee_types" in r
        assert "services" in r


def test_regions_include_eastus():
    regions = confidential_computing_service.get_supported_regions()
    names = [r["name"] for r in regions]
    assert "eastus" in names


def test_regions_have_at_least_one_service():
    regions = confidential_computing_service.get_supported_regions()
    for r in regions:
        assert len(r["services"]) >= 1


# ── Service Unit Tests: Recommendation ───────────────────────────────────────


def test_recommend_web_app():
    result = confidential_computing_service.recommend_confidential_config(
        "web_app", {}
    )
    assert result["workload_type"] == "web_app"
    assert result["recommended_option"]["id"] == "confidential_vms"
    assert "rationale" in result


def test_recommend_database():
    result = confidential_computing_service.recommend_confidential_config(
        "database", {}
    )
    assert result["recommended_option"]["id"] == "always_encrypted"


def test_recommend_container():
    result = confidential_computing_service.recommend_confidential_config(
        "container", {}
    )
    assert result["recommended_option"]["id"] == "confidential_containers"


def test_recommend_multi_party():
    result = confidential_computing_service.recommend_confidential_config(
        "multi_party", {}
    )
    assert result["recommended_option"]["id"] == "sgx_enclaves"


def test_recommend_with_tee_preference():
    result = confidential_computing_service.recommend_confidential_config(
        "web_app", {"tee_preference": "SGX"}
    )
    assert result["recommended_option"]["id"] == "sgx_enclaves"
    assert "SGX" in result["rationale"]


def test_recommend_with_region_filter():
    result = confidential_computing_service.recommend_confidential_config(
        "web_app", {"region": "eastus"}
    )
    for r in result["region_options"]:
        assert r["name"] == "eastus"


def test_recommend_returns_attestation():
    result = confidential_computing_service.recommend_confidential_config(
        "web_app", {"needs_attestation": True}
    )
    assert result["attestation"] is not None


def test_recommend_without_attestation():
    result = confidential_computing_service.recommend_confidential_config(
        "web_app", {"needs_attestation": False}
    )
    assert result["attestation"] is None


def test_recommend_unknown_workload_defaults():
    result = confidential_computing_service.recommend_confidential_config(
        "unknown_type", {}
    )
    assert result["recommended_option"]["id"] == "confidential_vms"


def test_recommend_returns_skus():
    result = confidential_computing_service.recommend_confidential_config(
        "web_app", {"min_vcpus": 4, "min_memory_gb": 16}
    )
    for sku in result["recommended_skus"]:
        assert sku["vcpus"] >= 4
        assert sku["memory_gb"] >= 16


# ── Service Unit Tests: Architecture Generation ──────────────────────────────


def test_generate_architecture_adds_cc_layer():
    base = {"management_groups": {}, "network": {}}
    result = confidential_computing_service.generate_confidential_architecture(
        base, {"cc_type": "confidential_vms"}
    )
    assert "confidential_computing" in result
    assert result["confidential_computing"]["enabled"] is True


def test_generate_architecture_preserves_base():
    base = {"management_groups": {"root": {}}, "custom_field": "value"}
    result = confidential_computing_service.generate_confidential_architecture(
        base, {"cc_type": "confidential_vms"}
    )
    assert result["custom_field"] == "value"


def test_generate_architecture_adds_vm_config():
    result = confidential_computing_service.generate_confidential_architecture(
        {}, {"cc_type": "confidential_vms", "vm_sku": "Standard_DC4as_v5"}
    )
    assert "vm_configuration" in result["confidential_computing"]


def test_generate_architecture_adds_attestation():
    result = confidential_computing_service.generate_confidential_architecture(
        {}, {"cc_type": "confidential_vms", "enable_attestation": True}
    )
    assert result["confidential_computing"]["attestation"]["enabled"] is True


def test_generate_architecture_no_attestation():
    result = confidential_computing_service.generate_confidential_architecture(
        {}, {"cc_type": "confidential_vms", "enable_attestation": False}
    )
    assert "attestation" not in result["confidential_computing"]


def test_generate_architecture_security_recommendations():
    result = confidential_computing_service.generate_confidential_architecture(
        {}, {"cc_type": "confidential_vms"}
    )
    recs = result["confidential_computing"]["security_recommendations"]
    assert len(recs) >= 3


# ── Service Unit Tests: Attestation Config ───────────────────────────────────


def test_attestation_config_vms():
    config = confidential_computing_service.get_attestation_config("confidential_vms")
    assert config["cc_type"] == "confidential_vms"
    assert "steps" in config


def test_attestation_config_sgx():
    config = confidential_computing_service.get_attestation_config("sgx_enclaves")
    assert config["cc_type"] == "sgx_enclaves"
    assert "SGX" in config["evidence_type"]


def test_attestation_config_unknown_returns_empty():
    config = confidential_computing_service.get_attestation_config("nonexistent")
    assert config == {}


# ── Bicep Service Unit Tests ─────────────────────────────────────────────────


def test_bicep_confidential_vm():
    result = confidential_bicep_service.generate_confidential_vm(
        {"name": "testVm", "location": "westeurope"}
    )
    assert "ConfidentialVM" in result
    assert "testVm" in result
    assert "westeurope" in result


def test_bicep_confidential_vm_windows():
    result = confidential_bicep_service.generate_confidential_vm(
        {"name": "winVm", "os_type": "Windows"}
    )
    assert "WindowsServer" in result


def test_bicep_confidential_aks():
    result = confidential_bicep_service.generate_confidential_aks(
        {"name": "testAks", "node_count": 5}
    )
    assert "testAks" in result
    assert "KataCcIsolation" in result
    assert "count: 5" in result


def test_bicep_attestation_provider():
    result = confidential_bicep_service.generate_attestation_provider(
        {"name": "testAttest", "location": "uksouth"}
    )
    assert "testAttest" in result
    assert "uksouth" in result
    assert "attestationProviders" in result


def test_bicep_confidential_sql():
    result = confidential_bicep_service.generate_confidential_sql(
        {"server_name": "testSql", "database_name": "testDb"}
    )
    assert "testSql" in result
    assert "testDb" in result
    assert "preferredEnclaveType" in result


def test_bicep_full_stack():
    result = confidential_bicep_service.generate_full_confidential_stack(
        {"name_prefix": "test", "location": "eastus"}
    )
    assert "Confidential Computing Landing Zone" in result
    assert "keyVault" in result.lower() or "key" in result.lower()
    assert "attestation" in result.lower()


def test_bicep_full_stack_without_aks():
    result = confidential_bicep_service.generate_full_confidential_stack(
        {"include_aks": False, "include_sql": True}
    )
    assert "managedClusters" not in result
    assert "sqlServer" in result or "Sql" in result


def test_bicep_full_stack_without_sql():
    result = confidential_bicep_service.generate_full_confidential_stack(
        {"include_aks": True, "include_sql": False}
    )
    assert "managedClusters" in result


# ── Route Tests: GET /api/confidential/options ───────────────────────────────


def test_route_options():
    response = client.get("/api/confidential/options")
    assert response.status_code == 200
    data = response.json()
    assert "options" in data
    assert "total" in data
    assert data["total"] >= 6


# ── Route Tests: GET /api/confidential/vm-skus ───────────────────────────────


def test_route_vm_skus():
    response = client.get("/api/confidential/vm-skus")
    assert response.status_code == 200
    data = response.json()
    assert "skus" in data
    assert "total" in data
    assert data["total"] >= 10


# ── Route Tests: GET /api/confidential/regions ───────────────────────────────


def test_route_regions():
    response = client.get("/api/confidential/regions")
    assert response.status_code == 200
    data = response.json()
    assert "regions" in data
    assert data["total"] >= 5


# ── Route Tests: POST /api/confidential/recommend ────────────────────────────


def test_route_recommend():
    response = client.post(
        "/api/confidential/recommend",
        json={"workload_type": "web_app", "requirements": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["workload_type"] == "web_app"
    assert "recommended_option" in data
    assert "rationale" in data


def test_route_recommend_with_requirements():
    response = client.post(
        "/api/confidential/recommend",
        json={
            "workload_type": "container",
            "requirements": {"min_vcpus": 4, "region": "eastus"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommended_option"]["id"] == "confidential_containers"


# ── Route Tests: POST /api/confidential/architecture ─────────────────────────


def test_route_architecture():
    response = client.post(
        "/api/confidential/architecture",
        json={
            "base_architecture": {"network": {}},
            "cc_options": {"cc_type": "confidential_vms"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cc_enabled"] is True
    assert "confidential_computing" in data["architecture"]


# ── Route Tests: POST /api/confidential/bicep ────────────────────────────────


def test_route_bicep_vm():
    response = client.post(
        "/api/confidential/bicep",
        json={
            "template_type": "confidential_vm",
            "config": {"name": "myVm"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["template_type"] == "confidential_vm"
    assert "ConfidentialVM" in data["bicep_template"]


def test_route_bicep_invalid_type():
    response = client.post(
        "/api/confidential/bicep",
        json={"template_type": "invalid_type", "config": {}},
    )
    assert response.status_code == 400
    data = response.json()
    assert "Unknown template_type" in data["error"]["message"]


# ── Route Tests: GET /api/confidential/attestation/{cc_type} ─────────────────


def test_route_attestation_found():
    response = client.get("/api/confidential/attestation/confidential_vms")
    assert response.status_code == 200
    data = response.json()
    assert data["cc_type"] == "confidential_vms"
    assert "steps" in data


def test_route_attestation_not_found():
    response = client.get("/api/confidential/attestation/nonexistent")
    assert response.status_code == 404


# ── Data Integrity Tests ─────────────────────────────────────────────────────


def test_all_option_ids_in_attestation_configs():
    """Every attestation-supported CC option has an attestation config."""
    for opt in CONFIDENTIAL_OPTIONS:
        if opt["attestation_supported"]:
            assert opt["id"] in ATTESTATION_CONFIGS


def test_regions_reference_valid_services():
    """All service IDs in regions exist in CONFIDENTIAL_OPTIONS."""
    option_ids = {o["id"] for o in CONFIDENTIAL_OPTIONS}
    for region in SUPPORTED_REGIONS:
        for svc in region["services"]:
            assert svc in option_ids, f"Unknown service '{svc}' in region '{region['name']}'"


def test_vm_sku_series_match_options():
    """VM SKU series appear in at least one CC option's vm_series."""
    option_series = set()
    for opt in CONFIDENTIAL_OPTIONS:
        option_series.update(opt["vm_series"])
    for sku in CONFIDENTIAL_VM_SKUS:
        assert sku["series"] in option_series, (
            f"SKU series '{sku['series']}' not referenced by any CC option"
        )
