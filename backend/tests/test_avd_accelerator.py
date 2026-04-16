"""Tests for Azure Virtual Desktop accelerator services and API routes."""

from starlette.testclient import TestClient

from app.main import app
from app.services.avd_accelerator import (
    AVD_BEST_PRACTICES,
    AVD_QUESTIONS,
    AVD_REFERENCE_ARCHITECTURES,
    AVD_SKUS,
    avd_accelerator,
)
from app.services.avd_bicep import avd_bicep_service

client = TestClient(app)


# ── Service Unit Tests: Questions ────────────────────────────────────────────


def test_get_questions_returns_list():
    questions = avd_accelerator.get_questions()
    assert isinstance(questions, list)
    assert len(questions) >= 10


def test_get_questions_have_required_fields():
    questions = avd_accelerator.get_questions()
    for q in questions:
        assert "id" in q
        assert "category" in q
        assert "text" in q
        assert "type" in q
        assert "options" in q
        assert "required" in q
        assert "order" in q


def test_get_questions_have_unique_ids():
    questions = avd_accelerator.get_questions()
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids))


def test_questions_cover_all_required_topics():
    questions = avd_accelerator.get_questions()
    ids = {q["id"] for q in questions}
    required_ids = {
        "avd_user_count",
        "avd_user_type",
        "avd_application_type",
        "avd_fslogix_storage",
        "avd_image_management",
        "avd_authentication",
        "avd_desktop_type",
        "avd_geographic_distribution",
        "avd_scaling_behavior",
        "avd_printing",
    }
    assert required_ids.issubset(ids)


def test_questions_have_nonempty_options():
    for q in avd_accelerator.get_questions():
        assert len(q["options"]) >= 2, f"{q['id']} must have ≥2 options"


# ── Service Unit Tests: SKU Recommendations ──────────────────────────────────


def test_get_sku_recommendations_returns_list():
    skus = avd_accelerator.get_sku_recommendations()
    assert isinstance(skus, list)
    assert len(skus) >= 1


def test_sku_recommendations_default_no_gpu():
    skus = avd_accelerator.get_sku_recommendations()
    for s in skus:
        assert s["gpu"] is False


def test_sku_recommendations_cad_returns_gpu():
    skus = avd_accelerator.get_sku_recommendations(
        user_type="developer", application_type="cad_3d"
    )
    assert len(skus) >= 1
    for s in skus:
        assert s["gpu"] is True


def test_sku_recommendations_task_worker():
    skus = avd_accelerator.get_sku_recommendations(
        user_type="task_worker", application_type="web_apps"
    )
    assert len(skus) >= 1
    for s in skus:
        assert "recommended_users" in s
        assert s["recommended_users"] > 0


def test_sku_recommendations_sorted_descending():
    skus = avd_accelerator.get_sku_recommendations(
        user_type="knowledge_worker"
    )
    users = [s["recommended_users"] for s in skus]
    assert users == sorted(users, reverse=True)


def test_sku_data_has_required_fields():
    for sku in AVD_SKUS:
        assert "name" in sku
        assert "series" in sku
        assert "family" in sku
        assert "vcpus" in sku
        assert "memory_gb" in sku
        assert "gpu" in sku
        assert "users_per_vm" in sku


def test_sku_families():
    families = {s["family"] for s in AVD_SKUS}
    assert "general_purpose" in families
    assert "memory_optimized" in families
    assert "gpu" in families


def test_sku_vcpus_positive():
    for sku in AVD_SKUS:
        assert sku["vcpus"] > 0
        assert sku["memory_gb"] > 0


# ── Service Unit Tests: Architecture Generation ──────────────────────────────


def test_generate_architecture_default():
    arch = avd_accelerator.generate_architecture({})
    assert "host_pool" in arch
    assert "session_hosts" in arch
    assert "fslogix" in arch
    assert "workspace" in arch
    assert "app_groups" in arch
    assert "network" in arch
    assert "monitoring" in arch
    assert "image_management" in arch
    assert "conditional_access" in arch


def test_generate_architecture_pooled():
    arch = avd_accelerator.generate_architecture(
        {"avd_desktop_type": "multi_session"}
    )
    assert arch["host_pool"]["type"] == "Pooled"
    assert arch["host_pool"]["load_balancer_type"] == "BreadthFirst"
    app_types = [g["type"] for g in arch["app_groups"]]
    assert "RemoteApp" in app_types


