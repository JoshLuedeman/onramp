"""Tests for the AI Foundry client."""

import pytest
from app.services.ai_foundry import AIFoundryClient


@pytest.fixture
def client():
    return AIFoundryClient()


def test_mock_completion(client):
    """Test that mock completion returns valid JSON."""
    import json

    result = client._mock_completion("system", "user")
    data = json.loads(result)
    assert "management_groups" in data
    assert "subscriptions" in data
    assert "network_topology" in data


def test_default_architecture(client):
    """Test the default architecture structure."""
    arch = client._get_default_architecture()

    assert arch["organization_size"] == "medium"
    assert "management_groups" in arch
    assert "subscriptions" in arch
    assert len(arch["subscriptions"]) > 0
    assert "network_topology" in arch
    assert arch["network_topology"]["type"] == "hub-spoke"
    assert "identity" in arch
    assert "security" in arch
    assert "governance" in arch
    assert "management" in arch
    assert "recommendations" in arch
    assert isinstance(arch["estimated_monthly_cost_usd"], int)


def test_architecture_system_prompt(client):
    """Test that the system prompt covers all CAF design areas."""
    prompt = client._get_architecture_system_prompt()
    assert "Billing" in prompt
    assert "Identity" in prompt
    assert "Resource Organization" in prompt
    assert "Network" in prompt
    assert "Security" in prompt
    assert "Management" in prompt
    assert "Governance" in prompt
    assert "Automation" in prompt


def test_format_architecture_request(client):
    """Test formatting of architecture request."""
    answers = {"org_size": "small", "industry": "healthcare"}
    result = client._format_architecture_request(answers)
    assert "healthcare" in result
    assert "small" in result
