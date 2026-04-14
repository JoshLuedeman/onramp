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


def test_get_valid_template():
    """Fetch a known template by name."""
    r = client.get("/api/bicep/templates")
    templates = r.json()["templates"]
    if templates:
        name = templates[0]["name"].replace(".bicep", "")
        r2 = client.get(f"/api/bicep/templates/{name}")
        assert r2.status_code == 200
        assert "content" in r2.json()


def test_generate_bicep_with_project_id():
    """Generate bicep with project_id — tests the persist branch (no DB in dev)."""
    arch = {"management_groups": [{"name": "root", "children": []}], "subscriptions": []}
    r = client.post("/api/bicep/generate", json={
        "architecture": arch,
        "use_ai": False,
        "project_id": "proj-bicep-1",
    })
    assert r.status_code == 200
    assert "files" in r.json()


def test_get_project_bicep_files_no_db():
    """Fetch project bicep files returns empty in dev mode (no DB)."""
    r = client.get("/api/bicep/project/nonexistent-proj")
    assert r.status_code == 200
    assert r.json()["files"] == []
    assert r.json()["project_id"] == "nonexistent-proj"


def test_download_bicep_returns_bytes():
    """Download endpoint returns content."""
    arch = {"management_groups": [{"name": "root"}], "subscriptions": []}
    r = client.post("/api/bicep/download", json={"architecture": arch, "use_ai": False})
    assert r.status_code == 200
    assert len(r.content) > 0


def test_templates_returns_list():
    """Templates endpoint returns a list."""
    r = client.get("/api/bicep/templates")
    assert r.status_code == 200
    assert isinstance(r.json()["templates"], list)
