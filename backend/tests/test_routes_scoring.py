"""Tests for scoring API routes."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_evaluate_compliance():
    arch = {"management_groups": [{"name": "root"}], "policies": {"budget_alerts": True}}
    r = client.post("/api/scoring/evaluate", json={"architecture": arch, "frameworks": ["SOC2"]})
    assert r.status_code == 200
    data = r.json()
    assert "overall_score" in data

def test_evaluate_multiple_frameworks():
    arch = {"management_groups": [{"name": "root"}], "policies": {}}
    r = client.post("/api/scoring/evaluate", json={"architecture": arch, "frameworks": ["SOC2", "HIPAA"]})
    assert r.status_code == 200

def test_evaluate_no_ai():
    arch = {"management_groups": [], "policies": {}}
    r = client.post("/api/scoring/evaluate", json={"architecture": arch, "frameworks": ["SOC2"], "use_ai": False})
    assert r.status_code == 200

def test_evaluate_unknown_framework():
    arch = {"management_groups": []}
    r = client.post("/api/scoring/evaluate", json={"architecture": arch, "frameworks": ["NONEXISTENT"], "use_ai": False})
    assert r.status_code == 200
    assert r.json()["overall_score"] == 0
