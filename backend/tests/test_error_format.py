"""Tests verifying that error responses use the structured error format.

The structured format is:
    {"error": {"code": "...", "message": "...", "type": "..."}}

These tests ensure:
1. Internal errors return structured error responses (not raw strings).
2. Error responses never contain Python tracebacks or exception class names.
3. The global exception handler catches unhandled errors properly.
"""

import re
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app

# Patterns that should never appear in error messages returned to clients.
# These indicate leaking of internal implementation details.
TRACEBACK_PATTERNS = [
    r"Traceback \(most recent call last\)",
    r"File \".*\", line \d+",
    r"raise \w+Error",
    r"\w+Error:",
    r"\w+Exception:",
    r"sqlalchemy\.",
    r"asyncpg\.",
    r"aiosqlite\.",
]


@pytest.fixture
def async_client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _make_broken_db():
    """Return a mock AsyncSession whose execute() always raises."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        side_effect=RuntimeError("connection pool exhausted")
    )
    return mock_db


@pytest.fixture
def broken_db_client():
    """Create a test client where the DB dependency raises on every query."""
    mock_db = _make_broken_db()

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_404_returns_structured_error(async_client):
    """A 404 error response has the structured error envelope."""
    resp = await async_client.get(
        "/api/projects/nonexistent-id-12345",
        headers={"Authorization": "Bearer test"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body, f"Expected 'error' key in response, got: {body}"
    error = body["error"]
    assert "code" in error
    assert "message" in error
    assert "type" in error


@pytest.mark.asyncio
async def test_422_validation_returns_structured_error(async_client):
    """A validation error (422) response has the structured error envelope."""
    # Send an invalid payload to trigger Pydantic validation
    resp = await async_client.post(
        "/api/projects/",
        json={},  # missing required 'name' field
        headers={"Authorization": "Bearer test"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "error" in body, f"Expected 'error' key in response, got: {body}"
    error = body["error"]
    assert "code" in error
    assert "message" in error
    assert "type" in error
    assert error["type"] == "validation"


@pytest.mark.asyncio
async def test_internal_error_returns_structured_response(broken_db_client):
    """When a route raises an unexpected exception, the response is structured
    and does not leak internal details."""
    resp = await broken_db_client.get(
        "/api/projects/",
        headers={"Authorization": "Bearer test"},
    )

    # Should get a 500 with structured error
    assert resp.status_code == 500
    body = resp.json()
    assert "error" in body, f"Expected 'error' key in response, got: {body}"
    error = body["error"]
    assert "code" in error
    assert "message" in error
    assert "type" in error

    # The error message must NOT contain the raw exception text
    assert "connection pool exhausted" not in error["message"]
    assert "RuntimeError" not in error["message"]


@pytest.mark.asyncio
async def test_error_response_never_contains_traceback(broken_db_client):
    """Verify that no error response contains Python traceback fragments."""
    resp = await broken_db_client.get(
        "/api/projects/",
        headers={"Authorization": "Bearer test"},
    )

    assert resp.status_code == 500
    body = resp.json()

    # Serialize the full response body to check for leaks
    body_str = str(body)
    for pattern in TRACEBACK_PATTERNS:
        assert not re.search(pattern, body_str), (
            f"Response body matched forbidden pattern: {pattern}"
        )


@pytest.mark.asyncio
async def test_error_response_has_correct_type_for_500(broken_db_client):
    """Internal errors should have type='internal'."""
    resp = await broken_db_client.get(
        "/api/projects/",
        headers={"Authorization": "Bearer test"},
    )

    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["type"] == "internal"
    assert body["error"]["code"] == "INTERNAL_ERROR"


@pytest.mark.asyncio
async def test_error_response_has_correct_type_for_404(async_client):
    """Not-found errors should have type='not_found'."""
    resp = await async_client.get(
        "/api/projects/does-not-exist",
        headers={"Authorization": "Bearer test"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["type"] == "not_found"
    assert body["error"]["code"] == "NOT_FOUND"
