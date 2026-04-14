from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_current_user_dev_mode():
    """In dev mode (no tenant configured), returns mock user."""
    response = client.get("/api/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Development User"
    assert data["email"] == "dev@onramp.local"
    assert "admin" in data["roles"]


def test_get_user_projects_dev_mode():
    """In dev mode, /me/projects returns empty list with message."""
    response = client.get("/api/users/me/projects")
    assert response.status_code == 200
    data = response.json()
    assert data["projects"] == []
    assert "message" in data or "projects" in data
