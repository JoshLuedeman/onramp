"""Tests for Azure China (21Vianet) services, schemas, and routes."""

import pytest

from app.services.china_regions import (
    CHINA_REGIONS,
    ChinaRegionService,
    china_region_service,
)
from app.services.china_bicep import (
    ChinaBicepService,
    china_bicep_service,
)
from app.services.china_questionnaire import (
    ChinaQuestionnaireService,
    china_questionnaire_service,
)
from app.schemas.china import (
    ChinaBicepRequest,
    ChinaBicepResponse,
    ChinaConstraintsRequest,
    ChinaConstraintsResponse,
    ChinaQuestionResponse,
    ChinaRegionListResponse,
    ChinaRegionResponse,
    DataResidencyRequirements,
    ICPRequirements,
)


# ══════════════════════════════════════════════════════════════════════════════
# ChinaRegionService
# ══════════════════════════════════════════════════════════════════════════════


class TestChinaRegionSingleton:
    """Verify singleton pattern."""

    def test_singleton_is_instance(self):
        assert isinstance(china_region_service, ChinaRegionService)

    def test_singleton_is_reusable(self):
        assert china_region_service is china_region_service


class TestChinaRegionDataIntegrity:
    """Verify region data is well-formed."""

    def test_exactly_six_regions(self):
        assert len(CHINA_REGIONS) == 6

    def test_regions_have_required_fields(self):
        required = {"name", "display_name", "paired_region", "geography", "available_zones"}
        for region in CHINA_REGIONS:
            missing = required - set(region.keys())
            assert not missing, f"{region['name']} missing: {missing}"

    def test_region_names_are_unique(self):
        names = [r["name"] for r in CHINA_REGIONS]
        assert len(names) == len(set(names))

    def test_all_regions_are_china_geography(self):
        for region in CHINA_REGIONS:
            assert region["geography"] == "China"

    def test_paired_regions_are_valid(self):
        names = {r["name"] for r in CHINA_REGIONS}
        for region in CHINA_REGIONS:
            assert region["paired_region"] in names, (
                f"{region['name']} paired to unknown region {region['paired_region']}"
            )

    def test_available_zones_are_lists(self):
        for region in CHINA_REGIONS:
            assert isinstance(region["available_zones"], list)

    def test_pairing_is_symmetric(self):
        by_name = {r["name"]: r for r in CHINA_REGIONS}
        for region in CHINA_REGIONS:
            partner = by_name[region["paired_region"]]
            assert partner["paired_region"] == region["name"], (
                f"Pairing not symmetric: {region['name']} <-> {partner['name']}"
            )


class TestChinaRegionGetRegions:
    """Tests for get_regions()."""

    def test_returns_list(self):
        result = china_region_service.get_regions()
        assert isinstance(result, list)

    def test_returns_all_six(self):
        result = china_region_service.get_regions()
        assert len(result) == 6

    def test_returns_copies(self):
        result = china_region_service.get_regions()
        result[0]["name"] = "modified"
        assert CHINA_REGIONS[0]["name"] != "modified"


class TestChinaRegionGetRegion:
    """Tests for get_region()."""

    def test_returns_known_region(self):
        result = china_region_service.get_region("chinanorth2")
        assert result is not None
        assert result["name"] == "chinanorth2"

    def test_returns_none_for_unknown(self):
        result = china_region_service.get_region("westus2")
        assert result is None

    def test_case_insensitive(self):
        result = china_region_service.get_region("CHINAEAST2")
        assert result is not None

    def test_has_display_name(self):
        result = china_region_service.get_region("chinaeast")
        assert result is not None
        assert "Shanghai" in result["display_name"]


class TestChinaRegionValidate:
    """Tests for validate_region()."""

    def test_valid_region(self):
        assert china_region_service.validate_region("chinanorth") is True

    def test_invalid_region(self):
        assert china_region_service.validate_region("eastus") is False

    def test_empty_string(self):
        assert china_region_service.validate_region("") is False


