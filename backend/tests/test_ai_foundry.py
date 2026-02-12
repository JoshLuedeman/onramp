"""Tests for the AI Foundry client."""

import pytest
from app.services.ai_foundry import AIFoundryClient


@pytest.fixture
def client():
    return AIFoundryClient()


def test_mock_completion(client):
    """Test that mock completion returns valid JSON for architecture prompts."""
    import json

    result = client._mock_completion("You are an architecture expert", "user")
    data = json.loads(result)
    assert "management_groups" in data
    assert "subscriptions" in data
    assert "network_topology" in data


def test_mock_completion_compliance(client):
    """Test that mock completion returns valid JSON for compliance prompts."""
    import json

    result = client._mock_completion("Evaluate compliance of this system", "user")
    data = json.loads(result)
    assert "overall_score" in data
    assert "frameworks" in data


def test_mock_completion_bicep(client):
    """Test that mock completion returns Bicep template for bicep prompts."""
    result = client._mock_completion("Generate Bicep templates", "user")
    assert "bicep" in result.lower() or "targetScope" in result


def test_mock_completion_fallback(client):
    """Test that mock completion returns a fallback for unknown prompts."""
    import json

    result = client._mock_completion("something else", "user")
    data = json.loads(result)
    assert "status" in data


def test_is_configured_false_by_default(client):
    """Test that is_configured is False when no endpoint/key set."""
    assert client.is_configured is False


def test_generate_completion_falls_back_to_mock(client):
    """Test that generate_completion falls back to mock when not configured."""
    import json

    result = client.generate_completion(
        "You are an architecture expert", "design a landing zone"
    )
    data = json.loads(result)
    assert "management_groups" in data
