"""Tests for the gap analysis engine and brownfield questionnaire flow."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.discovery_service import discovery_service
from app.services.gap_analyzer import GapAnalyzer, gap_analyzer
from app.services.questionnaire import QuestionnaireService, questionnaire_service


# ---------------------------------------------------------------------------
# Gap Analyzer Unit Tests
# ---------------------------------------------------------------------------


class TestGapAnalyzerService:
    """Unit tests for the GapAnalyzer class."""

    def test_singleton_exists(self):
        """gap_analyzer is a module-level singleton."""
        assert gap_analyzer is not None
        assert isinstance(gap_analyzer, GapAnalyzer)

    def test_analyze_empty_environment(self):
        """Analyze an environment with no resources produces critical findings."""
        summary = {
            "total_resource_groups": 0,
            "total_resources": 0,
            "total_vnets": 0,
            "total_nsgs": 0,
            "total_policies": 0,
            "total_role_assignments": 0,
            "scanned_at": "2026-01-01T00:00:00Z",
        }
        result = gap_analyzer.analyze(summary, [])

        assert result["total_findings"] > 0
        assert result["critical_count"] > 0
        assert len(result["areas_checked"]) == 7
        assert len(result["areas_skipped"]) == 0

    def test_analyze_well_configured_environment(self):
        """A well-configured environment has fewer findings."""
        summary = {
            "total_resource_groups": 5,
            "total_resources": 20,
            "total_vnets": 3,
            "total_nsgs": 5,
            "total_policies": 15,
            "total_role_assignments": 8,
            "scanned_at": "2026-01-01T00:00:00Z",
        }
        resources = [
            {
                "category": "resource",
                "resource_type": "Microsoft.KeyVault/vaults",
                "resource_id": "/sub/rg/kv-01",
                "name": "kv-prod-001",
                "properties": {"tags": {"environment": "prod"}},
            },
            {
                "category": "resource",
                "resource_type": "microsoft.operationalinsights/workspaces",
                "resource_id": "/sub/rg/log-01",
                "name": "log-prod-001",
                "properties": {"tags": {"environment": "prod"}},
            },
            {
                "category": "resource",
                "resource_type": "microsoft.insights/components",
                "resource_id": "/sub/rg/appi-01",
                "name": "appi-prod-001",
                "properties": {"tags": {"environment": "prod"}},
            },
            {
                "category": "network",
                "resource_type": "Microsoft.Network/virtualNetworks",
                "resource_id": "/sub/rg/vnet-01",
                "name": "vnet-hub-001",
                "properties": {},
            },
            {
                "category": "policy",
                "resource_type": "Microsoft.Authorization/policyAssignments",
                "resource_id": "/sub/pa-tags",
                "name": "Require Tags Policy",
                "properties": {},
            },
            {
                "category": "rbac",
                "resource_type": "Microsoft.Authorization/roleAssignments",
                "resource_id": "/sub/ra-01",
                "name": "ra-01",
                "properties": {"role_definition_id": "contributor"},
            },
        ]

        result = gap_analyzer.analyze(summary, resources)
        # Should have significantly fewer critical findings
        assert result["critical_count"] == 0

    def test_analyze_no_policies(self):
        """No policies → critical finding."""
        summary = {
            "total_resource_groups": 1,
            "total_resources": 5,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 0,
            "total_role_assignments": 2,
        }
        result = gap_analyzer.analyze(summary, [])

        policy_findings = [
            f for f in result["findings"] if f["category"] == "policy"
        ]
        assert any(f["severity"] == "critical" for f in policy_findings)

    def test_analyze_no_nsgs_with_vnets(self):
        """VNets without NSGs → critical finding."""
        summary = {
            "total_resource_groups": 1,
            "total_resources": 5,
            "total_vnets": 2,
            "total_nsgs": 0,
            "total_policies": 5,
            "total_role_assignments": 2,
        }
        result = gap_analyzer.analyze(summary, [])

        net_findings = [
            f for f in result["findings"] if f["category"] == "networking"
        ]
        assert any(f["severity"] == "critical" for f in net_findings)

    def test_analyze_no_key_vault(self):
        """No Key Vault → high finding."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 10,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        resources = [
            {
                "category": "resource",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "resource_id": "/sub/rg/vm-01",
                "name": "vm-01",
                "properties": {},
            },
        ]
        result = gap_analyzer.analyze(summary, resources)

        sec_findings = [
            f for f in result["findings"] if f["category"] == "security"
        ]
        assert any(
            "Key Vault" in f["title"] for f in sec_findings
        )

    def test_analyze_no_log_analytics(self):
        """No Log Analytics → high finding."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 10,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        result = gap_analyzer.analyze(summary, [])

        mon_findings = [
            f for f in result["findings"] if f["category"] == "monitoring"
        ]
        assert any(
            "Log Analytics" in f["title"] for f in mon_findings
        )

    def test_analyze_naming_violations(self):
        """Resources without CAF naming prefixes → medium finding."""
        summary = {
            "total_resource_groups": 1,
            "total_resources": 5,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "total_role_assignments": 2,
        }
        resources = [
            {
                "category": "resource",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "resource_id": f"/sub/rg/myvm{i}",
                "name": f"myvm{i}",
                "properties": {},
            }
            for i in range(5)
        ]
        result = gap_analyzer.analyze(summary, resources)

        naming_findings = [
            f for f in result["findings"] if f["category"] == "naming"
        ]
        assert len(naming_findings) > 0

    def test_analyze_resource_error_skips_areas(self):
        """Scan errors cause corresponding areas to be skipped."""
        summary = {
            "resource_error": "Auth failed",
            "total_policies": 5,
            "total_role_assignments": 2,
            "total_vnets": 1,
            "total_nsgs": 1,
        }
        result = gap_analyzer.analyze(summary, [])

        assert "management_groups" in result["areas_skipped"]
        assert "naming" in result["areas_skipped"]
        assert "monitoring" in result["areas_skipped"]
        assert "security" in result["areas_skipped"]
        assert "policy" in result["areas_checked"]
        assert "rbac" in result["areas_checked"]

    def test_analyze_network_error_skips_networking(self):
        """Network error causes networking area to be skipped."""
        summary = {
            "total_resource_groups": 1,
            "total_resources": 5,
            "total_policies": 5,
            "total_role_assignments": 2,
            "network_error": "Network scan failed",
        }
        result = gap_analyzer.analyze(summary, [])

        assert "networking" in result["areas_skipped"]
        assert "networking" not in result["areas_checked"]

    def test_analyze_policy_error_skips_policy(self):
        """Policy error causes policy area to be skipped."""
        summary = {
            "total_resource_groups": 1,
            "total_resources": 5,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_role_assignments": 2,
            "policy_error": "Forbidden",
        }
        result = gap_analyzer.analyze(summary, [])

        assert "policy" in result["areas_skipped"]

    def test_analyze_rbac_error_skips_rbac(self):
        """RBAC error causes rbac area to be skipped."""
        summary = {
            "total_resource_groups": 1,
            "total_resources": 5,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "rbac_error": "Auth failed",
        }
        result = gap_analyzer.analyze(summary, [])

        assert "rbac" in result["areas_skipped"]

    def test_finding_has_required_fields(self):
        """Each finding has all required fields."""
        summary = {
            "total_resource_groups": 0,
            "total_resources": 0,
            "total_vnets": 0,
            "total_nsgs": 0,
            "total_policies": 0,
            "total_role_assignments": 0,
        }
        result = gap_analyzer.analyze(summary, [])

        for finding in result["findings"]:
            assert "id" in finding
            assert "category" in finding
            assert "severity" in finding
            assert "title" in finding
            assert "description" in finding
            assert "remediation" in finding
            assert finding["severity"] in ("critical", "high", "medium", "low")

    def test_management_groups_check_many_rgs(self):
        """Many resource groups suggest need for management group hierarchy."""
        summary = {
            "total_resource_groups": 10,
            "total_resources": 50,
            "total_vnets": 2,
            "total_nsgs": 2,
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        result = gap_analyzer.analyze(summary, [])

        mg_findings = [
            f for f in result["findings"]
            if f["category"] == "management_groups"
        ]
        assert len(mg_findings) > 0

    def test_single_vnet_suggests_hub_spoke(self):
        """Single VNet → medium finding suggesting hub-spoke."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 10,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        result = gap_analyzer.analyze(summary, [])

        net_findings = [
            f for f in result["findings"] if f["category"] == "networking"
        ]
        assert any("hub-spoke" in f["title"].lower() for f in net_findings)

    def test_minimal_policies_high_finding(self):
        """Few policies → high finding about minimal coverage."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 10,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 3,
            "total_role_assignments": 3,
        }
        result = gap_analyzer.analyze(summary, [])

        policy_findings = [
            f for f in result["findings"]
            if f["category"] == "policy" and f["severity"] == "high"
        ]
        assert len(policy_findings) > 0

    def test_no_rbac_critical_finding(self):
        """No RBAC assignments → critical finding."""
        summary = {
            "total_resource_groups": 1,
            "total_resources": 5,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "total_role_assignments": 0,
        }
        result = gap_analyzer.analyze(summary, [])

        rbac_findings = [
            f for f in result["findings"] if f["category"] == "rbac"
        ]
        assert any(f["severity"] == "critical" for f in rbac_findings)

    def test_many_public_ips_finding(self):
        """Many public IPs → medium security finding."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 15,
            "total_vnets": 2,
            "total_nsgs": 2,
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        resources = [
            {
                "category": "resource",
                "resource_type": "microsoft.network/publicipaddresses",
                "resource_id": f"/sub/rg/pip-{i}",
                "name": f"pip-{i}",
                "properties": {},
            }
            for i in range(5)
        ]
        result = gap_analyzer.analyze(summary, resources)

        sec_findings = [
            f for f in result["findings"]
            if f["category"] == "security" and "public ip" in f["title"].lower()
        ]
        assert len(sec_findings) > 0

    def test_untagged_resources_finding(self):
        """Many untagged resources → low finding."""
        summary = {
            "total_resource_groups": 1,
            "total_resources": 6,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "total_role_assignments": 2,
        }
        resources = [
            {
                "category": "resource",
                "resource_type": "Microsoft.Compute/virtualMachines",
                "resource_id": f"/sub/rg/vm-{i}",
                "name": f"vm-{i}",
                "properties": {},
            }
            for i in range(5)
        ]
        result = gap_analyzer.analyze(summary, resources)

        naming_findings = [
            f for f in result["findings"]
            if f["category"] == "naming" and "tag" in f["title"].lower()
        ]
        assert len(naming_findings) > 0


