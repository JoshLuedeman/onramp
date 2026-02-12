"""Tests for compliance framework data and API."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.compliance_data import (
    get_all_frameworks,
    get_framework_by_short_name,
    get_controls_for_frameworks,
)

client = TestClient(app)


def test_get_all_frameworks():
    frameworks = get_all_frameworks()
    assert len(frameworks) == 6
    names = [f["short_name"] for f in frameworks]
    assert "SOC2" in names
    assert "HIPAA" in names
    assert "PCI-DSS" in names
    assert "FedRAMP" in names
    assert "NIST-800-53" in names
    assert "ISO-27001" in names


def test_get_framework_by_name():
    fw = get_framework_by_short_name("HIPAA")
    assert fw is not None
    assert fw["name"] == "HIPAA"
    assert len(fw["controls"]) > 0


def test_get_framework_not_found():
    fw = get_framework_by_short_name("NONEXISTENT")
    assert fw is None


def test_get_controls_for_multiple_frameworks():
    controls = get_controls_for_frameworks(["SOC2", "HIPAA"])
    assert len(controls) > 0
    frameworks_in_controls = set(c["framework"] for c in controls)
    assert "SOC2" in frameworks_in_controls
    assert "HIPAA" in frameworks_in_controls


def test_api_list_frameworks():
    response = client.get("/api/compliance/frameworks")
    assert response.status_code == 200
    data = response.json()
    assert len(data["frameworks"]) == 6


def test_api_get_framework():
    response = client.get("/api/compliance/frameworks/SOC2")
    assert response.status_code == 200
    data = response.json()
    assert data["short_name"] == "SOC2"
    assert "controls" in data


def test_api_get_framework_not_found():
    response = client.get("/api/compliance/frameworks/NONEXISTENT")
    assert response.status_code == 404


def test_api_get_controls():
    response = client.post("/api/compliance/controls", json=["SOC2", "HIPAA"])
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
