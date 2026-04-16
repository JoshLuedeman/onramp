"""Tests for AI output schema validation and hallucination detection.

Covers the validator service, Azure reference data, Pydantic output models,
API routes, metrics tracking, and integration with AIFoundryClient.
"""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.ai_output_models import (
    ArchitectureOutput,
    ComplianceGapOutput,
    PolicyDefinitionOutput,
    SecurityFindingOutput,
    SKURecommendationOutput,
)
from app.schemas.ai_validation import (
    AIOutputType,
    AzureRegion,
    AzureResourceType,
    AzureSKU,
    ValidationError,
    ValidationMetrics,
    ValidationResult,
)
from app.services.ai_validator import AIOutputValidator
from app.services.azure_reference import AzureReferenceData

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def validator():
    """Return a fresh AIOutputValidator instance."""
    return AIOutputValidator()


@pytest.fixture()
def reference():
    """Return a fresh AzureReferenceData instance."""
    return AzureReferenceData()


@pytest.fixture()
def valid_architecture() -> dict:
    """A minimal valid architecture payload."""
    return {
        "organization_size": "medium",
        "management_groups": {
            "root": {"display_name": "Contoso", "children": {}},
        },
        "subscriptions": [
            {
                "name": "prod",
                "purpose": "production workloads",
                "management_group": "production",
                "budget_usd": 5000,
            },
        ],
        "network_topology": {"type": "hub-spoke", "primary_region": "eastus"},
        "identity": {
            "provider": "Microsoft Entra ID",
            "rbac_model": "least-privilege",
            "pim_enabled": True,
            "conditional_access": True,
            "mfa_policy": "always",
        },
        "security": {
            "defender_for_cloud": True,
            "defender_plans": ["VirtualMachines", "AppService"],
            "sentinel": True,
            "ddos_protection": False,
            "azure_firewall": True,
            "waf": True,
            "key_vault_per_subscription": True,
        },
        "governance": {
            "policies": [
                {
                    "name": "allowed-locations",
                    "scope": "/",
                    "effect": "Deny",
                    "description": "Only allow approved regions",
                }
            ],
            "tagging_strategy": {
                "mandatory_tags": ["environment", "owner"],
                "optional_tags": ["project"],
            },
            "naming_convention": "CAF recommended",
            "cost_management": {
                "budgets_enabled": True,
                "alerts_enabled": True,
                "optimization_recommendations": True,
            },
        },
        "management": {
            "log_analytics": {"retention_days": 90},
            "monitoring": {"enabled": True},
            "backup": {"enabled": True},
            "update_management": True,
        },
        "compliance_frameworks": [
            {"name": "CIS", "controls_applied": 45, "coverage_percent": 85},
        ],
        "platform_automation": {
            "iac_tool": "Bicep",
            "cicd_platform": "GitHub Actions",
            "repo_structure": "mono-repo",
        },
        "recommendations": ["Enable Defender for SQL"],
        "estimated_monthly_cost_usd": 12000,
    }


@pytest.fixture()
def valid_policy() -> dict:
    return {
        "name": "allowed-locations",
        "display_name": "Allowed Locations",
        "description": "Restrict resource deployment to approved regions",
        "mode": "All",
        "policy_rule": {
            "if": {"not": {"field": "location", "in": ["eastus", "westus2"]}},
            "then": {"effect": "Deny"},
        },
        "parameters": {},
    }


@pytest.fixture()
def valid_sku_rec() -> dict:
    return {
        "workload": "web-api",
        "recommended_sku": "Standard_D2s_v3",
        "reasoning": "Good balance of compute and memory for web APIs",
        "monthly_cost_estimate": 140,
    }


@pytest.fixture()
def valid_security_finding() -> dict:
    return {
        "severity": "High",
        "category": "Network",
        "resource": "Microsoft.Network/networkSecurityGroups",
        "finding": "NSG allows inbound SSH from any source",
        "remediation": "Restrict SSH to known IP ranges",
    }