# ---------------------------------------------------------------------------
# Brownfield Context Tests
# ---------------------------------------------------------------------------


class TestBrownfieldContext:
    """Tests for brownfield questionnaire context generation."""

    def test_brownfield_context_structure(self):
        """get_brownfield_context returns expected structure."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 5,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        ctx = gap_analyzer.get_brownfield_context(summary, [])

        assert "discovered_answers" in ctx
        assert "gap_summary" in ctx
        assert isinstance(ctx["discovered_answers"], dict)
        assert isinstance(ctx["gap_summary"], dict)
        assert "total" in ctx["gap_summary"]

    def test_brownfield_infers_network_topology(self):
        """VNet count drives network_topology inference."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 5,
            "total_vnets": 3,
            "total_nsgs": 2,
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        ctx = gap_analyzer.get_brownfield_context(summary, [])

        assert "network_topology" in ctx["discovered_answers"]
        ans = ctx["discovered_answers"]["network_topology"]
        assert ans["source"] == "discovered"
        assert ans["confidence"] in ("high", "medium", "low")

    def test_brownfield_infers_monitoring_with_log_analytics(self):
        """Log Analytics workspace → monitoring_strategy=azure_native."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 5,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        resources = [
            {
                "category": "resource",
                "resource_type": "microsoft.operationalinsights/workspaces",
                "resource_id": "/sub/rg/log-01",
                "name": "log-prod-001",
                "properties": {},
            },
        ]
        ctx = gap_analyzer.get_brownfield_context(summary, resources)

        assert "monitoring_strategy" in ctx["discovered_answers"]
        assert ctx["discovered_answers"]["monitoring_strategy"]["value"] == "azure_native"
        assert ctx["discovered_answers"]["monitoring_strategy"]["confidence"] == "high"

    def test_brownfield_infers_security_level(self):
        """Many policies + Key Vault → enhanced security level."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 10,
            "total_vnets": 2,
            "total_nsgs": 2,
            "total_policies": 15,
            "total_role_assignments": 5,
        }
        resources = [
            {
                "category": "resource",
                "resource_type": "microsoft.keyvault/vaults",
                "resource_id": "/sub/rg/kv-01",
                "name": "kv-prod",
                "properties": {},
            },
        ]
        ctx = gap_analyzer.get_brownfield_context(summary, resources)

        assert "security_level" in ctx["discovered_answers"]
        assert ctx["discovered_answers"]["security_level"]["value"] == "enhanced"

    def test_brownfield_infers_naming_convention(self):
        """Resources with CAF prefixes → existing naming convention."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 6,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        resources = [
            {"category": "resource", "resource_type": "t", "resource_id": "r",
             "name": "vm-web-prod-001", "properties": {}},
            {"category": "resource", "resource_type": "t", "resource_id": "r",
             "name": "vnet-hub-prod", "properties": {}},
            {"category": "resource", "resource_type": "t", "resource_id": "r",
             "name": "kv-secrets-prod", "properties": {}},
            {"category": "resource", "resource_type": "t", "resource_id": "r",
             "name": "nsg-web-prod", "properties": {}},
        ]
        ctx = gap_analyzer.get_brownfield_context(summary, resources)

        assert "naming_convention" in ctx["discovered_answers"]
        assert ctx["discovered_answers"]["naming_convention"]["value"] == "existing"

    def test_brownfield_skips_errored_sections(self):
        """Errors in discovery prevent inference for those areas."""
        summary = {
            "total_resource_groups": 2,
            "total_resources": 5,
            "network_error": "Failed",
            "total_policies": 5,
            "total_role_assignments": 3,
        }
        ctx = gap_analyzer.get_brownfield_context(summary, [])

        # network_topology should NOT be inferred when network scan failed
        assert "network_topology" not in ctx["discovered_answers"]

    def test_brownfield_gap_summary_counts(self):
        """Gap summary includes severity counts."""
        summary = {
            "total_resource_groups": 0,
            "total_resources": 0,
            "total_vnets": 0,
            "total_nsgs": 0,
            "total_policies": 0,
            "total_role_assignments": 0,
        }
        ctx = gap_analyzer.get_brownfield_context(summary, [])

        assert ctx["gap_summary"]["total"] > 0
        assert "critical" in ctx["gap_summary"]
        assert "high" in ctx["gap_summary"]


# ---------------------------------------------------------------------------
# Questionnaire Brownfield Flow Tests
# ---------------------------------------------------------------------------


class TestQuestionnaireBrownfield:
    """Tests for brownfield branching in the questionnaire."""

    def test_existing_environment_question_exists(self):
        """existing_environment question is in the question list."""
        all_q = questionnaire_service.get_all_questions()
        ids = [q["id"] for q in all_q]
        assert "existing_environment" in ids

    def test_existing_environment_is_early(self):
        """existing_environment question appears early in the flow."""
        all_q = questionnaire_service.get_all_questions()
        orders = {q["id"]: q["order"] for q in all_q}
        assert orders["existing_environment"] < orders["azure_experience"]
        assert orders["existing_environment"] > orders["org_name"]

    def test_existing_environment_has_correct_options(self):
        """existing_environment has yes/no/_unsure options."""
        all_q = questionnaire_service.get_all_questions()
        q = next(q for q in all_q if q["id"] == "existing_environment")
        values = [o["value"] for o in q["options"]]
        assert "yes" in values
        assert "no" in values
        assert "_unsure" in values

    def test_greenfield_flow_unchanged(self):
        """Selecting 'no' for existing_environment keeps normal flow."""
        answers = {"org_name": "TestCorp", "org_size": "medium"}
        next_q = questionnaire_service.get_next_question(answers)
        assert next_q["id"] == "existing_environment"

        answers["existing_environment"] = "no"
        next_q = questionnaire_service.get_next_question(answers)
        assert next_q is not None
        assert next_q["id"] != "existing_environment"

    def test_brownfield_flow_with_context(self):
        """Brownfield context enriches questions with discovered answers."""
        answers = {
            "org_name": "TestCorp",
            "org_size": "medium",
            "existing_environment": "yes",
        }
        brownfield_ctx = {
            "discovered_answers": {
                "network_topology": {
                    "value": "hub_spoke",
                    "confidence": "medium",
                    "evidence": "Found 3 VNets",
                    "source": "discovered",
                },
            },
            "gap_summary": {"total": 5},
        }

        active = questionnaire_service.get_active_questions(
            answers, "medium", brownfield_ctx,
        )

        # Find the network_topology question
        net_q = next(
            (q for q in active if q["id"] == "network_topology"), None,
        )
        assert net_q is not None
        assert "discovered_answer" in net_q
        assert net_q["discovered_answer"]["value"] == "hub_spoke"

    def test_get_next_question_with_brownfield_context(self):
        """get_next_question works with brownfield context."""
        svc = QuestionnaireService()
        answers = {"org_name": "TestCorp"}
        next_q = svc.get_next_question(answers, brownfield_context=None)
        assert next_q is not None

    def test_progress_greenfield(self):
        """Progress calculation works for greenfield flow."""
        svc = QuestionnaireService()
        answers = {"org_name": "TestCorp", "org_size": "medium"}
        progress = svc.get_progress(answers)
        assert progress["answered"] == 2
        assert progress["total"] > 0
        assert progress["percent_complete"] > 0

    def test_progress_brownfield(self):
        """Progress calculation works for brownfield flow."""
        svc = QuestionnaireService()
        answers = {
            "org_name": "TestCorp",
            "org_size": "medium",
            "existing_environment": "yes",
        }
        brownfield_ctx = {
            "discovered_answers": {
                "network_topology": {
                    "value": "hub_spoke",
                    "confidence": "medium",
                    "evidence": "test",
                    "source": "discovered",
                },
            },
        }
        progress = svc.get_progress(answers, "medium", brownfield_ctx)
        assert progress["answered"] == 3
        assert progress["total"] > 0

    def test_validate_existing_environment_answer(self):
        """existing_environment accepts valid answers."""
        svc = QuestionnaireService()
        assert svc.validate_answer("existing_environment", "yes")
        assert svc.validate_answer("existing_environment", "no")
        assert svc.validate_answer("existing_environment", "_unsure")
        assert not svc.validate_answer("existing_environment", "maybe")


# ---------------------------------------------------------------------------
# Gap Analysis Schema Tests
# ---------------------------------------------------------------------------


class TestGapAnalysisSchemas:
    """Tests for gap analysis Pydantic schemas."""

    def test_gap_finding_model(self):
        """GapFinding schema validates correctly."""
        from app.schemas.gap_analysis import GapFinding

        finding = GapFinding(
            id="test-1",
            category="policy",
            severity="critical",
            title="No policies",
            description="Description",
            remediation="Fix it",
        )
        assert finding.id == "test-1"
        assert finding.can_auto_remediate is False

    def test_gap_analysis_response_model(self):
        """GapAnalysisResponse schema validates correctly."""
        from app.schemas.gap_analysis import GapAnalysisResponse

        resp = GapAnalysisResponse(
            scan_id="scan-1",
            total_findings=3,
            critical_count=1,
            high_count=1,
            medium_count=1,
            findings=[],
            areas_checked=["policy", "rbac"],
        )
        assert resp.scan_id == "scan-1"
        assert resp.total_findings == 3

    def test_brownfield_context_model(self):
        """BrownfieldContext schema validates correctly."""
        from app.schemas.gap_analysis import BrownfieldContext

        ctx = BrownfieldContext(
            scan_id="scan-1",
            discovered_answers={},
            gap_summary={"total": 5, "critical": 1},
        )
        assert ctx.scan_id == "scan-1"

    def test_discovered_answer_model(self):
        """DiscoveredAnswer schema validates correctly."""
        from app.schemas.gap_analysis import DiscoveredAnswer

        ans = DiscoveredAnswer(
            value="hub_spoke",
            confidence="high",
            evidence="3 VNets found",
        )
        assert ans.source == "discovered"

    def test_gap_severity_enum(self):
        """GapSeverity enum has expected values."""
        from app.schemas.gap_analysis import GapSeverity

        assert GapSeverity.critical == "critical"
        assert GapSeverity.high == "high"
        assert GapSeverity.medium == "medium"
        assert GapSeverity.low == "low"

    def test_gap_category_enum(self):
        """GapCategory enum has expected values."""
        from app.schemas.gap_analysis import GapCategory

        assert len(GapCategory) == 7
        assert GapCategory.management_groups == "management_groups"
        assert GapCategory.policy == "policy"

    def test_gap_analysis_request_default(self):
        """GapAnalysisRequest defaults use_ai to False."""
        from app.schemas.gap_analysis import GapAnalysisRequest

        req = GapAnalysisRequest()
        assert req.use_ai is False


# ---------------------------------------------------------------------------
# Route Tests
# ---------------------------------------------------------------------------


def _mock_completed_scan(scan_id="scan-123"):
    """Return a mock completed scan dict for route tests."""
    return {
        "id": scan_id,
        "project_id": "test-project",
        "subscription_id": "sub-1",
        "tenant_id": "dev-tenant",
        "status": "completed",
        "results": {
            "total_resource_groups": 2,
            "total_resources": 10,
            "total_vnets": 1,
            "total_nsgs": 1,
            "total_policies": 0,
            "total_role_assignments": 2,
        },
    }


def _mock_resources():
    """Return mock discovered resources for route tests."""
    return [
        {
            "category": "resource",
            "resource_type": "Microsoft.Compute/virtualMachines",
            "resource_id": "/sub/rg/vm-1",
            "name": "vm-1",
            "properties": {},
        },
        {
            "category": "resource_group",
            "resource_type": "resource_group",
            "resource_id": "/sub/rg-prod",
            "name": "rg-prod",
            "properties": {},
        },
    ]


class TestGapAnalysisRoutes:
    """Tests for the gap analysis API endpoints."""

    @pytest.mark.asyncio
    async def test_analyze_endpoint_returns_200(self):
        """POST /api/discovery/scan/{id}/analyze returns analysis."""
        from unittest.mock import AsyncMock, patch

        scan_id = "scan-analyze-200"
        with (
            patch.object(
                discovery_service, "get_scan",
                new_callable=AsyncMock,
                return_value=_mock_completed_scan(scan_id),
            ),
            patch.object(
                discovery_service, "get_scan_resources",
                new_callable=AsyncMock,
                return_value=_mock_resources(),
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test",
            ) as client:
                resp = await client.post(
                    f"/api/discovery/scan/{scan_id}/analyze",
                    json={"use_ai": False},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert "findings" in data
                assert "total_findings" in data
                assert "areas_checked" in data

    @pytest.mark.asyncio
    async def test_analyze_endpoint_not_found(self):
        """POST /api/discovery/scan/{bad_id}/analyze returns 404."""
        from unittest.mock import AsyncMock, patch

        with patch.object(
            discovery_service, "get_scan",
            new_callable=AsyncMock, return_value=None,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test",
            ) as client:
                resp = await client.post(
                    "/api/discovery/scan/nonexistent/analyze",
                    json={},
                )
                assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_brownfield_context_endpoint(self):
        """GET /api/discovery/scan/{id}/brownfield-context returns context."""
        from unittest.mock import AsyncMock, patch

        scan_id = "scan-bf-ctx"
        with (
            patch.object(
                discovery_service, "get_scan",
                new_callable=AsyncMock,
                return_value=_mock_completed_scan(scan_id),
            ),
            patch.object(
                discovery_service, "get_scan_resources",
                new_callable=AsyncMock,
                return_value=_mock_resources(),
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test",
            ) as client:
                resp = await client.get(
                    f"/api/discovery/scan/{scan_id}/brownfield-context",
                )
                assert resp.status_code == 200
                data = resp.json()
                assert "discovered_answers" in data
                assert "gap_summary" in data
                assert data["scan_id"] == scan_id

    @pytest.mark.asyncio
    async def test_brownfield_context_not_found(self):
        """GET /api/discovery/scan/{bad}/brownfield-context returns 404."""
        from unittest.mock import AsyncMock, patch

        with patch.object(
            discovery_service, "get_scan",
            new_callable=AsyncMock, return_value=None,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test",
            ) as client:
                resp = await client.get(
                    "/api/discovery/scan/bad-id/brownfield-context",
                )
                assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_analyze_findings_have_valid_categories(self):
        """Gap findings from analyze endpoint have valid categories."""
        from unittest.mock import AsyncMock, patch

        scan_id = "scan-cats"
        with (
            patch.object(
                discovery_service, "get_scan",
                new_callable=AsyncMock,
                return_value=_mock_completed_scan(scan_id),
            ),
            patch.object(
                discovery_service, "get_scan_resources",
                new_callable=AsyncMock,
                return_value=_mock_resources(),
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test",
            ) as client:
                resp = await client.post(
                    f"/api/discovery/scan/{scan_id}/analyze",
                    json={},
                )
                assert resp.status_code == 200
                data = resp.json()
                valid_cats = {
                    "management_groups", "policy", "rbac",
                    "networking", "monitoring", "security", "naming",
                }
                for finding in data["findings"]:
                    assert finding["category"] in valid_cats
                    assert finding["severity"] in (
                        "critical", "high", "medium", "low",
                    )

    @pytest.mark.asyncio
    async def test_analyze_counts_match_findings(self):
        """Severity counts match actual finding counts."""
        from unittest.mock import AsyncMock, patch

        scan_id = "scan-counts"
        with (
            patch.object(
                discovery_service, "get_scan",
                new_callable=AsyncMock,
                return_value=_mock_completed_scan(scan_id),
            ),
            patch.object(
                discovery_service, "get_scan_resources",
                new_callable=AsyncMock,
                return_value=_mock_resources(),
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test",
            ) as client:
                resp = await client.post(
                    f"/api/discovery/scan/{scan_id}/analyze",
                    json={},
                )
                assert resp.status_code == 200
                data = resp.json()

                actual_critical = sum(
                    1 for f in data["findings"]
                    if f["severity"] == "critical"
                )
                actual_high = sum(
                    1 for f in data["findings"]
                    if f["severity"] == "high"
                )
                assert data["critical_count"] == actual_critical
                assert data["high_count"] == actual_high
                assert data["total_findings"] == len(data["findings"])
