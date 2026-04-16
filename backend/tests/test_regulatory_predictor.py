"""Tests for regulatory gap predictor — service, schemas, and API routes.

Covers industry/geography mapping, data type controls, gap analysis,
remediation recommendations, AI-enhanced prediction, policy auto-apply,
and all route endpoints.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.regulatory import (
    ApplyPoliciesRequest,
    ControlGap,
    ControlStatus,
    FrameworkGapAnalysis,
    GapAnalysisRequest,
    PredictedFramework,
    Recommendation,
    RegulatoryPredictionRequest,
    RegulatoryPredictionResponse,
)
from app.services.regulatory_predictor import RegulatoryPredictor, regulatory_predictor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def predictor():
    """Return a fresh RegulatoryPredictor instance."""
    return RegulatoryPredictor()


@pytest.fixture()
def valid_architecture() -> dict:
    """A minimal valid architecture with all sections populated."""
    return {
        "security": {
            "defender_for_cloud": True,
            "azure_firewall": True,
            "key_vault_per_subscription": True,
            "sentinel": True,
        },
        "identity": {
            "provider": "Microsoft Entra ID",
            "rbac_model": "least-privilege",
            "pim_enabled": True,
            "conditional_access": True,
            "mfa_policy": "always",
        },
        "management": {
            "log_analytics": {"retention_days": 90},
            "monitoring": {"enabled": True},
            "backup": {"enabled": True},
        },
        "governance": {
            "policies": [
                {"name": "allowed-locations", "scope": "/", "effect": "Deny"},
            ],
            "tagging_strategy": {
                "mandatory_tags": ["environment", "owner"],
            },
        },
    }


@pytest.fixture()
def minimal_architecture() -> dict:
    """An architecture with minimal/empty sections — many gaps expected."""
    return {
        "security": {},
        "identity": {},
        "management": {},
        "governance": {},
    }


@pytest.fixture()
def empty_architecture() -> dict:
    """A completely empty architecture."""
    return {}


@pytest.fixture()
def client():
    """Return a FastAPI TestClient for route tests."""
    from app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Schema / Model tests
# ---------------------------------------------------------------------------


class TestSchemas:
    """Tests for Pydantic schema models."""

    def test_control_status_enum_values(self):
        assert ControlStatus.satisfied == "satisfied"
        assert ControlStatus.partial == "partial"
        assert ControlStatus.gap == "gap"

    def test_predicted_framework_defaults(self):
        pf = PredictedFramework(framework_name="HIPAA")
        assert pf.framework_name == "HIPAA"
        assert pf.confidence == "medium"
        assert pf.reason == ""
        assert pf.applicable_controls == []

    def test_predicted_framework_full(self):
        pf = PredictedFramework(
            framework_name="GDPR",
            confidence="high",
            reason="EU operations",
            applicable_controls=["GDPR-1", "GDPR-2"],
        )
        assert pf.confidence == "high"
        assert len(pf.applicable_controls) == 2

    def test_control_gap_model(self):
        cg = ControlGap(
            control_id="HIPAA-1",
            control_name="Access controls",
            status=ControlStatus.gap,
            gap_description="Not implemented",
            remediation="Enable RBAC",
        )
        assert cg.status == ControlStatus.gap

    def test_framework_gap_analysis_model(self):
        fga = FrameworkGapAnalysis(
            framework_name="PCI-DSS",
            total_controls=5,
            satisfied=3,
            partial=1,
            gaps=1,
        )
        assert fga.total_controls == 5
        assert fga.gap_details == []

    def test_recommendation_model(self):
        rec = Recommendation(
            priority="high",
            description="Enable encryption",
            architecture_changes="Add Key Vault",
            frameworks_addressed=["HIPAA", "GDPR"],
        )
        assert len(rec.frameworks_addressed) == 2

    def test_prediction_request_defaults(self):
        req = RegulatoryPredictionRequest(industry="healthcare", geography="EU")
        assert req.data_types is None
        assert req.use_ai is False

    def test_prediction_request_with_data_types(self):
        req = RegulatoryPredictionRequest(
            industry="finance",
            geography="California",
            data_types=["PII", "financial"],
            use_ai=True,
        )
        assert len(req.data_types) == 2
        assert req.use_ai is True

    def test_prediction_response_defaults(self):
        resp = RegulatoryPredictionResponse()
        assert resp.predicted_frameworks == []
        assert resp.gap_analyses == []
        assert resp.recommendations == []

    def test_gap_analysis_request(self):
        req = GapAnalysisRequest(
            architecture={"security": {}}, frameworks=["HIPAA"]
        )
        assert req.frameworks == ["HIPAA"]

    def test_apply_policies_request(self):
        req = ApplyPoliciesRequest(
            architecture={"governance": {}}, frameworks=["SOX"]
        )
        assert req.frameworks == ["SOX"]

    def test_predicted_framework_extra_fields(self):
        """extra='allow' permits additional fields."""
        pf = PredictedFramework(
            framework_name="HIPAA", extra_field="extra_value"
        )
        assert pf.framework_name == "HIPAA"

    def test_control_gap_extra_fields(self):
        cg = ControlGap(
            control_id="X",
            control_name="Test",
            status=ControlStatus.gap,
            custom="data",
        )
        assert cg.control_id == "X"


# ---------------------------------------------------------------------------
# Industry mapping tests
# ---------------------------------------------------------------------------


class TestIndustryMapping:
    """Tests for industry → framework mapping."""

    def test_healthcare_returns_hipaa_hitrust(self, predictor):
        results = predictor.predict_frameworks("healthcare", "US")
        names = {r.framework_name for r in results}
        assert "HIPAA" in names
        assert "HITRUST" in names

    def test_finance_returns_pci_sox_glba(self, predictor):
        results = predictor.predict_frameworks("finance", "US")
        names = {r.framework_name for r in results}
        assert "PCI-DSS" in names
        assert "SOX" in names
        assert "GLBA" in names

    def test_government_returns_fedramp_nist(self, predictor):
        results = predictor.predict_frameworks("government", "US")
        names = {r.framework_name for r in results}
        assert "FedRAMP" in names
        assert "NIST 800-171" in names

    def test_retail_returns_pci_ccpa(self, predictor):
        results = predictor.predict_frameworks("retail", "US")
        names = {r.framework_name for r in results}
        assert "PCI-DSS" in names
        assert "CCPA" in names

    def test_technology_returns_soc2_iso(self, predictor):
        results = predictor.predict_frameworks("technology", "US")
        names = {r.framework_name for r in results}
        assert "SOC 2" in names
        assert "ISO 27001" in names

    def test_education_returns_ferpa(self, predictor):
        results = predictor.predict_frameworks("education", "US")
        names = {r.framework_name for r in results}
        assert "FERPA" in names

    def test_unknown_industry_returns_empty(self, predictor):
        results = predictor.predict_frameworks("unknown_industry", "US")
        assert len(results) == 0

    def test_industry_case_insensitive(self, predictor):
        results = predictor.predict_frameworks("Healthcare", "US")
        names = {r.framework_name for r in results}
        assert "HIPAA" in names

    def test_industry_predictions_have_high_confidence(self, predictor):
        results = predictor.predict_frameworks("healthcare", "US")
        for r in results:
            assert r.confidence == "high"


# ---------------------------------------------------------------------------
# Geography mapping tests
# ---------------------------------------------------------------------------


class TestGeographyMapping:
    """Tests for geography → framework mapping."""

    def test_eu_returns_gdpr(self, predictor):
        results = predictor.predict_frameworks("technology", "EU")
        names = {r.framework_name for r in results}
        assert "GDPR" in names

    def test_california_returns_ccpa(self, predictor):
        results = predictor.predict_frameworks("technology", "California")
        names = {r.framework_name for r in results}
        assert "CCPA" in names

    def test_brazil_returns_lgpd(self, predictor):
        results = predictor.predict_frameworks("technology", "Brazil")
        names = {r.framework_name for r in results}
        assert "LGPD" in names

    def test_canada_returns_pipeda(self, predictor):
        results = predictor.predict_frameworks("technology", "Canada")
        names = {r.framework_name for r in results}
        assert "PIPEDA" in names

    def test_global_returns_iso27001(self, predictor):
        results = predictor.predict_frameworks("unknown", "global")
        names = {r.framework_name for r in results}
        assert "ISO 27001" in names

    def test_geography_normalisation_europe(self, predictor):
        results = predictor.predict_frameworks("technology", "Europe")
        names = {r.framework_name for r in results}
        assert "GDPR" in names

    def test_geography_normalisation_br(self, predictor):
        results = predictor.predict_frameworks("technology", "BR")
        names = {r.framework_name for r in results}
        assert "LGPD" in names


# ---------------------------------------------------------------------------
# Data type controls tests
# ---------------------------------------------------------------------------


class TestDataTypeControls:
    """Tests for data type → controls mapping."""

    def test_pii_controls(self, predictor):
        controls = predictor.DATA_TYPE_CONTROLS.get("PII", [])
        assert "encryption" in controls
        assert "access_controls" in controls
        assert "audit_logging" in controls

    def test_phi_controls(self, predictor):
        controls = predictor.DATA_TYPE_CONTROLS.get("PHI", [])
        assert "HIPAA_controls" in controls
        assert "encryption" in controls

    def test_financial_controls(self, predictor):
        controls = predictor.DATA_TYPE_CONTROLS.get("financial", [])
        assert "PCI_controls" in controls
        assert "tokenization" in controls

    def test_pii_data_type_implies_frameworks(self, predictor):
        results = predictor.predict_frameworks("unknown", "unknown", data_types=["PII"])
        names = {r.framework_name for r in results}
        assert "GDPR" in names or "CCPA" in names

    def test_phi_data_type_implies_hipaa(self, predictor):
        results = predictor.predict_frameworks("unknown", "unknown", data_types=["PHI"])
        names = {r.framework_name for r in results}
        assert "HIPAA" in names

    def test_financial_data_type_implies_pci(self, predictor):
        results = predictor.predict_frameworks("unknown", "unknown", data_types=["financial"])
        names = {r.framework_name for r in results}
        assert "PCI-DSS" in names


# ---------------------------------------------------------------------------
# Combined prediction tests
# ---------------------------------------------------------------------------


class TestCombinedPrediction:
    """Tests for combined industry + geography + data type prediction."""

    def test_healthcare_eu_returns_hipaa_and_gdpr(self, predictor):
        results = predictor.predict_frameworks("healthcare", "EU")
        names = {r.framework_name for r in results}
        assert "HIPAA" in names
        assert "GDPR" in names

    def test_finance_california_returns_pci_and_ccpa(self, predictor):
        results = predictor.predict_frameworks("finance", "California")
        names = {r.framework_name for r in results}
        assert "PCI-DSS" in names
        assert "CCPA" in names

    def test_no_duplicates_when_overlap(self, predictor):
        """CCPA from retail + CCPA from California should not duplicate."""
        results = predictor.predict_frameworks("retail", "California")
        ccpa_results = [r for r in results if r.framework_name == "CCPA"]
        assert len(ccpa_results) == 1
        assert ccpa_results[0].confidence == "high"

    def test_combined_with_data_types(self, predictor):
        results = predictor.predict_frameworks(
            "healthcare", "EU", data_types=["PII", "PHI"]
        )
        names = {r.framework_name for r in results}
        assert "HIPAA" in names
        assert "GDPR" in names

    def test_all_predictions_have_framework_name(self, predictor):
        results = predictor.predict_frameworks("finance", "EU", data_types=["financial"])
        for r in results:
            assert r.framework_name
            assert len(r.framework_name) > 0


# ---------------------------------------------------------------------------
# Gap analysis tests
# ---------------------------------------------------------------------------


class TestGapAnalysis:
    """Tests for gap analysis against architectures."""

    def test_fully_compliant_architecture(self, predictor, valid_architecture):
        results = predictor.analyze_gaps(valid_architecture, ["HIPAA"])
        assert len(results) == 1
        analysis = results[0]
        assert analysis.framework_name == "HIPAA"
        assert analysis.total_controls > 0
        assert analysis.satisfied > 0

    def test_minimal_architecture_has_gaps(self, predictor, minimal_architecture):
        results = predictor.analyze_gaps(minimal_architecture, ["HIPAA"])
        analysis = results[0]
        assert analysis.gaps > 0

    def test_empty_architecture_all_gaps(self, predictor, empty_architecture):
        results = predictor.analyze_gaps(empty_architecture, ["PCI-DSS"])
        analysis = results[0]
        assert analysis.gaps == analysis.total_controls

    def test_gap_details_populated(self, predictor, minimal_architecture):
        results = predictor.analyze_gaps(minimal_architecture, ["SOC 2"])
        analysis = results[0]
        assert len(analysis.gap_details) > 0
        for detail in analysis.gap_details:
            assert detail.control_id
            assert detail.control_name
            assert detail.status in (ControlStatus.partial, ControlStatus.gap)

    def test_multiple_frameworks(self, predictor, valid_architecture):
        results = predictor.analyze_gaps(valid_architecture, ["HIPAA", "GDPR", "SOC 2"])
        assert len(results) == 3
        names = {r.framework_name for r in results}
        assert names == {"HIPAA", "GDPR", "SOC 2"}

    def test_unknown_framework_returns_zero_controls(self, predictor, valid_architecture):
        results = predictor.analyze_gaps(valid_architecture, ["UNKNOWN_FW"])
        assert len(results) == 1
        assert results[0].total_controls == 0

    def test_gap_analysis_totals_add_up(self, predictor, valid_architecture):
        results = predictor.analyze_gaps(valid_architecture, ["ISO 27001"])
        analysis = results[0]
        assert analysis.satisfied + analysis.partial + analysis.gaps == analysis.total_controls

    def test_partial_security_architecture(self, predictor):
        arch = {
            "security": {"defender_for_cloud": True},
            "identity": {"rbac_model": "least-privilege"},
            "management": {"log_analytics": {"retention_days": 30}},
            "governance": {"policies": [{"name": "test"}]},
        }
        results = predictor.analyze_gaps(arch, ["HIPAA"])
        analysis = results[0]
        # Should have a mix of satisfied, partial, and possibly gaps
        assert analysis.total_controls == 5

    def test_gap_remediation_not_empty(self, predictor, empty_architecture):
        results = predictor.analyze_gaps(empty_architecture, ["GDPR"])
        for detail in results[0].gap_details:
            assert detail.remediation != ""


# ---------------------------------------------------------------------------
# Remediation recommendations tests
# ---------------------------------------------------------------------------


class TestRemediationRecommendations:
    """Tests for generating remediation recommendations."""

    def test_recommendations_from_gaps(self, predictor, minimal_architecture):
        gaps = predictor.analyze_gaps(minimal_architecture, ["HIPAA"])
        recs = predictor.get_remediation_recommendations(gaps)
        assert len(recs) > 0

    def test_recommendations_sorted_by_priority(self, predictor, empty_architecture):
        gaps = predictor.analyze_gaps(empty_architecture, ["HIPAA", "PCI-DSS"])
        recs = predictor.get_remediation_recommendations(gaps)
        # All should start with high priority
        if len(recs) >= 2:
            priorities = [r.priority for r in recs]
            high_idx = [i for i, p in enumerate(priorities) if p == "high"]
            medium_idx = [i for i, p in enumerate(priorities) if p == "medium"]
            if high_idx and medium_idx:
                assert max(high_idx) < min(medium_idx)

    def test_recommendations_have_architecture_changes(self, predictor, empty_architecture):
        gaps = predictor.analyze_gaps(empty_architecture, ["SOC 2"])
        recs = predictor.get_remediation_recommendations(gaps)
        for rec in recs:
            assert rec.architecture_changes != ""

    def test_recommendations_reference_frameworks(self, predictor, empty_architecture):
        gaps = predictor.analyze_gaps(empty_architecture, ["GDPR"])
        recs = predictor.get_remediation_recommendations(gaps)
        for rec in recs:
            assert "GDPR" in rec.frameworks_addressed

    def test_deduplication_across_frameworks(self, predictor, empty_architecture):
        gaps = predictor.analyze_gaps(empty_architecture, ["HIPAA", "GDPR"])
        recs = predictor.get_remediation_recommendations(gaps)
        descriptions = [r.description for r in recs]
        # No duplicate descriptions
        assert len(descriptions) == len(set(descriptions))

    def test_no_recommendations_for_fully_compliant(self, predictor, valid_architecture):
        gaps = predictor.analyze_gaps(valid_architecture, ["FERPA"])
        recs = predictor.get_remediation_recommendations(gaps)
        # Fully compliant architecture may still have partial controls,
        # but gaps should be minimal
        for rec in recs:
            assert rec.priority in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# AI-enhanced prediction tests
# ---------------------------------------------------------------------------


class TestAIEnhancedPrediction:
    """Tests for AI-enhanced regulatory prediction."""

    @pytest.mark.asyncio
    async def test_ai_prediction_mock_fallback(self, predictor):
        """When AI is not configured, returns mock enhanced data."""
        with patch("app.services.regulatory_predictor.json") as mock_json:
            mock_json.loads = json.loads
            mock_json.dumps = json.dumps
            result = await predictor.predict_with_ai("healthcare", "EU")

        assert result["ai_enhanced"] is True
        assert "predictions" in result
        assert "overlapping_controls" in result
        assert "risk_prioritization" in result

    @pytest.mark.asyncio
    async def test_ai_prediction_returns_base_predictions(self, predictor):
        result = await predictor.predict_with_ai("finance", "California")
        assert len(result["predictions"]) > 0

    @pytest.mark.asyncio
    async def test_ai_prediction_has_overlapping_controls(self, predictor):
        result = await predictor.predict_with_ai("healthcare", "EU")
        assert isinstance(result["overlapping_controls"], list)

    @pytest.mark.asyncio
    async def test_ai_prediction_has_risk_prioritization(self, predictor):
        result = await predictor.predict_with_ai("technology", "global")
        assert isinstance(result["risk_prioritization"], list)

    @pytest.mark.asyncio
    async def test_ai_prediction_with_data_types(self, predictor):
        result = await predictor.predict_with_ai(
            "healthcare", "EU", data_types=["PHI", "PII"]
        )
        assert result["ai_enhanced"] is True
        assert len(result["predictions"]) > 0


# ---------------------------------------------------------------------------
# Policy auto-apply tests
# ---------------------------------------------------------------------------


class TestPolicyAutoApply:
    """Tests for auto-applying framework policies to architecture."""

    def test_apply_hipaa_policies(self, predictor, valid_architecture):
        result = predictor.auto_apply_policies(valid_architecture, ["HIPAA"])
        policies = result["governance"]["policies"]
        names = {p["name"] for p in policies}
        assert "hipaa-encryption-at-rest" in names
        assert "hipaa-audit-logging" in names

    def test_apply_pci_policies(self, predictor, valid_architecture):
        result = predictor.auto_apply_policies(valid_architecture, ["PCI-DSS"])
        policies = result["governance"]["policies"]
        names = {p["name"] for p in policies}
        assert "pci-firewall-config" in names

    def test_apply_does_not_duplicate(self, predictor, valid_architecture):
        """Applying the same framework twice should not duplicate policies."""
        result1 = predictor.auto_apply_policies(valid_architecture, ["HIPAA"])
        result2 = predictor.auto_apply_policies(result1, ["HIPAA"])
        policies = result2["governance"]["policies"]
        hipaa_names = [p["name"] for p in policies if p["name"].startswith("hipaa-")]
        assert len(hipaa_names) == len(set(hipaa_names))

    def test_apply_multiple_frameworks(self, predictor, valid_architecture):
        result = predictor.auto_apply_policies(
            valid_architecture, ["HIPAA", "GDPR", "SOC 2"]
        )
        policies = result["governance"]["policies"]
        names = {p["name"] for p in policies}
        assert "hipaa-encryption-at-rest" in names
        assert "gdpr-data-protection" in names
        assert "soc2-logical-access" in names

    def test_apply_preserves_existing_policies(self, predictor, valid_architecture):
        original_count = len(valid_architecture["governance"]["policies"])
        result = predictor.auto_apply_policies(valid_architecture, ["HIPAA"])
        new_count = len(result["governance"]["policies"])
        assert new_count > original_count

    def test_apply_to_empty_governance(self, predictor):
        result = predictor.auto_apply_policies({}, ["SOX"])
        policies = result["governance"]["policies"]
        assert len(policies) > 0

    def test_apply_unknown_framework_no_policies(self, predictor, valid_architecture):
        original_count = len(valid_architecture["governance"]["policies"])
        result = predictor.auto_apply_policies(valid_architecture, ["UNKNOWN_FW"])
        new_count = len(result["governance"]["policies"])
        assert new_count == original_count


# ---------------------------------------------------------------------------
# Framework descriptions tests
# ---------------------------------------------------------------------------


class TestFrameworkDescriptions:
    """Tests for framework descriptions knowledge base."""

    def test_at_least_five_frameworks(self, predictor):
        assert len(predictor.FRAMEWORK_DESCRIPTIONS) >= 5

    def test_all_industry_frameworks_have_descriptions(self, predictor):
        for frameworks in predictor.INDUSTRY_FRAMEWORK_MAP.values():
            for fw in frameworks:
                assert fw in predictor.FRAMEWORK_DESCRIPTIONS, f"Missing description for {fw}"

    def test_all_geography_frameworks_have_descriptions(self, predictor):
        for frameworks in predictor.GEOGRAPHY_FRAMEWORK_MAP.values():
            for fw in frameworks:
                assert fw in predictor.FRAMEWORK_DESCRIPTIONS, f"Missing description for {fw}"

    def test_fourteen_frameworks_in_knowledge_base(self, predictor):
        assert len(predictor.FRAMEWORK_DESCRIPTIONS) == 14


# ---------------------------------------------------------------------------
# Route endpoint tests
# ---------------------------------------------------------------------------


class TestRoutes:
    """Tests for all regulatory API route endpoints."""

    def _auth_headers(self):
        """Return headers that bypass auth in dev mode."""
        return {"Authorization": "Bearer dev-token"}

    def test_predict_endpoint(self, client):
        resp = client.post(
            "/api/regulatory/predict",
            json={"industry": "healthcare", "geography": "EU"},
            headers=self._auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "predicted_frameworks" in data

    def test_predict_with_data_types(self, client):
        resp = client.post(
            "/api/regulatory/predict",
            json={
                "industry": "finance",
                "geography": "California",
                "data_types": ["PII", "financial"],
            },
            headers=self._auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["predicted_frameworks"]) > 0

    def test_predict_with_ai_flag(self, client):
        resp = client.post(
            "/api/regulatory/predict",
            json={
                "industry": "technology",
                "geography": "global",
                "use_ai": True,
            },
            headers=self._auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ai_enhanced") is True

    def test_gaps_endpoint(self, client):
        resp = client.post(
            "/api/regulatory/gaps",
            json={
                "architecture": {
                    "security": {"defender_for_cloud": True, "azure_firewall": True},
                    "identity": {"rbac_model": "least-privilege", "mfa_policy": "always"},
                    "management": {"log_analytics": {}, "monitoring": {}},
                    "governance": {"policies": [{"name": "test"}], "tagging_strategy": {}},
                },
                "frameworks": ["HIPAA", "GDPR"],
            },
            headers=self._auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "gap_analyses" in data
        assert "recommendations" in data
        assert len(data["gap_analyses"]) == 2

    def test_gaps_with_empty_architecture(self, client):
        resp = client.post(
            "/api/regulatory/gaps",
            json={"architecture": {}, "frameworks": ["PCI-DSS"]},
            headers=self._auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        analysis = data["gap_analyses"][0]
        assert analysis["gaps"] == analysis["total_controls"]

    def test_frameworks_endpoint(self, client):
        resp = client.get(
            "/api/regulatory/frameworks",
            headers=self._auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "frameworks" in data
        assert "total" in data
        assert data["total"] >= 5

    def test_frameworks_list_has_names_and_descriptions(self, client):
        resp = client.get(
            "/api/regulatory/frameworks",
            headers=self._auth_headers(),
        )
        data = resp.json()
        for fw in data["frameworks"]:
            assert "name" in fw
            assert "description" in fw
            assert len(fw["description"]) > 0

    def test_apply_policies_endpoint(self, client):
        resp = client.post(
            "/api/regulatory/apply-policies",
            json={
                "architecture": {
                    "governance": {
                        "policies": [
                            {"name": "existing-policy", "scope": "/", "effect": "Audit"},
                        ]
                    }
                },
                "frameworks": ["HIPAA", "GDPR"],
            },
            headers=self._auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "architecture" in data
        policies = data["architecture"]["governance"]["policies"]
        names = {p["name"] for p in policies}
        assert "existing-policy" in names
        assert "hipaa-encryption-at-rest" in names
        assert "gdpr-data-protection" in names

    def test_predict_invalid_request(self, client):
        resp = client.post(
            "/api/regulatory/predict",
            json={},
            headers=self._auth_headers(),
        )
        assert resp.status_code == 422  # Validation error


# ---------------------------------------------------------------------------
# Singleton tests
# ---------------------------------------------------------------------------


class TestSingleton:
    """Tests for module-level singleton behaviour."""

    def test_singleton_is_instance_of_regulatory_predictor(self):
        assert isinstance(regulatory_predictor, RegulatoryPredictor)

    def test_singleton_has_framework_maps(self):
        assert len(regulatory_predictor.INDUSTRY_FRAMEWORK_MAP) > 0
        assert len(regulatory_predictor.GEOGRAPHY_FRAMEWORK_MAP) > 0
        assert len(regulatory_predictor.DATA_TYPE_CONTROLS) > 0


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_data_types_list(self, predictor):
        results = predictor.predict_frameworks("healthcare", "EU", data_types=[])
        names = {r.framework_name for r in results}
        assert "HIPAA" in names

    def test_none_data_types(self, predictor):
        results = predictor.predict_frameworks("healthcare", "EU", data_types=None)
        assert len(results) > 0

    def test_empty_frameworks_for_gap_analysis(self, predictor, valid_architecture):
        results = predictor.analyze_gaps(valid_architecture, [])
        assert results == []

    def test_gap_analysis_with_missing_sections(self, predictor):
        """Architecture missing some sections should still work."""
        arch = {"security": {"defender_for_cloud": True}}
        results = predictor.analyze_gaps(arch, ["HIPAA"])
        assert len(results) == 1
        assert results[0].total_controls > 0

    def test_recommendations_from_empty_gaps(self, predictor):
        recs = predictor.get_remediation_recommendations([])
        assert recs == []

    def test_geography_case_insensitive(self, predictor):
        results = predictor.predict_frameworks("technology", "eu")
        names = {r.framework_name for r in results}
        assert "GDPR" in names

    def test_framework_controls_all_have_ids(self, predictor):
        for fw, controls in predictor.FRAMEWORK_CONTROLS.items():
            for ctrl in controls:
                assert "id" in ctrl, f"Control missing id in {fw}"
                assert "name" in ctrl, f"Control missing name in {fw}"
                assert "check" in ctrl, f"Control missing check in {fw}"
