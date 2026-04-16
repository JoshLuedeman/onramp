"""Tests for sovereign compliance and service availability API routes."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Framework Endpoints ──────────────────────────────────────────────────────


def test_list_frameworks():
    r = client.get("/api/sovereign/frameworks")
    assert r.status_code == 200
    data = r.json()
    assert "frameworks" in data
    assert data["total"] >= 6


def test_list_frameworks_has_expected_names():
    r = client.get("/api/sovereign/frameworks")
    names = {fw["short_name"] for fw in r.json()["frameworks"]}
    assert "FedRAMP_High" in names
    assert "MLPS_L3" in names


def test_get_framework_found():
    r = client.get("/api/sovereign/frameworks/FedRAMP_High")
    assert r.status_code == 200
    data = r.json()
    assert data["short_name"] == "FedRAMP_High"
    assert "control_families" in data
    assert data["total_controls"] > 0


def test_get_framework_not_found():
    r = client.get("/api/sovereign/frameworks/NONEXISTENT")
    assert r.status_code == 404


def test_get_framework_controls():
    r = client.get("/api/sovereign/frameworks/CMMC_L2/controls")
    assert r.status_code == 200
    data = r.json()
    assert data["framework"] == "CMMC_L2"
    assert len(data["controls"]) > 0


def test_get_framework_controls_not_found():
    r = client.get("/api/sovereign/frameworks/FAKE/controls")
    assert r.status_code == 404


def test_evaluate_compliance():
    arch = {
        "security": {"defender_enabled": True},
        "identity": {"mfa_policy": "all_users"},
    }
    r = client.post(
        "/api/sovereign/frameworks/FedRAMP_High/evaluate",
        json={"architecture": arch},
    )
    assert r.status_code == 200
    data = r.json()
    assert "overall_score" in data
    assert "family_scores" in data


def test_evaluate_compliance_empty_arch():
    r = client.post(
        "/api/sovereign/frameworks/FedRAMP_Moderate/evaluate",
        json={"architecture": {}},
    )
    assert r.status_code == 200
    assert r.json()["overall_score"] == 0


# ── Service Availability Endpoints ───────────────────────────────────────────


def test_list_services():
    r = client.get("/api/sovereign/services")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 30


def test_get_service_found():
    r = client.get("/api/sovereign/services/Key Vault")
    assert r.status_code == 200
    data = r.json()
    assert data["service_name"] == "Key Vault"


def test_get_service_not_found():
    r = client.get("/api/sovereign/services/FakeService")
    assert r.status_code == 404


def test_get_availability_matrix():
    r = client.get("/api/sovereign/services/matrix")
    assert r.status_code == 200
    data = r.json()
    assert "environments" in data
    assert "services" in data
    assert data["total_services"] >= 30


def test_check_compatibility_compatible():
    r = client.post(
        "/api/sovereign/services/check-compatibility",
        json={
            "architecture": {"services": ["Virtual Machines", "Key Vault"]},
            "target_environment": "commercial",
        },
    )
    assert r.status_code == 200
    assert r.json()["compatible"] is True


def test_check_compatibility_incompatible():
    r = client.post(
        "/api/sovereign/services/check-compatibility",
        json={
            "architecture": {"services": ["Container Apps"]},
            "target_environment": "china",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["compatible"] is False
    assert "Container Apps" in data["missing_services"]


def test_check_compatibility_returns_alternatives():
    r = client.post(
        "/api/sovereign/services/check-compatibility",
        json={
            "architecture": {"services": ["Container Apps"]},
            "target_environment": "china",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "Container Apps" in data["alternatives"]
