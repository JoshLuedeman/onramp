"""Tests for the AI evaluation framework.

Covers golden datasets, scoring engine, regression detection,
evaluator API, and route endpoints.  Targets 50+ tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.ai_eval import (
    EvalFeature,
    EvaluationReport,
    FullEvaluationReport,
    GoldenTest,
    IndividualResult,
    OutputScore,
    RegressionItem,
    RegressionResult,
)
from app.services.ai_eval.evaluator import (
    AIEvaluator,
    _clamp,
    _mock_architecture,
    _mock_policy,
    _mock_regulatory,
    _mock_security,
    _mock_sizing,
    _score_azure_validity,
    _score_completeness,
    _score_security_posture,
    _score_structural,
    ai_evaluator,
)
from app.services.ai_eval.golden_datasets import (
    ALL_GOLDEN_TESTS,
    ARCHITECTURE_GOLDEN_TESTS,
    POLICY_GOLDEN_TESTS,
    REGULATORY_GOLDEN_TESTS,
    SECURITY_GOLDEN_TESTS,
    SIZING_GOLDEN_TESTS,
)

client = TestClient(app)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture(autouse=True)
def _reset_evaluator():
    """Reset the evaluator singleton between tests."""
    ai_evaluator.reset()
    yield
    ai_evaluator.reset()


# ===================================================================
# 1. Golden Dataset completeness
# ===================================================================


class TestGoldenDatasetCompleteness:
    """Verify golden datasets are well-formed and cover all features."""

    def test_all_features_have_datasets(self):
        expected_features = {"architecture", "policy", "sizing", "security", "regulatory"}
        assert set(ALL_GOLDEN_TESTS.keys()) == expected_features

    def test_architecture_has_minimum_tests(self):
        assert len(ARCHITECTURE_GOLDEN_TESTS) >= 5

    def test_policy_has_minimum_tests(self):
        assert len(POLICY_GOLDEN_TESTS) >= 5

    def test_sizing_has_minimum_tests(self):
        assert len(SIZING_GOLDEN_TESTS) >= 5

    def test_security_has_minimum_tests(self):
        assert len(SECURITY_GOLDEN_TESTS) >= 5

    def test_regulatory_has_minimum_tests(self):
        assert len(REGULATORY_GOLDEN_TESTS) >= 5

    def test_all_golden_tests_are_golden_test_type(self):
        for feature, tests in ALL_GOLDEN_TESTS.items():
            for test in tests:
                assert isinstance(test, GoldenTest), (
                    f"{feature}/{test.name} is not a GoldenTest"
                )

    def test_all_golden_tests_have_names(self):
        for feature, tests in ALL_GOLDEN_TESTS.items():
            for test in tests:
                assert test.name, f"Test in {feature} has no name"

    def test_all_golden_tests_have_input_data(self):
        for feature, tests in ALL_GOLDEN_TESTS.items():
            for test in tests:
                assert test.input_data, f"{feature}/{test.name} has no input_data"

    def test_all_golden_tests_have_expected_patterns(self):
        for feature, tests in ALL_GOLDEN_TESTS.items():
            for test in tests:
                assert test.expected_patterns, (
                    f"{feature}/{test.name} has no expected_patterns"
                )

    def test_all_golden_tests_have_matching_feature(self):
        for feature, tests in ALL_GOLDEN_TESTS.items():
            for test in tests:
                assert test.feature == feature, (
                    f"{test.name}: feature '{test.feature}' != '{feature}'"
                )

    def test_golden_test_names_are_unique_per_feature(self):
        for feature, tests in ALL_GOLDEN_TESTS.items():
            names = [t.name for t in tests]
            assert len(names) == len(set(names)), (
                f"Duplicate test names in {feature}"
            )

    def test_architecture_tests_cover_varied_org_sizes(self):
        sizes = {t.input_data.get("organization_size") for t in ARCHITECTURE_GOLDEN_TESTS}
        assert len(sizes) >= 3, "Architecture tests should cover at least 3 org sizes"

    def test_architecture_tests_cover_varied_regions(self):
        regions = {t.input_data.get("primary_region") for t in ARCHITECTURE_GOLDEN_TESTS}
        assert len(regions) >= 3, "Architecture tests should cover at least 3 regions"

    def test_sizing_tests_cover_gpu_workloads(self):
        gpu_tests = [
            t for t in SIZING_GOLDEN_TESTS
            if t.input_data.get("gpu_required", False)
        ]
        assert len(gpu_tests) >= 1, "Sizing tests should cover GPU workloads"


# ===================================================================
# 2. Schema validation
# ===================================================================


class TestSchemas:
    """Test Pydantic schema models."""

    def test_output_score_defaults(self):
        score = OutputScore()
        assert score.structural == 0.0
        assert score.azure_validity == 0.0
        assert score.completeness == 0.0
        assert score.security == 0.0
        assert score.overall == 0.0

    def test_output_score_with_values(self):
        score = OutputScore(structural=80, azure_validity=90, completeness=70,
                            security=85, overall=81.25)
        assert score.structural == 80
        assert score.overall == 81.25

    def test_golden_test_creation(self):
        gt = GoldenTest(name="test1", input_data={"a": 1},
                        expected_patterns={"b": 2}, feature="architecture")
        assert gt.name == "test1"
        assert gt.feature == "architecture"

    def test_individual_result_defaults(self):
        r = IndividualResult(test_name="x", passed=True)
        assert r.errors == []
        assert r.score.overall == 0.0

    def test_evaluation_report_defaults(self):
        r = EvaluationReport(feature="architecture")
        assert r.test_count == 0
        assert r.passed == 0
        assert r.failed == 0

    def test_full_evaluation_report_has_timestamp(self):
        r = FullEvaluationReport()
        assert r.timestamp is not None
        assert r.overall_score == 0.0

    def test_regression_result_no_regression(self):
        r = RegressionResult()
        assert r.has_regression is False
        assert r.regressions == []

    def test_regression_item_creation(self):
        item = RegressionItem(
            feature="architecture", metric="structural",
            baseline=90.0, current=80.0, delta=-10.0,
        )
        assert item.delta == -10.0

    def test_eval_feature_enum_values(self):
        assert EvalFeature.architecture.value == "architecture"
        assert EvalFeature.policy.value == "policy"
        assert EvalFeature.sizing.value == "sizing"
        assert EvalFeature.security.value == "security"
        assert EvalFeature.regulatory.value == "regulatory"


# ===================================================================
# 3. Mock generators
# ===================================================================


class TestMockGenerators:
    """Test that mock generators produce valid output."""

    def test_mock_architecture_small(self):
        output = _mock_architecture({
            "organization_size": "small",
            "primary_region": "eastus",
            "budget_usd": 5000,
            "compliance_frameworks": [],
        })
        assert output["organization_size"] == "small"
        assert len(output["subscriptions"]) >= 1
        assert output["network_topology"]["type"] == "hub-spoke"

    def test_mock_architecture_enterprise(self):
        output = _mock_architecture({
            "organization_size": "enterprise",
            "primary_region": "westeurope",
            "budget_usd": 500000,
            "compliance_frameworks": ["PCI-DSS"],
        })
        assert output["organization_size"] == "enterprise"
        assert len(output["subscriptions"]) >= 3
        assert output["security"]["sentinel"] is True

    def test_mock_policy_generates_valid_structure(self):
        output = _mock_policy({"description": "Deny public access"})
        assert "name" in output
        assert "policy_rule" in output
        assert "then" in output["policy_rule"]

    def test_mock_sizing_low_cpu(self):
        output = _mock_sizing({"workload": "web-app", "cpu_avg_percent": 10})
        assert output["recommended_sku"].startswith("Standard_B")

    def test_mock_sizing_high_cpu(self):
        output = _mock_sizing({"workload": "compute", "cpu_avg_percent": 95})
        assert output["recommended_sku"].startswith("Standard_F")

    def test_mock_sizing_gpu(self):
        output = _mock_sizing({
            "workload": "ml-training", "cpu_avg_percent": 90, "gpu_required": True,
        })
        assert output["recommended_sku"].startswith("Standard_NC")

    def test_mock_sizing_medium_cpu(self):
        output = _mock_sizing({"workload": "api", "cpu_avg_percent": 65})
        assert output["recommended_sku"].startswith("Standard_E")

    def test_mock_security_with_resources(self):
        output = _mock_security({
            "architecture": {
                "resources": [
                    {"type": "Microsoft.Storage/storageAccounts",
                     "name": "publicstore", "public_access": True},
                ],
            },
        })
        assert output["severity"] in ("critical", "high", "medium", "low")
        assert output["resource"] == "publicstore"

    def test_mock_security_no_defender(self):
        output = _mock_security({
            "architecture": {"security": {"defender_for_cloud": False}},
        })
        assert output["severity"] == "high"
        assert "Defender" in output["finding"]

    def test_mock_security_empty_architecture(self):
        output = _mock_security({"architecture": {}})
        assert output["severity"] == "medium"

    def test_mock_regulatory_healthcare(self):
        output = _mock_regulatory({
            "industry": "healthcare", "geography": "United States",
        })
        assert output["framework"] == "HIPAA"

    def test_mock_regulatory_financial(self):
        output = _mock_regulatory({
            "industry": "financial-services", "geography": "EU",
        })
        assert output["framework"] == "PCI-DSS"

    def test_mock_regulatory_government(self):
        output = _mock_regulatory({
            "industry": "government", "geography": "US",
        })
        assert output["framework"] == "FedRAMP"

    def test_mock_regulatory_unknown_industry(self):
        output = _mock_regulatory({
            "industry": "unknown", "geography": "global",
        })
        assert output["framework"] == "ISO27001"


# ===================================================================
# 4. Scoring — structural
# ===================================================================


class TestStructuralScoring:
    """Test structural correctness scoring."""

    def test_valid_architecture_scores_100(self):
        output = _mock_architecture({
            "organization_size": "small", "primary_region": "eastus",
            "budget_usd": 5000, "compliance_frameworks": [],
        })
        assert _score_structural("architecture", output) == 100.0

    def test_valid_policy_scores_100(self):
        output = _mock_policy({"description": "test"})
        assert _score_structural("policy", output) == 100.0

    def test_valid_sizing_scores_100(self):
        output = _mock_sizing({"workload": "web", "cpu_avg_percent": 50})
        assert _score_structural("sizing", output) == 100.0

    def test_valid_security_scores_100(self):
        output = _mock_security({
            "architecture": {
                "resources": [{"type": "x", "name": "y", "public_access": True}],
            },
        })
        assert _score_structural("security", output) == 100.0

    def test_valid_regulatory_scores_100(self):
        output = _mock_regulatory({"industry": "healthcare", "geography": "US"})
        assert _score_structural("regulatory", output) == 100.0

    def test_invalid_architecture_scores_low(self):
        # Missing required field 'organization_size'
        score = _score_structural("architecture", {})
        assert score < 100.0

    def test_invalid_policy_missing_name(self):
        score = _score_structural("policy", {})
        assert score < 100.0

    def test_invalid_sizing_missing_fields(self):
        score = _score_structural("sizing", {})
        assert score < 100.0

    def test_unknown_feature_scores_zero(self):
        assert _score_structural("nonexistent", {}) == 0.0


# ===================================================================
# 5. Scoring — Azure validity
# ===================================================================


class TestAzureValidityScoring:
    """Test Azure validity scoring."""

    def test_valid_architecture_region(self):
        output = _mock_architecture({
            "organization_size": "small", "primary_region": "eastus",
            "budget_usd": 5000, "compliance_frameworks": [],
        })
        score = _score_azure_validity("architecture", output)
        assert score == 100.0

    def test_invalid_architecture_region(self):
        output = {
            "organization_size": "small",
            "network_topology": {"type": "hub-spoke", "primary_region": "fakeland"},
        }
        score = _score_azure_validity("architecture", output)
        assert score < 100.0

    def test_valid_sku(self):
        output = {"recommended_sku": "Standard_D4s_v5"}
        score = _score_azure_validity("sizing", output)
        assert score == 100.0

    def test_invalid_sku(self):
        output = {"recommended_sku": "Fake_SKU_X99"}
        score = _score_azure_validity("sizing", output)
        assert score == 0.0

    def test_valid_policy_mode(self):
        output = _mock_policy({"description": "test"})
        score = _score_azure_validity("policy", output)
        assert score == 100.0

    def test_invalid_policy_mode(self):
        output = {"mode": "InvalidMode", "policy_rule": {"then": {"effect": "Deny"}}}
        score = _score_azure_validity("policy", output)
        assert score < 100.0

    def test_valid_security_severity(self):
        output = {"severity": "high"}
        score = _score_azure_validity("security", output)
        assert score == 100.0

    def test_invalid_security_severity(self):
        output = {"severity": "super-critical"}
        score = _score_azure_validity("security", output)
        assert score == 0.0

    def test_valid_regulatory_status(self):
        output = {"status": "partial"}
        score = _score_azure_validity("regulatory", output)
        assert score == 100.0

    def test_invalid_regulatory_status(self):
        output = {"status": "maybe"}
        score = _score_azure_validity("regulatory", output)
        assert score == 0.0

    def test_no_checks_returns_100(self):
        # If no fields to check, assume valid
        score = _score_azure_validity("architecture", {})
        assert score == 100.0


# ===================================================================
# 6. Scoring — completeness
# ===================================================================


class TestCompletenessScoring:
    """Test completeness scoring against expected patterns."""

    def test_complete_architecture(self):
        output = _mock_architecture({
            "organization_size": "small", "primary_region": "eastus",
            "budget_usd": 5000, "compliance_frameworks": [],
        })
        expected = ARCHITECTURE_GOLDEN_TESTS[0].expected_patterns
        score = _score_completeness("architecture", output, expected)
        assert score >= 80.0

    def test_empty_architecture_scores_low(self):
        score = _score_completeness("architecture", {}, {
            "has_management_groups": True,
            "has_subscriptions": True,
            "organization_size": "small",
        })
        assert score < 50.0

    def test_complete_policy(self):
        output = _mock_policy({"description": "Deny public access"})
        expected = POLICY_GOLDEN_TESTS[0].expected_patterns
        score = _score_completeness("policy", output, expected)
        assert score >= 80.0

    def test_complete_sizing(self):
        output = _mock_sizing({"workload": "web-app", "cpu_avg_percent": 15})
        expected = SIZING_GOLDEN_TESTS[0].expected_patterns
        score = _score_completeness("sizing", output, expected)
        assert score >= 80.0

    def test_no_expected_patterns_returns_100(self):
        score = _score_completeness("architecture", {}, {})
        assert score == 100.0


# ===================================================================
# 7. Scoring — security posture
# ===================================================================


class TestSecurityPostureScoring:
    """Test security posture scoring."""

    def test_secure_architecture_scores_high(self):
        output = _mock_architecture({
            "organization_size": "enterprise", "primary_region": "eastus",
            "budget_usd": 500000, "compliance_frameworks": [],
        })
        score = _score_security_posture("architecture", output)
        assert score >= 80.0

    def test_insecure_architecture_scores_low(self):
        output = {
            "security": {
                "defender_for_cloud": False,
                "key_vault_per_subscription": False,
                "waf": False,
            },
            "identity": {
                "conditional_access": False,
                "mfa_policy": "optional",
            },
        }
        score = _score_security_posture("architecture", output)
        assert score < 50.0

    def test_security_finding_with_remediation(self):
        output = {"severity": "high", "remediation": "Fix it"}
        score = _score_security_posture("security", output)
        assert score == 100.0

    def test_security_finding_no_severity(self):
        output = {"remediation": "Fix it"}
        score = _score_security_posture("security", output)
        assert score < 100.0

    def test_security_finding_no_remediation(self):
        output = {"severity": "high"}
        score = _score_security_posture("security", output)
        assert score < 100.0

    def test_policy_with_rule_scores_high(self):
        output = _mock_policy({"description": "test"})
        score = _score_security_posture("policy", output)
        assert score == 100.0

    def test_policy_without_rule_scores_low(self):
        output = {"name": "test", "policy_rule": {}}
        score = _score_security_posture("policy", output)
        assert score < 100.0

    def test_sizing_always_100(self):
        score = _score_security_posture("sizing", {})
        assert score == 100.0

    def test_regulatory_always_100(self):
        score = _score_security_posture("regulatory", {})
        assert score == 100.0


# ===================================================================
# 8. Clamp helper
# ===================================================================


class TestClamp:
    """Test the _clamp utility."""

    def test_clamp_within_range(self):
        assert _clamp(50.0) == 50.0

    def test_clamp_below_zero(self):
        assert _clamp(-10.0) == 0.0

    def test_clamp_above_100(self):
        assert _clamp(150.0) == 100.0

    def test_clamp_boundaries(self):
        assert _clamp(0.0) == 0.0
        assert _clamp(100.0) == 100.0


# ===================================================================
# 9. AIEvaluator — score_output
# ===================================================================


class TestScoreOutput:
    """Test the evaluator's score_output method."""

    def test_valid_architecture_score(self):
        output = _mock_architecture({
            "organization_size": "small", "primary_region": "eastus",
            "budget_usd": 5000, "compliance_frameworks": [],
        })
        score = ai_evaluator.score_output(
            "architecture", output,
            ARCHITECTURE_GOLDEN_TESTS[0].expected_patterns,
        )
        assert score.overall >= 60.0
        assert score.structural == 100.0

    def test_valid_policy_score(self):
        output = _mock_policy({"description": "Deny public blob access"})
        score = ai_evaluator.score_output(
            "policy", output, POLICY_GOLDEN_TESTS[0].expected_patterns,
        )
        assert score.overall >= 60.0

    def test_empty_output_scores_low(self):
        score = ai_evaluator.score_output(
            "architecture", {},
            {"has_management_groups": True, "has_subscriptions": True},
        )
        assert score.overall < 60.0


