"""Tests for project API routes."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_projects():
    r = client.get("/api/projects/")
    assert r.status_code == 200
    assert "projects" in r.json()

def test_create_project():
    r = client.post("/api/projects/", json={"name": "Test Project", "description": "A test"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Project"
    assert "id" in data

def test_create_project_minimal():
    r = client.post("/api/projects/", json={"name": "Minimal"})
    assert r.status_code == 200


def test_create_project_has_status():
    r = client.post("/api/projects/", json={"name": "With Status", "description": "desc"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "draft"


def test_create_project_in_memory_message():
    """In dev mode without DB, response includes in-memory message."""
    r = client.post("/api/projects/", json={"name": "Dev Project"})
    data = r.json()
    assert "id" in data
    assert data["name"] == "Dev Project"


def test_get_project_no_db():
    """GET by ID returns 404 when DB is not configured."""
    r = client.get("/api/projects/nonexistent-id")
    assert r.status_code == 404


def test_delete_project_no_db():
    """DELETE returns success when DB is not configured."""
    r = client.delete("/api/projects/some-id")
    assert r.status_code == 200
    data = r.json()
    assert data["deleted"] is True


def test_list_projects_returns_empty_in_dev():
    """In dev mode, list returns empty projects array."""
    r = client.get("/api/projects/")
    data = r.json()
    assert data["projects"] == []


def test_create_project_missing_name():
    """Create without name returns 422."""
    r = client.post("/api/projects/", json={"description": "no name"})
    assert r.status_code == 422
