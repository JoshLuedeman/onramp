"""Security configuration and middleware."""

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

# Default CSP for React SPA with Fluent UI v9
_DEFAULT_CSP_PROD = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

_DEFAULT_CSP_DEV = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self' ws: wss:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def get_csp_policy() -> str:
    """Return the CSP policy string, using config override or sensible default."""
    if settings.csp_policy:
        return settings.csp_policy
    return _DEFAULT_CSP_DEV if settings.is_dev_mode else _DEFAULT_CSP_PROD


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses, including CSP."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = get_csp_policy()
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate incoming requests — reject oversized bodies and suspicious paths."""

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_CONTENT_LENGTH:
            return Response(
                content='{"detail":"Request body too large"}',
                status_code=413,
                media_type="application/json",
            )

        if ".." in request.url.path:
            return Response(
                content='{"detail":"Invalid request path"}',
                status_code=400,
                media_type="application/json",
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter with path-based tiers.

    Uses a sliding window counter per client IP. Tiers:
    - AI generation endpoints: rate_limit_ai/min
    - Deployment endpoints: rate_limit_deploy/min
    - Default API endpoints: rate_limit_default/min
    """

    WINDOW_SECONDS = 60

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # {client_key: [(timestamp, ...)] }
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_limit_for_path(self, path: str) -> int:
        """Return the rate limit for a given path."""
        if path.startswith("/api/architecture/generate") or path.startswith("/api/architecture/refine"):
            return settings.rate_limit_ai
        if path.startswith("/api/deployment"):
            return settings.rate_limit_deploy
        return settings.rate_limit_default

    def _get_client_key(self, request: Request, path: str) -> str:
        """Build a key from client IP + path tier."""
        client_ip = request.client.host if request.client else "unknown"
        if path.startswith("/api/architecture/generate") or path.startswith("/api/architecture/refine"):
            return f"{client_ip}:ai"
        if path.startswith("/api/deployment"):
            return f"{client_ip}:deploy"
        return f"{client_ip}:default"

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting in dev mode
        if settings.is_dev_mode:
            return await call_next(request)

        # Skip health checks
        if request.url.path == "/health":
            return await call_next(request)

        path = request.url.path
        limit = self._get_limit_for_path(path)
        key = self._get_client_key(request, path)
        now = time.monotonic()
        window_start = now - self.WINDOW_SECONDS

        # Prune old entries and count recent requests
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > window_start
        ]

        if len(self._requests[key]) >= limit:
            retry_after = int(self.WINDOW_SECONDS - (now - self._requests[key][0])) + 1
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._requests[key].append(now)
        return await call_next(request)
