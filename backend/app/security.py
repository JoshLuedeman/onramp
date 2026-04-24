"""Security configuration and middleware."""

import logging
import re
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Secret masking filter (#154)                                                 #
# --------------------------------------------------------------------------- #

_SENSITIVE_PATTERN = re.compile(
    r"(key|secret|password|token|connection_string|credential)"
    r"(\s*[=:]\s*)"
    r"(\S+)",
    re.IGNORECASE,
)

_REDACTED = "***REDACTED***"


class SecretMaskingFilter(logging.Filter):
    """Redact sensitive values (keys, passwords, tokens, etc.) from log output."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._redact(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._redact(a) if isinstance(a, str) else a
                    for a in record.args
                )
        return True

    @staticmethod
    def _redact(value: object) -> object:
        if not isinstance(value, str):
            return value
        return _SENSITIVE_PATTERN.sub(rf"\1\2{_REDACTED}", value)


def install_secret_masking_filter() -> None:
    """Attach :class:`SecretMaskingFilter` to the root logger."""
    root = logging.getLogger()
    # Guard against duplicate installs
    if not any(isinstance(f, SecretMaskingFilter) for f in root.filters):
        root.addFilter(SecretMaskingFilter())

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
        if content_length:
            try:
                parsed = int(content_length)
            except ValueError:
                return Response(
                    content='{"detail":"Invalid Content-Length header"}',
                    status_code=400,
                    media_type="application/json",
                )
            if parsed < 0:
                return Response(
                    content='{"detail":"Invalid Content-Length header"}',
                    status_code=400,
                    media_type="application/json",
                )
            if parsed > self.MAX_CONTENT_LENGTH:
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
        """Build a key from client IP + path tier.

        Uses X-Forwarded-For when behind a reverse proxy, falling back to
        request.client.host.
        """
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
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

        # Skip health checks and CORS preflight requests
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        limit = self._get_limit_for_path(path)
        key = self._get_client_key(request, path)
        now = time.monotonic()
        window_start = now - self.WINDOW_SECONDS

        # Prune old entries and count recent requests
        recent = [ts for ts in self._requests[key] if ts > window_start]
        if recent:
            self._requests[key] = recent
        else:
            # Evict empty keys to prevent unbounded memory growth
            self._requests.pop(key, None)
            recent = []

        if len(recent) >= limit:
            retry_after = int(self.WINDOW_SECONDS - (now - recent[0])) + 1
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._requests[key] = recent + [now]
        return await call_next(request)