# ===================================================================
# 10. AIEvaluator — evaluate_feature
# ===================================================================


class TestEvaluateFeature:
    """Test evaluate_feature runs all golden tests."""

    def test_evaluate_architecture(self):
        report = ai_evaluator.evaluate_feature(
            "architecture", ARCHITECTURE_GOLDEN_TESTS,
        )
        assert report.feature == "architecture"
        assert report.test_count == len(ARCHITECTURE_GOLDEN_TESTS)
        assert report.passed + report.failed == report.test_count
        assert report.passed > 0

    def test_evaluate_policy(self):
        report = ai_evaluator.evaluate_feature("policy", POLICY_GOLDEN_TESTS)
        assert report.feature == "policy"
        assert report.test_count >= 5

    def test_evaluate_sizing(self):
        report = ai_evaluator.evaluate_feature("sizing", SIZING_GOLDEN_TESTS)
        assert report.test_count >= 5
        assert report.passed > 0

    def test_evaluate_security(self):
        report = ai_evaluator.evaluate_feature("security", SECURITY_GOLDEN_TESTS)
        assert report.test_count >= 5

    def test_evaluate_regulatory(self):
        report = ai_evaluator.evaluate_feature("regulatory", REGULATORY_GOLDEN_TESTS)
        assert report.test_count >= 5

    def test_evaluate_empty_tests(self):
        report = ai_evaluator.evaluate_feature("architecture", [])
        assert report.test_count == 0
        assert report.passed == 0
        assert report.failed == 0

    def test_individual_results_populated(self):
        report = ai_evaluator.evaluate_feature(
            "architecture", ARCHITECTURE_GOLDEN_TESTS,
        )
        assert len(report.individual_results) == report.test_count
        for r in report.individual_results:
            assert r.test_name
            assert isinstance(r.passed, bool)

    def test_avg_score_reasonable(self):
        report = ai_evaluator.evaluate_feature(
            "architecture", ARCHITECTURE_GOLDEN_TESTS,
        )
        assert 0.0 <= report.avg_score.overall <= 100.0
        assert 0.0 <= report.avg_score.structural <= 100.0


