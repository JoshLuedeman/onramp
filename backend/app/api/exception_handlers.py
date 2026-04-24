"""Exception handlers that produce structured ``ErrorResponse`` payloads.

Register these once at application startup so that *every* error —
whether from FastAPI validation, explicit ``HTTPException`` raises, or
unexpected crashes — goes through a single formatting pipeline.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.error_codes import STATUS_TO_CODE, STATUS_TO_TYPE, ErrorCode
from app.middleware.request_id import get_request_id
from app.schemas.errors import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def _current_request_id() -> str | None:
    """Return the request ID from the contextvar (set by RequestIDMiddleware)."""
    return get_request_id()


def _build_error_response(
    status_code: int,
    *,
    code: str | None = None,
    message: str = "An unexpected error occurred.",
    error_type: str | None = None,
    details: list[dict] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Build a ``JSONResponse`` wrapping a structured ``ErrorResponse``."""
    resolved_code = code or STATUS_TO_CODE.get(
        status_code, ErrorCode.INTERNAL_ERROR
    ).value
    resolved_type = error_type or STATUS_TO_TYPE.get(status_code, "internal")
    body = ErrorResponse(
        error=ErrorDetail(
            code=resolved_code,
            message=message,
            type=resolved_type,
            details=details,
            request_id=request_id,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException | StarletteHTTPException,
) -> JSONResponse:
    """Handle explicit ``HTTPException`` raises (FastAPI and Starlette)."""
    detail_str = str(exc.detail) if exc.detail else "Request failed."
    return _build_error_response(
        exc.status_code,
        message=detail_str,
        request_id=_current_request_id(),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic / FastAPI request validation errors."""
    field_errors: list[dict] = []
    for err in exc.errors():
        field_errors.append(
            {
                "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            }
        )
    return _build_error_response(
        422,
        code=ErrorCode.VALIDATION_ERROR.value,
        message="Request validation failed.",
        error_type="validation",
        details=field_errors,
        request_id=_current_request_id(),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leak stack traces."""
    request_id = _current_request_id() or "unknown"
    logger.exception(
        "Unhandled exception [request_id=%s]: %s",
        request_id,
        exc,
    )
    return _build_error_response(
        500,
        code=ErrorCode.INTERNAL_ERROR.value,
        message="An internal server error occurred.",
        error_type="internal",
        request_id=request_id,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to the FastAPI application."""
    # Register for both FastAPI and Starlette HTTPException so that
    # router-level 404s (which use starlette.exceptions.HTTPException)
    # also get the structured format.
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(
        StarletteHTTPException, http_exception_handler
    )
    app.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
    app.add_exception_handler(Exception, generic_exception_handler)
