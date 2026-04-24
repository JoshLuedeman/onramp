"""Tests for the architecture comparator — pure helper functions and comparisons."""

import pytest

from app.services.architecture_comparator import (
    _compute_compliance_scores,
    _count_resources,
    _derive_complexity,
    _derive_cost_range,
    _make_cost_optimised,
    _make_enterprise_grade,
)


SAMPLE_ARCH = {
    "subscriptions": [
        {"name": "sub-platform", "budget_usd": 5000},
        {"name": "sub-workload-1", "budget_usd": 3000},
    ],
    "network_topology": {
        "hub": {"subnets": ["GatewaySubnet", "AzureFirewallSubnet"]},
        "spokes": [{"name": "spoke-1"}, {"name": "spoke-2"}],
    },
    "governance": {"policies": ["require-tags", "allowed-locations"]},
    "security": {
        "sentinel": False,
        "ddos_protection": False,
        "azure_firewall": True,
    },
    "compliance_frameworks": [
        {"name": "NIST", "coverage_percent": 70},
        {"name": "ISO 27001", "coverage_percent": 85},
    ],
    "management": {
        "log_analytics": {"retention_days": 90},
        "backup": True,
    },
    "estimated_monthly_cost_usd": 5000,
}


class TestCountResources:
    """Test _count_resources estimation."""

    def test_counts_subscriptions(self):
        count = _count_resources({"subscriptions": [1, 2, 3]})
        assert count >= 3

    def test_counts_spokes(self):
        count = _count_resources({"network_topology": {"spokes": [1, 2]}})
        assert count >= 2

    def test_sample_arch(self):
        count = _count_resources(SAMPLE_ARCH)
        assert count > 0

    def test_empty_arch(self):
        assert _count_resources({}) == 0


class TestComputeComplianceScores:
    """Test compliance score extraction."""

    def test_extracts_scores(self):
        scores = _compute_compliance_scores(SAMPLE_ARCH)
        assert scores["NIST"] == 70.0
        assert scores["ISO 27001"] == 85.0

    def test_empty_frameworks(self):
        assert _compute_compliance_scores({}) == {}


class TestDeriveCostRange:
    """Test cost range estimation."""

    def test_default_range(self):
        low, high = _derive_cost_range(SAMPLE_ARCH)
        assert low < 5000
        assert high > 5000

    def test_custom_multipliers(self):
        low, high = _derive_cost_range(SAMPLE_ARCH, 0.5, 2.0)
        assert low == 2500.0
        assert high == 10000.0

    def test_zero_cost(self):
        low, high = _derive_cost_range({})
        assert low == 0.0
        assert high == 0.0


class TestDeriveComplexity:
    """Test complexity derivation."""

    def test_simple_arch(self):
        assert _derive_complexity(SAMPLE_ARCH) == "simple"

    def test_complex_with_security(self):
        arch = {
            "subscriptions": [1, 2, 3],
            "security": {"sentinel": True, "ddos_protection": True},
        }
        assert _derive_complexity(arch) == "complex"

    def test_complex_with_many_subs(self):
        arch = {"subscriptions": list(range(10))}
        assert _derive_complexity(arch) == "complex"

    def test_moderate(self):
        arch = {
            "subscriptions": [1, 2, 3, 4, 5],
            "security": {"sentinel": True, "ddos_protection": False},
        }
        assert _derive_complexity(arch) == "moderate"


class TestMakeCostOptimised:
    """Test cost-optimised variant generation."""

    def test_reduces_subscriptions(self):
        arch = {
            "subscriptions": [
                {"name": f"sub-{i}", "budget_usd": 1000} for i in range(6)
            ],
            "security": {},
            "management": {},
            "estimated_monthly_cost_usd": 10000,
        }
        result = _make_cost_optimised(arch)
        assert len(result["subscriptions"]) <= 3

    def test_disables_premium_security(self):
        result = _make_cost_optimised(SAMPLE_ARCH)
        assert result["security"]["sentinel"] is False
        assert result["security"]["ddos_protection"] is False

    def test_reduces_cost(self):
        result = _make_cost_optimised(SAMPLE_ARCH)
        assert result["estimated_monthly_cost_usd"] < 5000

    def test_does_not_mutate_original(self):
        original_cost = SAMPLE_ARCH["estimated_monthly_cost_usd"]
        _make_cost_optimised(SAMPLE_ARCH)
        assert SAMPLE_ARCH["estimated_monthly_cost_usd"] == original_cost


class TestMakeEnterpriseGrade:
    """Test enterprise-grade variant generation."""

    def test_enables_premium_security(self):
        result = _make_enterprise_grade(SAMPLE_ARCH)
        assert result["security"]["sentinel"] is True
        assert result["security"]["ddos_protection"] is True
        assert result["security"]["waf"] is True

    def test_enables_pim(self):
        result = _make_enterprise_grade(SAMPLE_ARCH)
        assert result["identity"]["pim_enabled"] is True

    def test_increases_cost(self):
        result = _make_enterprise_grade(SAMPLE_ARCH)
        assert result["estimated_monthly_cost_usd"] > 5000

    def test_does_not_mutate_original(self):
        original_subs = len(SAMPLE_ARCH["subscriptions"])
        _make_enterprise_grade(SAMPLE_ARCH)
        assert len(SAMPLE_ARCH["subscriptions"]) == original_subs
