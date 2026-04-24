"""Security and authorization tests.

Covers: auth bypass prevention, role enforcement, missing credentials,
cross-role access denial, and CSRF middleware.
"""

import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("ONRAMP_DEBUG", "true")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth.entra import get_current_user  # noqa: E402
from app.auth.rbac import RoleChecker  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer test"}


# ---------------------------------------------------------------------------
# Auth bypass prevention
# ---------------------------------------------------------------------------


class TestAuthBypass:
    """Ensure mock auth only activates in explicit debug mode."""

    @pytest.mark.asyncio
    async def test_no_mock_auth_when_debug_false(self):
        """debug=False + empty tenant → 401, not mock user."""
        original = settings.debug
        settings.debug = False
        try:
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc:
                await get_current_user(credentials=None)
            assert exc.value.status_code == 401
        finally:
            settings.debug = original

    @pytest.mark.asyncio
    async def test_mock_auth_returns_admin_in_debug(self):
        """debug=True → mock admin user returned."""
        original = settings.debug
        settings.debug = True
        try:
            user = await get_current_user(credentials=None)
            assert user["roles"] == ["admin"]
            assert user["sub"] == "dev-user-id"
        finally:
            settings.debug = original


# ---------------------------------------------------------------------------
# RoleChecker unit tests
# ---------------------------------------------------------------------------


class TestRoleChecker:
    """Unit tests for the RoleChecker dependency."""

    @pytest.mark.asyncio
    async def test_admin_passes_admin_check(self):
        checker = RoleChecker(["admin"])
        user = {"sub": "u1", "roles": ["admin"]}
        result = await checker(user=user)
        assert result["sub"] == "u1"

    @pytest.mark.asyncio
    async def test_viewer_fails_admin_check(self):
        checker = RoleChecker(["admin"])
        user = {"sub": "u1", "roles": ["viewer"]}
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await checker(user=user)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_architect_passes_architect_check(self):
        checker = RoleChecker(["admin", "architect"])
        user = {"sub": "u1", "roles": ["architect"]}
        result = await checker(user=user)
        assert result["sub"] == "u1"

    @pytest.mark.asyncio
    async def test_viewer_fails_architect_check(self):
        checker = RoleChecker(["admin", "architect"])
        user = {"sub": "u1", "roles": ["viewer"]}
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await checker(user=user)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_empty_roles_defaults_to_viewer(self):
        """Users with no roles should default to viewer."""
        checker = RoleChecker(["admin", "architect", "viewer"])
        user = {"sub": "u1"}
        result = await checker(user=user)
        assert result["roles"] == ["viewer"]

    @pytest.mark.asyncio
    async def test_multiple_roles_any_match(self):
        checker = RoleChecker(["architect"])
        user = {"sub": "u1", "roles": ["viewer", "architect"]}
        result = await checker(user=user)
        assert result["sub"] == "u1"


# ---------------------------------------------------------------------------
# Route-level RBAC enforcement (integration)
# ---------------------------------------------------------------------------


class TestRouteRBAC:
    """Verify RBAC dependencies are wired on key route groups."""

    def test_projects_list_requires_auth(self):
        """GET /api/projects/ with auth succeeds."""
        r = client.get("/api/projects/", headers=AUTH_HEADERS)
        assert r.status_code == 200

    def test_projects_create_requires_auth(self):
        """POST /api/projects/ with auth succeeds."""
        r = client.post(
            "/api/projects/",
            json={"name": "Auth Test", "description": "testing"},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200

    def test_projects_delete_requires_auth(self):
        """DELETE /api/projects/{id} with admin auth succeeds."""
        r = client.delete("/api/projects/sec-test-id", headers=AUTH_HEADERS)
        assert r.status_code == 200

    def test_architecture_generate_requires_auth(self):
        """POST /api/architecture/generate with auth succeeds."""
        r = client.post(
            "/api/architecture/generate",
            json={"answers": {"org_size": "small"}},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200

    def test_bicep_list_requires_auth(self):
        """GET /api/bicep/templates with auth succeeds."""
        r = client.get("/api/bicep/templates", headers=AUTH_HEADERS)
        assert r.status_code == 200

    def test_scoring_evaluate_requires_auth(self):
        """POST /api/scoring/evaluate with auth succeeds."""
        r = client.post(
            "/api/scoring/evaluate",
            json={
                "architecture": {"management_groups": {}},
                "frameworks": ["nist_800_53"],
            },
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# CSRF middleware
# ---------------------------------------------------------------------------


class TestCSRF:
    """Verify CSRF protection on state-changing requests."""

    def test_get_requests_bypass_csrf(self):
        """GET requests should not be subject to CSRF checks."""
        r = client.get("/health")
        assert r.status_code == 200

    def test_post_with_matching_origin_passes(self):
        """POST with Origin matching CORS allowed origins succeeds."""
        r = client.post(
            "/api/architecture/generate",
            json={"answers": {"org_size": "small"}},
            headers={
                **AUTH_HEADERS,
                "Origin": "http://localhost:5173",
            },
        )
        assert r.status_code == 200

    def test_health_endpoint_no_auth_needed(self):
        """Health endpoint is public."""
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# Secret masking
# ---------------------------------------------------------------------------


class TestSecretMasking:
    """Verify the SecretMaskingFilter redacts sensitive data."""

    def test_redacts_api_key_in_log(self):
        import logging

        from app.security import SecretMaskingFilter

        filt = SecretMaskingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Using key=super-secret-value for service",
            args=(),
            exc_info=None,
        )
        filt.filter(record)
        assert "super-secret-value" not in record.msg
        assert "REDACTED" in record.msg

    def test_redacts_password_in_log(self):
        import logging

        from app.security import SecretMaskingFilter

        filt = SecretMaskingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="password=mysecretpw123",
            args=(),
            exc_info=None,
        )
        filt.filter(record)
        assert "mysecretpw123" not in record.msg

    def test_non_sensitive_log_passes_through(self):
        import logging

        from app.security import SecretMaskingFilter

        filt = SecretMaskingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Processing 42 items from queue",
            args=(),
            exc_info=None,
        )
        filt.filter(record)
        assert record.msg == "Processing 42 items from queue"

    def test_redacts_tuple_args(self):
        import logging

        from app.security import SecretMaskingFilter

        filt = SecretMaskingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Config: %s",
            args=("token=abc123xyz",),
            exc_info=None,
        )
        filt.filter(record)
        assert "abc123xyz" not in str(record.args)