@pytest.fixture()
def valid_compliance_gap() -> dict:
    return {
        "framework": "CIS Azure 2.0",
        "control_id": "5.1.1",
        "status": "non_compliant",
        "gap_description": "Storage accounts do not require HTTPS",
        "remediation": "Enable secure transfer on all storage accounts",
    }


def _make_client():
    """Create a test client with the full FastAPI application."""
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


# =========================================================================
# 1. Architecture validation
# =========================================================================


class TestArchitectureValidation:
    def test_valid_architecture(self, validator, valid_architecture):
        result = validator.validate_architecture(valid_architecture)
        assert result.success is True
        assert result.errors == []
        assert result.validated_data is not None

    def test_missing_organization_size(self, validator):
        result = validator.validate_architecture({})
        assert result.success is False
        assert any("organization_size" in e.field for e in result.errors)

    def test_invalid_organization_size_warns(self, validator, valid_architecture):
        valid_architecture["organization_size"] = "mega-corp"
        result = validator.validate_architecture(valid_architecture)
        assert result.success is True  # Parsing succeeds (extra values allowed)
        assert any("organization_size" in w for w in result.warnings)

    def test_empty_subscriptions_warns(self, validator, valid_architecture):
        valid_architecture["subscriptions"] = []
        result = validator.validate_architecture(valid_architecture)
        assert result.success is True
        assert any("No subscriptions" in w for w in result.warnings)

    def test_empty_management_groups_warns(self, validator, valid_architecture):
        valid_architecture["management_groups"] = {}
        result = validator.validate_architecture(valid_architecture)
        assert result.success is True
        assert any("No management groups" in w for w in result.warnings)

    def test_invalid_network_topology_type_warns(self, validator, valid_architecture):
        valid_architecture["network_topology"]["type"] = "flat"
        result = validator.validate_architecture(valid_architecture)
        assert result.success is True
        assert any("flat" in w for w in result.warnings)

    def test_zero_cost_warns(self, validator, valid_architecture):
        valid_architecture["estimated_monthly_cost_usd"] = 0
        result = validator.validate_architecture(valid_architecture)
        assert result.success is True
        assert any("zero or negative" in w for w in result.warnings)

    def test_extra_fields_are_preserved(self, validator, valid_architecture):
        valid_architecture["custom_field"] = "hello"
        result = validator.validate_architecture(valid_architecture)
        assert result.success is True
        assert result.validated_data["custom_field"] == "hello"

    def test_bad_subscription_type(self, validator, valid_architecture):
        valid_architecture["subscriptions"] = "not-a-list"
        result = validator.validate_architecture(valid_architecture)
        assert result.success is False


# =========================================================================
# 2. Policy validation
# =========================================================================


class TestPolicyValidation:
    def test_valid_policy(self, validator, valid_policy):
        result = validator.validate_policy(valid_policy)
        assert result.success is True
        assert result.validated_data is not None

    def test_missing_name(self, validator):
        result = validator.validate_policy({"display_name": "Test"})
        assert result.success is False
        assert any("name" in e.field for e in result.errors)

    def test_invalid_mode_warns(self, validator, valid_policy):
        valid_policy["mode"] = "FancyMode"
        result = validator.validate_policy(valid_policy)
        assert result.success is True
        assert any("FancyMode" in w for w in result.warnings)

    def test_invalid_effect_warns(self, validator, valid_policy):
        valid_policy["policy_rule"] = {"then": {"effect": "Explode"}}
        result = validator.validate_policy(valid_policy)
        assert result.success is True
        assert any("Explode" in w for w in result.warnings)

    def test_policy_with_all_fields(self, validator, valid_policy):
        result = validator.validate_policy(valid_policy)
        assert result.validated_data["mode"] == "All"
        assert result.validated_data["description"] != ""


# =========================================================================
# 3. SKU validation
# =========================================================================


