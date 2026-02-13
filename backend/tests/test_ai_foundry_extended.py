"""Extended tests for AI Foundry client — mock/fallback paths."""

import json
import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_foundry import AIFoundryClient, ai_client


@pytest.fixture
def client():
    return AIFoundryClient()


def test_is_configured_false_by_default(client):
    assert client.is_configured is False


def test_is_configured_true_when_set():
    with patch("app.services.ai_foundry.settings") as mock_settings:
        mock_settings.ai_foundry_endpoint = "https://test.openai.azure.com"
        mock_settings.ai_foundry_key = "test-key"
        c = AIFoundryClient()
        assert c.is_configured is True


def test_get_client_returns_none_when_not_configured(client):
    assert client._get_client() is None


def test_get_async_client_returns_none_when_not_configured(client):
    assert client._get_async_client() is None


@pytest.mark.asyncio
async def test_generate_architecture_mock_mode(client):
    answers = {"org_size": "small", "network_topology": "hub_spoke"}
    result = await client.generate_architecture(answers)
    assert isinstance(result, dict)
    # Mock mode returns a valid architecture dict (may come from archetype fallback)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_evaluate_compliance_mock_mode(client):
    arch = {"management_groups": {"name": "Org"}, "subscriptions": []}
    result = await client.evaluate_compliance(arch, ["SOC2"])
    assert isinstance(result, dict)
    assert "overall_score" in result
    assert "frameworks" in result
    assert result["overall_score"] == 68


@pytest.mark.asyncio
async def test_generate_bicep_mock_mode(client):
    arch = {"management_groups": {"name": "Org"}}
    result = await client.generate_bicep(arch)
    assert isinstance(result, str)
    data = json.loads(result)
    assert "main.bicep" in data


@pytest.mark.asyncio
async def test_estimate_costs_mock_mode(client):
    arch = {"subscriptions": []}
    result = await client.estimate_costs(arch)
    assert isinstance(result, dict)
    assert "estimated_monthly_total_usd" in result
    assert result["estimated_monthly_total_usd"] == 4250
    assert "breakdown" in result
    assert len(result["breakdown"]) > 0


def test_mock_completion_architecture_prompt(client):
    result = client._mock_completion(
        "You are an architecture expert for landing zone design", "design me a zone"
    )
    data = json.loads(result)
    assert isinstance(data, dict)


def test_mock_completion_architecture_with_parsed_answers(client):
    """Architecture prompt with parseable user_prompt lines."""
    user_prompt = "- org_size: small\n- network_topology: hub_spoke\n"
    result = client._mock_completion(
        "You are an architecture expert for landing zone design", user_prompt
    )
    data = json.loads(result)
    assert isinstance(data, dict)


def test_mock_completion_landing_zone_keyword(client):
    """'landing zone' keyword triggers architecture mock."""
    result = client._mock_completion(
        "Design a landing zone", "- org_size: medium\n"
    )
    data = json.loads(result)
    assert isinstance(data, dict)


def test_mock_completion_architecture_no_parseable_answers(client):
    """Architecture mock with no parseable answer lines falls back to archetype."""
    result = client._mock_completion(
        "You are an architecture expert for landing zone design",
        "just some plain text with no dash-colon format"
    )
    data = json.loads(result)
    assert isinstance(data, dict)
    assert isinstance(data, dict)


def test_mock_completion_cost_estimation(client):
    result = client._mock_completion(
        "You are a cost estimation expert", "estimate this"
    )
    data = json.loads(result)
    assert "estimated_monthly_total_usd" in data
    assert "cost_optimization_tips" in data


def test_mock_completion_compliance_evaluation(client):
    result = client._mock_completion(
        "Evaluate compliance of this architecture", "check it"
    )
    data = json.loads(result)
    assert "overall_score" in data
    assert "top_recommendations" in data


def test_mock_completion_bicep_generation(client):
    result = client._mock_completion("Generate Bicep templates", "do it")
    data = json.loads(result)
    assert "main.bicep" in data
    assert "targetScope" in data["main.bicep"]


def test_mock_completion_unknown_prompt(client):
    result = client._mock_completion("random prompt", "random user prompt")
    data = json.loads(result)
    assert data["status"] == "mock response"


def test_generate_completion_falls_back_to_mock(client):
    result = client.generate_completion(
        "Evaluate compliance and check", "evaluate this"
    )
    data = json.loads(result)
    assert "overall_score" in data


@pytest.mark.asyncio
async def test_generate_completion_async_falls_back_to_mock(client):
    result = await client.generate_completion_async(
        "You are an architecture expert", "build me a landing zone"
    )
    data = json.loads(result)
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_stream_completion_mock_mode(client):
    chunks = []
    async for chunk in client.stream_completion(
        "You are an architecture expert", "design a landing zone"
    ):
        chunks.append(chunk)
    assert len(chunks) > 0
    full = "".join(chunks)
    assert len(full) > 0


@pytest.mark.asyncio
async def test_generate_architecture_json_parse_error():
    """When mock returns non-JSON for architecture, falls back to archetype."""
    c = AIFoundryClient()
    with patch.object(c, "generate_completion", return_value="not-json"):
        result = await c.generate_architecture({"org_size": "small"})
        assert isinstance(result, dict)
        assert "management_groups" in result or "subscriptions" in result


@pytest.mark.asyncio
async def test_evaluate_compliance_json_parse_error():
    c = AIFoundryClient()
    with patch.object(c, "generate_completion", return_value="not-json"):
        result = await c.evaluate_compliance({}, ["SOC2"])
        assert "error" in result
        assert "raw" in result


@pytest.mark.asyncio
async def test_estimate_costs_json_parse_error():
    c = AIFoundryClient()
    with patch.object(c, "generate_completion", return_value="not-json"):
        result = await c.estimate_costs({})
        assert "error" in result
        assert "raw" in result


def test_singleton_exists():
    assert ai_client is not None
    assert isinstance(ai_client, AIFoundryClient)


def test_get_client_import_error():
    """If openai not installed, _get_client returns None."""
    with patch("app.services.ai_foundry.settings") as mock_settings:
        mock_settings.ai_foundry_endpoint = "https://test.openai.azure.com"
        mock_settings.ai_foundry_key = "test-key"
        c = AIFoundryClient()
        with patch.dict("sys.modules", {"openai": None}):
            result = c._get_client()
            assert result is None


def test_get_async_client_import_error():
    """If openai not installed, _get_async_client returns None."""
    with patch("app.services.ai_foundry.settings") as mock_settings:
        mock_settings.ai_foundry_endpoint = "https://test.openai.azure.com"
        mock_settings.ai_foundry_key = "test-key"
        c = AIFoundryClient()
        with patch.dict("sys.modules", {"openai": None}):
            result = c._get_async_client()
            assert result is None
