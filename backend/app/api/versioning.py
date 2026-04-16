"""API versioning layer.

Provides a URL-rewriting middleware that maps ``/api/v1/…`` requests to
the existing ``/api/…`` route tree so that the canonical versioned URL
works without modifying any individual route file.

Unversioned ``/api/…`` routes continue to work as backward-compatible
aliases but receive a ``Deprecation`` header nudging clients toward the
``/api/v1/`` prefix.

Every response carries an ``API-Version`` header.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

API_VERSION = "v1"
VERSIONED_PREFIX = f"/api/{API_VERSION}/"
UNVERSIONED_PREFIX = "/api/"


class APIVersionHeaderMiddleware:
    """Pure ASGI middleware that injects ``API-Version`` and deprecation headers.

    Uses raw ASGI ``send`` wrapping so it never interferes with
    request-body reading (avoids the ``BaseHTTPMiddleware`` pitfall).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        original_path: str = (scope.get("state") or {}).get(
            "_original_path", ""
        )
        is_api = path.startswith(UNVERSIONED_PREFIX) or original_path.startswith(
            VERSIONED_PREFIX
        )
        is_unversioned = (
            path.startswith(UNVERSIONED_PREFIX)
            and not path.startswith(VERSIONED_PREFIX)
            and not original_path
        )

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start" and is_api:
                headers = list(message.get("headers", []))
                headers.append(
                    (b"api-version", API_VERSION.encode())
                )
                if is_unversioned:
                    versioned = path.replace(
                        "/api/", f"/api/{API_VERSION}/", 1
                    )
                    headers.append((b"deprecation", b"true"))
                    headers.append((b"sunset", b"2026-06-01"))
                    headers.append(
                        (
                            b"link",
                            f'<{versioned}>; rel="successor-version"'.encode(),
                        )
                    )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


class VersionRewriteMiddleware:
    """Pure ASGI middleware that rewrites ``/api/v1/…`` → ``/api/…``.

    This runs *before* routing so that FastAPI's router sees the path it
    already knows (``/api/…``).  The original path is stashed in
    ``scope["state"]["_original_path"]`` for the header middleware to read.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] in ("http", "websocket"):
            path: str = scope.get("path", "")
            if path.startswith(VERSIONED_PREFIX):
                # Rewrite: /api/v1/foo → /api/foo
                new_path = "/api/" + path[len(VERSIONED_PREFIX):]
                scope = dict(scope, path=new_path)
                # Stash original so the header middleware can detect it
                state = scope.get("state", {})
                state["_original_path"] = path
                scope["state"] = state

        await self.app(scope, receive, send)