# ===================================================================
# 11. AIEvaluator — run_full_evaluation
# ===================================================================


class TestRunFullEvaluation:
    """Test full evaluation across all features."""

    def test_full_evaluation_covers_all_features(self):
        report = ai_evaluator.run_full_evaluation()
        assert set(report.features.keys()) == set(ALL_GOLDEN_TESTS.keys())

    def test_full_evaluation_has_overall_score(self):
        report = ai_evaluator.run_full_evaluation()
        assert 0.0 <= report.overall_score <= 100.0

    def test_full_evaluation_has_timestamp(self):
        report = ai_evaluator.run_full_evaluation()
        assert report.timestamp is not None

    def test_full_evaluation_caches_as_latest(self):
        assert ai_evaluator.latest_report is None
        report = ai_evaluator.run_full_evaluation()
        assert ai_evaluator.latest_report is report


# ===================================================================
# 12. AIEvaluator — check_regression
# ===================================================================


class TestCheckRegression:
    """Test regression detection."""

    def test_no_regression_when_scores_equal(self):
        report = ai_evaluator.run_full_evaluation()
        result = ai_evaluator.check_regression(report, report)
        assert result.has_regression is False
        assert result.regressions == []

    def test_no_regression_when_scores_improve(self):
        baseline = ai_evaluator.run_full_evaluation()
        # Run again — should produce same scores → no regression
        current = ai_evaluator.run_full_evaluation()
        result = ai_evaluator.check_regression(current, baseline)
        assert result.has_regression is False

    def test_regression_detected_when_score_drops(self):
        baseline = ai_evaluator.run_full_evaluation()
        # Artificially lower a score in current
        current = ai_evaluator.run_full_evaluation()
        current.features["architecture"].avg_score.structural = 10.0
        current.features["architecture"].avg_score.overall = 10.0
        result = ai_evaluator.check_regression(current, baseline)
        assert result.has_regression is True
        assert len(result.regressions) > 0
        regression_features = {r.feature for r in result.regressions}
        assert "architecture" in regression_features

    def test_regression_threshold(self):
        baseline = ai_evaluator.run_full_evaluation()
        current = ai_evaluator.run_full_evaluation()
        # Small drop — below threshold → no regression
        orig = current.features["architecture"].avg_score.structural
        current.features["architecture"].avg_score.structural = orig - 3.0
        result = ai_evaluator.check_regression(current, baseline)
        # 3 point drop is under the 5 point threshold
        arch_regressions = [
            r for r in result.regressions
            if r.feature == "architecture" and r.metric == "structural"
        ]
        assert len(arch_regressions) == 0

    def test_regression_for_missing_baseline_feature(self):
        """Features only in current (not baseline) should not flag regression."""
        baseline = FullEvaluationReport()
        current = ai_evaluator.run_full_evaluation()
        result = ai_evaluator.check_regression(current, baseline)
        assert result.has_regression is False


