"""Tests for workload-extension, SKU and validation API routes."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Workload extension routes (/api/workloads/extensions)
# ---------------------------------------------------------------------------


def test_list_extensions():
    response = client.get("/api/workloads/extensions/")
    assert response.status_code == 200
    data = response.json()
    assert "extensions" in data
    assert len(data["extensions"]) >= 4


def test_get_extension_ai_ml():
    response = client.get("/api/workloads/extensions/ai_ml")
    assert response.status_code == 200
    data = response.json()
    assert data["workload_type"] == "ai_ml"
    assert "questions" in data
    assert "best_practices" in data


def test_get_extension_not_found():
    response = client.get("/api/workloads/extensions/nonexistent")
    assert response.status_code == 404


def test_get_questions_sap():
    response = client.get("/api/workloads/extensions/sap/questions")
    assert response.status_code == 200
    data = response.json()
    assert data["workload_type"] == "sap"
    assert len(data["questions"]) >= 2


def test_get_best_practices_avd():
    response = client.get("/api/workloads/extensions/avd/best-practices")
    assert response.status_code == 200
    data = response.json()
    assert data["workload_type"] == "avd"
    assert len(data["best_practices"]) >= 2


def test_validate_architecture_for_workload():
    response = client.post(
        "/api/workloads/extensions/ai_ml/validate",
        json={
            "architecture": {
                "services": [
                    {"name": "Azure Machine Learning"},
                    {"name": "Azure Storage"},
                ],
                "network_topology": {"private_endpoints": True},
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


def test_estimate_sizing_iot():
    response = client.post(
        "/api/workloads/extensions/iot/sizing",
        json={"requirements": {"device_count": "medium", "telemetry_frequency": "low"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "sizing" in data
    assert data["workload_type"] == "iot"


def test_get_questions_not_found():
    response = client.get("/api/workloads/extensions/nonexistent/questions")
    assert response.status_code == 404


def test_get_best_practices_not_found():
    response = client.get("/api/workloads/extensions/nonexistent/best-practices")
    assert response.status_code == 404


def test_estimate_sizing_not_found():
    response = client.post(
        "/api/workloads/extensions/nonexistent/sizing",
        json={"requirements": {}},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# SKU routes (/api/skus)
# ---------------------------------------------------------------------------


def test_list_compute_skus():
    response = client.get("/api/skus/compute")
    assert response.status_code == 200
    data = response.json()
    assert "skus" in data
    assert data["count"] >= 10


def test_list_compute_skus_filter_family():
    response = client.get("/api/skus/compute?family=N")
    assert response.status_code == 200
    data = response.json()
    assert all(s["family"] == "N" for s in data["skus"])


def test_list_storage_skus():
    response = client.get("/api/skus/storage")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 4


def test_list_database_skus():
    response = client.get("/api/skus/database")
    assert response.status_code == 200
    assert response.json()["count"] >= 5


def test_list_networking_skus():
    response = client.get("/api/skus/networking")
    assert response.status_code == 200
    assert response.json()["count"] >= 5


def test_recommend_sku():
    response = client.post(
        "/api/skus/recommend",
        json={"workload_type": "ai_ml", "requirements": {"gpu": True}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommended_sku" in data
    assert "reason" in data


def test_compare_skus():
    response = client.post(
        "/api/skus/compare",
        json={"sku_ids": ["b2s", "d4s_v5"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["skus"]) == 2


def test_validate_sku_availability():
    response = client.post(
        "/api/skus/validate",
        json={"sku": "Standard_D4s_v5", "region": "eastus", "cloud_env": "commercial"},
    )
    assert response.status_code == 200
    assert response.json()["available"] is True


# ---------------------------------------------------------------------------
# Validation routes (/api/validation)
# ---------------------------------------------------------------------------


def test_validate_architecture_full():
    response = client.post(
        "/api/validation/architecture",
        json={
            "architecture": {"region": "eastus", "resources": [], "network_topology": {}},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data


def test_validate_skus_endpoint():
    response = client.post(
        "/api/validation/skus",
        json={"architecture": {"resources": []}, "region": "eastus"},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_compliance_endpoint():
    response = client.post(
        "/api/validation/compliance",
        json={
            "architecture": {
                "security": {
                    "encryption_at_rest": True,
                    "centralized_logging": True,
                    "mfa_enabled": True,
                },
            },
            "framework": "soc2",
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_networking_endpoint():
    response = client.post(
        "/api/validation/networking",
        json={"architecture": {"network_topology": {}}},
    )
    assert response.status_code == 200


def test_list_validation_rules():
    response = client.get("/api/validation/rules")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert len(data["rules"]) >= 8
