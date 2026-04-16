"""Machine-readable error codes used across the API.

Each member maps to a unique string that clients can match on for
programmatic error handling without relying on human-readable messages.
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Canonical error codes returned in ``ErrorDetail.code``."""

    # --- Generic / framework-level ---
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    BAD_REQUEST = "BAD_REQUEST"

    # --- Domain-specific ---
    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    ARCHITECTURE_NOT_FOUND = "ARCHITECTURE_NOT_FOUND"
    DEPLOYMENT_NOT_FOUND = "DEPLOYMENT_NOT_FOUND"
    WORKLOAD_NOT_FOUND = "WORKLOAD_NOT_FOUND"
    SCAN_NOT_FOUND = "SCAN_NOT_FOUND"
    CONVERSATION_NOT_FOUND = "CONVERSATION_NOT_FOUND"
    POLICY_NOT_FOUND = "POLICY_NOT_FOUND"

    # --- AI / external service ---
    AI_SERVICE_UNAVAILABLE = "AI_SERVICE_UNAVAILABLE"
    AI_GENERATION_FAILED = "AI_GENERATION_FAILED"

    # --- Deployment lifecycle ---
    DEPLOYMENT_IN_PROGRESS = "DEPLOYMENT_IN_PROGRESS"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"


# Mapping from HTTP status codes to default error type categories.
STATUS_TO_TYPE: dict[int, str] = {
    400: "validation",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "validation",
    409: "conflict",
    422: "validation",
    429: "rate_limited",
    500: "internal",
}

# Mapping from HTTP status codes to default error codes.
STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
}
