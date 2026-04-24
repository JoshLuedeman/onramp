"""Tests for CSRF Origin/Referer validation middleware."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Ensure dev/debug mode so the app boots without Azure credentials
os.environ.setdefault("ONRAMP_DEBUG", "true")

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

AUTH_HEADERS = {"Authorization": "Bearer test"}


# -- Safe methods pass without Origin ----------------------------------------


def test_get_request_passes_without_origin():
    """GET is a safe method and must never be blocked by CSRF checks."""
    r = client.get("/health", headers=AUTH_HEADERS)
    assert r.status_code == 200


def test_options_request_exempt():
    """OPTIONS (CORS preflight) must be exempt from CSRF validation."""
    r = client.options("/api/projects", headers=AUTH_HEADERS)
    # OPTIONS may return 200 or 405 depending on route config,
    # but it must NOT return 403 CSRF error
    assert r.status_code != 403


# -- Health endpoint is always exempt ----------------------------------------


def test_health_endpoint_exempt_from_csrf():
    """POST to /health should not be blocked by CSRF even without Origin."""
    # /health is GET-only so FastAPI returns 405, but the middleware must not
    # intercept it with a 403.
    r = client.post("/health", headers=AUTH_HEADERS)
    assert r.status_code != 403


# -- Dev mode: state-changing requests allowed without Origin ----------------


def test_post_without_origin_allowed_in_dev_mode():
    """In dev mode (debug=True) POST without Origin should be allowed through."""
    assert settings.debug is True, "Test assumes ONRAMP_DEBUG=true"
    r = client.post(
        "/api/projects",
        json={"name": "csrf-test"},
        headers=AUTH_HEADERS,
    )
    # Should NOT be 403; the actual status depends on auth/validation
    assert r.status_code != 403


# -- Production mode: CSRF blocks bad / missing origins ----------------------


def test_post_with_valid_origin_succeeds_in_prod():
    """POST with an Origin that matches cors_origins must pass CSRF checks."""
    with patch.object(settings, "debug", False), \
         patch.object(settings, "cors_origins", ["http://localhost:5173"]):
        r = client.post(
            "/api/projects",
            json={"name": "csrf-test"},
            headers={**AUTH_HEADERS, "Origin": "http://localhost:5173"},
        )
        # Must not be 403; actual status depends on downstream auth
        assert r.status_code != 403


def test_post_without_origin_rejected_in_prod():
    """POST without Origin/Referer must be rejected with 403 in prod mode."""
    with patch.object(settings, "debug", False), \
         patch.object(settings, "cors_origins", ["http://localhost:5173"]):
        r = client.post(
            "/api/projects",
            json={"name": "csrf-test"},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 403
        body = r.json()
        assert body["error"]["code"] == "CSRF_VALIDATION_FAILED"


def test_post_with_invalid_origin_rejected_in_prod():
    """POST with an Origin not in cors_origins must be rejected with 403."""
    with patch.object(settings, "debug", False), \
         patch.object(settings, "cors_origins", ["http://localhost:5173"]):
        r = client.post(
            "/api/projects",
            json={"name": "csrf-test"},
            headers={**AUTH_HEADERS, "Origin": "https://evil.example.com"},
        )
        assert r.status_code == 403
        body = r.json()
        assert body["error"]["code"] == "CSRF_VALIDATION_FAILED"
