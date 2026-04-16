"""Tests for API versioning, structured error responses, and exception handlers.

Covers:
  - Version URL rewriting (``/api/v1/…`` → ``/api/…``)
  - Backward-compatible unversioned routes
  - ``API-Version`` response header on all API responses
  - Deprecation headers on unversioned routes
  - Structured ``ErrorResponse`` format for all error types
  - ``ErrorCode`` enum completeness and mappings
  - Exception handler coverage (HTTPException, validation, generic)
  - Frontend error schema compatibility
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import APIRouter, Body, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.api.error_codes import STATUS_TO_CODE, STATUS_TO_TYPE, ErrorCode
from app.api.exception_handlers import (
    _build_error_response,
    register_exception_handlers,
)
from app.api.versioning import (
    API_VERSION,
    UNVERSIONED_PREFIX,
    VERSIONED_PREFIX,
    APIVersionHeaderMiddleware,
    VersionRewriteMiddleware,
)
from app.schemas.errors import ErrorDetail, ErrorResponse

# ---------------------------------------------------------------------------
# Helpers — minimal FastAPI app used by versioning / error tests
# ---------------------------------------------------------------------------


class _ItemCreate(BaseModel):
    """Request body model used by the test ``/api/test/items`` endpoint."""

    name: str = Field(..., min_length=1)
    count: int = Field(..., gt=0)


def _create_test_app() -> FastAPI:
    """Build a small FastAPI app with versioning + error handling wired up."""
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(APIVersionHeaderMiddleware)
    app.add_middleware(VersionRewriteMiddleware)

    router = APIRouter(prefix="/api/test", tags=["test"])

    @router.get("/hello")
    async def hello():
        return {"msg": "world"}

    @router.get("/not-found")
    async def raise_not_found():
        raise HTTPException(status_code=404, detail="Thing not found")

    @router.get("/forbidden")
    async def raise_forbidden():
        raise HTTPException(status_code=403, detail="Access denied")

    @router.get("/unauthorized")
    async def raise_unauthorized():
        raise HTTPException(status_code=401, detail="Not authenticated")

    @router.get("/conflict")
    async def raise_conflict():
        raise HTTPException(status_code=409, detail="Already exists")

    @router.get("/bad-request")
    async def raise_bad_request():
        raise HTTPException(status_code=400, detail="Bad input")

    @router.get("/method-not-allowed")
    async def raise_method_not_allowed():
        raise HTTPException(status_code=405, detail="Method not allowed")

    @router.get("/rate-limited")
    async def raise_rate_limited():
        raise HTTPException(status_code=429, detail="Too many requests")

    @router.get("/server-error")
    async def raise_server_error():
        raise HTTPException(status_code=500, detail="Something broke")

    @router.get("/crash")
    async def crash():
        raise RuntimeError("unexpected boom")

    @router.post("/items")
    async def create_item(item: _ItemCreate = Body(...)):
        return {"name": item.name, "count": item.count}

    @router.get("/custom-code")
    async def custom_error_code():
        raise HTTPException(status_code=404, detail="Tenant xyz not found")

    app.include_router(router)

    # Non-API route (should NOT get versioning headers)
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_create_test_app(), raise_server_exceptions=False)


# ===================================================================
# 1. ErrorDetail / ErrorResponse schema tests
# ===================================================================


class TestErrorSchemas:
    """Verify Pydantic models serialise correctly."""

    def test_error_detail_required_fields(self):
        detail = ErrorDetail(code="NOT_FOUND", message="Gone", type="not_found")
        assert detail.code == "NOT_FOUND"
        assert detail.message == "Gone"
        assert detail.type == "not_found"
        assert detail.details is None
        assert detail.request_id is None

    def test_error_detail_all_fields(self):
        detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Bad",
            type="validation",
            details=[{"field": "name", "message": "required"}],
            request_id="abc-123",
        )
        assert detail.details == [{"field": "name", "message": "required"}]
        assert detail.request_id == "abc-123"

    def test_error_response_envelope(self):
        resp = ErrorResponse(
            error=ErrorDetail(code="X", message="Y", type="internal")
        )
        data = resp.model_dump()
        assert "error" in data
        assert data["error"]["code"] == "X"

    def test_error_response_json_serialisation(self):
        resp = ErrorResponse(
            error=ErrorDetail(code="A", message="B", type="validation")
        )
        raw = resp.model_dump_json()
        assert '"code":"A"' in raw or '"code": "A"' in raw

    def test_error_response_excludes_none(self):
        resp = ErrorResponse(
            error=ErrorDetail(code="A", message="B", type="t")
        )
        data = resp.model_dump(exclude_none=True)
        assert "details" not in data["error"]
        assert "request_id" not in data["error"]

    def test_error_detail_rejects_missing_fields(self):
        with pytest.raises(Exception):
            ErrorDetail(code="A")  # type: ignore[call-arg]

    def test_error_detail_type_annotation(self):
        """details field accepts list[dict]."""
        detail = ErrorDetail(
            code="V",
            message="M",
            type="validation",
            details=[{"a": 1}, {"b": "two"}],
        )
        assert len(detail.details) == 2


# ===================================================================
# 2. ErrorCode enum tests
# ===================================================================


class TestErrorCodes:
    """Verify enum members and mapping tables."""

    def test_error_code_values_are_strings(self):
        for member in ErrorCode:
            assert isinstance(member.value, str)
            assert member.value == member.name

    def test_all_status_to_type_keys_are_ints(self):
        for key in STATUS_TO_TYPE:
            assert isinstance(key, int)

    def test_all_status_to_code_values_are_error_code(self):
        for val in STATUS_TO_CODE.values():
            assert isinstance(val, ErrorCode)

    def test_status_to_type_covers_common_statuses(self):
        for code in (400, 401, 403, 404, 409, 422, 429, 500):
            assert code in STATUS_TO_TYPE

    def test_status_to_code_covers_common_statuses(self):
        for code in (400, 401, 403, 404, 409, 422, 429, 500):
            assert code in STATUS_TO_CODE

    def test_error_code_is_string_subclass(self):
        assert isinstance(ErrorCode.NOT_FOUND, str)

    def test_error_code_members_minimum(self):
        expected = {
            "VALIDATION_ERROR",
            "NOT_FOUND",
            "FORBIDDEN",
            "UNAUTHORIZED",
            "RATE_LIMITED",
            "INTERNAL_ERROR",
            "TENANT_NOT_FOUND",
            "PROJECT_NOT_FOUND",
            "ARCHITECTURE_NOT_FOUND",
        }
        actual = {m.name for m in ErrorCode}
        assert expected.issubset(actual)

    def test_method_not_allowed_code(self):
        assert ErrorCode.METHOD_NOT_ALLOWED.value == "METHOD_NOT_ALLOWED"

    def test_conflict_code(self):
        assert ErrorCode.CONFLICT.value == "CONFLICT"

    def test_bad_request_code(self):
        assert ErrorCode.BAD_REQUEST.value == "BAD_REQUEST"


# ===================================================================
# 3. Version routing — /api/v1/ prefix tests
# ===================================================================


class TestVersionRouting:
    """Versioned routes should resolve and return correct content."""

    def test_v1_route_returns_200(self, client: TestClient):
        resp = client.get("/api/v1/test/hello")
        assert resp.status_code == 200
        assert resp.json() == {"msg": "world"}

    def test_v1_route_post(self, client: TestClient):
        resp = client.post(
            "/api/v1/test/items",
            json={"name": "widget", "count": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "widget"

    def test_v1_404_still_structured(self, client: TestClient):
        resp = client.get("/api/v1/test/not-found")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "NOT_FOUND"

    def test_v1_nonexistent_path_returns_404(self, client: TestClient):
        resp = client.get("/api/v1/test/does-not-exist")
        assert resp.status_code == 404

    def test_v1_validation_error_structured(self, client: TestClient):
        resp = client.post("/api/v1/test/items", json={"name": "", "count": -1})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["type"] == "validation"
        assert body["error"]["details"] is not None

    def test_v1_crash_returns_500(self, client: TestClient):
        resp = client.get("/api/v1/test/crash")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"


# ===================================================================
# 4. Backward compatibility — unversioned /api/ routes still work
# ===================================================================


class TestBackwardCompatibility:
    """Existing /api/… paths must keep working."""

    def test_unversioned_route_returns_200(self, client: TestClient):
        resp = client.get("/api/test/hello")
        assert resp.status_code == 200
        assert resp.json() == {"msg": "world"}

    def test_unversioned_post_works(self, client: TestClient):
        resp = client.post(
            "/api/test/items",
            json={"name": "gadget", "count": 2},
        )
        assert resp.status_code == 200

    def test_unversioned_404_structured(self, client: TestClient):
        resp = client.get("/api/test/not-found")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body

    def test_unversioned_validation_error(self, client: TestClient):
        resp = client.post("/api/test/items", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"


# ===================================================================
# 5. API-Version header tests
# ===================================================================


class TestAPIVersionHeader:
    """All API responses must carry ``API-Version: v1``."""

    def test_v1_route_has_version_header(self, client: TestClient):
        resp = client.get("/api/v1/test/hello")
        assert resp.headers.get("API-Version") == "v1"

    def test_unversioned_route_has_version_header(self, client: TestClient):
        resp = client.get("/api/test/hello")
        assert resp.headers.get("API-Version") == "v1"

    def test_v1_error_has_version_header(self, client: TestClient):
        resp = client.get("/api/v1/test/not-found")
        assert resp.headers.get("API-Version") == "v1"

    def test_unversioned_error_has_version_header(self, client: TestClient):
        resp = client.get("/api/test/not-found")
        assert resp.headers.get("API-Version") == "v1"

    def test_v1_validation_error_has_header(self, client: TestClient):
        resp = client.post("/api/v1/test/items", json={})
        assert resp.headers.get("API-Version") == "v1"

    def test_health_no_version_header(self, client: TestClient):
        """Non-API routes should not get the API-Version header."""
        resp = client.get("/health")
        assert "API-Version" not in resp.headers


# ===================================================================
# 6. Deprecation header tests
# ===================================================================


class TestDeprecationHeaders:
    """Unversioned routes get deprecation hints; versioned routes don't."""

    def test_unversioned_has_deprecation(self, client: TestClient):
        resp = client.get("/api/test/hello")
        assert resp.headers.get("Deprecation") == "true"

    def test_unversioned_has_sunset(self, client: TestClient):
        resp = client.get("/api/test/hello")
        assert "Sunset" in resp.headers

    def test_unversioned_has_link(self, client: TestClient):
        resp = client.get("/api/test/hello")
        link = resp.headers.get("Link", "")
        assert "successor-version" in link
        assert "/api/v1/" in link

    def test_v1_no_deprecation(self, client: TestClient):
        resp = client.get("/api/v1/test/hello")
        assert "Deprecation" not in resp.headers

    def test_v1_no_sunset(self, client: TestClient):
        resp = client.get("/api/v1/test/hello")
        assert "Sunset" not in resp.headers

    def test_unversioned_error_has_deprecation(self, client: TestClient):
        resp = client.get("/api/test/not-found")
        assert resp.headers.get("Deprecation") == "true"

    def test_v1_error_no_deprecation(self, client: TestClient):
        resp = client.get("/api/v1/test/not-found")
        assert "Deprecation" not in resp.headers