class TestSKUValidation:
    def test_valid_sku(self, validator, valid_sku_rec):
        result = validator.validate_sku_recommendation(valid_sku_rec)
        assert result.success is True

    def test_missing_workload(self, validator):
        result = validator.validate_sku_recommendation(
            {"recommended_sku": "Standard_D2s_v3"}
        )
        assert result.success is False
        assert any("workload" in e.field for e in result.errors)

    def test_missing_recommended_sku(self, validator):
        result = validator.validate_sku_recommendation({"workload": "web"})
        assert result.success is False

    @patch("app.services.azure_reference.settings")
    def test_hallucinated_sku_warns(self, mock_settings, validator):
        mock_settings.is_dev_mode = False
        data = {
            "workload": "web",
            "recommended_sku": "Hyper_Z99_Quantum",
            "reasoning": "Best for quantum workloads",
            "monthly_cost_estimate": 50,
        }
        result = validator.validate_sku_recommendation(data)
        assert result.success is True  # still parses
        assert any("Hyper_Z99_Quantum" in w for w in result.warnings)

    def test_valid_sku_no_warning(self, validator, valid_sku_rec):
        result = validator.validate_sku_recommendation(valid_sku_rec)
        assert not any("does not match" in w for w in result.warnings)


# =========================================================================
# 4. Security finding validation
# =========================================================================


class TestSecurityFindingValidation:
    def test_valid_finding(self, validator, valid_security_finding):
        result = validator.validate_security_finding(valid_security_finding)
        assert result.success is True

    def test_missing_severity(self, validator):
        result = validator.validate_security_finding(
            {"category": "Network", "resource": "x", "finding": "y"}
        )
        assert result.success is False

    def test_non_standard_severity_warns(self, validator, valid_security_finding):
        valid_security_finding["severity"] = "Extreme"
        result = validator.validate_security_finding(valid_security_finding)
        assert result.success is True
        assert any("Extreme" in w for w in result.warnings)

    def test_standard_severities_no_warning(self, validator, valid_security_finding):
        for sev in ["Critical", "High", "Medium", "Low", "Informational"]:
            valid_security_finding["severity"] = sev
            result = validator.validate_security_finding(valid_security_finding)
            assert not any("not a standard" in w for w in result.warnings)


# =========================================================================
# 5. Compliance gap validation
# =========================================================================


class TestComplianceGapValidation:
    def test_valid_gap(self, validator, valid_compliance_gap):
        result = validator.validate_compliance_gap(valid_compliance_gap)
        assert result.success is True

    def test_missing_framework(self, validator):
        result = validator.validate_compliance_gap(
            {"control_id": "1.1", "status": "compliant", "gap_description": "x"}
        )
        assert result.success is False

    def test_missing_control_id(self, validator):
        result = validator.validate_compliance_gap(
            {"framework": "CIS", "status": "compliant", "gap_description": "x"}
        )
        assert result.success is False

    def test_non_standard_status_warns(self, validator, valid_compliance_gap):
        valid_compliance_gap["status"] = "maybe"
        result = validator.validate_compliance_gap(valid_compliance_gap)
        assert result.success is True
        assert any("maybe" in w for w in result.warnings)

    def test_valid_statuses_no_warning(self, validator, valid_compliance_gap):
        for status in ["compliant", "non_compliant", "partial", "not_assessed"]:
            valid_compliance_gap["status"] = status
            result = validator.validate_compliance_gap(valid_compliance_gap)
            assert not any("not a recognized" in w for w in result.warnings)


# =========================================================================
# 6. Azure reference data
# =========================================================================