class TestChinaRegionPaired:
    """Tests for get_paired_region()."""

    def test_returns_paired_region(self):
        assert china_region_service.get_paired_region("chinanorth2") == "chinaeast2"

    def test_returns_none_for_unknown(self):
        assert china_region_service.get_paired_region("westus") is None

    def test_chinaeast3_paired_with_chinanorth3(self):
        assert china_region_service.get_paired_region("chinaeast3") == "chinanorth3"


class TestChinaRegionDataResidency:
    """Tests for get_data_residency_requirements()."""

    def test_returns_dict(self):
        result = china_region_service.get_data_residency_requirements()
        assert isinstance(result, dict)

    def test_has_jurisdiction(self):
        result = china_region_service.get_data_residency_requirements()
        assert "jurisdiction" in result

    def test_cross_border_is_false(self):
        result = china_region_service.get_data_residency_requirements()
        assert result["cross_border_transfer"] is False

    def test_has_regulations(self):
        result = china_region_service.get_data_residency_requirements()
        assert len(result["regulations"]) >= 3


# ══════════════════════════════════════════════════════════════════════════════
# ChinaBicepService
# ══════════════════════════════════════════════════════════════════════════════


class TestChinaBicepSingleton:
    """Verify singleton pattern."""

    def test_singleton_is_instance(self):
        assert isinstance(china_bicep_service, ChinaBicepService)


class TestChinaBicepCustomize:
    """Tests for customize_for_china()."""

    def test_replaces_management_endpoint(self):
        content = "var url = 'https://management.azure.com'"
        result = china_bicep_service.customize_for_china(content, "chinanorth2")
        assert "management.chinacloudapi.cn" in result
        assert "management.azure.com" not in result

    def test_replaces_storage_suffix(self):
        content = "var suffix = '.blob.core.windows.net'"
        result = china_bicep_service.customize_for_china(content, "chinanorth2")
        assert ".blob.core.chinacloudapi.cn" in result

    def test_replaces_login_endpoint(self):
        content = "var auth = 'https://login.microsoftonline.com'"
        result = china_bicep_service.customize_for_china(content, "chinanorth2")
        assert "login.chinacloudapi.cn" in result

    def test_adds_environment_header(self):
        content = "param location string"
        result = china_bicep_service.customize_for_china(content, "chinaeast2")
        assert "Azure China (21Vianet)" in result
        assert "chinaeast2" in result

    def test_preserves_original_content(self):
        content = "param location string\nresource rg 'Microsoft.Resources/resourceGroups@2023-07-01'"
        result = china_bicep_service.customize_for_china(content, "chinanorth2")
        assert "param location string" in result

    def test_replaces_keyvault_suffix(self):
        content = "var kvUri = '.vault.azure.net'"
        result = china_bicep_service.customize_for_china(content, "chinanorth2")
        assert ".vault.azure.cn" in result


class TestChinaBicepServiceMapping:
    """Tests for get_china_service_mapping()."""

    def test_returns_dict(self):
        result = china_bicep_service.get_china_service_mapping()
        assert isinstance(result, dict)

    def test_contains_front_door(self):
        mapping = china_bicep_service.get_china_service_mapping()
        assert "Azure Front Door" in mapping

    def test_mapping_has_china_equivalent(self):
        mapping = china_bicep_service.get_china_service_mapping()
        for service, details in mapping.items():
            assert "china_equivalent" in details, f"{service} missing china_equivalent"


class TestChinaBicepMLPSTags:
    """Tests for add_mlps_tags()."""

    def test_injects_tags_into_resource(self):
        content = "resource myVm 'Microsoft.Compute/virtualMachines@2023-03-01' = {\n  name: 'vm1'\n}"
        result = china_bicep_service.add_mlps_tags(content)
        assert "MLPS-Level-3" in result

    def test_mlps2_tags(self):
        content = "resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {\n}"
        result = china_bicep_service.add_mlps_tags(content, "mlps2")
        assert "MLPS-Level-2" in result

    def test_mlps4_tags(self):
        content = "resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {\n}"
        result = china_bicep_service.add_mlps_tags(content, "mlps4")
        assert "MLPS-Level-4" in result

    def test_invalid_level_defaults_to_mlps3(self):
        content = "resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {\n}"
        result = china_bicep_service.add_mlps_tags(content, "invalid")
        assert "MLPS-Level-3" in result


