"""Tests for architecture API routes."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_archetypes():
    r = client.get("/api/architecture/archetypes")
    assert r.status_code == 200
    assert "archetypes" in r.json()
    assert len(r.json()["archetypes"]) >= 3

def test_generate_with_archetype():
    answers = {"org_size": "small", "industry": "technology"}
    r = client.post("/api/architecture/generate", json={"answers": answers, "use_archetype": True})
    assert r.status_code == 200
    arch = r.json()["architecture"]
    assert "management_groups" in arch

def test_generate_with_ai():
    answers = {"org_size": "enterprise", "network_topology": "hub_spoke"}
    r = client.post("/api/architecture/generate", json={"answers": answers, "use_ai": True})
    assert r.status_code == 200
    assert "architecture" in r.json()

def test_generate_default_is_ai():
    answers = {"org_size": "medium"}
    r = client.post("/api/architecture/generate", json={"answers": answers})
    assert r.status_code == 200

def test_estimate_costs():
    arch = {"management_groups": [], "subscriptions": [{"name": "prod"}]}
    r = client.post("/api/architecture/estimate-costs", json={"architecture": arch})
    assert r.status_code == 200

def test_refine_architecture():
    arch = {"management_groups": [{"name": "root"}]}
    r = client.post("/api/architecture/refine", json={"architecture": arch, "message": "Add a sandbox subscription"})
    assert r.status_code == 200
    assert "response" in r.json()