# ===================================================================
# 13. AIEvaluator — generate_mock_output
# ===================================================================


class TestGenerateMockOutput:
    """Test the mock output generator dispatch."""

    def test_architecture_mock(self):
        output = ai_evaluator.generate_mock_output("architecture", {
            "organization_size": "medium",
        })
        assert "management_groups" in output

    def test_unknown_feature_returns_empty(self):
        output = ai_evaluator.generate_mock_output("nonexistent", {})
        assert output == {}

    def test_all_features_have_generators(self):
        for feature in ALL_GOLDEN_TESTS:
            output = ai_evaluator.generate_mock_output(
                feature, ALL_GOLDEN_TESTS[feature][0].input_data,
            )
            assert output, f"No output for {feature}"


# ===================================================================
# 14. AIEvaluator — reset
# ===================================================================


class TestEvaluatorReset:
    """Test evaluator reset."""

    def test_reset_clears_latest_report(self):
        ai_evaluator.run_full_evaluation()
        assert ai_evaluator.latest_report is not None
        ai_evaluator.reset()
        assert ai_evaluator.latest_report is None


# ===================================================================
# 15. Golden tests produce expected results with mock AI
# ===================================================================


class TestGoldenTestsWithMockAI:
    """Each golden test should pass with mock AI outputs."""

    def test_all_architecture_golden_tests_pass(self):
        for test in ARCHITECTURE_GOLDEN_TESTS:
            output = ai_evaluator.generate_mock_output("architecture", test.input_data)
            score = ai_evaluator.score_output(
                "architecture", output, test.expected_patterns,
            )
            assert score.overall >= 60.0, (
                f"Architecture test '{test.name}' failed: overall={score.overall}"
            )

    def test_all_policy_golden_tests_pass(self):
        for test in POLICY_GOLDEN_TESTS:
            output = ai_evaluator.generate_mock_output("policy", test.input_data)
            score = ai_evaluator.score_output(
                "policy", output, test.expected_patterns,
            )
            assert score.overall >= 60.0, (
                f"Policy test '{test.name}' failed: overall={score.overall}"
            )

    def test_all_sizing_golden_tests_pass(self):
        for test in SIZING_GOLDEN_TESTS:
            output = ai_evaluator.generate_mock_output("sizing", test.input_data)
            score = ai_evaluator.score_output(
                "sizing", output, test.expected_patterns,
            )
            assert score.overall >= 60.0, (
                f"Sizing test '{test.name}' failed: overall={score.overall}"
            )

    def test_all_security_golden_tests_pass(self):
        for test in SECURITY_GOLDEN_TESTS:
            output = ai_evaluator.generate_mock_output("security", test.input_data)
            score = ai_evaluator.score_output(
                "security", output, test.expected_patterns,
            )
            assert score.overall >= 60.0, (
                f"Security test '{test.name}' failed: overall={score.overall}"
            )

    def test_all_regulatory_golden_tests_pass(self):
        for test in REGULATORY_GOLDEN_TESTS:
            output = ai_evaluator.generate_mock_output(
                "regulatory", test.input_data,
            )
            score = ai_evaluator.score_output(
                "regulatory", output, test.expected_patterns,
            )
            assert score.overall >= 60.0, (
                f"Regulatory test '{test.name}' failed: overall={score.overall}"
            )