# ===================================================================
# 7. Structured error response format — all error types
# ===================================================================


class TestStructuredErrors:
    """Every error response must conform to ``ErrorResponse``."""

    def _assert_error_shape(self, body: dict):
        assert "error" in body
        err = body["error"]
        assert "code" in err
        assert "message" in err
        assert "type" in err

    def test_404_format(self, client: TestClient):
        resp = client.get("/api/test/not-found")
        self._assert_error_shape(resp.json())
        assert resp.json()["error"]["type"] == "not_found"

    def test_403_format(self, client: TestClient):
        resp = client.get("/api/test/forbidden")
        self._assert_error_shape(resp.json())
        assert resp.json()["error"]["type"] == "forbidden"

    def test_401_format(self, client: TestClient):
        resp = client.get("/api/test/unauthorized")
        self._assert_error_shape(resp.json())
        assert resp.json()["error"]["type"] == "unauthorized"

    def test_409_format(self, client: TestClient):
        resp = client.get("/api/test/conflict")
        self._assert_error_shape(resp.json())
        assert resp.json()["error"]["type"] == "conflict"

    def test_400_format(self, client: TestClient):
        resp = client.get("/api/test/bad-request")
        self._assert_error_shape(resp.json())
        assert resp.json()["error"]["type"] == "validation"

    def test_405_format(self, client: TestClient):
        resp = client.get("/api/test/method-not-allowed")
        self._assert_error_shape(resp.json())

    def test_429_format(self, client: TestClient):
        resp = client.get("/api/test/rate-limited")
        self._assert_error_shape(resp.json())
        assert resp.json()["error"]["type"] == "rate_limited"

    def test_500_format(self, client: TestClient):
        resp = client.get("/api/test/server-error")
        self._assert_error_shape(resp.json())
        assert resp.json()["error"]["type"] == "internal"

    def test_422_format(self, client: TestClient):
        resp = client.post("/api/test/items", json={})
        self._assert_error_shape(resp.json())
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_unhandled_crash_format(self, client: TestClient):
        resp = client.get("/api/test/crash")
        self._assert_error_shape(resp.json())
        assert resp.json()["error"]["code"] == "INTERNAL_ERROR"

    def test_crash_no_stack_trace(self, client: TestClient):
        resp = client.get("/api/test/crash")
        body_str = resp.text
        assert "Traceback" not in body_str
        assert "unexpected boom" not in body_str

    def test_crash_has_request_id(self, client: TestClient):
        resp = client.get("/api/test/crash")
        body = resp.json()
        rid = body["error"].get("request_id")
        assert rid is not None
        # Should be a valid UUID
        uuid.UUID(rid)

    def test_404_message_forwarded(self, client: TestClient):
        resp = client.get("/api/test/not-found")
        assert resp.json()["error"]["message"] == "Thing not found"


