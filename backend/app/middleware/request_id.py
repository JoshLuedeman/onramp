"""Request ID middleware — generates and propagates a unique ID per request.

The ID is stored in a ``contextvars.ContextVar`` so any code running in
the same async context (service layers, ORM calls, background tasks
spawned from the request) can access it via ``get_request_id()``.

The ID is also returned to the client as the ``X-Request-ID`` response
header for correlation in support tickets and log searches.
"""

import contextvars
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ContextVar holding the request-scoped ID
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

HEADER_NAME = "X-Request-ID"


def get_request_id() -> str | None:
    """Return the current request ID, or ``None`` outside a request."""
    return _request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a UUID to every inbound request and expose it on the response."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        # Honour client-supplied ID if present (useful for distributed tracing)
        rid = request.headers.get(HEADER_NAME) or str(uuid.uuid4())
        token = _request_id_var.set(rid)
        try:
            response = await call_next(request)
            response.headers[HEADER_NAME] = rid
            return response
        finally:
            _request_id_var.reset(token)
