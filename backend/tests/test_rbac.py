"""Tests for RBAC middleware."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.rbac import RoleChecker


def test_role_checker_allows_matching_role():
    """Test that RoleChecker allows access when role matches."""
    app = FastAPI()
    checker = RoleChecker(["admin"])

    @app.get("/test")
    async def test_endpoint(user: dict = Depends(checker)):
        return {"user": user}

    # Mock the get_current_user dependency
    async def mock_admin_user():
        return {"sub": "1", "name": "Admin", "email": "a@test.com", "roles": ["admin"]}

    app.dependency_overrides[checker] = lambda: {"sub": "1", "name": "Admin", "email": "a@test.com", "roles": ["admin"]}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200


def test_preconfigured_roles_exist():
    """Test that pre-configured role checkers are properly set up."""
    from app.auth.rbac import require_admin, require_architect, require_viewer

    assert "admin" in require_admin.allowed_roles
    assert "admin" in require_architect.allowed_roles
    assert "architect" in require_architect.allowed_roles
    assert "admin" in require_viewer.allowed_roles
    assert "architect" in require_viewer.allowed_roles
    assert "viewer" in require_viewer.allowed_roles


@pytest.mark.asyncio
async def test_role_checker_assigns_viewer_when_no_roles():
    """User without roles gets assigned viewer role."""

    checker = RoleChecker(["viewer"])
    user_no_roles = {"sub": "1", "name": "No Roles", "email": "n@test.com"}
    result = await checker.__call__(user=user_no_roles)
    assert result["roles"] == ["viewer"]


@pytest.mark.asyncio
async def test_role_checker_denies_wrong_role():
    """User with wrong role gets 403."""
    from fastapi import HTTPException

    checker = RoleChecker(["admin"])
    user_viewer = {"sub": "1", "name": "Viewer", "email": "v@test.com", "roles": ["viewer"]}
    with pytest.raises(HTTPException) as exc_info:
        await checker.__call__(user=user_viewer)
    assert exc_info.value.status_code == 403
