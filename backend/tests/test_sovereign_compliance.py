"""Tests for the sovereign compliance service."""

import pytest

from app.services.sovereign_compliance import (
    SOVEREIGN_FRAMEWORKS,
    SovereignComplianceService,
    sovereign_compliance_service,
)


# ── Singleton ────────────────────────────────────────────────────────────────


class TestSingleton:
    """Verify singleton instantiation."""

    def test_singleton_is_instance(self):
        assert isinstance(sovereign_compliance_service, SovereignComplianceService)

    def test_singleton_is_reusable(self):
        svc1 = sovereign_compliance_service
        svc2 = sovereign_compliance_service
        assert svc1 is svc2


# ── Framework Data Integrity ─────────────────────────────────────────────────


class TestFrameworkData:
    """Verify all frameworks have required fields and data integrity."""

    def test_all_frameworks_present(self):
        names = {fw["short_name"] for fw in SOVEREIGN_FRAMEWORKS}
        expected = {
            "FedRAMP_High",
            "FedRAMP_Moderate",
            "CMMC_L2",
            "MLPS_L3",
            "GBT_22239",
            "IRAP_Protected",
        }
        assert expected == names

    def test_frameworks_have_required_fields(self):
        required = {"short_name", "name", "description", "version", "cloud_environments", "control_families"}
        for fw in SOVEREIGN_FRAMEWORKS:
            missing = required - set(fw.keys())
            assert not missing, f"{fw['short_name']} missing: {missing}"

    def test_control_families_have_required_fields(self):
        required = {"id", "name", "description", "control_count"}
        for fw in SOVEREIGN_FRAMEWORKS:
            for cf in fw["control_families"]:
                missing = required - set(cf.keys())
                assert not missing, (
                    f"{fw['short_name']}/{cf.get('id', '?')} missing: {missing}"
                )

    def test_cloud_environments_are_valid(self):
        valid = {"commercial", "government", "china"}
        for fw in SOVEREIGN_FRAMEWORKS:
            for env in fw["cloud_environments"]:
                assert env in valid, f"{fw['short_name']} has invalid env: {env}"

    def test_control_counts_are_positive(self):
        for fw in SOVEREIGN_FRAMEWORKS:
            for cf in fw["control_families"]:
                assert cf["control_count"] > 0, (
                    f"{fw['short_name']}/{cf['id']} has non-positive control_count"
                )

    def test_fedramp_high_has_17_families(self):
        fw = next(f for f in SOVEREIGN_FRAMEWORKS if f["short_name"] == "FedRAMP_High")
        assert len(fw["control_families"]) == 17

    def test_fedramp_moderate_is_subset_of_high(self):
        high = next(f for f in SOVEREIGN_FRAMEWORKS if f["short_name"] == "FedRAMP_High")
        mod = next(f for f in SOVEREIGN_FRAMEWORKS if f["short_name"] == "FedRAMP_Moderate")
        high_ids = {cf["id"] for cf in high["control_families"]}
        mod_ids = {cf["id"] for cf in mod["control_families"]}
        assert mod_ids.issubset(high_ids)


# ── get_sovereign_frameworks ─────────────────────────────────────────────────


class TestGetSovereignFrameworks:
    """Tests for the list-all method."""

    def test_returns_list(self):
        result = sovereign_compliance_service.get_sovereign_frameworks()
        assert isinstance(result, list)

    def test_returns_all_frameworks(self):
        result = sovereign_compliance_service.get_sovereign_frameworks()
        assert len(result) == len(SOVEREIGN_FRAMEWORKS)

    def test_summary_fields_present(self):
        result = sovereign_compliance_service.get_sovereign_frameworks()
        for fw in result:
            assert "short_name" in fw
            assert "name" in fw
            assert "control_family_count" in fw
            assert "control_families" not in fw  # Summary, not detail


# ── get_framework ────────────────────────────────────────────────────────────


class TestGetFramework:
    """Tests for single-framework lookup."""

    def test_returns_framework_by_name(self):
        result = sovereign_compliance_service.get_framework("FedRAMP_High")
        assert result is not None
        assert result["short_name"] == "FedRAMP_High"

    def test_case_insensitive_lookup(self):
        result = sovereign_compliance_service.get_framework("fedramp_high")
        assert result is not None
        assert result["short_name"] == "FedRAMP_High"

    def test_returns_none_for_unknown(self):
        result = sovereign_compliance_service.get_framework("NONEXISTENT")
        assert result is None

    def test_includes_total_controls(self):
        result = sovereign_compliance_service.get_framework("FedRAMP_High")
        assert result is not None
        assert result["total_controls"] > 0

    def test_includes_control_families_detail(self):
        result = sovereign_compliance_service.get_framework("CMMC_L2")
        assert result is not None
        assert "control_families" in result
        assert len(result["control_families"]) > 0


# ── get_frameworks_for_environment ───────────────────────────────────────────


