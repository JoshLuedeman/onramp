"""AI Evaluation Engine.

Runs golden tests against AI outputs and scores them on structural
correctness, Azure validity, completeness, and security posture.

Works entirely with mock AI responses in dev mode.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import ValidationError as PydanticValidationError

from app.schemas.ai_eval import (
    EvaluationReport,
    FullEvaluationReport,
    GoldenTest,
    IndividualResult,
    OutputScore,
    RegressionItem,
    RegressionResult,
)
from app.schemas.ai_output_models import (
    ArchitectureOutput,
    ComplianceGapOutput,
    PolicyDefinitionOutput,
    SecurityFindingOutput,
    SKURecommendationOutput,
)
from app.services.ai_eval.golden_datasets import ALL_GOLDEN_TESTS
from app.services.azure_reference import AzureReferenceData

logger = logging.getLogger(__name__)

# Regression threshold — a drop of more than this many points flags a regression
_REGRESSION_THRESHOLD = 5.0


def _clamp(value: float) -> float:
    """Clamp *value* to [0, 100]."""
    return max(0.0, min(100.0, value))


# ---------------------------------------------------------------------------
# Mock output generators (dev mode)
# ---------------------------------------------------------------------------

def _mock_architecture(input_data: dict) -> dict:
    """Return a structurally valid architecture output for testing."""
    org_size = input_data.get("organization_size", "medium")
    region = input_data.get("primary_region", "eastus")
    budget = input_data.get("budget_usd", 10000)
    frameworks = input_data.get("compliance_frameworks", [])

    subs = [
        {
            "name": "prod-sub",
            "purpose": "Production workloads",
            "management_group": "Production",
            "budget_usd": int(budget * 0.7),
        },
        {
            "name": "dev-sub",
            "purpose": "Development and testing",
            "management_group": "NonProduction",
            "budget_usd": int(budget * 0.3),
        },
    ]
    if org_size in ("large", "enterprise"):
        subs.append({
            "name": "shared-services-sub",
            "purpose": "Shared services and connectivity",
            "management_group": "Platform",
            "budget_usd": int(budget * 0.1),
        })

    return {
        "organization_size": org_size,
        "management_groups": {
            "Tenant Root Group": {
                "display_name": "Tenant Root Group",
                "children": {
                    "Platform": {
                        "display_name": "Platform",
                        "children": {},
                    },
                    "Production": {
                        "display_name": "Production",
                        "children": {},
                    },
                    "NonProduction": {
                        "display_name": "NonProduction",
                        "children": {},
                    },
                },
            },
        },
        "subscriptions": subs,
        "network_topology": {
            "type": "hub-spoke",
            "primary_region": region,
        },
        "identity": {
            "provider": "Entra ID",
            "rbac_model": "RBAC",
            "pim_enabled": org_size in ("large", "enterprise"),
            "conditional_access": True,
            "mfa_policy": "required",
        },
        "security": {
            "defender_for_cloud": True,
            "defender_plans": ["VirtualMachines", "SqlServers", "Storage"],
            "sentinel": org_size in ("large", "enterprise"),
            "ddos_protection": org_size == "enterprise",
            "azure_firewall": org_size in ("large", "enterprise"),
            "waf": True,
            "key_vault_per_subscription": True,
        },
        "governance": {
            "policies": [
                {
                    "name": "require-tags",
                    "scope": "management-group",
                    "effect": "Deny",
                    "description": "Require mandatory tags",
                },
            ],
            "tagging_strategy": {
                "mandatory_tags": ["Environment", "CostCenter", "Owner"],
                "optional_tags": ["Project"],
            },
            "naming_convention": "{resource-type}-{workload}-{env}-{region}",
            "cost_management": {
                "budgets_enabled": True,
                "alerts_enabled": True,
                "optimization_recommendations": True,
            },
        },
        "management": {
            "log_analytics": {"enabled": True, "retention_days": 90},
            "monitoring": {"enabled": True},
            "backup": {"enabled": True},
            "update_management": True,
        },
        "compliance_frameworks": [
            {"name": fw, "controls_applied": 10, "coverage_percent": 80}
            for fw in frameworks
        ],
        "platform_automation": {
            "iac_tool": "Bicep",
            "cicd_platform": "GitHub Actions",
            "repo_structure": "mono-repo",
        },
        "recommendations": [
            "Enable Microsoft Defender for Cloud",
            "Implement Azure Policy for governance",
        ],
        "estimated_monthly_cost_usd": budget,
    }


def _mock_policy(input_data: dict) -> dict:
    """Return a structurally valid policy output for testing."""
    desc = input_data.get("description", "Custom policy")
    return {
        "name": "custom-policy-01",
        "display_name": f"Policy: {desc[:50]}",
        "description": desc,
        "mode": "All",
        "policy_rule": {
            "if": {
                "allOf": [
                    {"field": "type", "equals": "Microsoft.Storage/storageAccounts"},
                ]
            },
            "then": {"effect": "Deny"},
        },
        "parameters": {
            "allowedLocations": {
                "type": "Array",
                "metadata": {"description": "Allowed Azure regions"},
            }
        },
    }


def _mock_sizing(input_data: dict) -> dict:
    """Return a structurally valid SKU recommendation for testing."""
    workload = input_data.get("workload", "web-application")
    cpu = input_data.get("cpu_avg_percent", 50)
    gpu = input_data.get("gpu_required", False)

    # Simple heuristic to pick realistic SKU families
    if gpu:
        sku = "Standard_NC6s_v3"
        cost = 1200
    elif cpu >= 90:
        sku = "Standard_Fv2"
        cost = 300
    elif cpu >= 60:
        sku = "Standard_E4s_v5"
        cost = 250
    elif cpu >= 30:
        sku = "Standard_D4s_v5"
        cost = 180
    else:
        sku = "Standard_B2ms"
        cost = 60

    return {
        "workload": workload,
        "recommended_sku": sku,
        "reasoning": f"Selected {sku} based on {cpu}% CPU and workload profile '{workload}'",
        "monthly_cost_estimate": cost,
    }


def _mock_security(input_data: dict) -> dict:
    """Return a structurally valid security finding for testing."""
    arch = input_data.get("architecture", {})
    resources = arch.get("resources", [])
    security_cfg = arch.get("security", {})

    # Generate a finding based on the first resource or security config
    if resources:
        resource = resources[0]
        return {
            "severity": "high",
            "category": "data-protection",
            "resource": resource.get("name", "unknown-resource"),
            "finding": f"Resource '{resource.get('name', 'unknown')}' has a security misconfiguration",
            "remediation": "Review and remediate the resource configuration",
        }

    if security_cfg and not security_cfg.get("defender_for_cloud", True):
        return {
            "severity": "high",
            "category": "security-monitoring",
            "resource": "subscription",
            "finding": "Microsoft Defender for Cloud is not enabled",
            "remediation": "Enable Microsoft Defender for Cloud with recommended plans",
        }

    return {
        "severity": "medium",
        "category": "general",
        "resource": "architecture",
        "finding": "General security review recommended",
        "remediation": "Perform a thorough security review",
    }


def _mock_regulatory(input_data: dict) -> dict:
    """Return a structurally valid compliance gap for testing."""
    industry = input_data.get("industry", "general")
    geography = input_data.get("geography", "global")

    framework_map = {
        "healthcare": "HIPAA",
        "financial-services": "PCI-DSS",
        "banking": "ISO27001",
        "government": "FedRAMP",
        "education": "ISO27001",
        "retail": "PCI-DSS",
    }
    framework = framework_map.get(industry, "ISO27001")

    return {
        "framework": framework,
        "control_id": f"{framework}-001",
        "status": "partial",
        "gap_description": (
            f"Partial compliance with {framework} for "
            f"{industry} in {geography}"
        ),
        "remediation": f"Implement remaining {framework} controls",
    }


_MOCK_GENERATORS: dict[str, callable] = {
    "architecture": _mock_architecture,
    "policy": _mock_policy,
    "sizing": _mock_sizing,
    "security": _mock_security,
    "regulatory": _mock_regulatory,
}


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

_FEATURE_MODELS = {
    "architecture": ArchitectureOutput,
    "policy": PolicyDefinitionOutput,
    "sizing": SKURecommendationOutput,
    "security": SecurityFindingOutput,
    "regulatory": ComplianceGapOutput,
}


def _score_structural(feature: str, output: dict) -> float:
    """Score structural correctness via Pydantic validation (0-100)."""
    model_cls = _FEATURE_MODELS.get(feature)
    if model_cls is None:
        return 0.0
    try:
        model_cls.model_validate(output)
        return 100.0
    except PydanticValidationError as exc:
        # Deduct points per error, floor at 0
        return _clamp(100.0 - len(exc.errors()) * 20.0)


def _score_azure_validity(feature: str, output: dict) -> float:
    """Score Azure validity — real regions, SKUs, resource types (0-100)."""
    ref = AzureReferenceData()
    checks = 0
    passed = 0

    if feature == "architecture":
        # Check region
        net = output.get("network_topology", {})
        if isinstance(net, dict):
            region = net.get("primary_region", "")
            if region:
                checks += 1
                if region.lower() in ref.VALID_REGIONS:
                    passed += 1

        # Check org size
        org = output.get("organization_size", "")
        if org:
            checks += 1
            if org.lower() in {"small", "medium", "large", "enterprise"}:
                passed += 1

    elif feature == "sizing":
        sku = output.get("recommended_sku", "")
        if sku:
            checks += 1
            if any(sku.startswith(prefix) for prefix in ref.VALID_VM_SKUS):
                passed += 1

    elif feature == "policy":
        mode = output.get("mode", "")
        if mode:
            checks += 1
            valid_modes = {"all", "indexed", "microsoft.kubernetes.data",
                           "microsoft.keyvault.data", "microsoft.network.data"}
            if mode.lower() in valid_modes:
                passed += 1

        rule = output.get("policy_rule", {})
        if isinstance(rule, dict):
            then = rule.get("then", {})
            if isinstance(then, dict):
                effect = then.get("effect", "")
                if effect:
                    checks += 1
                    valid_effects = {
                        "deny", "audit", "append", "modify",
                        "deployifnotexists", "auditifnotexists",
                        "disabled", "denyaction",
                    }
                    if effect.lower() in valid_effects:
                        passed += 1

    elif feature == "security":
        severity = output.get("severity", "")
        if severity:
            checks += 1
            if severity.lower() in {
                "critical", "high", "medium", "low", "informational",
            }:
                passed += 1

    elif feature == "regulatory":
        status = output.get("status", "")
        if status:
            checks += 1
            if status.lower() in {
                "compliant", "non_compliant", "partial", "not_assessed",
            }:
                passed += 1

    if checks == 0:
        return 100.0  # Nothing to check → assume valid
    return _clamp((passed / checks) * 100.0)


def _score_completeness(feature: str, output: dict, expected: dict) -> float:
    """Score completeness against expected patterns (0-100)."""
    checks = 0
    passed = 0

    for key, value in expected.items():
        if key.startswith("has_"):
            field_name = key[4:]  # strip "has_"
            checks += 1
            if feature == "architecture":
                mapping = {
                    "management_groups": "management_groups",
                    "subscriptions": "subscriptions",
                    "security_config": "security",
                    "identity": "identity",
                    "compliance_frameworks": "compliance_frameworks",
                }
                actual_field = mapping.get(field_name, field_name)
                val = output.get(actual_field)
                if val and val not in ({}, []):
                    passed += 1
            else:
                # Generic: check the field exists and is non-empty
                val = output.get(field_name)
                if val is not None and val != "" and val != {} and val != []:
                    passed += 1

        elif key == "min_subscriptions":
            checks += 1
            subs = output.get("subscriptions", [])
            if isinstance(subs, list) and len(subs) >= value:
                passed += 1

        elif key == "organization_size":
            checks += 1
            if output.get("organization_size", "").lower() == value.lower():
                passed += 1

        elif key == "valid_network_type":
            checks += 1
            net = output.get("network_topology", {})
            if isinstance(net, dict):
                net_type = net.get("type", "")
                if net_type in value:
                    passed += 1

        elif key == "valid_regions":
            checks += 1
            net = output.get("network_topology", {})
            if isinstance(net, dict):
                region = net.get("primary_region", "")
                if region in value:
                    passed += 1

        elif key == "valid_mode":
            checks += 1
            mode = output.get("mode", "")
            if mode in value:
                passed += 1

        elif key == "valid_effect":
            checks += 1
            rule = output.get("policy_rule", {})
            if isinstance(rule, dict):
                then = rule.get("then", {})
                if isinstance(then, dict):
                    effect = then.get("effect", "")
                    if effect in value:
                        passed += 1

        elif key == "valid_sku_families":
            checks += 1
            sku = output.get("recommended_sku", "")
            if sku and any(sku.startswith(prefix) for prefix in value):
                passed += 1

        elif key == "valid_severities":
            checks += 1
            severity = output.get("severity", "")
            if severity.lower() in [v.lower() for v in value]:
                passed += 1

        elif key == "valid_statuses":
            checks += 1
            status = output.get("status", "")
            if status.lower() in [v.lower() for v in value]:
                passed += 1

        elif key == "expected_frameworks":
            checks += 1
            framework = output.get("framework", "")
            if framework in value:
                passed += 1

    if checks == 0:
        return 100.0
    return _clamp((passed / checks) * 100.0)


def _score_security_posture(feature: str, output: dict) -> float:
    """Score security posture — no insecure defaults (0-100)."""
    if feature == "architecture":
        score = 100.0
        security = output.get("security", {})
        if isinstance(security, dict):
            if not security.get("defender_for_cloud", False):
                score -= 20.0
            if not security.get("key_vault_per_subscription", False):
                score -= 15.0
            if not security.get("waf", False):
                score -= 10.0
        identity = output.get("identity", {})
        if isinstance(identity, dict):
            if not identity.get("conditional_access", False):
                score -= 15.0
            mfa = identity.get("mfa_policy", "")
            if mfa and mfa.lower() != "required":
                score -= 10.0
        return _clamp(score)

    elif feature == "security":
        score = 100.0
        severity = output.get("severity", "")
        if not severity:
            score -= 30.0
        remediation = output.get("remediation", "")
        if not remediation:
            score -= 30.0
        return _clamp(score)

    elif feature == "policy":
        score = 100.0
        rule = output.get("policy_rule", {})
        if not rule:
            score -= 50.0
        return _clamp(score)

    # For sizing and regulatory, security posture is less relevant
    return 100.0


# ---------------------------------------------------------------------------
# AIEvaluator
# ---------------------------------------------------------------------------


class AIEvaluator:
    """Runs golden tests and scores AI outputs.

    Singleton pattern — use the module-level ``ai_evaluator`` instance.
    """

    _instance: AIEvaluator | None = None

    def __new__(cls) -> AIEvaluator:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._latest_report: FullEvaluationReport | None = None
        return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_mock_output(self, feature: str, input_data: dict) -> dict:
        """Generate a mock AI output for the given feature and input."""
        generator = _MOCK_GENERATORS.get(feature)
        if generator is None:
            logger.warning("No mock generator for feature '%s'", feature)
            return {}
        return generator(input_data)

    def score_output(
        self, feature: str, output: dict, expected: dict,
    ) -> OutputScore:
        """Score an AI output against expected patterns.

        Returns an ``OutputScore`` with 0-100 scores for each dimension.
        """
        structural = _score_structural(feature, output)
        azure_validity = _score_azure_validity(feature, output)
        completeness = _score_completeness(feature, output, expected)
        security = _score_security_posture(feature, output)
        overall = (structural + azure_validity + completeness + security) / 4.0

        return OutputScore(
            structural=round(structural, 2),
            azure_validity=round(azure_validity, 2),
            completeness=round(completeness, 2),
            security=round(security, 2),
            overall=round(overall, 2),
        )

    def evaluate_feature(
        self, feature: str, golden_tests: list[GoldenTest],
    ) -> EvaluationReport:
        """Run all golden tests for a single feature and return a report."""
        results: list[IndividualResult] = []

        for test in golden_tests:
            errors: list[str] = []
            try:
                output = self.generate_mock_output(feature, test.input_data)
                score = self.score_output(feature, output, test.expected_patterns)
                passed = score.overall >= 60.0
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Error evaluating golden test '%s'", test.name,
                )
                errors.append(str(exc))
                score = OutputScore()
                passed = False

            results.append(
                IndividualResult(
                    test_name=test.name,
                    passed=passed,
                    score=score,
                    errors=errors,
                )
            )

        # Aggregate
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        if results:
            avg = OutputScore(
                structural=round(
                    sum(r.score.structural for r in results) / len(results), 2,
                ),
                azure_validity=round(
                    sum(r.score.azure_validity for r in results) / len(results), 2,
                ),
                completeness=round(
                    sum(r.score.completeness for r in results) / len(results), 2,
                ),
                security=round(
                    sum(r.score.security for r in results) / len(results), 2,
                ),
                overall=round(
                    sum(r.score.overall for r in results) / len(results), 2,
                ),
            )
        else:
            avg = OutputScore()

        return EvaluationReport(
            feature=feature,
            test_count=len(results),
            passed=passed_count,
            failed=failed_count,
            avg_score=avg,
            individual_results=results,
        )

    def run_full_evaluation(self) -> FullEvaluationReport:
        """Run all golden tests across all features.

        Returns a ``FullEvaluationReport`` and caches it as the latest.
        """
        features: dict[str, EvaluationReport] = {}
        for feature, tests in ALL_GOLDEN_TESTS.items():
            features[feature] = self.evaluate_feature(feature, tests)

        overall = 0.0
        if features:
            overall = round(
                sum(r.avg_score.overall for r in features.values()) / len(features),
                2,
            )

        report = FullEvaluationReport(
            features=features,
            overall_score=overall,
            timestamp=datetime.now(timezone.utc),
        )
        self._latest_report = report
        return report

    @property
    def latest_report(self) -> FullEvaluationReport | None:
        """Return the most recent full evaluation report, if any."""
        return self._latest_report

    def check_regression(
        self,
        current: FullEvaluationReport,
        baseline: FullEvaluationReport,
    ) -> RegressionResult:
        """Compare *current* scores against *baseline* and flag regressions.

        A regression is flagged when the current score drops by more than
        ``_REGRESSION_THRESHOLD`` points for any metric/feature pair.
        """
        regressions: list[RegressionItem] = []

        for feature, curr_report in current.features.items():
            base_report = baseline.features.get(feature)
            if base_report is None:
                continue

            metrics = [
                "structural", "azure_validity", "completeness",
                "security", "overall",
            ]
            for metric in metrics:
                curr_val = getattr(curr_report.avg_score, metric, 0.0)
                base_val = getattr(base_report.avg_score, metric, 0.0)
                delta = curr_val - base_val
                if delta < -_REGRESSION_THRESHOLD:
                    regressions.append(
                        RegressionItem(
                            feature=feature,
                            metric=metric,
                            baseline=base_val,
                            current=curr_val,
                            delta=round(delta, 2),
                        )
                    )

        return RegressionResult(
            has_regression=len(regressions) > 0,
            regressions=regressions,
        )

    def reset(self) -> None:
        """Clear cached state (useful for testing)."""
        self._latest_report = None


# Module-level singleton
ai_evaluator = AIEvaluator()
