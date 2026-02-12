"""Tests for startup validation."""

from app.startup import validate_environment


def test_validate_environment_dev_mode():
    """In dev mode (no env vars), should return development mode with warnings."""
    result = validate_environment()
    assert result["mode"] == "development"
    assert result["auth"] == "mock"
    assert result["ai"] == "mock"
    assert len(result["warnings"]) > 0
    assert len(result["errors"]) == 0