# ===================================================================
# 16. Route endpoints
# ===================================================================


class TestRoutes:
    """Test API route endpoints."""

    def test_run_full_evaluation(self):
        resp = client.post("/api/ai/eval/run")
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data
        assert "overall_score" in data
        assert "timestamp" in data

    def test_run_feature_architecture(self):
        resp = client.post("/api/ai/eval/feature/architecture")
        assert resp.status_code == 200
        data = resp.json()
        assert data["feature"] == "architecture"
        assert data["test_count"] >= 5

    def test_run_feature_policy(self):
        resp = client.post("/api/ai/eval/feature/policy")
        assert resp.status_code == 200
        assert resp.json()["feature"] == "policy"

    def test_run_feature_sizing(self):
        resp = client.post("/api/ai/eval/feature/sizing")
        assert resp.status_code == 200
        assert resp.json()["feature"] == "sizing"

    def test_run_feature_security(self):
        resp = client.post("/api/ai/eval/feature/security")
        assert resp.status_code == 200
        assert resp.json()["feature"] == "security"

    def test_run_feature_regulatory(self):
        resp = client.post("/api/ai/eval/feature/regulatory")
        assert resp.status_code == 200
        assert resp.json()["feature"] == "regulatory"

    def test_run_feature_invalid(self):
        resp = client.post("/api/ai/eval/feature/nonexistent")
        assert resp.status_code == 422  # FastAPI enum validation

    def test_get_results_before_run(self):
        resp = client.get("/api/ai/eval/results")
        assert resp.status_code == 404

    def test_get_results_after_run(self):
        client.post("/api/ai/eval/run")
        resp = client.get("/api/ai/eval/results")
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data

    def test_list_golden_tests(self):
        resp = client.get("/api/ai/eval/golden-tests")
        assert resp.status_code == 200
        data = resp.json()
        assert "features" in data
        assert "total" in data
        assert data["total"] >= 25  # 5+ per feature × 5 features

    def test_list_golden_tests_has_all_features(self):
        resp = client.get("/api/ai/eval/golden-tests")
        features = resp.json()["features"]
        assert set(features.keys()) == {
            "architecture", "policy", "sizing", "security", "regulatory",
        }

    def test_run_evaluation_response_structure(self):
        resp = client.post("/api/ai/eval/run")
        data = resp.json()
        for feature_name, report in data["features"].items():
            assert "test_count" in report
            assert "passed" in report
            assert "failed" in report
            assert "avg_score" in report
            assert "individual_results" in report
            avg = report["avg_score"]
            assert "structural" in avg
            assert "azure_validity" in avg
            assert "completeness" in avg
            assert "security" in avg
            assert "overall" in avg
