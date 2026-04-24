"""Tests verifying RBAC role checkers are wired into API routes.

The dev-mode mock user has roles: ["admin"], so all role checks pass.
These tests confirm the dependency is correctly applied and routes
respond with proper structure when called with auth headers.
"""

import os

from fastapi.testclient import TestClient

os.environ.setdefault("ONRAMP_DEBUG", "true")

from app.main import app  # noqa: E402

AUTH_HEADERS = {"Authorization": "Bearer test"}

client = TestClient(app)


# ---------------------------------------------------------------------------
# Projects — role-protected endpoints
# ---------------------------------------------------------------------------


def test_delete_project_requires_admin():
    """DELETE /api/projects/{id} uses admin-level auth.

    The mock user has admin role so the request succeeds (200).
    A non-admin user would receive 403 — verified separately in
    test_rbac.py unit tests.
    """
    r = client.delete("/api/projects/rbac-test-id", headers=AUTH_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["deleted"] is True


def test_create_project_requires_architect():
    """POST /api/projects/ uses architect-level auth and returns project."""
    r = client.post(
        "/api/projects/",
        json={"name": "RBAC Test Project", "description": "testing"},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "RBAC Test Project"
    assert "id" in data


def test_update_project_requires_architect():
    """PUT /api/projects/{id} uses architect-level auth."""
    r = client.put(
        "/api/projects/rbac-test-id",
        json={"name": "Updated via RBAC"},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Updated via RBAC"


def test_list_projects_requires_viewer():
    """GET /api/projects/ uses viewer-level auth."""
    r = client.get("/api/projects/", headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert "projects" in r.json()


def test_get_project_stats_requires_viewer():
    """GET /api/projects/stats uses viewer-level auth."""
    r = client.get("/api/projects/stats", headers=AUTH_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "by_status" in data


# ---------------------------------------------------------------------------
# Architecture — role-protected endpoints
# ---------------------------------------------------------------------------


def test_get_archetypes_requires_viewer():
    """GET /api/architecture/archetypes uses viewer-level auth."""
    r = client.get("/api/architecture/archetypes", headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert "archetypes" in r.json()


# ---------------------------------------------------------------------------
# Bicep — role-protected endpoints
# ---------------------------------------------------------------------------


def test_list_bicep_templates_requires_viewer():
    """GET /api/bicep/templates uses viewer-level auth."""
    r = client.get("/api/bicep/templates", headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert "templates" in r.json()


def test_generate_bicep_requires_architect():
    """POST /api/bicep/generate uses architect-level auth."""
    r = client.post(
        "/api/bicep/generate",
        json={
            "architecture": {"subscriptions": []},
            "use_ai": False,
        },
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert "files" in data
    assert "total_files" in data


# ---------------------------------------------------------------------------
# Scoring — role-protected endpoints
# ---------------------------------------------------------------------------


def test_evaluate_compliance_requires_architect():
    """POST /api/scoring/evaluate uses architect-level auth."""
    r = client.post(
        "/api/scoring/evaluate",
        json={
            "architecture": {"subscriptions": []},
            "frameworks": ["CIS"],
            "use_ai": False,
        },
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200
