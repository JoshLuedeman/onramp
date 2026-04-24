"""Tests for the policy generation service and API routes.

Covers: policy generation (mock & AI modes), policy validation,
template library, and all route endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.policy import (
    PolicyDefinition,
    PolicyGenerateRequest,
    PolicyLibraryResponse,
    PolicyTemplate,
    PolicyValidationResult,
    PolicyApplyRequest,
)
from app.services.policy_generator import (
    PolicyGenerator,
    policy_generator,
    _mock_policy,
    POLICY_TEMPLATES,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def generator() -> PolicyGenerator:
    return PolicyGenerator()


@pytest.fixture()
def valid_policy() -> dict:
    return {
        "name": "require-tags",
        "display_name": "Require Tags",
        "description": "Enforce mandatory tags on resources.",
        "mode": "All",
        "policy_rule": {
            "if": {
                "field": "tags['CostCenter']",
                "exists": "false",
            },
            "then": {"effect": "Deny"},
        },
        "parameters": {},
        "metadata": {"category": "Tags"},
    }


@pytest.fixture()
def invalid_policy_no_name() -> dict:
    return {
        "display_name": "Missing Name",
        "policy_rule": {
            "if": {"field": "type", "equals": "Microsoft.Compute/virtualMachines"},
            "then": {"effect": "Deny"},
        },
    }


@pytest.fixture()
def invalid_policy_no_rule() -> dict:
    return {
        "name": "missing-rule",
        "display_name": "Missing Rule",
    }


@pytest.fixture()
def invalid_policy_no_if() -> dict:
    return {
        "name": "no-if",
        "policy_rule": {
            "then": {"effect": "Audit"},
        },
    }


@pytest.fixture()
def invalid_policy_no_then() -> dict:
    return {
        "name": "no-then",
        "policy_rule": {
            "if": {"field": "type", "equals": "Microsoft.Storage/storageAccounts"},
        },
    }


@pytest.fixture()
def invalid_policy_no_effect() -> dict:
    return {
        "name": "no-effect",
        "policy_rule": {
            "if": {"field": "type", "equals": "Microsoft.Storage/storageAccounts"},
            "then": {},
        },
    }


# ── Schema Tests ─────────────────────────────────────────────────────────────


class TestPolicySchemas:
    def test_policy_generate_request_minimal(self):
        req = PolicyGenerateRequest(description="Block public IPs")
        assert req.description == "Block public IPs"
        assert req.context is None

    def test_policy_generate_request_with_context(self):
        req = PolicyGenerateRequest(
            description="Enforce tags",
            context={"environment": "production"},
        )
        assert req.context == {"environment": "production"}

    def test_policy_definition_defaults(self):
        pd = PolicyDefinition(name="test-policy")
        assert pd.name == "test-policy"
        assert pd.mode == "All"
        assert pd.policy_rule == {}
        assert pd.parameters == {}
        assert pd.metadata == {}

    def test_policy_definition_full(self, valid_policy):
        pd = PolicyDefinition(**valid_policy)
        assert pd.name == "require-tags"
        assert pd.display_name == "Require Tags"
        assert "if" in pd.policy_rule
        assert pd.metadata["category"] == "Tags"

    def test_policy_definition_allows_extra_fields(self):
        pd = PolicyDefinition(name="extra", extra_field="test")
        assert pd.model_dump()["extra_field"] == "test"

    def test_policy_validation_result_valid(self):
        r = PolicyValidationResult(valid=True)
        assert r.valid is True
        assert r.errors == []
        assert r.warnings == []

    def test_policy_validation_result_invalid(self):
        r = PolicyValidationResult(valid=False, errors=["missing name"])
        assert r.valid is False
        assert len(r.errors) == 1

    def test_policy_template_schema(self):
        t = PolicyTemplate(
            id="test-1",
            name="Test",
            description="A test",
            category="General",
            policy_json={"name": "test-1"},
        )
        assert t.id == "test-1"
        assert t.policy_json["name"] == "test-1"

    def test_policy_library_response(self):
        resp = PolicyLibraryResponse(
            policies=[
                PolicyTemplate(
                    id="t1", name="T1", description="d", category="c", policy_json={}
                )
            ]
        )
        assert len(resp.policies) == 1

    def test_policy_apply_request_minimal(self):
        req = PolicyApplyRequest(policy={"name": "test"})
        assert req.architecture_id is None

    def test_policy_apply_request_with_arch_id(self):
        req = PolicyApplyRequest(policy={"name": "test"}, architecture_id="arch-1")
        assert req.architecture_id == "arch-1"


# ── Mock Policy Helper Tests ────────────────────────────────────────────────


class TestMockPolicy:
    def test_mock_policy_has_required_fields(self):
        result = _mock_policy("Deny public IPs in production")
        assert result["name"]
        assert result["display_name"]
        assert result["description"] == "Deny public IPs in production"
        assert result["mode"] == "All"
        assert "if" in result["policy_rule"]
        assert "then" in result["policy_rule"]
        assert result["policy_rule"]["then"]["effect"] == "Audit"

    def test_mock_policy_includes_context(self):
        ctx = {"environment": "staging"}
        result = _mock_policy("Test policy", context=ctx)
        assert result["metadata"]["context"] == ctx

    def test_mock_policy_name_is_truncated_kebab(self):
        long_desc = "A" * 100
        result = _mock_policy(long_desc)
        assert len(result["name"]) <= 50

    def test_mock_policy_none_context(self):
        result = _mock_policy("Simple rule")
        assert result["metadata"]["context"] == {}


# ── Validation Tests ─────────────────────────────────────────────────────────


class TestPolicyValidation:
    def test_valid_policy_passes(self, generator, valid_policy):
        result = generator.validate_policy_json(valid_policy)
        assert result.valid is True
        assert result.errors == []

    def test_missing_name_fails(self, generator, invalid_policy_no_name):
        result = generator.validate_policy_json(invalid_policy_no_name)
        assert result.valid is False
        assert any("name" in e for e in result.errors)

    def test_missing_policy_rule_fails(self, generator, invalid_policy_no_rule):
        result = generator.validate_policy_json(invalid_policy_no_rule)
        assert result.valid is False
        assert any("policy_rule" in e for e in result.errors)

    def test_missing_if_condition_fails(self, generator, invalid_policy_no_if):
        result = generator.validate_policy_json(invalid_policy_no_if)
        assert result.valid is False
        assert any("if" in e for e in result.errors)

    def test_missing_then_action_fails(self, generator, invalid_policy_no_then):
        result = generator.validate_policy_json(invalid_policy_no_then)
        assert result.valid is False
        assert any("then" in e for e in result.errors)

    def test_missing_effect_fails(self, generator, invalid_policy_no_effect):
        result = generator.validate_policy_json(invalid_policy_no_effect)
        assert result.valid is False
        assert any("effect" in e for e in result.errors)

    def test_invalid_effect_warns(self, generator):
        policy = {
            "name": "bad-effect",
            "policy_rule": {
                "if": {"field": "type", "equals": "Microsoft.Compute/virtualMachines"},
                "then": {"effect": "CustomEffect"},
            },
        }
        result = generator.validate_policy_json(policy)
        assert result.valid is True
        assert any("CustomEffect" in w for w in result.warnings)

    def test_invalid_mode_warns(self, generator):
        policy = {
            "name": "bad-mode",
            "mode": "CustomMode",
            "policy_rule": {
                "if": {"field": "type", "equals": "Microsoft.Compute/virtualMachines"},
                "then": {"effect": "Deny"},
            },
        }
        result = generator.validate_policy_json(policy)
        assert result.valid is True
        assert any("CustomMode" in w for w in result.warnings)

    def test_indexed_mode_passes(self, generator):
        policy = {
            "name": "indexed-mode",
            "mode": "Indexed",
            "policy_rule": {
                "if": {"field": "location", "notIn": ["eastus"]},
                "then": {"effect": "Deny"},
            },
        }
        result = generator.validate_policy_json(policy)
        assert result.valid is True
        assert result.warnings == []

    def test_policy_rule_not_dict_fails(self, generator):
        policy = {"name": "bad-rule", "policy_rule": "not-a-dict"}
        result = generator.validate_policy_json(policy)
        assert result.valid is False
        assert any("JSON object" in e for e in result.errors)

    def test_then_not_dict_fails(self, generator):
        policy = {
            "name": "bad-then",
            "policy_rule": {
                "if": {"field": "type", "equals": "Microsoft.Compute/virtualMachines"},
                "then": "not-a-dict",
            },
        }
        result = generator.validate_policy_json(policy)
        assert result.valid is False
        assert any("JSON object" in e for e in result.errors)

    def test_empty_policy_multiple_errors(self, generator):
        result = generator.validate_policy_json({})
        assert result.valid is False
        assert len(result.errors) >= 2  # name + policy_rule

    def test_valid_policy_with_parameters(self, generator):
        policy = {
            "name": "with-params",
            "mode": "All",
            "policy_rule": {
                "if": {"field": "type", "equals": "Microsoft.Compute/virtualMachines"},
                "then": {"effect": "Deny"},
            },
            "parameters": {
                "allowedSizes": {
                    "type": "Array",
                    "defaultValue": ["Standard_B2s"],
                }
            },
        }
        result = generator.validate_policy_json(policy)
        assert result.valid is True


# ── Template Library Tests ───────────────────────────────────────────────────


class TestPolicyLibrary:
    def test_library_returns_templates(self, generator):
        templates = generator.get_policy_library()
        assert len(templates) >= 10

    def test_library_templates_are_policy_template_type(self, generator):
        templates = generator.get_policy_library()
        for t in templates:
            assert isinstance(t, PolicyTemplate)

    def test_library_templates_have_required_fields(self, generator):
        templates = generator.get_policy_library()
        for t in templates:
            assert t.id
            assert t.name
            assert t.description
            assert t.category
            assert isinstance(t.policy_json, dict)

    def test_library_templates_have_valid_policy_json(self, generator):
        templates = generator.get_policy_library()
        for t in templates:
            result = generator.validate_policy_json(t.policy_json)
            assert result.valid is True, (
                f"Template '{t.id}' has invalid policy_json: {result.errors}"
            )

    def test_library_has_diverse_categories(self, generator):
        templates = generator.get_policy_library()
        categories = {t.category for t in templates}
        assert len(categories) >= 4

    def test_library_unique_ids(self, generator):
        templates = generator.get_policy_library()
        ids = [t.id for t in templates]
        assert len(ids) == len(set(ids))

    def test_library_templates_match_raw_data(self, generator):
        templates = generator.get_policy_library()
        assert len(templates) == len(POLICY_TEMPLATES)


# ── Policy Generation Tests (Dev / Mock Mode) ───────────────────────────────


class TestPolicyGeneration:
    @pytest.mark.asyncio()
    async def test_generate_returns_policy_definition(self, generator):
        with patch("app.services.policy_generator.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            mock_settings.ai_foundry_endpoint = ""
            result = await generator.generate_policy("Deny public IP creation")
            assert isinstance(result, PolicyDefinition)
            assert result.name

    @pytest.mark.asyncio()
    async def test_generate_mock_preserves_description(self, generator):
        with patch("app.services.policy_generator.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            mock_settings.ai_foundry_endpoint = ""
            result = await generator.generate_policy("Require encryption on storage")
            assert "encryption" in result.description.lower() or "storage" in result.description.lower()

    @pytest.mark.asyncio()
    async def test_generate_mock_with_context(self, generator):
        with patch("app.services.policy_generator.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            mock_settings.ai_foundry_endpoint = ""
            ctx = {"environment": "production"}
            result = await generator.generate_policy("Block VMs", context=ctx)
            assert isinstance(result, PolicyDefinition)

    @pytest.mark.asyncio()
    async def test_generate_falls_back_on_ai_error(self, generator):
        """When the AI import/client fails, the generator falls back to mock."""
        with patch("app.services.policy_generator.settings") as mock_settings:
            mock_settings.is_dev_mode = False
            mock_settings.ai_foundry_endpoint = "https://fake.openai.azure.com"
            with patch(
                "app.services.ai_foundry.ai_client",
            ) as mock_client:
                mock_client.generate_completion_async = AsyncMock(
                    side_effect=Exception("AI unavailable"),
                )
                result = await generator.generate_policy("Test policy")
                assert isinstance(result, PolicyDefinition)

    @pytest.mark.asyncio()
    async def test_generate_dev_mode_returns_valid_structure(self, generator):
        with patch("app.services.policy_generator.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            mock_settings.ai_foundry_endpoint = ""
            result = await generator.generate_policy("Enforce HTTPS")
            assert result.mode == "All"
            assert result.policy_rule.get("if")
            assert result.policy_rule.get("then")


# ── AI Integration Tests ─────────────────────────────────────────────────────


class TestAIIntegration:
    @pytest.mark.asyncio()
    async def test_ai_generation_success_path(self, generator):
        """Test the AI path returns a valid policy when the AI client succeeds."""
        mock_ai_response = '{"name":"ai-policy","display_name":"AI Policy","description":"test","mode":"All","policy_rule":{"if":{"field":"type","equals":"Microsoft.Compute/virtualMachines"},"then":{"effect":"Deny"}},"parameters":{},"metadata":{"category":"Compute"}}'

        with patch("app.services.policy_generator.settings") as mock_settings:
            mock_settings.is_dev_mode = False
            mock_settings.ai_foundry_endpoint = "https://fake.openai.azure.com"
            with patch("app.services.ai_foundry.ai_client") as mock_client:
                mock_client.generate_completion_async = AsyncMock(
                    return_value=mock_ai_response
                )
                result = await generator.generate_policy("Deny VMs")
                assert isinstance(result, PolicyDefinition)
                assert result.name == "ai-policy"

    @pytest.mark.asyncio()
    async def test_ai_generation_invalid_json_falls_back(self, generator):
        """When AI returns invalid JSON, the generator falls back to mock."""
        with patch("app.services.policy_generator.settings") as mock_settings:
            mock_settings.is_dev_mode = False
            mock_settings.ai_foundry_endpoint = "https://fake.openai.azure.com"
            with patch("app.services.ai_foundry.ai_client") as mock_client:
                mock_client.generate_completion_async = AsyncMock(
                    return_value="not valid json {"
                )
                result = await generator.generate_policy("Test policy")
                assert isinstance(result, PolicyDefinition)

    @pytest.mark.asyncio()
    async def test_ai_generation_validation_failure_falls_back(self, generator):
        """When AI returns valid JSON that fails policy validation, fall back to mock."""
        bad_policy = '{"name":"","display_name":"","description":"","mode":"All","policy_rule":{},"parameters":{}}'

        with patch("app.services.policy_generator.settings") as mock_settings:
            mock_settings.is_dev_mode = False
            mock_settings.ai_foundry_endpoint = "https://fake.openai.azure.com"
            with patch("app.services.ai_foundry.ai_client") as mock_client:
                mock_client.generate_completion_async = AsyncMock(
                    return_value=bad_policy
                )
                result = await generator.generate_policy("Test")
                assert isinstance(result, PolicyDefinition)

    def test_ai_validator_integration_valid(self):
        """Verify valid policy passes the ai_validator.validate_policy()."""
        from app.services.ai_validator import ai_validator

        data = {
            "name": "test-policy",
            "display_name": "Test",
            "description": "A test",
            "mode": "All",
            "policy_rule": {
                "if": {"field": "type", "equals": "Microsoft.Compute/virtualMachines"},
                "then": {"effect": "Deny"},
            },
            "parameters": {},
        }
        result = ai_validator.validate_policy(data)
        assert result.success is True

    def test_ai_validator_integration_missing_name(self):
        """Verify policy without name fails ai_validator."""
        from app.services.ai_validator import ai_validator

        data = {"policy_rule": {}}
        result = ai_validator.validate_policy(data)
        assert result.success is False


# ── Route Tests ──────────────────────────────────────────────────────────────


class TestPolicyRoutes:
    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient
        from app.api.routes.policies import router

        from fastapi import FastAPI

        test_app = FastAPI()
        test_app.include_router(router)

        # Override auth dependency
        from app.auth import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: {
            "sub": "test-user",
            "tid": "test-tenant",
        }

        return TestClient(test_app)

    def test_generate_endpoint(self, client):
        resp = client.post(
            "/api/policies/generate",
            json={"description": "Deny public IP addresses"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "policy" in data
        assert data["policy"]["name"]

    def test_generate_endpoint_with_context(self, client):
        resp = client.post(
            "/api/policies/generate",
            json={
                "description": "Enforce encryption",
                "context": {"environment": "production"},
            },
        )
        assert resp.status_code == 200
        assert "policy" in resp.json()

    def test_validate_endpoint_valid(self, client, valid_policy):
        resp = client.post(
            "/api/policies/validate",
            json={"policy": valid_policy},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True

    def test_validate_endpoint_invalid(self, client):
        resp = client.post(
            "/api/policies/validate",
            json={"policy": {"description": "No name or rule"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_library_endpoint(self, client):
        resp = client.get("/api/policies/library")
        assert resp.status_code == 200
        data = resp.json()
        assert "policies" in data
        assert len(data["policies"]) >= 10

    def test_library_template_structure(self, client):
        resp = client.get("/api/policies/library")
        data = resp.json()
        template = data["policies"][0]
        assert "id" in template
        assert "name" in template
        assert "description" in template
        assert "category" in template
        assert "policy_json" in template

    def test_apply_endpoint_success(self, client, valid_policy):
        resp = client.post(
            "/api/policies/apply",
            json={"policy": valid_policy, "architecture_id": "arch-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "applied"
        assert data["policy_name"] == "require-tags"
        assert data["architecture_id"] == "arch-1"

    def test_apply_endpoint_invalid_policy(self, client):
        resp = client.post(
            "/api/policies/apply",
            json={"policy": {"description": "Invalid"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert len(data["errors"]) > 0

    def test_apply_endpoint_no_architecture_id(self, client, valid_policy):
        resp = client.post(
            "/api/policies/apply",
            json={"policy": valid_policy},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "applied"
        assert data["architecture_id"] is None

    def test_generate_endpoint_empty_description(self, client):
        resp = client.post(
            "/api/policies/generate",
            json={"description": ""},
        )
        # Empty description is rejected by validation constraints
        assert resp.status_code == 422

    def test_validate_endpoint_empty_policy(self, client):
        resp = client.post(
            "/api/policies/validate",
            json={"policy": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False


# ── Singleton Tests ──────────────────────────────────────────────────────────


class TestSingleton:
    def test_module_singleton_exists(self):
        assert policy_generator is not None
        assert isinstance(policy_generator, PolicyGenerator)

    def test_singleton_has_generate_method(self):
        assert hasattr(policy_generator, "generate_policy")

    def test_singleton_has_validate_method(self):
        assert hasattr(policy_generator, "validate_policy_json")

    def test_singleton_has_library_method(self):
        assert hasattr(policy_generator, "get_policy_library")
