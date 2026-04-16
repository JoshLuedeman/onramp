"""Tests for the AI/ML landing zone accelerator.

Covers the AiMlAccelerator service, AiMlBicepService and the
/api/accelerators/aiml/* API routes.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.aiml_accelerator import AiMlAccelerator, aiml_accelerator
from app.services.aiml_bicep import AiMlBicepService, aiml_bicep_service

client = TestClient(app)


# =====================================================================
# AiMlAccelerator – Questions
# =====================================================================


def test_get_questions_returns_list():
    questions = aiml_accelerator.get_questions()
    assert isinstance(questions, list)
    assert len(questions) >= 10


def test_questions_have_required_keys():
    for q in aiml_accelerator.get_questions():
        assert "id" in q
        assert "text" in q
        assert "type" in q
        assert "category" in q


def test_questions_include_workload_type():
    ids = [q["id"] for q in aiml_accelerator.get_questions()]
    assert "ml_workload_type" in ids


def test_questions_include_gpu_requirements():
    ids = [q["id"] for q in aiml_accelerator.get_questions()]
    assert "gpu_requirements" in ids


def test_questions_include_framework():
    ids = [q["id"] for q in aiml_accelerator.get_questions()]
    assert "ml_framework" in ids


def test_questions_include_responsible_ai():
    ids = [q["id"] for q in aiml_accelerator.get_questions()]
    assert "responsible_ai" in ids


def test_questions_independent_copy():
    q1 = aiml_accelerator.get_questions()
    q2 = aiml_accelerator.get_questions()
    assert q1 is not q2


# =====================================================================
# AiMlAccelerator – SKU Recommendations
# =====================================================================


def test_get_all_skus():
    skus = aiml_accelerator.get_sku_recommendations({})
    assert isinstance(skus, list)
    assert len(skus) >= 8


def test_filter_skus_by_gpu_type():
    skus = aiml_accelerator.get_sku_recommendations({"gpu_type": "A100"})
    assert all(s["gpu_type"] == "A100" for s in skus)
    assert len(skus) >= 2


def test_filter_skus_by_family():
    skus = aiml_accelerator.get_sku_recommendations({"family": "ND"})
    assert all(s["family"] == "ND" for s in skus)


def test_filter_skus_by_price_tier():
    skus = aiml_accelerator.get_sku_recommendations(
        {"price_tier": "standard"}
    )
    assert all(s["price_tier"] == "standard" for s in skus)


def test_filter_skus_by_min_gpu_count():
    skus = aiml_accelerator.get_sku_recommendations({"min_gpu_count": 4})
    assert all(s["gpu_count"] >= 4 for s in skus)


def test_skus_sorted_by_gpu_memory_descending():
    skus = aiml_accelerator.get_sku_recommendations({})
    memories = [s["gpu_memory_gb"] for s in skus]
    assert memories == sorted(memories, reverse=True)


def test_no_matching_skus_returns_empty():
    skus = aiml_accelerator.get_sku_recommendations(
        {"gpu_type": "NONEXISTENT"}
    )
    assert skus == []


# =====================================================================
# AiMlAccelerator – Architecture Generation
# =====================================================================


def test_generate_architecture_basic():
    arch = aiml_accelerator.generate_architecture({
        "ml_workload_type": "training",
        "gpu_requirements": "single",
        "data_volume": "medium",
    })
    assert "services" in arch
    assert "compute" in arch
    assert "storage" in arch
    assert "networking" in arch


def test_architecture_includes_ml_workspace():
    arch = aiml_accelerator.generate_architecture({})
    svc_names = [s["name"] for s in arch["services"]]
    assert any("Machine Learning" in n for n in svc_names)


def test_architecture_includes_key_vault():
    arch = aiml_accelerator.generate_architecture({})
    svc_names = [s["name"] for s in arch["services"]]
    assert any("Key Vault" in n for n in svc_names)


def test_architecture_inference_adds_endpoint():
    arch = aiml_accelerator.generate_architecture({
        "ml_workload_type": "inference",
        "realtime_inference": True,
    })
    assert "inference_cluster" in arch["compute"]


def test_architecture_optional_databricks():
    arch = aiml_accelerator.generate_architecture({
        "optional_services": ["databricks"],
    })
    opt_names = [s["name"] for s in arch["optional_services"]]
    assert "Azure Databricks" in opt_names


def test_architecture_optional_openai():
    arch = aiml_accelerator.generate_architecture({
        "optional_services": ["openai"],
    })
    opt_names = [s["name"] for s in arch["optional_services"]]
    assert "Azure OpenAI Service" in opt_names


def test_architecture_responsible_ai_flags():
    arch = aiml_accelerator.generate_architecture({
        "responsible_ai": ["fairness", "explainability"],
    })
    rai = arch["responsible_ai"]
    assert rai["fairness"] is True
    assert rai["explainability"] is True
    assert rai["privacy"] is False


def test_architecture_private_endpoints_enabled():
    arch = aiml_accelerator.generate_architecture({})
    assert arch["networking"]["private_endpoints"] is True


def test_architecture_multi_node_cluster():
    arch = aiml_accelerator.generate_architecture({
        "gpu_requirements": "multi_node",
    })
    cluster = arch["compute"]["training_cluster"]
    assert cluster["vm_size"] == "Standard_ND96asr_v4"
    assert cluster["max_nodes"] == 8


# =====================================================================
# AiMlAccelerator – Best Practices
# =====================================================================


def test_best_practices_returns_list():
    bps = aiml_accelerator.get_best_practices()
    assert isinstance(bps, list)
    assert len(bps) >= 5


def test_best_practices_have_required_keys():
    for bp in aiml_accelerator.get_best_practices():
        assert "id" in bp
        assert "title" in bp
        assert "category" in bp
        assert "priority" in bp
        assert "description" in bp


# =====================================================================
# AiMlAccelerator – Sizing Estimation
# =====================================================================


def test_sizing_no_gpu():
    sizing = aiml_accelerator.estimate_sizing({
        "gpu_requirements": "none"
    })
    assert sizing["compute_sku"] == "Standard_DS3_v2"
    assert sizing["gpu_nodes_max"] == 0


def test_sizing_single_gpu():
    sizing = aiml_accelerator.estimate_sizing({
        "gpu_requirements": "single"
    })
    assert "NC4as_T4_v3" in sizing["compute_sku"]


def test_sizing_multi_gpu():
    sizing = aiml_accelerator.estimate_sizing({
        "gpu_requirements": "multi_gpu"
    })
    assert "A100" in sizing["compute_sku"]


def test_sizing_large_storage():
    sizing = aiml_accelerator.estimate_sizing({
        "data_volume": "large"
    })
    assert sizing["storage_gb"] >= 4096
    assert sizing["storage_tier"] == "Premium_LRS"


def test_sizing_enterprise_team():
    sizing = aiml_accelerator.estimate_sizing({
        "team_size": "enterprise"
    })
    assert sizing["compute_instances"] >= 20


def test_sizing_has_cost_estimate():
    sizing = aiml_accelerator.estimate_sizing({
        "gpu_requirements": "single",
        "data_volume": "medium",
        "team_size": "small",
    })
    assert "estimated_monthly_cost_usd" in sizing
    assert sizing["estimated_monthly_cost_usd"] > 0


# =====================================================================
# AiMlAccelerator – Validation
# =====================================================================


def test_validate_valid_architecture():
    result = aiml_accelerator.validate_architecture({
        "services": [
            {"name": "Azure Machine Learning Workspace"},
            {"name": "Storage Account (ADLS Gen2)"},
            {"name": "Key Vault"},
            {"name": "Container Registry"},
        ],
        "networking": {"private_endpoints": True},
        "monitoring": {"application_insights": True},
        "compute": {"training_cluster": {"vm_size": "NC4as_T4_v3"}},
    })
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_missing_ml_workspace():
    result = aiml_accelerator.validate_architecture({
        "services": [{"name": "Storage Account"}],
    })
    assert result["valid"] is False
    assert any("Machine Learning" in e for e in result["errors"])


def test_validate_missing_storage():
    result = aiml_accelerator.validate_architecture({
        "services": [{"name": "Azure Machine Learning Workspace"}],
    })
    assert result["valid"] is False
    assert any("Storage" in e for e in result["errors"])


def test_validate_warnings_for_no_key_vault():
    result = aiml_accelerator.validate_architecture({
        "services": [
            {"name": "Azure Machine Learning Workspace"},
            {"name": "Storage Account"},
        ],
    })
    assert any("Key Vault" in w for w in result["warnings"])


def test_validate_suggestions_for_no_monitoring():
    result = aiml_accelerator.validate_architecture({
        "services": [
            {"name": "Azure Machine Learning Workspace"},
            {"name": "Storage Account"},
            {"name": "Key Vault"},
        ],
        "monitoring": {},
    })
    assert any("Application Insights" in s for s in result["suggestions"])


# =====================================================================
# AiMlAccelerator – Reference Architectures
# =====================================================================


def test_reference_architectures_count():
    archs = aiml_accelerator.get_reference_architectures()
    assert len(archs) == 3


def test_reference_architectures_ids():
    ids = {a["id"] for a in aiml_accelerator.get_reference_architectures()}
    assert ids == {"small_team", "enterprise_training", "realtime_inference"}


def test_reference_architecture_has_services():
    for arch in aiml_accelerator.get_reference_architectures():
        assert len(arch["services"]) >= 3
        assert "name" in arch
        assert "estimated_monthly_cost_usd" in arch


# =====================================================================
# AiMlAccelerator – Singleton
# =====================================================================


def test_singleton_is_instance():
    assert isinstance(aiml_accelerator, AiMlAccelerator)


# =====================================================================
# AiMlBicepService – ML Workspace
# =====================================================================


def test_bicep_ml_workspace_contains_resource():
    bicep = aiml_bicep_service.generate_ml_workspace({})
    assert "Microsoft.MachineLearningServices" in bicep
    assert "workspaceName" in bicep


def test_bicep_ml_workspace_custom_name():
    bicep = aiml_bicep_service.generate_ml_workspace(
        {"name": "my-ml-ws", "location": "westus2"}
    )
    assert "my-ml-ws" in bicep
    assert "westus2" in bicep


def test_bicep_ml_workspace_private_endpoint():
    bicep = aiml_bicep_service.generate_ml_workspace(
        {"private_endpoint": True}
    )
    assert "privateEndpoints" in bicep


def test_bicep_ml_workspace_no_private_endpoint():
    bicep = aiml_bicep_service.generate_ml_workspace(
        {"private_endpoint": False}
    )
    assert "privateEndpoints" not in bicep


# =====================================================================
# AiMlBicepService – Compute Cluster
# =====================================================================


def test_bicep_compute_cluster_contains_resource():
    bicep = aiml_bicep_service.generate_compute_cluster({})
    assert "AmlCompute" in bicep
    assert "vmSize" in bicep


def test_bicep_compute_cluster_custom_config():
    bicep = aiml_bicep_service.generate_compute_cluster({
        "cluster_name": "train-gpu",
        "vm_size": "Standard_NC24ads_A100_v4",
        "max_nodes": 8,
    })
    assert "train-gpu" in bicep
    assert "Standard_NC24ads_A100_v4" in bicep
    assert "maxNodeCount: 8" in bicep


# =====================================================================
# AiMlBicepService – Full Stack
# =====================================================================


def test_bicep_full_stack_includes_workspace_and_cluster():
    bicep = aiml_bicep_service.generate_full_aiml_stack({})
    assert "MachineLearningServices" in bicep
    assert "AmlCompute" in bicep
    assert "targetScope" in bicep


def test_bicep_full_stack_with_databricks():
    bicep = aiml_bicep_service.generate_full_aiml_stack(
        {"include_databricks": True}
    )
    assert "Databricks" in bicep


def test_bicep_full_stack_without_databricks():
    bicep = aiml_bicep_service.generate_full_aiml_stack(
        {"include_databricks": False}
    )
    assert "Databricks" not in bicep


def test_bicep_service_singleton():
    assert isinstance(aiml_bicep_service, AiMlBicepService)


# =====================================================================
# API Routes – /api/accelerators/aiml/*
# =====================================================================


def test_api_get_questions():
    response = client.get("/api/accelerators/aiml/questions")
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert len(data["questions"]) >= 10


def test_api_get_skus():
    response = client.get("/api/accelerators/aiml/skus")
    assert response.status_code == 200
    data = response.json()
    assert "skus" in data
    assert data["count"] >= 8


def test_api_get_skus_filter_gpu_type():
    response = client.get("/api/accelerators/aiml/skus?gpu_type=A100")
    assert response.status_code == 200
    data = response.json()
    assert all(s["gpu_type"] == "A100" for s in data["skus"])


def test_api_generate_architecture():
    response = client.post(
        "/api/accelerators/aiml/architecture",
        json={"answers": {"ml_workload_type": "training"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "architecture" in data


def test_api_estimate_sizing():
    response = client.post(
        "/api/accelerators/aiml/sizing",
        json={"requirements": {"gpu_requirements": "single"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "sizing" in data
    assert data["sizing"]["compute_sku"] is not None


def test_api_get_best_practices():
    response = client.get("/api/accelerators/aiml/best-practices")
    assert response.status_code == 200
    data = response.json()
    assert "best_practices" in data
    assert len(data["best_practices"]) >= 5


def test_api_generate_bicep_full():
    response = client.post(
        "/api/accelerators/aiml/bicep",
        json={"template_type": "full_stack", "config": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "bicep" in data
    assert data["template_type"] == "full_stack"


def test_api_generate_bicep_workspace():
    response = client.post(
        "/api/accelerators/aiml/bicep",
        json={"template_type": "ml_workspace", "config": {}},
    )
    assert response.status_code == 200
    assert "MachineLearningServices" in response.json()["bicep"]


def test_api_generate_bicep_compute():
    response = client.post(
        "/api/accelerators/aiml/bicep",
        json={
            "template_type": "compute_cluster",
            "config": {"vm_size": "Standard_NC24ads_A100_v4"},
        },
    )
    assert response.status_code == 200
    assert "AmlCompute" in response.json()["bicep"]


def test_api_get_reference_architectures():
    response = client.get(
        "/api/accelerators/aiml/reference-architectures"
    )
    assert response.status_code == 200
    data = response.json()
    assert "reference_architectures" in data
    assert len(data["reference_architectures"]) == 3


def test_api_validate_valid():
    response = client.post(
        "/api/accelerators/aiml/validate",
        json={
            "architecture": {
                "services": [
                    {"name": "Azure Machine Learning Workspace"},
                    {"name": "Storage Account"},
                    {"name": "Key Vault"},
                    {"name": "Container Registry"},
                ],
                "networking": {"private_endpoints": True},
                "monitoring": {"application_insights": True},
                "compute": {"training_cluster": {}},
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_api_validate_invalid():
    response = client.post(
        "/api/accelerators/aiml/validate",
        json={"architecture": {"services": []}},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert len(response.json()["errors"]) > 0
