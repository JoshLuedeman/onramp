"""Tests for the security posture advisor."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.security import (
    RemediationStep,
    SecurityAnalysisResult,
    SecurityAnalyzeRequest,
    SecurityCheck,
    SecurityFinding,
    Severity,
)
from app.services.security_analyzer import SecurityAnalyzer, security_analyzer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def analyzer() -> SecurityAnalyzer:
    """Return a fresh SecurityAnalyzer instance (singleton is reused)."""
    return SecurityAnalyzer()


@pytest.fixture()
def minimal_arch() -> dict:
    """Architecture with almost nothing configured — triggers most rules."""
    return {
        "organization_size": "medium",
        "subscriptions": [
            {"name": "sub-web", "purpose": "Web application hosting", "management_group": "landing-zones"},
            {"name": "sub-data", "purpose": "SQL database and storage", "management_group": "landing-zones"},
        ],
        "network_topology": {
            "type": "hub-spoke",
            "primary_region": "eastus2",
            "hub": {"subnets": [{"name": "GatewaySubnet"}]},
            "spokes": [
                {"name": "spoke-web", "subnets": [{"name": "app-subnet"}]},
            ],
        },
        "identity": {},
        "security": {},
        "governance": {"policies": []},
        "management": {},
    }


@pytest.fixture()
def secure_arch() -> dict:
    """Architecture that passes most rule checks."""
    return {
        "organization_size": "enterprise",
        "subscriptions": [
            {"name": "sub-platform", "purpose": "Platform services", "management_group": "platform"},
        ],
        "network_topology": {
            "type": "hub-spoke",
            "primary_region": "eastus2",
            "hub": {
                "subnets": [
                    {"name": "AzureFirewallSubnet", "nsg": True},
                    {"name": "GatewaySubnet", "nsg": True},
                ],
            },
            "spokes": [],
            "private_endpoints": True,
        },
        "identity": {
            "rbac_model": "least-privilege",
            "pim_enabled": True,
            "conditional_access": True,
        },
        "security": {
            "defender_for_cloud": True,
            "defender_plans": ["Servers", "AppService", "SqlServers", "Storage", "KeyVaults"],
            "ddos_protection": True,
            "waf": True,
            "key_vault_per_subscription": True,
            "encryption_at_rest": True,
            "sql_tde": True,
        },
        "governance": {
            "policies": [
                {"name": "enforce-encryption", "description": "Enforce encryption at rest"},
                {"name": "least-privilege", "description": "Enforce least privilege RBAC"},
            ],
        },
        "management": {
            "log_analytics": {"workspace": "central-law"},
            "monitoring": {"enabled": True},
            "diagnostic_settings": True,
        },
    }


@pytest.fixture()
def client() -> TestClient:
    """TestClient for the FastAPI app."""
    from app.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchemas:
    """Tests for the security Pydantic schemas."""

    def test_severity_enum_values(self):
        assert Severity.critical.value == "critical"
        assert Severity.high.value == "high"
        assert Severity.medium.value == "medium"
        assert Severity.low.value == "low"

    def test_security_finding_creation(self):
        f = SecurityFinding(
            id="SEC-001",
            severity=Severity.high,
            category="networking",
            resource="subnet",
            finding="Missing NSG",
        )
        assert f.id == "SEC-001"
        assert f.severity == Severity.high
        assert f.auto_fixable is False
        assert f.remediation == ""

    def test_security_finding_with_remediation(self):
        f = SecurityFinding(
            id="SEC-002",
            severity=Severity.critical,
            category="identity",
            resource="rbac",
            finding="Overly permissive",
            remediation="Apply least privilege",
            auto_fixable=True,
        )
        assert f.remediation == "Apply least privilege"
        assert f.auto_fixable is True

    def test_security_analysis_result(self):
        r = SecurityAnalysisResult(
            score=85,
            findings=[],
            summary="All clear",
        )
        assert r.score == 85
        assert r.findings == []
        assert isinstance(r.analyzed_at, datetime)

    def test_security_analysis_result_score_bounds(self):
        r = SecurityAnalysisResult(score=0, summary="Min")
        assert r.score == 0
        r2 = SecurityAnalysisResult(score=100, summary="Max")
        assert r2.score == 100

    def test_security_analyze_request_defaults(self):
        req = SecurityAnalyzeRequest(architecture={"foo": "bar"})
        assert req.use_ai is False

    def test_security_analyze_request_with_ai(self):
        req = SecurityAnalyzeRequest(architecture={"foo": "bar"}, use_ai=True)
        assert req.use_ai is True

    def test_remediation_step(self):
        step = RemediationStep(
            finding_id="SEC-001",
            description="Fix it",
            architecture_changes={"security.waf": True},
        )
        assert step.finding_id == "SEC-001"
        assert step.architecture_changes["security.waf"] is True

    def test_remediation_step_defaults(self):
        step = RemediationStep(finding_id="SEC-002", description="Fix")
        assert step.architecture_changes == {}

    def test_security_check(self):
        c = SecurityCheck(
            id="nsg-check",
            name="Missing NSG Rules",
            description="Checks subnets",
            category="networking",
            severity=Severity.high,
        )
        assert c.id == "nsg-check"


# ---------------------------------------------------------------------------
# Rule-based check tests (one per rule)
# ---------------------------------------------------------------------------


class TestRuleChecks:
    """Each rule-based check is tested individually."""

    def test_rule1_missing_nsg_detected(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 1: subnets without NSGs are flagged."""
        result = analyzer.analyze(minimal_arch)
        nsg = [f for f in result.findings if "NSG" in f.finding or "nsg" in f.finding.lower()]
        assert len(nsg) >= 1
        assert nsg[0].severity == Severity.high
        assert nsg[0].category == "networking"

    def test_rule1_nsg_present_no_finding(self, analyzer: SecurityAnalyzer):
        """No NSG finding when all subnets have NSGs."""
        arch = {
            "network_topology": {
                "hub": {"subnets": [{"name": "sub1", "nsg": True}]},
                "spokes": [{"name": "spoke1", "subnets": [{"name": "sub2", "nsg": True}]}],
            },
            "subscriptions": [],
            "identity": {},
            "security": {"defender_for_cloud": True, "ddos_protection": True, "key_vault_per_subscription": True},
            "governance": {"policies": []},
            "management": {"log_analytics": True},
        }
        result = analyzer.analyze(arch)
        nsg = [f for f in result.findings if "NSG" in f.finding]
        assert len(nsg) == 0

    def test_rule2_public_endpoints_without_waf(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 2: public endpoints without WAF are flagged."""
        result = analyzer.analyze(minimal_arch)
        waf = [f for f in result.findings if "WAF" in f.finding or "Front Door" in f.finding]
        assert len(waf) >= 1
        assert waf[0].severity == Severity.high

    def test_rule2_waf_present_no_finding(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """No WAF finding when WAF is enabled."""
        minimal_arch["security"]["waf"] = True
        result = analyzer.analyze(minimal_arch)
        waf = [f for f in result.findings if "WAF" in f.finding]
        assert len(waf) == 0

    def test_rule3_storage_without_encryption(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 3: storage without encryption flagged."""
        result = analyzer.analyze(minimal_arch)
        enc = [f for f in result.findings if "encryption" in f.finding.lower() or "encrypt" in f.finding.lower()]
        assert len(enc) >= 1

    def test_rule3_encryption_present_no_finding(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """No encryption finding when encryption_at_rest is set."""
        minimal_arch["security"]["encryption_at_rest"] = True
        result = analyzer.analyze(minimal_arch)
        enc = [f for f in result.findings if "encryption at rest" in f.finding.lower()]
        assert len(enc) == 0

    def test_rule4_sql_without_tde(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 4: SQL databases without TDE are flagged."""
        result = analyzer.analyze(minimal_arch)
        tde = [f for f in result.findings if "TDE" in f.finding or "Transparent Data Encryption" in f.finding]
        assert len(tde) >= 1

    def test_rule4_tde_enabled_no_finding(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """No TDE finding when sql_tde is enabled."""
        minimal_arch["security"]["sql_tde"] = True
        result = analyzer.analyze(minimal_arch)
        tde = [f for f in result.findings if "TDE" in f.finding]
        assert len(tde) == 0

    def test_rule5_missing_defender(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 5: missing Defender for Cloud is flagged."""
        result = analyzer.analyze(minimal_arch)
        defender = [f for f in result.findings if "Defender" in f.finding]
        assert len(defender) >= 1
        assert defender[0].severity == Severity.critical

    def test_rule5_defender_enabled_no_finding(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """No Defender finding when defender_for_cloud is True."""
        minimal_arch["security"]["defender_for_cloud"] = True
        result = analyzer.analyze(minimal_arch)
        defender = [f for f in result.findings if "Defender" in f.finding]
        assert len(defender) == 0

    def test_rule6_overly_permissive_rbac(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 6: overly permissive RBAC is flagged."""
        result = analyzer.analyze(minimal_arch)
        rbac = [f for f in result.findings if "RBAC" in f.finding or "Owner" in f.finding]
        assert len(rbac) >= 1
        assert rbac[0].severity == Severity.critical

    def test_rule6_least_privilege_no_finding(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """No RBAC finding when least-privilege model is set."""
        minimal_arch["identity"]["rbac_model"] = "least-privilege"
        result = analyzer.analyze(minimal_arch)
        rbac = [f for f in result.findings if "RBAC" in f.finding]
        assert len(rbac) == 0

    def test_rule7_missing_ddos(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 7: missing DDoS protection is flagged."""
        result = analyzer.analyze(minimal_arch)
        ddos = [f for f in result.findings if "DDoS" in f.finding]
        assert len(ddos) >= 1
        assert ddos[0].severity == Severity.medium

    def test_rule7_ddos_enabled_no_finding(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """No DDoS finding when ddos_protection is True."""
        minimal_arch["security"]["ddos_protection"] = True
        result = analyzer.analyze(minimal_arch)
        ddos = [f for f in result.findings if "DDoS" in f.finding]
        assert len(ddos) == 0

    def test_rule8_no_private_endpoints(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 8: PaaS without private endpoints is flagged."""
        result = analyzer.analyze(minimal_arch)
        pep = [f for f in result.findings if "private endpoint" in f.finding.lower() or "Private Endpoint" in f.finding]
        assert len(pep) >= 1

    def test_rule8_private_endpoints_present(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """No private endpoint finding when private_endpoints is set."""
        minimal_arch["network_topology"]["private_endpoints"] = True
        result = analyzer.analyze(minimal_arch)
        pep = [f for f in result.findings if "private endpoint" in f.finding.lower()]
        assert len(pep) == 0

    def test_rule9_missing_diagnostics(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 9: missing diagnostic settings is flagged."""
        result = analyzer.analyze(minimal_arch)
        diag = [f for f in result.findings if "diagnostic" in f.finding.lower() or "Log Analytics" in f.finding]
        assert len(diag) >= 1
        assert diag[0].severity == Severity.medium

    def test_rule9_logging_present_no_finding(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """No diagnostic finding when log_analytics is configured."""
        minimal_arch["management"]["log_analytics"] = {"workspace": "law-1"}
        result = analyzer.analyze(minimal_arch)
        diag = [f for f in result.findings if "diagnostic" in f.finding.lower()]
        assert len(diag) == 0

    def test_rule10_missing_key_vault(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Rule 10: missing Key Vault is flagged."""
        result = analyzer.analyze(minimal_arch)
        kv = [f for f in result.findings if "Key Vault" in f.finding]
        assert len(kv) >= 1
        assert kv[0].severity == Severity.high

    def test_rule10_key_vault_present_no_finding(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """No Key Vault finding when key_vault_per_subscription is True."""
        minimal_arch["security"]["key_vault_per_subscription"] = True
        result = analyzer.analyze(minimal_arch)
        kv = [f for f in result.findings if "Key Vault" in f.finding]
        assert len(kv) == 0


# ---------------------------------------------------------------------------
# Score calculation tests
# ---------------------------------------------------------------------------


class TestScoreCalculation:
    """Tests for security score calculation."""

    def test_score_perfect_no_findings(self, analyzer: SecurityAnalyzer):
        assert analyzer.calculate_security_score([]) == 100

    def test_score_single_critical(self, analyzer: SecurityAnalyzer):
        findings = [
            SecurityFinding(id="f1", severity=Severity.critical, category="x", resource="y", finding="z"),
        ]
        assert analyzer.calculate_security_score(findings) == 75

    def test_score_single_high(self, analyzer: SecurityAnalyzer):
        findings = [
            SecurityFinding(id="f1", severity=Severity.high, category="x", resource="y", finding="z"),
        ]
        assert analyzer.calculate_security_score(findings) == 85

    def test_score_single_medium(self, analyzer: SecurityAnalyzer):
        findings = [
            SecurityFinding(id="f1", severity=Severity.medium, category="x", resource="y", finding="z"),
        ]
        assert analyzer.calculate_security_score(findings) == 92

    def test_score_single_low(self, analyzer: SecurityAnalyzer):
        findings = [
            SecurityFinding(id="f1", severity=Severity.low, category="x", resource="y", finding="z"),
        ]
        assert analyzer.calculate_security_score(findings) == 97

    def test_score_mixed_findings(self, analyzer: SecurityAnalyzer):
        findings = [
            SecurityFinding(id="f1", severity=Severity.critical, category="x", resource="y", finding="z"),
            SecurityFinding(id="f2", severity=Severity.high, category="x", resource="y", finding="z"),
            SecurityFinding(id="f3", severity=Severity.medium, category="x", resource="y", finding="z"),
            SecurityFinding(id="f4", severity=Severity.low, category="x", resource="y", finding="z"),
        ]
        # 100 - 25 - 15 - 8 - 3 = 49
        assert analyzer.calculate_security_score(findings) == 49

    def test_score_floor_at_zero(self, analyzer: SecurityAnalyzer):
        findings = [
            SecurityFinding(id=f"f{i}", severity=Severity.critical, category="x", resource="y", finding="z")
            for i in range(10)
        ]
        assert analyzer.calculate_security_score(findings) == 0

    def test_score_multiple_same_severity(self, analyzer: SecurityAnalyzer):
        findings = [
            SecurityFinding(id="f1", severity=Severity.high, category="x", resource="y", finding="z"),
            SecurityFinding(id="f2", severity=Severity.high, category="x", resource="y", finding="z"),
        ]
        assert analyzer.calculate_security_score(findings) == 70

    def test_secure_arch_high_score(self, analyzer: SecurityAnalyzer, secure_arch: dict):
        """A well-configured architecture should have a high score."""
        result = analyzer.analyze(secure_arch)
        assert result.score >= 80

    def test_minimal_arch_low_score(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """A poorly-configured architecture should have a low score."""
        result = analyzer.analyze(minimal_arch)
        assert result.score < 50


# ---------------------------------------------------------------------------
# Remediation tests
# ---------------------------------------------------------------------------


class TestRemediation:
    """Tests for remediation generation."""

    def test_remediation_for_networking_finding(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-001",
            severity=Severity.high,
            category="networking",
            resource="subnet",
            finding="Missing NSG",
        )
        step = analyzer.get_remediation(f)
        assert isinstance(step, RemediationStep)
        assert step.finding_id == "SEC-001"
        assert "network" in step.description.lower() or "security" in step.description.lower()
        assert len(step.architecture_changes) > 0

    def test_remediation_for_data_protection_finding(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-002",
            severity=Severity.high,
            category="data_protection",
            resource="storage",
            finding="No encryption",
        )
        step = analyzer.get_remediation(f)
        assert step.finding_id == "SEC-002"
        assert "data protection" in step.description.lower() or "encryption" in step.description.lower()

    def test_remediation_for_threat_protection_finding(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-003",
            severity=Severity.critical,
            category="threat_protection",
            resource="subscription",
            finding="No Defender",
        )
        step = analyzer.get_remediation(f)
        assert "defender_for_cloud" in str(step.architecture_changes).lower() or "threat" in step.description.lower()

    def test_remediation_for_identity_finding(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-004",
            severity=Severity.critical,
            category="identity",
            resource="rbac",
            finding="Overly permissive",
        )
        step = analyzer.get_remediation(f)
        assert "identity" in step.description.lower() or "access" in step.description.lower()

    def test_remediation_for_monitoring_finding(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-005",
            severity=Severity.medium,
            category="monitoring",
            resource="management",
            finding="No logging",
        )
        step = analyzer.get_remediation(f)
        assert "logging" in step.description.lower() or "monitoring" in step.description.lower()

    def test_remediation_for_unknown_category(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-006",
            severity=Severity.low,
            category="unknown_category",
            resource="something",
            finding="Some issue",
            remediation="Do something about it",
        )
        step = analyzer.get_remediation(f)
        assert step.finding_id == "SEC-006"
        # Falls back to finding.remediation
        assert step.description == "Do something about it"


# ---------------------------------------------------------------------------
# AI-enhanced analysis tests
# ---------------------------------------------------------------------------


class TestAIAnalysis:
    """Tests for AI-enhanced analysis."""

    def test_ai_analysis_adds_findings(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """AI analysis adds extra findings beyond rule-based checks."""
        result_no_ai = analyzer.analyze(minimal_arch, use_ai=False)
        result_ai = analyzer.analyze(minimal_arch, use_ai=True)
        assert len(result_ai.findings) > len(result_no_ai.findings)

    def test_ai_findings_have_sec_ai_prefix(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """AI-generated findings have SEC-AI prefix."""
        result = analyzer.analyze(minimal_arch, use_ai=True)
        ai_findings = [f for f in result.findings if f.id.startswith("SEC-AI-")]
        assert len(ai_findings) >= 1

    def test_ai_findings_not_auto_fixable(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """AI findings are not auto-fixable."""
        result = analyzer.analyze(minimal_arch, use_ai=True)
        ai_findings = [f for f in result.findings if f.id.startswith("SEC-AI-")]
        for f in ai_findings:
            assert f.auto_fixable is False

    def test_ai_findings_have_remediation(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """AI findings include remediation guidance."""
        result = analyzer.analyze(minimal_arch, use_ai=True)
        ai_findings = [f for f in result.findings if f.id.startswith("SEC-AI-")]
        for f in ai_findings:
            assert len(f.remediation) > 0


# ---------------------------------------------------------------------------
# Auto-fix tests
# ---------------------------------------------------------------------------


class TestAutoFix:
    """Tests for auto-fix capability."""

    def test_auto_fix_applies_changes(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-001",
            severity=Severity.critical,
            category="threat_protection",
            resource="subscription",
            finding="No Defender",
            auto_fixable=True,
        )
        arch = {"security": {}}
        fixed = analyzer.apply_auto_fix(f, arch)
        assert fixed["security"]["defender_for_cloud"] is True

    def test_auto_fix_skips_non_fixable(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-002",
            severity=Severity.critical,
            category="identity",
            resource="rbac",
            finding="Overly permissive",
            auto_fixable=False,
        )
        arch = {"identity": {}}
        fixed = analyzer.apply_auto_fix(f, arch)
        assert fixed == arch

    def test_auto_fix_networking(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-003",
            severity=Severity.high,
            category="networking",
            resource="subnet",
            finding="No WAF",
            auto_fixable=True,
        )
        arch = {"security": {}, "network_topology": {}}
        fixed = analyzer.apply_auto_fix(f, arch)
        assert fixed["security"]["waf"] is True

    def test_auto_fix_data_protection(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-004",
            severity=Severity.high,
            category="data_protection",
            resource="storage",
            finding="No encryption",
            auto_fixable=True,
        )
        arch = {"security": {}}
        fixed = analyzer.apply_auto_fix(f, arch)
        assert fixed["security"]["encryption_at_rest"] is True

    def test_auto_fix_monitoring(self, analyzer: SecurityAnalyzer):
        f = SecurityFinding(
            id="SEC-005",
            severity=Severity.medium,
            category="monitoring",
            resource="management",
            finding="No logging",
            auto_fixable=True,
        )
        arch = {"management": {}}
        fixed = analyzer.apply_auto_fix(f, arch)
        assert fixed["management"]["diagnostic_settings"] is True


# ---------------------------------------------------------------------------
# Available checks tests
# ---------------------------------------------------------------------------


class TestAvailableChecks:
    """Tests for the checks listing."""

    def test_get_available_checks_returns_list(self, analyzer: SecurityAnalyzer):
        checks = analyzer.get_available_checks()
        assert isinstance(checks, list)

    def test_at_least_10_checks(self, analyzer: SecurityAnalyzer):
        checks = analyzer.get_available_checks()
        assert len(checks) >= 10

    def test_checks_have_required_fields(self, analyzer: SecurityAnalyzer):
        checks = analyzer.get_available_checks()
        for c in checks:
            assert isinstance(c, SecurityCheck)
            assert c.id
            assert c.name
            assert c.description
            assert c.category
            assert c.severity in Severity


# ---------------------------------------------------------------------------
# Full analysis integration tests
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    """Integration-level tests for the analyze method."""

    def test_analyze_returns_result(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        result = analyzer.analyze(minimal_arch)
        assert isinstance(result, SecurityAnalysisResult)

    def test_analyze_has_findings(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        result = analyzer.analyze(minimal_arch)
        assert len(result.findings) > 0

    def test_analyze_score_matches_findings(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        result = analyzer.analyze(minimal_arch)
        recalculated = analyzer.calculate_security_score(result.findings)
        assert result.score == recalculated

    def test_analyze_summary_contains_count(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        result = analyzer.analyze(minimal_arch)
        assert "issue(s)" in result.summary

    def test_analyze_has_analyzed_at(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        result = analyzer.analyze(minimal_arch)
        assert result.analyzed_at is not None
        assert isinstance(result.analyzed_at, datetime)

    def test_analyze_empty_arch(self, analyzer: SecurityAnalyzer):
        """Empty architecture should not crash."""
        result = analyzer.analyze({})
        assert isinstance(result, SecurityAnalysisResult)

    def test_analyze_with_ai_flag(self, analyzer: SecurityAnalyzer, minimal_arch: dict):
        """Analysis with use_ai=True should include AI findings."""
        result = analyzer.analyze(minimal_arch, use_ai=True)
        assert len(result.findings) > 0
        ai_count = sum(1 for f in result.findings if f.id.startswith("SEC-AI-"))
        assert ai_count >= 1

    def test_singleton_instance(self):
        a = SecurityAnalyzer()
        b = SecurityAnalyzer()
        assert a is b

    def test_module_level_singleton(self):
        assert security_analyzer is not None
        assert isinstance(security_analyzer, SecurityAnalyzer)


# ---------------------------------------------------------------------------
# Route endpoint tests
# ---------------------------------------------------------------------------


class TestRoutes:
    """Tests for the security API routes."""

    def test_analyze_endpoint(self, client: TestClient):
        resp = client.post(
            "/api/security/analyze",
            json={
                "architecture": {
                    "subscriptions": [
                        {"name": "sub-1", "purpose": "web hosting", "management_group": "lz"},
                    ],
                    "network_topology": {"type": "hub-spoke", "hub": {}, "spokes": []},
                    "identity": {},
                    "security": {},
                    "governance": {"policies": []},
                    "management": {},
                },
                "use_ai": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "findings" in data
        assert "summary" in data
        assert "analyzed_at" in data

    def test_analyze_endpoint_with_ai(self, client: TestClient):
        resp = client.post(
            "/api/security/analyze",
            json={"architecture": {"foo": "bar"}, "use_ai": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "findings" in data

    def test_checks_endpoint(self, client: TestClient):
        resp = client.get("/api/security/checks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 10
        for check in data:
            assert "id" in check
            assert "name" in check
            assert "description" in check

    def test_fix_endpoint_not_found(self, client: TestClient):
        resp = client.post(
            "/api/security/fix",
            params={"finding_id": "nonexistent-id"},
            json={"architecture": {}},
        )
        assert resp.status_code == 404

    def test_analyze_returns_findings_for_insecure_arch(self, client: TestClient):
        resp = client.post(
            "/api/security/analyze",
            json={
                "architecture": {
                    "subscriptions": [
                        {"name": "sub-web", "purpose": "Web application", "management_group": "lz"},
                    ],
                    "network_topology": {
                        "type": "hub-spoke",
                        "hub": {"subnets": [{"name": "default"}]},
                        "spokes": [],
                    },
                    "identity": {},
                    "security": {},
                    "governance": {"policies": []},
                    "management": {},
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] < 100
        assert len(data["findings"]) > 0