def test_generate_architecture_personal():
    arch = avd_accelerator.generate_architecture(
        {"avd_desktop_type": "personal"}
    )
    assert arch["host_pool"]["type"] == "Personal"
    assert arch["host_pool"]["load_balancer_type"] == "Persistent"


def test_generate_architecture_gpu_sku():
    arch = avd_accelerator.generate_architecture(
        {
            "avd_application_type": "cad_3d",
            "avd_user_type": "developer",
        }
    )
    assert "NV" in arch["session_hosts"]["vm_sku"]


def test_generate_architecture_fslogix_storage():
    arch = avd_accelerator.generate_architecture(
        {"avd_fslogix_storage": "azure_netapp_files"}
    )
    assert arch["fslogix"]["storage_type"] == "azure_netapp_files"


def test_generate_architecture_monitoring():
    arch = avd_accelerator.generate_architecture(
        {"avd_monitoring": "avd_insights"}
    )
    assert arch["monitoring"]["avd_insights"] is True


def test_generate_architecture_printing():
    arch = avd_accelerator.generate_architecture(
        {"avd_printing": "universal_print"}
    )
    assert arch["printing"]["method"] == "universal_print"


# ── Service Unit Tests: Best Practices ───────────────────────────────────────


def test_get_best_practices_returns_list():
    bp = avd_accelerator.get_best_practices()
    assert isinstance(bp, list)
    assert len(bp) >= 5


def test_best_practices_have_required_fields():
    for bp in AVD_BEST_PRACTICES:
        assert "id" in bp
        assert "title" in bp
        assert "description" in bp
        assert "category" in bp
        assert "severity" in bp


def test_best_practices_unique_ids():
    ids = [bp["id"] for bp in AVD_BEST_PRACTICES]
    assert len(ids) == len(set(ids))


# ── Service Unit Tests: Sizing ───────────────────────────────────────────────


def test_estimate_sizing_default():
    sz = avd_accelerator.estimate_sizing({})
    assert sz["session_host_count"] >= 2
    assert sz["users_per_host"] > 0
    assert sz["recommended_sku"] != ""
    assert sz["total_users"] > 0
    assert sz["storage_gb"] > 0


def test_estimate_sizing_small():
    sz = avd_accelerator.estimate_sizing(
        {"user_count": "10-50", "user_type": "task_worker"}
    )
    assert sz["total_users"] == 30
    assert sz["session_host_count"] >= 2


def test_estimate_sizing_large():
    sz = avd_accelerator.estimate_sizing(
        {"user_count": "1000+", "user_type": "knowledge_worker"}
    )
    assert sz["total_users"] == 1500
    assert sz["session_host_count"] >= 100


def test_estimate_sizing_developer():
    sz = avd_accelerator.estimate_sizing(
        {"user_count": "50-200", "user_type": "developer"}
    )
    assert "NV" in sz["recommended_sku"]


# ── Service Unit Tests: Validation ───────────────────────────────────────────


def test_validate_architecture_valid():
    arch = avd_accelerator.generate_architecture({})
    result = avd_accelerator.validate_architecture(arch)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_architecture_missing_host_pool():
    result = avd_accelerator.validate_architecture({})
    assert result["valid"] is False
    assert any("host_pool" in e for e in result["errors"])


def test_validate_architecture_invalid_pool_type():
    result = avd_accelerator.validate_architecture(
        {
            "host_pool": {"type": "Invalid"},
            "session_hosts": {"count": 2},
            "fslogix": {},
            "network": {"nsg_enabled": True, "private_endpoints": True},
        }
    )
    assert result["valid"] is False


def test_validate_architecture_warnings():
    result = avd_accelerator.validate_architecture(
        {
            "host_pool": {"type": "Pooled"},
            "session_hosts": {"count": 1},
            "fslogix": {},
            "network": {"nsg_enabled": False, "private_endpoints": False},
        }
    )
    assert result["valid"] is True
    assert len(result["warnings"]) >= 2


# ── Service Unit Tests: Reference Architectures ─────────────────────────────


def test_get_reference_architectures_returns_three():
    refs = avd_accelerator.get_reference_architectures()
    assert len(refs) == 3


def test_reference_architectures_have_required_fields():
    for ref in AVD_REFERENCE_ARCHITECTURES:
        assert "id" in ref
        assert "name" in ref
        assert "description" in ref
        assert "host_pool_type" in ref
        assert "vm_sku" in ref
        assert "components" in ref