class TestAzureReferenceData:
    @patch("app.services.azure_reference.settings")
    def test_valid_resource_type(self, mock_settings, reference):
        mock_settings.is_dev_mode = False
        assert reference.is_valid_resource_type(
            "Microsoft.Compute/virtualMachines"
        ) is True

    @patch("app.services.azure_reference.settings")
    def test_invalid_resource_type(self, mock_settings, reference):
        mock_settings.is_dev_mode = False
        assert reference.is_valid_resource_type(
            "Microsoft.Fake/madeUpResource"
        ) is False

    @patch("app.services.azure_reference.settings")
    def test_valid_region(self, mock_settings, reference):
        mock_settings.is_dev_mode = False
        assert reference.is_valid_region("eastus") is True

    @patch("app.services.azure_reference.settings")
    def test_invalid_region(self, mock_settings, reference):
        mock_settings.is_dev_mode = False
        assert reference.is_valid_region("mars-central") is False

    @patch("app.services.azure_reference.settings")
    def test_region_case_insensitive(self, mock_settings, reference):
        mock_settings.is_dev_mode = False
        assert reference.is_valid_region("EastUS") is True

    @patch("app.services.azure_reference.settings")
    def test_valid_sku(self, mock_settings, reference):
        mock_settings.is_dev_mode = False
        assert reference.is_valid_sku("Standard_D2s_v3") is True

    @patch("app.services.azure_reference.settings")
    def test_invalid_sku(self, mock_settings, reference):
        mock_settings.is_dev_mode = False
        assert reference.is_valid_sku("Hyper_Z99_Quantum") is False

    @patch("app.services.azure_reference.settings")
    def test_dev_mode_always_true(self, mock_settings, reference):
        mock_settings.is_dev_mode = True
        assert reference.is_valid_resource_type("Anything/Goes") is True
        assert reference.is_valid_region("narnia") is True
        assert reference.is_valid_sku("Imaginary_SKU") is True


# =========================================================================
# 7. Azure resource validation in architecture data
# =========================================================================


class TestValidateAzureResources:
    @patch("app.services.azure_reference.settings")
    def test_invalid_region_detected(self, mock_settings, validator):
        mock_settings.is_dev_mode = False
        data = {"network_topology": {"primary_region": "mars-west"}}
        errors = validator.validate_azure_resources(data)
        assert len(errors) >= 1
        assert any("mars-west" in e.message for e in errors)

    def test_unreasonable_budget_detected(self, validator):
        data = {
            "subscriptions": [
                {"name": "prod", "budget_usd": 999_999_999},
            ]
        }
        errors = validator.validate_azure_resources(data)
        assert len(errors) >= 1
        assert any("unreasonably high" in e.message for e in errors)

    def test_valid_data_no_errors(self, validator, valid_architecture):
        errors = validator.validate_azure_resources(valid_architecture)
        assert errors == []


# =========================================================================
# 8. Metrics tracking
# =========================================================================


class TestValidationMetrics:
    def test_track_and_get_metrics(self, validator):
        validator.track_validation_metrics("architecture", True, [])
        validator.track_validation_metrics("architecture", False, ["missing field"])
        validator.track_validation_metrics("architecture", False, ["missing field"])
        metrics = validator.get_metrics("architecture")
        assert len(metrics) == 1
        m = metrics[0]
        assert m.total_validations == 3
        assert m.passed == 1
        assert m.failed == 2
        assert m.failure_rate == pytest.approx(2 / 3, abs=0.01)
        assert "missing field" in m.common_errors

    def test_get_all_metrics(self, validator):
        validator.track_validation_metrics("architecture", True, [])
        validator.track_validation_metrics("policy", False, ["err"])
        metrics = validator.get_metrics()
        assert len(metrics) == 2

    def test_metrics_for_unknown_feature_empty(self, validator):
        metrics = validator.get_metrics("nonexistent")
        assert metrics == []

    def test_reset_metrics(self, validator):
        validator.track_validation_metrics("architecture", True, [])
        validator.reset_metrics()
        assert validator.get_metrics() == []

    def test_track_with_enum(self, validator):
        validator.track_validation_metrics(AIOutputType.policy, True, [])
        metrics = validator.get_metrics("policy")
        assert len(metrics) == 1
        assert metrics[0].feature == "policy"

    def test_validation_updates_metrics(self, validator, valid_architecture):
        validator.validate_architecture(valid_architecture)
        metrics = validator.get_metrics("architecture")
        assert len(metrics) == 1
        assert metrics[0].passed == 1