class TestGetFrameworksForEnvironment:
    """Tests for environment-based filtering."""

    def test_government_includes_fedramp(self):
        result = sovereign_compliance_service.get_frameworks_for_environment("government")
        names = {fw["short_name"] for fw in result}
        assert "FedRAMP_High" in names
        assert "FedRAMP_Moderate" in names
        assert "CMMC_L2" in names

    def test_china_includes_mlps(self):
        result = sovereign_compliance_service.get_frameworks_for_environment("china")
        names = {fw["short_name"] for fw in result}
        assert "MLPS_L3" in names
        assert "GBT_22239" in names

    def test_commercial_includes_irap(self):
        result = sovereign_compliance_service.get_frameworks_for_environment("commercial")
        names = {fw["short_name"] for fw in result}
        assert "IRAP_Protected" in names

    def test_case_insensitive_env(self):
        result = sovereign_compliance_service.get_frameworks_for_environment("GOVERNMENT")
        assert len(result) > 0

    def test_unknown_env_returns_empty(self):
        result = sovereign_compliance_service.get_frameworks_for_environment("mars")
        assert result == []


# ── get_framework_controls ───────────────────────────────────────────────────


class TestGetFrameworkControls:
    """Tests for control-family listing."""

    def test_returns_controls_for_known_framework(self):
        result = sovereign_compliance_service.get_framework_controls("FedRAMP_High")
        assert len(result) == 17

    def test_returns_empty_for_unknown_framework(self):
        result = sovereign_compliance_service.get_framework_controls("FAKE")
        assert result == []

    def test_control_has_expected_fields(self):
        controls = sovereign_compliance_service.get_framework_controls("CMMC_L2")
        assert len(controls) > 0
        first = controls[0]
        assert "id" in first
        assert "name" in first
        assert "control_count" in first


# ── evaluate_sovereign_compliance ────────────────────────────────────────────


class TestEvaluateSovereignCompliance:
    """Tests for the compliance scoring engine."""

    def test_unknown_framework_returns_zero_score(self):
        result = sovereign_compliance_service.evaluate_sovereign_compliance(
            {}, "NONEXISTENT"
        )
        assert result["overall_score"] == 0
        assert result["status"] == "unknown"
        assert "not found" in result["message"].lower()

    def test_empty_architecture_low_score(self):
        result = sovereign_compliance_service.evaluate_sovereign_compliance(
            {}, "FedRAMP_High"
        )
        assert result["overall_score"] == 0
        assert result["status"] == "non_compliant"

    def test_well_configured_architecture_scores_higher(self):
        arch = {
            "security": {
                "rbac_model": "Azure RBAC",
                "defender_enabled": True,
                "sentinel_enabled": True,
                "disk_encryption": True,
                "storage_encryption": True,
                "tls_policy": "TLS 1.2",
                "vulnerability_scanning": True,
                "threat_assessment": True,
                "antimalware": True,
            },
            "identity": {
                "mfa_policy": "all_users",
                "conditional_access": True,
                "rbac_model": "Azure RBAC",
                "pim_enabled": True,
            },
            "network": {
                "topology": "hub-spoke",
                "firewall_enabled": True,
                "nsg_enabled": True,
            },
            "management": {
                "log_analytics": True,
                "diagnostic_settings": True,
                "backup_policy": True,
                "disaster_recovery": True,
                "update_management": True,
                "patch_policy": True,
            },
            "governance": {
                "policy_assignments": True,
                "compliance_monitoring": True,
                "resource_locks": True,
                "tag_policies": True,
                "approved_services": True,
                "service_catalog": True,
            },
        }
        result = sovereign_compliance_service.evaluate_sovereign_compliance(
            arch, "FedRAMP_High"
        )
        assert result["overall_score"] > 50
        assert result["framework"] == "FedRAMP_High"

    def test_family_scores_present(self):
        result = sovereign_compliance_service.evaluate_sovereign_compliance(
            {}, "FedRAMP_Moderate"
        )
        assert "family_scores" in result
        assert len(result["family_scores"]) > 0

    def test_not_applicable_families(self):
        result = sovereign_compliance_service.evaluate_sovereign_compliance(
            {}, "FedRAMP_High"
        )
        na_families = [
            fs for fs in result["family_scores"] if fs["status"] == "not_applicable"
        ]
        # PE and PS have no architecture checks
        assert len(na_families) >= 2

    def test_recommendations_for_non_compliant(self):
        result = sovereign_compliance_service.evaluate_sovereign_compliance(
            {}, "CMMC_L2"
        )
        assert len(result["recommendations"]) > 0

    def test_china_framework_evaluation(self):
        result = sovereign_compliance_service.evaluate_sovereign_compliance(
            {"network": {"topology": "hub-spoke", "firewall_enabled": True}},
            "MLPS_L3",
        )
        assert result["framework"] == "MLPS_L3"
        assert "family_scores" in result


# ── _resolve_path helper ─────────────────────────────────────────────────────


class TestResolvePath:
    """Tests for the dotted-path resolver."""

    def test_shallow_path(self):
        assert SovereignComplianceService._resolve_path({"a": True}, "a") is True

    def test_nested_path(self):
        data = {"security": {"defender_enabled": True}}
        assert SovereignComplianceService._resolve_path(data, "security.defender_enabled") is True

    def test_missing_key(self):
        assert SovereignComplianceService._resolve_path({}, "a.b.c") is False

    def test_falsy_value(self):
        assert SovereignComplianceService._resolve_path({"a": False}, "a") is False
        assert SovereignComplianceService._resolve_path({"a": 0}, "a") is False
        assert SovereignComplianceService._resolve_path({"a": ""}, "a") is False