def test_reference_architectures_unique_ids():
    ids = [r["id"] for r in AVD_REFERENCE_ARCHITECTURES]
    assert len(ids) == len(set(ids))


def test_reference_architectures_include_expected():
    ids = {r["id"] for r in AVD_REFERENCE_ARCHITECTURES}
    assert "small_team" in ids
    assert "enterprise_pooled" in ids
    assert "developer_personal" in ids


# ── Bicep Service Tests ──────────────────────────────────────────────────────


def test_bicep_host_pool():
    tpl = avd_bicep_service.generate_host_pool({})
    assert "Microsoft.DesktopVirtualization/hostPools" in tpl
    assert "hostPoolType" in tpl


def test_bicep_session_hosts():
    tpl = avd_bicep_service.generate_session_hosts({"count": 3})
    assert "Microsoft.Compute/virtualMachines" in tpl
    assert "vmCount int = 3" in tpl


def test_bicep_workspace():
    tpl = avd_bicep_service.generate_workspace({"name": "ws1"})
    assert "Microsoft.DesktopVirtualization/workspaces" in tpl


def test_bicep_app_group():
    tpl = avd_bicep_service.generate_app_group({"group_type": "RemoteApp"})
    assert "applicationGroupType: 'RemoteApp'" in tpl


def test_bicep_storage():
    tpl = avd_bicep_service.generate_storage({})
    assert "Microsoft.Storage/storageAccounts" in tpl
    assert "FileStorage" in tpl


def test_bicep_networking():
    tpl = avd_bicep_service.generate_networking({})
    assert "Microsoft.Network/virtualNetworks" in tpl
    assert "SessionHosts" in tpl
    assert "PrivateEndpoints" in tpl


def test_bicep_full_stack():
    tpl = avd_bicep_service.generate_full_avd_stack({})
    assert "targetScope = 'resourceGroup'" in tpl
    assert "Microsoft.DesktopVirtualization/hostPools" in tpl
    assert "Microsoft.Compute/virtualMachines" in tpl
    assert "Microsoft.Storage/storageAccounts" in tpl
    assert "Microsoft.OperationalInsights/workspaces" in tpl


def test_bicep_full_stack_custom_config():
    tpl = avd_bicep_service.generate_full_avd_stack(
        {
            "name_prefix": "prod",
            "location": "westus2",
            "pool_type": "Personal",
            "vm_sku": "Standard_E8s_v5",
            "host_count": 5,
        }
    )
    assert "'Personal'" in tpl
    assert "Standard_E8s_v5" in tpl
    assert "westus2" in tpl


# ── API Route Tests ──────────────────────────────────────────────────────────

AUTH_HEADERS = {"Authorization": "Bearer test"}


def test_api_get_questions():
    resp = client.get(
        "/api/accelerators/avd/questions", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 10


def test_api_get_sku_recommendations():
    resp = client.post(
        "/api/accelerators/avd/sku-recommendations",
        json={
            "user_type": "knowledge_worker",
            "application_type": "office_productivity",
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_api_generate_architecture():
    resp = client.post(
        "/api/accelerators/avd/architecture",
        json={"answers": {"avd_desktop_type": "multi_session"}},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    arch = resp.json()["architecture"]
    assert "host_pool" in arch


def test_api_get_best_practices():
    resp = client.get(
        "/api/accelerators/avd/best-practices",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5


def test_api_estimate_sizing():
    resp = client.post(
        "/api/accelerators/avd/sizing",
        json={"requirements": {"user_count": "200-1000"}},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_host_count"] > 0


def test_api_validate_architecture():
    arch = avd_accelerator.generate_architecture({})
    resp = client.post(
        "/api/accelerators/avd/validate",
        json={"architecture": arch},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_api_get_reference_architectures():
    resp = client.get(
        "/api/accelerators/avd/reference-architectures",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3


def test_api_generate_bicep():
    resp = client.post(
        "/api/accelerators/avd/bicep",
        json={"template_type": "host_pool", "config": {}},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_type"] == "host_pool"
    assert "hostPool" in data["bicep_template"]


def test_api_generate_bicep_invalid_type():
    resp = client.post(
        "/api/accelerators/avd/bicep",
        json={"template_type": "invalid_type", "config": {}},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400
