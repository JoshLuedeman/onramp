"""Tests for Bicep API routes."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_templates():
    r = client.get("/api/bicep/templates")
    assert r.status_code == 200
    assert "templates" in r.json()

def test_generate_bicep():
    arch = {"management_groups": [{"name": "root", "children": []}], "subscriptions": []}
    r = client.post("/api/bicep/generate", json={"architecture": arch})
    assert r.status_code == 200
    data = r.json()
    assert "files" in data
    assert "total_files" in data
    assert data["total_files"] > 0

def test_generate_bicep_no_ai():
    arch = {"management_groups": [{"name": "root", "children": []}], "subscriptions": []}
    r = client.post("/api/bicep/generate", json={"architecture": arch, "use_ai": False})
    assert r.status_code == 200

def test_download_bicep():
    arch = {"management_groups": [{"name": "root", "children": []}], "subscriptions": []}
    r = client.post("/api/bicep/download", json={"architecture": arch, "use_ai": False})
    assert r.status_code == 200
    assert "bicep" in r.headers.get("content-disposition", "").lower() or r.text != ""

def test_get_template_not_found():
    r = client.get("/api/bicep/templates/nonexistent")
    assert r.status_code == 404