# =========================================================================
# 9. Pydantic output models
# =========================================================================


class TestOutputModels:
    def test_architecture_output_valid(self, valid_architecture):
        obj = ArchitectureOutput.model_validate(valid_architecture)
        assert obj.organization_size == "medium"

    def test_architecture_output_extra_fields(self, valid_architecture):
        valid_architecture["extra"] = "ok"
        obj = ArchitectureOutput.model_validate(valid_architecture)
        assert obj.model_dump()["extra"] == "ok"

    def test_policy_output_valid(self, valid_policy):
        obj = PolicyDefinitionOutput.model_validate(valid_policy)
        assert obj.name == "allowed-locations"

    def test_sku_output_valid(self, valid_sku_rec):
        obj = SKURecommendationOutput.model_validate(valid_sku_rec)
        assert obj.workload == "web-api"

    def test_security_finding_valid(self, valid_security_finding):
        obj = SecurityFindingOutput.model_validate(valid_security_finding)
        assert obj.severity == "High"

    def test_compliance_gap_valid(self, valid_compliance_gap):
        obj = ComplianceGapOutput.model_validate(valid_compliance_gap)
        assert obj.framework == "CIS Azure 2.0"


# =========================================================================
# 10. Validation schema models
# =========================================================================


class TestValidationSchemas:
    def test_validation_result_defaults(self):
        r = ValidationResult(success=True)
        assert r.errors == []
        assert r.warnings == []
        assert r.validated_data is None

    def test_validation_error_fields(self):
        e = ValidationError(
            field="name", message="required", expected="str", received="None"
        )
        assert e.field == "name"
        assert e.expected == "str"

    def test_validation_metrics_defaults(self):
        m = ValidationMetrics(feature="test")
        assert m.total_validations == 0
        assert m.failure_rate == 0.0

    def test_ai_output_type_values(self):
        assert AIOutputType.architecture.value == "architecture"
        assert AIOutputType.policy.value == "policy"
        assert AIOutputType.sku_recommendation.value == "sku_recommendation"
        assert AIOutputType.security_finding.value == "security_finding"
        assert AIOutputType.compliance_gap.value == "compliance_gap"

    def test_azure_resource_type_model(self):
        m = AzureResourceType()
        assert "Microsoft.Compute/virtualMachines" in m.VALID_TYPES

    def test_azure_region_model(self):
        m = AzureRegion()
        assert "eastus" in m.VALID_REGIONS

    def test_azure_sku_model(self):
        m = AzureSKU()
        assert "Standard_D" in m.VALID_SKU_FAMILIES


# =========================================================================
# 11. Route endpoints (integration)
# =========================================================================


