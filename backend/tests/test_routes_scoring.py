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


def test_evaluate_with_project_id():
    """Evaluate with project_id — tests the persist branch (no DB in dev)."""
    arch = {"management_groups": [{"name": "root"}], "policies": {"budget_alerts": True}}
    r = client.post("/api/scoring/evaluate", json={
        "architecture": arch,
        "frameworks": ["SOC2"],
        "use_ai": False,
        "project_id": "proj-score-1",
    })
    assert r.status_code == 200
    assert "overall_score" in r.json()


def test_get_project_scoring_no_db():
    """Fetch project scoring results returns empty in dev mode."""
    r = client.get("/api/scoring/project/nonexistent-proj")
    assert r.status_code == 200
    data = r.json()
    assert data["results"] == []
    assert data["project_id"] == "nonexistent-proj"


def test_evaluate_empty_architecture():
    """Evaluate with empty architecture still returns a result."""
    r = client.post("/api/scoring/evaluate", json={
        "architecture": {},
        "frameworks": ["SOC2"],
        "use_ai": False,
    })
    assert r.status_code == 200
    assert "overall_score" in r.json()


def test_evaluate_missing_frameworks():
    """Evaluate without frameworks returns 422."""
    r = client.post("/api/scoring/evaluate", json={"architecture": {}})
    assert r.status_code == 422
