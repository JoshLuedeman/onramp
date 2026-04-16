"""Tests for Azure Government cloud support.

Covers the region registry, Bicep customizer, questionnaire extensions,
schema validation, and all API route endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.government import (
    GovernmentBicepRequest,
    GovernmentBicepResponse,
    GovernmentConstraintsRequest,
    GovernmentConstraintsResponse,
    GovernmentQuestionResponse,
    GovernmentRegionListResponse,
    GovernmentRegionResponse,
)
from app.services.government_bicep import (
    GovernmentBicepService,
    government_bicep_service,
)
from app.services.government_questionnaire import (
    GOVERNMENT_QUESTIONS,
    GovernmentQuestionnaireService,
    government_questionnaire_service,
)
from app.services.government_regions import (
    GOVERNMENT_REGIONS,
    GovernmentRegionService,
    government_region_service,
)

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-token"}


# ══════════════════════════════════════════════════════════════════════════════
#  Government Region Service Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestGovernmentRegionSingleton:
    def test_singleton_is_instance(self):
        assert isinstance(government_region_service, GovernmentRegionService)


class TestGovernmentRegionData:
    def test_all_six_regions_present(self):
        assert len(GOVERNMENT_REGIONS) == 6

    def test_region_names(self):
        names = {r["name"] for r in GOVERNMENT_REGIONS}
        expected = {
            "usgovvirginia",
            "usgovtexas",
            "usgoviowa",
            "usgovarizona",
            "usdodcentral",
            "usdodeast",
        }
        assert names == expected

    def test_all_regions_have_required_fields(self):
        required = {
            "name",
            "display_name",
            "paired_region",
            "geography",
            "available_zones",
            "restricted",
        }
        for region in GOVERNMENT_REGIONS:
            missing = required - set(region.keys())
            assert not missing, f"{region['name']} missing: {missing}"

    def test_dod_regions_are_restricted(self):
        for r in GOVERNMENT_REGIONS:
            if r["name"].startswith("usdod"):
                assert r["restricted"] is True

    def test_non_dod_regions_are_not_restricted(self):
        for r in GOVERNMENT_REGIONS:
            if r["name"].startswith("usgov"):
                assert r["restricted"] is False


class TestGetRegions:
    def test_returns_all_regions(self):
        regions = government_region_service.get_regions()
        assert len(regions) == 6

    def test_returns_copies(self):
        regions = government_region_service.get_regions()
        regions[0]["name"] = "modified"
        assert GOVERNMENT_REGIONS[0]["name"] != "modified"


class TestGetRegion:
    def test_get_existing_region(self):
        region = government_region_service.get_region("usgovvirginia")
        assert region is not None
        assert region["display_name"] == "US Gov Virginia"

    def test_get_region_case_insensitive(self):
        region = government_region_service.get_region("USGovVirginia")
        assert region is not None
        assert region["name"] == "usgovvirginia"

    def test_get_nonexistent_region(self):
        assert government_region_service.get_region("eastus") is None


class TestGetDodRegions:
    def test_returns_two_dod_regions(self):
        dod = government_region_service.get_dod_regions()
        assert len(dod) == 2

    def test_all_dod_regions_are_restricted(self):
        for r in government_region_service.get_dod_regions():
            assert r["restricted"] is True

    def test_dod_region_names(self):
        names = {r["name"] for r in government_region_service.get_dod_regions()}
        assert names == {"usdodcentral", "usdodeast"}


class TestGetNonDodRegions:
    def test_returns_four_non_dod_regions(self):
        non_dod = government_region_service.get_non_dod_regions()
        assert len(non_dod) == 4

    def test_no_restricted_regions(self):
        for r in government_region_service.get_non_dod_regions():
            assert r["restricted"] is False


class TestValidateRegion:
    def test_valid_region(self):
        assert government_region_service.validate_region("usgovvirginia") is True

    def test_invalid_region(self):
        assert government_region_service.validate_region("eastus") is False

    def test_case_insensitive(self):
        assert government_region_service.validate_region("USGovTexas") is True


class TestGetPairedRegion:
    def test_virginia_paired_with_texas(self):
        assert government_region_service.get_paired_region("usgovvirginia") == "usgovtexas"

    def test_texas_paired_with_virginia(self):
        assert government_region_service.get_paired_region("usgovtexas") == "usgovvirginia"

    def test_dod_central_paired_with_dod_east(self):
        assert government_region_service.get_paired_region("usdodcentral") == "usdodeast"

    def test_unknown_region_returns_none(self):
        assert government_region_service.get_paired_region("westus") is None


# ══════════════════════════════════════════════════════════════════════════════
#  Government Bicep Service Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestGovernmentBicepSingleton:
    def test_singleton_is_instance(self):
        assert isinstance(government_bicep_service, GovernmentBicepService)


class TestEndpointReplacement:
    def test_replaces_management_endpoint(self):
        bicep = "param endpoint string = 'https://management.azure.com'"
        result = government_bicep_service.customize_for_government(
            bicep, "usgovvirginia"
        )
        assert result.count("management.usgovcloudapi.net") == 1
        assert "management.azure.com" not in result

    def test_replaces_login_endpoint(self):
        bicep = "var auth = 'https://login.microsoftonline.com/tenant'"
        result = government_bicep_service.customize_for_government(
            bicep, "usgovvirginia"
        )
        assert "login.microsoftonline.us" in result

    def test_replaces_storage_suffix(self):
        bicep = "var blob = 'myaccount.blob.core.windows.net'"
        result = government_bicep_service.customize_for_government(
            bicep, "usgovvirginia"
        )
        assert result.count(".blob.core.usgovcloudapi.net") == 1

    def test_replaces_keyvault_suffix(self):
        bicep = "var kv = 'myvault.vault.azure.net'"
        result = government_bicep_service.customize_for_government(
            bicep, "usgovvirginia"
        )
        assert result.count(".vault.usgovcloudapi.net") == 1


class TestFedRAMPTags:
    def test_injects_high_tags(self):
        bicep = "resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {\n  name: 'test'\n  tags: {\n    env: 'prod'\n  }\n}"
        result = government_bicep_service.add_fedramp_tags(bicep, "high")
        assert "fedramp_level" in result
        assert "'High'" in result

    def test_injects_moderate_tags(self):
        result = government_bicep_service.add_fedramp_tags(
            "resource sa 'type' = {\n  tags: {\n  }\n}", "moderate"
        )
        assert "'Moderate'" in result

    def test_injects_low_tags(self):
        result = government_bicep_service.add_fedramp_tags(
            "resource sa 'type' = {\n  tags: {\n  }\n}", "low"
        )
        assert "'Low'" in result

    def test_defaults_to_high_for_unknown_level(self):
        result = government_bicep_service.add_fedramp_tags(
            "resource sa 'type' = {\n  tags: {\n  }\n}", "unknown"
        )
        assert "'High'" in result

    def test_adds_tags_block_when_missing(self):
        bicep = "resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {\n  name: 'test'\n}"
        result = government_bicep_service.add_fedramp_tags(bicep, "high")
        assert "fedramp_level" in result


class TestDiagnosticSettings:
    def test_injects_diagnostic_settings(self):
        bicep = "resource storageAccount 'type' = { }"
        result = government_bicep_service.inject_diagnostic_settings(bicep)
        assert "diagnosticSettings" in result
        assert "fedramp-diagnostics" in result

    def test_does_not_duplicate_diagnostic_settings(self):
        bicep = "resource diagnosticSettings 'type' = { }"
        result = government_bicep_service.inject_diagnostic_settings(bicep)
        assert result.count("diagnosticSettings") == 1


class TestSKUMapping:
    def test_get_sku_mapping_returns_dict(self):
        mapping = government_bicep_service.get_government_sku_mapping()
        assert isinstance(mapping, dict)
        assert len(mapping) > 0

    def test_standard_grs_maps_to_lrs(self):
        mapping = government_bicep_service.get_government_sku_mapping()
        assert mapping["Standard_GRS"] == "Standard_LRS"

    def test_replaces_skus_in_template(self):
        bicep = "sku: { name: 'Standard_GRS' }"
        result = government_bicep_service.customize_for_government(
            bicep, "usgovvirginia"
        )
        assert "Standard_LRS" in result
        assert "Standard_GRS" not in result


class TestCustomizeForGovernment:
    def test_sets_region(self):
        bicep = "param location string = 'eastus'"
        result = government_bicep_service.customize_for_government(
            bicep, "usgovvirginia"
        )
        assert "usgovvirginia" in result
        assert "eastus" not in result

    def test_adds_environment_property(self):
        bicep = "resource rg 'type' = {\n  properties:\n    foo: 'bar'\n}"
        result = government_bicep_service.customize_for_government(
            bicep, "usgovvirginia"
        )
        assert "AzureUSGovernment" in result

    def test_full_customization_pipeline(self):
        bicep = (
            "param location string = 'eastus'\n"
            "resource sa 'Microsoft.Storage/storageAccounts@2023-01-01' = {\n"
            "  name: 'test'\n"
            "  properties:\n"
            "    supportsHttpsTrafficOnly: true\n"
            "  tags: {\n"
            "    env: 'prod'\n"
            "  }\n"
            "}"
        )
        result = government_bicep_service.customize_for_government(
            bicep, "usgovtexas", "moderate"
        )
        assert "usgovtexas" in result
        assert "AzureUSGovernment" in result
        assert "'Moderate'" in result
        assert "diagnosticSettings" in result


# ══════════════════════════════════════════════════════════════════════════════
#  Government Questionnaire Service Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestGovernmentQuestionnaireSingleton:
    def test_singleton_is_instance(self):
        assert isinstance(
            government_questionnaire_service, GovernmentQuestionnaireService
        )


class TestGovernmentQuestions:
    def test_returns_five_questions(self):
        questions = government_questionnaire_service.get_government_questions()
        assert len(questions) == 5

    def test_question_ids(self):
        ids = {q["id"] for q in government_questionnaire_service.get_government_questions()}
        expected = {
            "gov_impact_level",
            "gov_dod_workload",
            "gov_fedramp_level",
            "gov_itar",
            "gov_region",
        }
        assert ids == expected

    def test_questions_have_required_fields(self):
        required = {"id", "text", "type", "options", "required", "category"}
        for q in government_questionnaire_service.get_government_questions():
            missing = required - set(q.keys())
            assert not missing, f"Question {q['id']} missing: {missing}"

    def test_all_questions_are_government_category(self):
        for q in government_questionnaire_service.get_government_questions():
            assert q["category"] == "government"

    def test_impact_level_has_four_options(self):
        questions = government_questionnaire_service.get_government_questions()
        il_q = next(q for q in questions if q["id"] == "gov_impact_level")
        assert len(il_q["options"]) == 4

    def test_region_question_has_all_six_regions(self):
        questions = government_questionnaire_service.get_government_questions()
        region_q = next(q for q in questions if q["id"] == "gov_region")
        assert len(region_q["options"]) == 6


class TestShouldShowGovernmentQuestions:
    def test_shows_for_government(self):
        assert government_questionnaire_service.should_show_government_questions(
            {"cloud_environment": "government"}
        ) is True

    def test_shows_for_government_case_insensitive(self):
        assert government_questionnaire_service.should_show_government_questions(
            {"cloud_environment": "Government"}
        ) is True

    def test_does_not_show_for_commercial(self):
        assert government_questionnaire_service.should_show_government_questions(
            {"cloud_environment": "commercial"}
        ) is False

    def test_does_not_show_for_empty_answers(self):
        assert government_questionnaire_service.should_show_government_questions(
            {}
        ) is False

    def test_does_not_show_for_non_string(self):
        assert government_questionnaire_service.should_show_government_questions(
            {"cloud_environment": 123}
        ) is False


class TestApplyGovernmentConstraints:
    def test_sets_cloud_environment(self):
        result = government_questionnaire_service.apply_government_constraints(
            {}, {"gov_impact_level": "IL2"}
        )
        assert result["cloud_environment"] == "government"

    def test_sets_impact_level(self):
        result = government_questionnaire_service.apply_government_constraints(
            {}, {"gov_impact_level": "IL4"}
        )
        assert result["compliance"]["impact_level"] == "IL4"

    def test_sets_fedramp_level(self):
        result = government_questionnaire_service.apply_government_constraints(
            {}, {"gov_fedramp_level": "moderate"}
        )
        assert result["compliance"]["fedramp_level"] == "moderate"

    def test_sets_region_and_paired_region(self):
        result = government_questionnaire_service.apply_government_constraints(
            {}, {"gov_region": "usgovvirginia"}
        )
        assert result["region"] == "usgovvirginia"
        assert result["paired_region"] == "usgovtexas"

    def test_dod_workload_in_non_dod_region_warns(self):
        result = government_questionnaire_service.apply_government_constraints(
            {},
            {"gov_dod_workload": "yes", "gov_region": "usgovvirginia"},
        )
        assert result["compliance"]["dod_workload"] is True
        assert any("DoD workload" in w for w in result.get("warnings", []))

    def test_dod_workload_in_dod_region_no_warning(self):
        result = government_questionnaire_service.apply_government_constraints(
            {},
            {"gov_dod_workload": "yes", "gov_region": "usdodcentral"},
        )
        assert result["compliance"]["dod_workload"] is True
        assert not result.get("warnings", [])

    def test_itar_sets_security_constraints(self):
        result = government_questionnaire_service.apply_government_constraints(
            {}, {"gov_itar": "yes"}
        )
        assert result["compliance"]["itar_required"] is True
        assert result["security"]["data_residency"] == "us_only"
        assert result["security"]["access_restriction"] == "us_persons_only"

    def test_il5_enables_double_encryption(self):
        result = government_questionnaire_service.apply_government_constraints(
            {}, {"gov_impact_level": "IL5"}
        )
        assert result["security"]["encryption_at_rest"] is True
        assert result["security"]["double_encryption"] is True

    def test_il6_enables_dedicated_hsm(self):
        result = government_questionnaire_service.apply_government_constraints(
            {}, {"gov_impact_level": "IL6"}
        )
        assert result["security"]["dedicated_hsm"] is True
        assert result["security"]["classification_level"] == "SECRET"

    def test_preserves_existing_architecture(self):
        base = {"existing_key": "existing_value"}
        result = government_questionnaire_service.apply_government_constraints(
            base, {}
        )
        assert result["existing_key"] == "existing_value"


# ══════════════════════════════════════════════════════════════════════════════
#  Schema Validation Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestGovernmentSchemas:
    def test_region_response_roundtrip(self):
        resp = GovernmentRegionResponse(
            name="usgovvirginia",
            display_name="US Gov Virginia",
            paired_region="usgovtexas",
            geography="US Government",
            available_zones=["1", "2", "3"],
            restricted=False,
        )
        assert resp.name == "usgovvirginia"
        assert resp.restricted is False

    def test_region_list_response(self):
        resp = GovernmentRegionListResponse(
            regions=[
                GovernmentRegionResponse(
                    name="usgovvirginia",
                    display_name="US Gov Virginia",
                    paired_region="usgovtexas",
                    geography="US Government",
                )
            ],
            total=1,
        )
        assert resp.total == 1

    def test_bicep_request_defaults(self):
        req = GovernmentBicepRequest(
            bicep_content="test", region="usgovvirginia"
        )
        assert req.compliance_level == "high"

    def test_bicep_response(self):
        resp = GovernmentBicepResponse(
            customized_content="test",
            changes_applied=["change1"],
        )
        assert len(resp.changes_applied) == 1

    def test_question_response(self):
        resp = GovernmentQuestionResponse(
            id="q1",
            text="test?",
            type="single_choice",
            options=[],
        )
        assert resp.required is True

    def test_constraints_request(self):
        req = GovernmentConstraintsRequest(
            architecture={"key": "val"},
            gov_answers={"gov_impact_level": "IL4"},
        )
        assert req.architecture["key"] == "val"

    def test_constraints_response(self):
        resp = GovernmentConstraintsResponse(
            architecture={"region": "usgovvirginia"},
            warnings=["warning1"],
        )
        assert len(resp.warnings) == 1


# ══════════════════════════════════════════════════════════════════════════════
#  Route / API Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestListRegionsRoute:
    def test_returns_200(self):
        resp = client.get("/api/government/regions", headers=AUTH_HEADERS)
        assert resp.status_code == 200

    def test_returns_six_regions(self):
        resp = client.get("/api/government/regions", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] == 6
        assert len(data["regions"]) == 6

    def test_region_has_required_fields(self):
        resp = client.get("/api/government/regions", headers=AUTH_HEADERS)
        region = resp.json()["regions"][0]
        assert "name" in region
        assert "display_name" in region
        assert "paired_region" in region


class TestGetRegionRoute:
    def test_get_existing_region(self):
        resp = client.get(
            "/api/government/regions/usgovvirginia", headers=AUTH_HEADERS
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "usgovvirginia"

    def test_get_nonexistent_region_returns_404(self):
        resp = client.get(
            "/api/government/regions/eastus", headers=AUTH_HEADERS
        )
        assert resp.status_code == 404


class TestListDodRegionsRoute:
    def test_returns_200(self):
        resp = client.get("/api/government/regions/dod", headers=AUTH_HEADERS)
        assert resp.status_code == 200

    def test_returns_two_dod_regions(self):
        resp = client.get("/api/government/regions/dod", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] == 2

    def test_all_regions_are_restricted(self):
        resp = client.get("/api/government/regions/dod", headers=AUTH_HEADERS)
        for region in resp.json()["regions"]:
            assert region["restricted"] is True


class TestCustomizeBicepRoute:
    def test_returns_200_with_valid_request(self):
        resp = client.post(
            "/api/government/bicep/customize",
            json={
                "bicep_content": "param location string = 'eastus'",
                "region": "usgovvirginia",
                "compliance_level": "high",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "usgovvirginia" in data["customized_content"]
        assert len(data["changes_applied"]) > 0

    def test_invalid_region_returns_400(self):
        resp = client.post(
            "/api/government/bicep/customize",
            json={
                "bicep_content": "test",
                "region": "eastus",
                "compliance_level": "high",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400


class TestGetQuestionsRoute:
    def test_returns_200(self):
        resp = client.get("/api/government/questions", headers=AUTH_HEADERS)
        assert resp.status_code == 200

    def test_returns_five_questions(self):
        resp = client.get("/api/government/questions", headers=AUTH_HEADERS)
        data = resp.json()
        assert len(data) == 5

    def test_question_has_required_fields(self):
        resp = client.get("/api/government/questions", headers=AUTH_HEADERS)
        q = resp.json()[0]
        assert "id" in q
        assert "text" in q
        assert "type" in q
        assert "options" in q


class TestApplyConstraintsRoute:
    def test_returns_200(self):
        resp = client.post(
            "/api/government/constraints",
            json={
                "architecture": {"name": "test"},
                "gov_answers": {"gov_impact_level": "IL4"},
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200

    def test_applies_impact_level(self):
        resp = client.post(
            "/api/government/constraints",
            json={
                "architecture": {},
                "gov_answers": {
                    "gov_impact_level": "IL5",
                    "gov_region": "usgovvirginia",
                },
            },
            headers=AUTH_HEADERS,
        )
        data = resp.json()
        assert data["architecture"]["compliance"]["impact_level"] == "IL5"

    def test_returns_warnings_for_dod_in_non_dod_region(self):
        resp = client.post(
            "/api/government/constraints",
            json={
                "architecture": {},
                "gov_answers": {
                    "gov_dod_workload": "yes",
                    "gov_region": "usgovvirginia",
                },
            },
            headers=AUTH_HEADERS,
        )
        data = resp.json()
        assert len(data["warnings"]) > 0
        assert any("DoD" in w for w in data["warnings"])
