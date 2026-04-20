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


def test_is_configured_true_with_key():
    """is_configured returns True when endpoint + key are set."""
    from unittest.mock import patch

    with patch("app.services.ai_foundry.settings") as mock_settings:
        mock_settings.ai_foundry_endpoint = "https://ai.example.com"
        mock_settings.ai_foundry_key = "test-key"
        mock_settings.managed_identity_client_id = ""
        c = AIFoundryClient()
        assert c.is_configured is True
        assert c._use_mi_auth is False


def test_is_configured_true_with_mi():
    """is_configured returns True when endpoint + MI client ID set (no key)."""
    from unittest.mock import patch

    with patch("app.services.ai_foundry.settings") as mock_settings:
        mock_settings.ai_foundry_endpoint = "https://ai.example.com"
        mock_settings.ai_foundry_key = ""
        mock_settings.managed_identity_client_id = "mi-client-id"
        c = AIFoundryClient()
        assert c.is_configured is True
        assert c._use_mi_auth is True


def test_is_configured_false_without_auth():
    """is_configured returns False when endpoint set but no key or MI."""
    from unittest.mock import patch

    with patch("app.services.ai_foundry.settings") as mock_settings:
        mock_settings.ai_foundry_endpoint = "https://ai.example.com"
        mock_settings.ai_foundry_key = ""
        mock_settings.managed_identity_client_id = ""
        c = AIFoundryClient()
        assert c.is_configured is False


async def test_close_cleans_up():
    """close() resets internal state without errors."""
    c = AIFoundryClient()
    await c.close()
    assert c._client is None
    assert c._async_client is None
    assert c._async_token_provider is None
