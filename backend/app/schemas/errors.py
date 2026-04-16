"""Structured error response schemas.

Provides a consistent error contract for all API responses so that
clients can rely on a single, machine-parseable format regardless of
the error origin (validation, business logic, or unexpected failure).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Individual error payload returned inside every error response."""

    code: str = Field(
        ...,
        description="Machine-readable error code, e.g. 'VALIDATION_ERROR'.",
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of the error.",
    )
    type: str = Field(
        ...,
        description=(
            "Error category: 'validation', 'not_found', 'forbidden', "
            "'unauthorized', 'conflict', 'rate_limited', 'internal'."
        ),
    )
    details: list[dict] | None = Field(
        default=None,
        description="Optional list of contextual detail objects (e.g. field errors).",
    )
    request_id: str | None = Field(
        default=None,
        description="Optional request trace identifier.",
    )


class ErrorResponse(BaseModel):
    """Top-level envelope for all error responses."""

    error: ErrorDetail
