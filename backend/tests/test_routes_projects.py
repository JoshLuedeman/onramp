"""Tests for project API routes."""
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app

client = TestClient(app)

def test_list_projects():
    r = client.get("/api/projects/")
    assert r.status_code == 200
    assert "projects" in r.json()

def test_create_project():
    r = client.post("/api/projects/", json={"name": "Test Project", "description": "A test"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Project"
    assert "id" in data

def test_create_project_minimal():
    r = client.post("/api/projects/", json={"name": "Minimal"})
    assert r.status_code == 201


def test_create_project_has_status():
    r = client.post("/api/projects/", json={"name": "With Status", "description": "desc"})
    assert r.status_code == 201
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


def test_get_project_stats():
    """GET /api/projects/stats returns stats with total and by_status."""
    r = client.get("/api/projects/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "by_status" in data
    assert isinstance(data["total"], int)
    assert isinstance(data["by_status"], dict)


def test_update_project():
    """PUT /api/projects/{id} returns updated project data."""
    r = client.put(
        "/api/projects/some-id",
        json={"status": "deployed"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "some-id"
    assert data["status"] == "deployed"


def test_create_and_list():
    """POST to create then GET list; list returns projects array."""
    create_resp = client.post(
        "/api/projects/", json={"name": "Integration Test"}
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["name"] == "Integration Test"

    list_resp = client.get("/api/projects/")
    assert list_resp.status_code == 200
    assert "projects" in list_resp.json()


# Additional sync tests for better coverage of mock branches


def test_update_project_with_name():
    """Update project with name change."""
    r = client.put("/api/projects/test-id", json={"name": "New Name"})
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


def test_update_project_with_description():
    """Update project with description."""
    r = client.put("/api/projects/test-id", json={"description": "New desc"})
    assert r.status_code == 200


def test_update_project_all_fields():
    """Update project with all fields."""
    r = client.put("/api/projects/test-id", json={
        "name": "Updated",
        "description": "Updated desc",
        "status": "architecture_generated"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "architecture_generated"


def test_update_project_invalid_status():
    """Update project with invalid status returns 422."""
    r = client.put("/api/projects/test-id", json={"status": "invalid_status"})
    assert r.status_code == 422


def test_stats_returns_zero_total():
    """Stats endpoint returns zero total in dev mode."""
    r = client.get("/api/projects/stats")
    data = r.json()
    assert data["total"] == 0
    assert data["avg_compliance_score"] is None
    assert data["deployment_success_rate"] is None


def test_stats_returns_empty_recent():
    """Stats endpoint returns empty recent_projects."""
    r = client.get("/api/projects/stats")
    data = r.json()
    assert data["recent_projects"] == []


def test_create_project_has_timestamps():
    """Created project has created_at and updated_at."""
    r = client.post("/api/projects/", json={"name": "Timestamps Test"})
    data = r.json()
    assert "created_at" in data
    assert "updated_at" in data


def test_update_project_has_timestamps():
    """Updated project response has timestamps."""
    r = client.put("/api/projects/test-id", json={"name": "TS Test"})
    data = r.json()
    assert "created_at" in data
    assert "updated_at" in data


def test_update_project_no_fields():
    """Update with empty body still returns 200."""
    r = client.put("/api/projects/test-id", json={})
    assert r.status_code == 200


# Async tests


@pytest.mark.asyncio
async def test_list_projects_async():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/projects/")
        assert r.status_code == 200
        assert "projects" in r.json()


@pytest.mark.asyncio
async def test_create_project_async():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/projects/", json={"name": "Async Project"})
        assert r.status_code == 201
        assert r.json()["name"] == "Async Project"


@pytest.mark.asyncio
async def test_stats_async():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/projects/stats")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_update_project_status_values():
    """Test all valid status values."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for status in [
            "draft", "questionnaire_complete", "architecture_generated",
            "compliance_scored", "bicep_ready", "deploying", "deployed", "failed",
        ]:
            r = await ac.put(
                f"/api/projects/test-{status}", json={"status": status}
            )
            assert r.status_code == 200
            assert r.json()["status"] == status


@pytest.mark.asyncio
async def test_delete_project_async():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.delete("/api/projects/async-delete-id")
        assert r.status_code == 200
        assert r.json()["deleted"] is True


@pytest.mark.asyncio
async def test_get_project_not_found_async():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/projects/nonexistent")
        assert r.status_code == 404