class TestChinaBicepICP:
    """Tests for get_icp_requirements()."""

    def test_no_resources_no_icp(self):
        result = china_bicep_service.get_icp_requirements({"resources": []})
        assert result["requires_icp"] is False

    def test_web_site_requires_icp(self):
        arch = {"resources": [{"type": "Microsoft.Web/sites"}]}
        result = china_bicep_service.get_icp_requirements(arch)
        assert result["requires_icp"] is True
        assert "Microsoft.Web/sites" in result["affected_resources"]

    def test_compute_does_not_require_icp(self):
        arch = {"resources": [{"type": "Microsoft.Compute/virtualMachines"}]}
        result = china_bicep_service.get_icp_requirements(arch)
        assert result["requires_icp"] is False

    def test_missing_resources_key(self):
        result = china_bicep_service.get_icp_requirements({})
        assert result["requires_icp"] is False

    def test_icp_types_present(self):
        result = china_bicep_service.get_icp_requirements({"resources": []})
        assert len(result["icp_types"]) == 2


class TestChinaBicepDataResidencyConfig:
    """Tests for get_data_residency_config()."""

    def test_returns_dict(self):
        result = china_bicep_service.get_data_residency_config()
        assert isinstance(result, dict)

    def test_allowed_regions_are_china(self):
        result = china_bicep_service.get_data_residency_config()
        for region in result["allowed_regions"]:
            assert region.startswith("china")

    def test_has_storage_replication(self):
        result = china_bicep_service.get_data_residency_config()
        assert "storage_replication" in result


# ══════════════════════════════════════════════════════════════════════════════
# ChinaQuestionnaireService
# ══════════════════════════════════════════════════════════════════════════════


class TestChinaQuestionnaireSingleton:
    """Verify singleton pattern."""

    def test_singleton_is_instance(self):
        assert isinstance(china_questionnaire_service, ChinaQuestionnaireService)


class TestChinaQuestionnaireGetQuestions:
    """Tests for get_china_questions()."""

    def test_returns_list(self):
        result = china_questionnaire_service.get_china_questions()
        assert isinstance(result, list)

    def test_exactly_five_questions(self):
        result = china_questionnaire_service.get_china_questions()
        assert len(result) == 5

    def test_all_have_required_fields(self):
        required = {"id", "text", "description", "type", "options", "required", "category"}
        for q in china_questionnaire_service.get_china_questions():
            missing = required - set(q.keys())
            assert not missing, f"Question {q['id']} missing: {missing}"

    def test_icp_question_present(self):
        questions = china_questionnaire_service.get_china_questions()
        ids = [q["id"] for q in questions]
        assert "china_icp_license" in ids

    def test_mlps_question_present(self):
        questions = china_questionnaire_service.get_china_questions()
        ids = [q["id"] for q in questions]
        assert "china_mlps_level" in ids

    def test_region_question_has_six_options(self):
        questions = china_questionnaire_service.get_china_questions()
        region_q = next(q for q in questions if q["id"] == "china_region")
        assert len(region_q["options"]) == 6


class TestChinaQuestionnaireShouldShow:
    """Tests for should_show_china_questions()."""

    def test_shows_for_china_env(self):
        assert china_questionnaire_service.should_show_china_questions(
            {"cloud_environment": "china"}
        ) is True

    def test_hides_for_commercial(self):
        assert china_questionnaire_service.should_show_china_questions(
            {"cloud_environment": "commercial"}
        ) is False

    def test_supports_environment_key(self):
        assert china_questionnaire_service.should_show_china_questions(
            {"environment": "china"}
        ) is True

    def test_case_insensitive(self):
        assert china_questionnaire_service.should_show_china_questions(
            {"cloud_environment": "CHINA"}
        ) is True

    def test_empty_answers(self):
        assert china_questionnaire_service.should_show_china_questions({}) is False


