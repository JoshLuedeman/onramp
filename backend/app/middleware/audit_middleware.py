"""ASGI middleware that auto-logs mutating HTTP operations to the audit trail."""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)

# HTTP methods considered mutating
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths to skip (health checks, auth, docs, etc.)
_SKIP_PREFIXES = ("/health", "/docs", "/openapi.json", "/redoc")


def _resource_from_path(path: str) -> tuple[str | None, str | None]:
    """Extract (resource_type, resource_id) from a URL path.

    Heuristic: ``/api/<resource>/...`` → resource_type = first segment,
    resource_id = second segment if it looks like a UUID or slug.
    """
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return None, None

    # Skip the 'api' prefix
    if parts[0] == "api":
        parts = parts[1:]

    resource_type = parts[0] if parts else None
    resource_id = parts[1] if len(parts) > 1 else None
    return resource_type, resource_id


class AuditMiddleware(BaseHTTPMiddleware):
    """Automatically log mutating operations (POST/PUT/PATCH/DELETE).

    This is a best-effort, fire-and-forget audit trail.  Failures are
    logged but never propagate to the caller.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.method not in _MUTATING_METHODS:
            return response

        if any(request.url.path.startswith(p) for p in _SKIP_PREFIXES):
            return response

        # Skip the audit endpoint itself to avoid recursion
        if "/api/audit" in request.url.path:
            return response

        try:
            await self._record(request, response)
        except Exception:
            logger.debug(
                "Audit middleware: failed to log %s %s",
                request.method, request.url.path,
                exc_info=True,
            )

        return response

    async def _record(self, request: Request, response) -> None:
        """Best-effort audit record using a fresh DB session."""
        from app.db.session import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return

        resource_type, resource_id = _resource_from_path(
            request.url.path,
        )
        action = audit_service.action_from_method(request.method)

        # Extract actor from request state if auth middleware set it
        actor_id: str | None = None
        if hasattr(request.state, "user"):
            actor_id = getattr(request.state.user, "sub", None)

        ip_address: str | None = None
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        elif request.client:
            ip_address = request.client.host

        async with factory() as session:
            await audit_service.log_event(
                session,
                event_type=f"http.{action}",
                actor_id=actor_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "ip_address": ip_address,
                },
                request=request,
            )
            await session.commit()