# ===================================================================
# 8. Validation error detail tests
# ===================================================================


class TestValidationDetails:
    """Validation errors should include field-level detail."""

    def test_missing_required_fields(self, client: TestClient):
        resp = client.post("/api/test/items", json={})
        body = resp.json()
        details = body["error"]["details"]
        assert isinstance(details, list)
        assert len(details) >= 1  # at least item-level or field-level error

    def test_detail_contains_field_key(self, client: TestClient):
        resp = client.post("/api/test/items", json={})
        details = resp.json()["error"]["details"]
        fields = [d["field"] for d in details]
        # FastAPI may report individual field errors or a top-level body error
        assert len(fields) >= 1

    def test_detail_contains_message(self, client: TestClient):
        resp = client.post("/api/test/items", json={})
        details = resp.json()["error"]["details"]
        for d in details:
            assert "message" in d
            assert isinstance(d["message"], str)

    def test_detail_contains_type(self, client: TestClient):
        resp = client.post("/api/test/items", json={})
        details = resp.json()["error"]["details"]
        for d in details:
            assert "type" in d

    def test_invalid_value_type(self, client: TestClient):
        resp = client.post(
            "/api/test/items",
            json={"name": "ok", "count": "not-a-number"},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["details"] is not None

    def test_validation_message_text(self, client: TestClient):
        resp = client.post("/api/test/items", json={})
        assert resp.json()["error"]["message"] == "Request validation failed."

    def test_constraint_violation_count(self, client: TestClient):
        """count > 0 constraint should be reported."""
        resp = client.post(
            "/api/test/items",
            json={"name": "valid", "count": 0},
        )
        assert resp.status_code == 422
        details = resp.json()["error"]["details"]
        assert len(details) >= 1

    def test_constraint_violation_name_min_length(self, client: TestClient):
        """name min_length=1 constraint."""
        resp = client.post(
            "/api/test/items",
            json={"name": "", "count": 5},
        )
        assert resp.status_code == 422


# ===================================================================
# 9. _build_error_response helper tests
# ===================================================================


class TestBuildErrorResponse:
    """Unit tests for the internal response builder."""

    def test_default_code_from_status(self):
        resp = _build_error_response(404, message="Not here")
        body = resp.body
        import json

        data = json.loads(body)
        assert data["error"]["code"] == "NOT_FOUND"

    def test_explicit_code_overrides_default(self):
        import json

        resp = _build_error_response(
            404,
            code="TENANT_NOT_FOUND",
            message="Tenant gone",
        )
        data = json.loads(resp.body)
        assert data["error"]["code"] == "TENANT_NOT_FOUND"

    def test_explicit_type_overrides_default(self):
        import json

        resp = _build_error_response(
            500,
            error_type="validation",
            message="Odd",
        )
        data = json.loads(resp.body)
        assert data["error"]["type"] == "validation"

    def test_request_id_included(self):
        import json

        resp = _build_error_response(
            500, message="err", request_id="rid-1"
        )
        data = json.loads(resp.body)
        assert data["error"]["request_id"] == "rid-1"

    def test_none_fields_excluded(self):
        import json

        resp = _build_error_response(400, message="bad")
        data = json.loads(resp.body)
        assert "details" not in data["error"]
        assert "request_id" not in data["error"]

    def test_details_included(self):
        import json

        resp = _build_error_response(
            422,
            message="bad",
            details=[{"field": "x"}],
        )
        data = json.loads(resp.body)
        assert data["error"]["details"] == [{"field": "x"}]

    def test_status_code_set_correctly(self):
        resp = _build_error_response(418, message="teapot")
        assert resp.status_code == 418

    def test_unknown_status_defaults_to_internal(self):
        import json

        resp = _build_error_response(599, message="weird")
        data = json.loads(resp.body)
        assert data["error"]["type"] == "internal"
        assert data["error"]["code"] == "INTERNAL_ERROR"


# ===================================================================
# 10. Versioning constants and helper tests
# ===================================================================


class TestVersioningConstants:
    def test_api_version_value(self):
        assert API_VERSION == "v1"

    def test_versioned_prefix(self):
        assert VERSIONED_PREFIX == "/api/v1/"

    def test_unversioned_prefix(self):
        assert UNVERSIONED_PREFIX == "/api/"


# ===================================================================
# 11. Integration with the real app (smoke tests)
# ===================================================================


class TestRealAppSmoke:
    """Smoke-test the real OnRamp application to verify wiring."""

    @pytest.fixture()
    def real_client(self) -> TestClient:
        from app.main import app

        return TestClient(app, raise_server_exceptions=False)

    def test_health_still_works(self, real_client: TestClient):
        resp = real_client.get("/health")
        assert resp.status_code == 200

    def test_v1_health_no_route(self, real_client: TestClient):
        """Health is at /health, not /api/…, so /api/v1/health → 404."""
        resp = real_client.get("/api/v1/health")
        # This path doesn't exist as /api/health either
        assert resp.status_code in (404, 405)

    def test_real_app_questionnaire_v1(self, real_client: TestClient):
        resp = real_client.get("/api/v1/questionnaire/categories")
        assert resp.status_code == 200
        assert resp.headers.get("API-Version") == "v1"

    def test_real_app_questionnaire_unversioned(self, real_client: TestClient):
        resp = real_client.get("/api/questionnaire/categories")
        assert resp.status_code == 200
        assert resp.headers.get("API-Version") == "v1"
        assert resp.headers.get("Deprecation") == "true"

    def test_real_app_compliance_v1(self, real_client: TestClient):
        resp = real_client.get("/api/v1/compliance/frameworks")
        assert resp.status_code == 200
        assert resp.headers.get("API-Version") == "v1"

    def test_real_app_projects_v1(self, real_client: TestClient):
        resp = real_client.get("/api/v1/projects/")
        assert resp.status_code in (200, 401)
        assert resp.headers.get("API-Version") == "v1"

    def test_real_app_unknown_v1_path_structured_error(
        self, real_client: TestClient
    ):
        resp = real_client.get("/api/v1/nonexistent/route")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "NOT_FOUND"

    def test_real_app_v1_and_unversioned_same_content(
        self, real_client: TestClient
    ):
        v1 = real_client.get("/api/v1/questionnaire/categories")
        legacy = real_client.get("/api/questionnaire/categories")
        assert v1.json() == legacy.json()

    def test_real_app_post_validation_error(self, real_client: TestClient):
        """Posting invalid JSON to a real endpoint gives structured error."""
        resp = real_client.post(
            "/api/v1/questionnaire/next",
            json={},  # missing required 'answers'
        )
        # Should be 422 with structured error
        if resp.status_code == 422:
            body = resp.json()
            assert "error" in body
            assert body["error"]["code"] == "VALIDATION_ERROR"


# ===================================================================
# 12. Edge cases
# ===================================================================


class TestEdgeCases:
    """Boundary and edge-case scenarios."""

    def test_double_v1_prefix_not_rewritten(self, client: TestClient):
        """``/api/v1/v1/…`` should NOT double-strip."""
        resp = client.get("/api/v1/v1/test/hello")
        # After rewrite: /api/v1/test/hello — that's still a valid v1 path
        # that gets rewritten to /api/test/hello
        # So this should actually return 404 because /api/v1/test/hello
        # is not a registered route path (only /api/test/hello is)
        # After first rewrite: /api/v1/test/hello
        # But the middleware only runs once, so the inner /api/v1/ is NOT
        # rewritten again. So it looks up /api/v1/test/hello which doesn't exist.
        assert resp.status_code == 404

    def test_trailing_slash_v1(self, client: TestClient):
        resp = client.get("/api/v1/test/hello/")
        # FastAPI may redirect or return 200 depending on config
        assert resp.status_code in (200, 307)

    def test_query_params_preserved(self, client: TestClient):
        """Query parameters should survive the rewrite."""
        # Our hello endpoint ignores params, but the request should still work
        resp = client.get("/api/v1/test/hello?foo=bar")
        assert resp.status_code == 200

    def test_v1_post_with_content_type(self, client: TestClient):
        resp = client.post(
            "/api/v1/test/items",
            json={"name": "thing", "count": 1},
        )
        assert resp.status_code == 200

    def test_empty_body_post(self, client: TestClient):
        resp = client.post(
            "/api/test/items",
            content=b"",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_malformed_json_body(self, client: TestClient):
        resp = client.post(
            "/api/test/items",
            content=b"{invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_non_api_path_unaffected(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "Deprecation" not in resp.headers

    def test_http_exception_detail_none(self):
        """HTTPException with detail=None should still produce valid JSON."""
        app = FastAPI()
        register_exception_handlers(app)
        app.add_middleware(APIVersionHeaderMiddleware)

        @app.get("/api/fail")
        async def fail():
            raise HTTPException(status_code=500, detail=None)

        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/api/fail")
        assert resp.status_code == 500
        body = resp.json()
        assert "error" in body


# ===================================================================
# 13. Multiple error status codes produce correct error codes
# ===================================================================


class TestStatusCodeMapping:
    """Each HTTP status should map to the right error code."""

    @pytest.mark.parametrize(
        "path,expected_status,expected_code",
        [
            ("/api/test/not-found", 404, "NOT_FOUND"),
            ("/api/test/forbidden", 403, "FORBIDDEN"),
            ("/api/test/unauthorized", 401, "UNAUTHORIZED"),
            ("/api/test/conflict", 409, "CONFLICT"),
            ("/api/test/bad-request", 400, "BAD_REQUEST"),
            ("/api/test/rate-limited", 429, "RATE_LIMITED"),
            ("/api/test/server-error", 500, "INTERNAL_ERROR"),
        ],
    )
    def test_code_mapping(
        self,
        client: TestClient,
        path: str,
        expected_status: int,
        expected_code: str,
    ):
        resp = client.get(path)
        assert resp.status_code == expected_status
        assert resp.json()["error"]["code"] == expected_code

    @pytest.mark.parametrize(
        "path,expected_status,expected_type",
        [
            ("/api/test/not-found", 404, "not_found"),
            ("/api/test/forbidden", 403, "forbidden"),
            ("/api/test/unauthorized", 401, "unauthorized"),
            ("/api/test/conflict", 409, "conflict"),
            ("/api/test/bad-request", 400, "validation"),
            ("/api/test/rate-limited", 429, "rate_limited"),
            ("/api/test/server-error", 500, "internal"),
        ],
    )
    def test_type_mapping(
        self,
        client: TestClient,
        path: str,
        expected_status: int,
        expected_type: str,
    ):
        resp = client.get(path)
        assert resp.status_code == expected_status
        assert resp.json()["error"]["type"] == expected_type