class TestChinaQuestionnaireApplyConstraints:
    """Tests for apply_china_constraints()."""

    def test_sets_region(self):
        result = china_questionnaire_service.apply_china_constraints(
            {}, {"china_region": "chinaeast2"}
        )
        assert result["region"] == "chinaeast2"

    def test_sets_paired_region(self):
        result = china_questionnaire_service.apply_china_constraints(
            {}, {"china_region": "chinaeast2"}
        )
        assert result["paired_region"] == "chinanorth2"

    def test_sets_compliance(self):
        result = china_questionnaire_service.apply_china_constraints(
            {}, {"china_mlps_level": "level3"}
        )
        assert result["compliance"]["framework"] == "MLPS"

    def test_defaults_invalid_region(self):
        result = china_questionnaire_service.apply_china_constraints(
            {}, {"china_region": "westus"}
        )
        assert result["region"] == "chinanorth2"

    def test_sets_icp_warning_when_no_license(self):
        result = china_questionnaire_service.apply_china_constraints(
            {}, {"china_icp_license": "no"}
        )
        assert result["icp_license"]["warning"] is not None

    def test_no_icp_warning_when_licensed(self):
        result = china_questionnaire_service.apply_china_constraints(
            {}, {"china_icp_license": "yes"}
        )
        assert result["icp_license"]["warning"] is None

    def test_sets_cloud_environment(self):
        result = china_questionnaire_service.apply_china_constraints({}, {})
        assert result["cloud_environment"] == "china"

    def test_sets_operator(self):
        result = china_questionnaire_service.apply_china_constraints({}, {})
        assert result["operator"] == "21Vianet"

    def test_preserves_existing_architecture_keys(self):
        result = china_questionnaire_service.apply_china_constraints(
            {"name": "my-arch"}, {}
        )
        assert result["name"] == "my-arch"


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic Schemas
# ══════════════════════════════════════════════════════════════════════════════


class TestChinaSchemas:
    """Validate Pydantic schema construction."""

    def test_china_region_response(self):
        r = ChinaRegionResponse(
            name="chinanorth2",
            display_name="China North 2",
            paired_region="chinaeast2",
            geography="China",
            available_zones=["1", "2", "3"],
        )
        assert r.name == "chinanorth2"

    def test_china_region_list_response(self):
        r = ChinaRegionListResponse(regions=[], total=0)
        assert r.total == 0

    def test_china_bicep_request(self):
        r = ChinaBicepRequest(
            bicep_content="param location string",
            region="chinanorth2",
        )
        assert r.compliance_level == "mlps3"

    def test_china_bicep_response(self):
        r = ChinaBicepResponse(
            customized_content="content",
            region="chinanorth2",
            compliance_level="mlps3",
            endpoints_replaced=5,
        )
        assert r.endpoints_replaced == 5

    def test_china_question_response(self):
        r = ChinaQuestionResponse(
            id="q1",
            text="Question?",
            description="Desc",
            type="single_choice",
            options=[],
            required=True,
            category="compliance",
        )
        assert r.required is True

    def test_china_constraints_request(self):
        r = ChinaConstraintsRequest(
            architecture={"name": "test"},
            china_answers={"china_region": "chinanorth2"},
        )
        assert r.architecture["name"] == "test"

    def test_china_constraints_response(self):
        r = ChinaConstraintsResponse(
            architecture={},
            region="chinanorth2",
            compliance_level="level3",
        )
        assert r.cloud_environment == "china"

    def test_data_residency_requirements(self):
        r = DataResidencyRequirements(
            jurisdiction="PRC",
            data_boundary="mainland_china",
            cross_border_transfer=False,
            regulations=["PIPL"],
            requirements=["Data must stay in China"],
            operator="21Vianet",
            operator_relationship="Microsoft tech, 21Vianet ops",
        )
        assert r.cross_border_transfer is False

    def test_icp_requirements(self):
        r = ICPRequirements(
            requires_icp=True,
            affected_resources=["Microsoft.Web/sites"],
            resource_types_checked=1,
            guidance="ICP needed",
            icp_types=[],
        )
        assert r.requires_icp is True