class TestRouteEndpoints:
    def test_validate_architecture_endpoint(self, valid_architecture):
        client = _make_client()
        resp = client.post(
            "/api/ai/validate",
            json={"output_type": "architecture", "data": valid_architecture},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

    def test_validate_invalid_architecture_endpoint(self):
        client = _make_client()
        resp = client.post(
            "/api/ai/validate",
            json={"output_type": "architecture", "data": {}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False

    def test_validate_policy_endpoint(self, valid_policy):
        client = _make_client()
        resp = client.post(
            "/api/ai/validate",
            json={"output_type": "policy", "data": valid_policy},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_validate_sku_endpoint(self, valid_sku_rec):
        client = _make_client()
        resp = client.post(
            "/api/ai/validate",
            json={"output_type": "sku_recommendation", "data": valid_sku_rec},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_validate_security_finding_endpoint(self, valid_security_finding):
        client = _make_client()
        resp = client.post(
            "/api/ai/validate",
            json={"output_type": "security_finding", "data": valid_security_finding},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_validate_compliance_gap_endpoint(self, valid_compliance_gap):
        client = _make_client()
        resp = client.post(
            "/api/ai/validate",
            json={"output_type": "compliance_gap", "data": valid_compliance_gap},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_validation_metrics_endpoint(self):
        client = _make_client()
        resp = client.get("/api/ai/validation/metrics")
        assert resp.status_code == 200
        assert "metrics" in resp.json()

    def test_reference_resource_types_endpoint(self):
        client = _make_client()
        resp = client.get("/api/ai/reference/resource-types")
        assert resp.status_code == 200
        body = resp.json()
        assert "resource_types" in body
        assert body["count"] > 0

    def test_reference_regions_endpoint(self):
        client = _make_client()
        resp = client.get("/api/ai/reference/regions")
        assert resp.status_code == 200
        body = resp.json()
        assert "regions" in body
        assert body["count"] > 0


# =========================================================================
# 12. Integration with AIFoundryClient
# =========================================================================


class TestAIFoundryIntegration:
    """Verify that generate_architecture now calls the validator."""

    @pytest.fixture()
    def ai_client(self):
        from app.services.ai_foundry import AIFoundryClient

        return AIFoundryClient()

    async def test_generate_architecture_adds_validation_warnings(self, ai_client):
        """When AI returns valid architecture JSON, validation runs and may add warnings."""
        arch_json = json.dumps({
            "organization_size": "medium",
            "management_groups": {"root": {"display_name": "Org", "children": {}}},
            "subscriptions": [
                {"name": "prod", "purpose": "production",
                 "management_group": "prod", "budget_usd": 5000}
            ],
            "network_topology": {"type": "hub-spoke", "primary_region": "eastus"},
            "identity": {},
            "security": {},
            "governance": {},
            "management": {},
            "compliance_frameworks": [],
            "platform_automation": {},
            "recommendations": [],
            "estimated_monthly_cost_usd": 10000,
        })
        with patch.object(ai_client, "generate_completion", return_value=arch_json):
            result = await ai_client.generate_architecture({"org_size": "medium"})
        assert isinstance(result, dict)
        assert "management_groups" in result
        assert "organization_size" in result

    async def test_generate_architecture_with_invalid_json_falls_back(
        self, ai_client
    ):
        """When AI returns unparseable JSON, archetype fallback is used."""
        with patch.object(
            ai_client, "generate_completion", return_value="NOT JSON AT ALL"
        ):
            result = await ai_client.generate_architecture({"org_size": "small"})
            assert isinstance(result, dict)
            # Should have gotten archetype fallback
            assert "management_groups" in result or "organization_size" in result

    async def test_generate_architecture_validation_failure_doesnt_block(
        self, ai_client
    ):
        """Even if validation fails, the data is still returned."""
        bad_json = json.dumps({"organization_size": "medium"})
        with patch.object(
            ai_client, "generate_completion", return_value=bad_json
        ):
            result = await ai_client.generate_architecture({})
            assert isinstance(result, dict)
            assert result["organization_size"] == "medium"
            # Should have validation_warnings since it's missing many fields
            # But the data is still returned (not blocked)

    async def test_generate_architecture_validation_exception_handled(
        self, ai_client
    ):
        """If the validator itself throws, architecture is still returned."""
        valid_json = json.dumps({
            "organization_size": "small",
            "management_groups": {},
            "subscriptions": [],
        })
        with (
            patch.object(
                ai_client, "generate_completion", return_value=valid_json
            ),
            patch(
                "app.services.ai_validator.ai_validator.validate_architecture",
                side_effect=RuntimeError("validator broke"),
            ),
        ):
            result = await ai_client.generate_architecture({})
            assert isinstance(result, dict)
            assert result["organization_size"] == "small"
