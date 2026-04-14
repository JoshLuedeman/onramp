"""Tests for security headers middleware, CSP, request validation, and rate limiting."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_security_headers_present():
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age" in r.headers.get("Strict-Transport-Security", "")
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_permissions_policy():
    r = client.get("/health")
    pp = r.headers.get("Permissions-Policy", "")
    assert "camera=()" in pp
    assert "microphone=()" in pp
    assert "geolocation=()" in pp


# --------------------------------------------------------------------------- #
# CSP header tests (#50)                                                       #
# --------------------------------------------------------------------------- #


def test_csp_header_present():
    """CSP header should be present on all responses."""
    r = client.get("/health")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp


def test_csp_dev_mode_allows_ws():
    """Dev mode CSP should allow WebSocket for Vite HMR."""
    r = client.get("/health")
    csp = r.headers.get("Content-Security-Policy", "")
    # Dev mode (no azure_tenant_id) should include ws: for HMR
    assert "ws:" in csp


def test_csp_allows_unsafe_inline_styles():
    """CSP must allow unsafe-inline styles for Fluent UI Griffel."""
    r = client.get("/health")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "'unsafe-inline'" in csp


def test_csp_allows_data_uris():
    """CSP must allow data: URIs for images and fonts (Fluent UI)."""
    r = client.get("/health")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "data:" in csp


def test_csp_configurable_via_env():
    """CSP policy should be overridable via ONRAMP_CSP_POLICY."""
    custom_csp = "default-src 'none'"
    with patch("app.security.settings") as mock_settings:
        mock_settings.csp_policy = custom_csp
        mock_settings.is_dev_mode = True
        from app.security import get_csp_policy
        assert get_csp_policy() == custom_csp


def test_csp_production_no_ws():
    """Production CSP should NOT include ws: connections."""
    with patch("app.security.settings") as mock_settings:
        mock_settings.csp_policy = ""
        mock_settings.is_dev_mode = False
        from app.security import get_csp_policy
        csp = get_csp_policy()
        assert "ws:" not in csp
        assert "default-src 'self'" in csp


# --------------------------------------------------------------------------- #
# Request validation middleware tests (#51)                                     #
# --------------------------------------------------------------------------- #


def test_request_validation_blocks_path_traversal():
    """Requests with .. in path should be rejected with 400."""
    from app.security import RequestValidationMiddleware

    mw = RequestValidationMiddleware(app=None)
    request = MagicMock()
    request.url.path = "/api/../etc/passwd"
    request.headers = {}
    call_next = AsyncMock()

    response = asyncio.get_event_loop().run_until_complete(
        mw.dispatch(request, call_next)
    )
    assert response.status_code == 400
    call_next.assert_not_called()


def test_request_validation_blocks_oversized_body():
    """Requests with Content-Length exceeding limit should get 413."""
    from app.security import RequestValidationMiddleware

    mw = RequestValidationMiddleware(app=None)
    request = MagicMock()
    request.url.path = "/api/architecture/generate"
    request.headers = {"content-length": "999999999"}
    call_next = AsyncMock()

    response = asyncio.get_event_loop().run_until_complete(
        mw.dispatch(request, call_next)
    )
    assert response.status_code == 413
    call_next.assert_not_called()


def test_request_validation_rejects_invalid_content_length():
    """Non-numeric Content-Length should be rejected with 400."""
    from app.security import RequestValidationMiddleware

    mw = RequestValidationMiddleware(app=None)
    request = MagicMock()
    request.url.path = "/api/test"
    request.headers = {"content-length": "not-a-number"}
    call_next = AsyncMock()

    response = asyncio.get_event_loop().run_until_complete(
        mw.dispatch(request, call_next)
    )
    assert response.status_code == 400
    assert b"Invalid Content-Length" in response.body


def test_request_validation_rejects_negative_content_length():
    """Negative Content-Length should be rejected with 400."""
    from app.security import RequestValidationMiddleware

    mw = RequestValidationMiddleware(app=None)
    request = MagicMock()
    request.url.path = "/api/test"
    request.headers = {"content-length": "-1"}
    call_next = AsyncMock()

    response = asyncio.get_event_loop().run_until_complete(
        mw.dispatch(request, call_next)
    )
    assert response.status_code == 400
    assert b"Invalid Content-Length" in response.body


def test_request_validation_allows_normal_requests():
    """Normal requests should pass through validation."""
    r = client.get("/health")
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# Health endpoint production mode tests (#54)                                  #
# --------------------------------------------------------------------------- #


def test_health_dev_mode_verbose():
    """Dev mode health should return detailed status info."""
    r = client.get("/health")
    data = r.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "mode" in data
    assert "auth" in data
    assert "ai" in data
    assert "database" in data


def test_health_production_minimal():
    """Production health should return ONLY status — no dev-only keys."""
    with patch("app.main.settings") as mock_settings:
        mock_settings.is_dev_mode = False
        mock_settings.cors_origins = ["https://example.com"]
        r = client.get("/health")
        data = r.json()
        assert data["status"] == "healthy"
        # Dev-only keys must be absent in production
        for key in ("service", "mode", "auth", "ai", "database"):
            assert key not in data, f"Dev-only key '{key}' found in production health"


# --------------------------------------------------------------------------- #
# Rate limiting middleware tests (#52)                                          #
# --------------------------------------------------------------------------- #


def test_rate_limiting_disabled_in_dev_mode():
    """Rate limiting should be disabled in dev mode — no 429s on API endpoints."""
    for _ in range(100):
        r = client.get("/api/questionnaire/categories")
        # Should never get 429 in dev mode (404 or 200 are both fine)
        assert r.status_code != 429


def test_rate_limit_middleware_exists():
    """RateLimitMiddleware should be importable and instantiable."""
    from app.security import RateLimitMiddleware
    assert RateLimitMiddleware is not None


def test_rate_limit_returns_429_when_exceeded():
    """Rate limiter should return 429 with Retry-After when limit exceeded."""
    from app.security import RateLimitMiddleware

    mw = RateLimitMiddleware(app=None)
    now = time.monotonic()
    call_next = AsyncMock(return_value=MagicMock())

    # Simulate production mode
    with patch("app.security.settings") as mock_settings:
        mock_settings.is_dev_mode = False
        mock_settings.rate_limit_default = 2
        mock_settings.rate_limit_ai = 5
        mock_settings.rate_limit_deploy = 3

        # Build a mock request for a non-exempt endpoint
        request = MagicMock()
        request.url.path = "/api/questionnaire/next"
        request.method = "POST"
        request.headers = {}
        request.client.host = "10.0.0.1"

        # First two requests should succeed
        for _ in range(2):
            resp = asyncio.get_event_loop().run_until_complete(
                mw.dispatch(request, call_next)
            )
        assert call_next.call_count == 2

        # Third request should be rate limited
        resp = asyncio.get_event_loop().run_until_complete(
            mw.dispatch(request, call_next)
        )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers


def test_rate_limit_skips_options_preflight():
    """OPTIONS (CORS preflight) requests should bypass rate limiting."""
    from app.security import RateLimitMiddleware

    mw = RateLimitMiddleware(app=None)
    call_next = AsyncMock(return_value=MagicMock())

    with patch("app.security.settings") as mock_settings:
        mock_settings.is_dev_mode = False

        request = MagicMock()
        request.url.path = "/api/architecture/generate"
        request.method = "OPTIONS"
        request.headers = {}
        request.client.host = "10.0.0.2"

        # OPTIONS should always pass through
        for _ in range(20):
            asyncio.get_event_loop().run_until_complete(
                mw.dispatch(request, call_next)
            )
        # All 20 should have been forwarded (no 429)
        assert call_next.call_count == 20


def test_rate_limit_config_settings():
    """Rate limit config values should be accessible."""
    from app.config import settings
    assert settings.rate_limit_default == 60
    assert settings.rate_limit_ai == 5
    assert settings.rate_limit_deploy == 3


def test_rate_limit_path_tiers():
    """Different paths should map to different rate limit tiers."""
    from app.security import RateLimitMiddleware
    mw = RateLimitMiddleware(app=None)

    from app.config import settings
    assert mw._get_limit_for_path("/api/architecture/generate") == settings.rate_limit_ai
    assert mw._get_limit_for_path("/api/architecture/refine") == settings.rate_limit_ai
    assert mw._get_limit_for_path("/api/deployment/create") == settings.rate_limit_deploy
    assert mw._get_limit_for_path("/api/questionnaire/next") == settings.rate_limit_default
    assert mw._get_limit_for_path("/health") == settings.rate_limit_default


def test_rate_limit_uses_x_forwarded_for():
    """Rate limiter should use X-Forwarded-For header when present."""
    from app.security import RateLimitMiddleware

    mw = RateLimitMiddleware(app=None)
    request = MagicMock()
    request.url.path = "/api/test"
    request.headers = {"x-forwarded-for": "1.2.3.4, 10.0.0.1"}
    request.client.host = "10.0.0.1"

    key = mw._get_client_key(request, "/api/test")
    assert key.startswith("1.2.3.4:")


def test_rate_limit_memory_eviction():
    """Expired entries should be evicted to prevent unbounded memory growth."""
    from app.security import RateLimitMiddleware

    mw = RateLimitMiddleware(app=None)
    key = "eviction-test:default"
    # Add entries from 120 seconds ago (well outside the 60s window)
    old_time = time.monotonic() - 120
    mw._requests[key] = [old_time] * 5

    call_next = AsyncMock(return_value=MagicMock())
    with patch("app.security.settings") as mock_settings:
        mock_settings.is_dev_mode = False
        mock_settings.rate_limit_default = 60
        mock_settings.rate_limit_ai = 5
        mock_settings.rate_limit_deploy = 3

        request = MagicMock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.client.host = "eviction-test"

        asyncio.get_event_loop().run_until_complete(
            mw.dispatch(request, call_next)
        )
    # After processing, the old entries should be gone and key should have 1 new entry
    assert len(mw._requests.get("eviction-test:default", [])) == 1


# --------------------------------------------------------------------------- #
# CORS configuration tests (#51)                                               #
# --------------------------------------------------------------------------- #


def test_cors_dev_mode_permissive():
    """Dev mode CORS should use wildcard methods/headers."""
    from app.main import _cors_methods, _cors_headers
    # In dev mode (no azure_tenant_id), CORS should be permissive
    assert _cors_methods == ["*"]
    assert _cors_headers == ["*"]


# --------------------------------------------------------------------------- #
# is_dev_mode alignment (#51)                                                  #
# --------------------------------------------------------------------------- #


def test_is_dev_mode_requires_both_tenant_and_client():
    """is_dev_mode should be True unless BOTH tenant and client IDs are set."""
    from app.config import Settings

    # No credentials = dev mode
    s = Settings(azure_tenant_id="", azure_client_id="")
    assert s.is_dev_mode is True

    # Only tenant = still dev mode
    s = Settings(azure_tenant_id="tid", azure_client_id="")
    assert s.is_dev_mode is True

    # Only client = still dev mode
    s = Settings(azure_tenant_id="", azure_client_id="cid")
    assert s.is_dev_mode is True

    # Both set = production mode
    s = Settings(azure_tenant_id="tid", azure_client_id="cid")
    assert s.is_dev_mode is False
