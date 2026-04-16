"""Tests for architecture comparison mode.

Covers variant generation, cost ordering, resource counts, complexity ratings,
comparison metrics, trade-off analysis, and the HTTP endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.architecture_compare import (
    ArchitectureVariant,
    CompareRequest,
    ComparisonResult,
)
from app.services.architecture_comparator import (
    ArchitectureComparator,
    _count_resources,
    _compute_compliance_scores,
    _derive_complexity,
    _derive_cost_range,
    _make_cost_optimised,
    _make_enterprise_grade,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def comparator() -> ArchitectureComparator:
    return ArchitectureComparator()


@pytest.fixture()
def small_answers() -> dict:
    return {"org_size": "small", "industry": "technology"}


@pytest.fixture()
def medium_answers() -> dict:
    return {"org_size": "medium", "network_topology": "hub_spoke"}


@pytest.fixture()
def enterprise_answers() -> dict:
    return {"org_size": "enterprise", "compliance_frameworks": ["nist_800_53", "iso_27001"]}


@pytest.fixture()
def sample_variants(comparator: ArchitectureComparator, medium_answers: dict):
    return comparator.generate_variants(medium_answers)


# ---------------------------------------------------------------------------
# Schema model tests
# ---------------------------------------------------------------------------

class TestSchemaModels:
    def test_architecture_variant_defaults(self):
        v = ArchitectureVariant(name="Test", description="A test variant")
        assert v.resource_count == 0
        assert v.estimated_monthly_cost_min == 0.0
        assert v.estimated_monthly_cost_max == 0.0
        assert v.complexity == "moderate"
        assert v.compliance_scores == {}

    def test_architecture_variant_with_values(self):
        v = ArchitectureVariant(
            name="Enterprise",
            description="Full",
            architecture={"subscriptions": []},
            resource_count=42,
            estimated_monthly_cost_min=5000,
            estimated_monthly_cost_max=8000,
            complexity="complex",
            compliance_scores={"nist": 85.0},
        )
        assert v.name == "Enterprise"
        assert v.resource_count == 42
        assert v.complexity == "complex"
        assert v.compliance_scores["nist"] == 85.0

    def test_comparison_result_defaults(self):
        r = ComparisonResult()
        assert r.variants == []
        assert r.tradeoff_analysis == ""
        assert r.recommended_index == 1

    def test_compare_request_minimal(self):
        req = CompareRequest(answers={"org_size": "small"})
        assert req.options is None

    def test_compare_request_with_options(self):
        req = CompareRequest(
            answers={"org_size": "medium"},
            options={"include_compliance": True},
        )
        assert req.options == {"include_compliance": True}


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_count_resources_empty(self):
        assert _count_resources({}) == 0

    def test_count_resources_with_subscriptions(self):
        arch = {"subscriptions": [{"name": "a"}, {"name": "b"}]}
        assert _count_resources(arch) >= 2

    def test_count_resources_includes_security_flags(self):
        arch = {
            "subscriptions": [],
            "security": {"sentinel": True, "ddos_protection": True, "waf": False},
        }
        count = _count_resources(arch)
        assert count >= 2  # sentinel + ddos

    def test_count_resources_includes_spokes(self):
        arch = {
            "subscriptions": [],
            "network_topology": {"spokes": [{"name": "a"}, {"name": "b"}]},
        }
        assert _count_resources(arch) >= 2

    def test_count_resources_includes_hub_subnets(self):
        arch = {
            "subscriptions": [],
            "network_topology": {"hub": {"subnets": [{"name": "fw"}, {"name": "gw"}]}},
        }
        assert _count_resources(arch) >= 2

    def test_count_resources_includes_policies(self):
        arch = {
            "subscriptions": [],
            "governance": {"policies": [{"name": "p1"}, {"name": "p2"}, {"name": "p3"}]},
        }
        assert _count_resources(arch) >= 3

    def test_count_resources_includes_management(self):
        arch = {
            "subscriptions": [],
            "management": {"log_analytics": {"workspace_count": 1}, "update_management": True},
        }
        assert _count_resources(arch) >= 2

    def test_count_resources_includes_security_lists(self):
        arch = {
            "subscriptions": [],
            "security": {"defender_plans": ["Servers", "SQL", "KeyVaults"]},
        }
        assert _count_resources(arch) >= 3

    def test_compute_compliance_scores_empty(self):
        assert _compute_compliance_scores({}) == {}

    def test_compute_compliance_scores_with_frameworks(self):
        arch = {
            "compliance_frameworks": [
                {"name": "NIST", "coverage_percent": 85},
                {"name": "ISO 27001", "coverage_percent": 70},
            ],
        }
        scores = _compute_compliance_scores(arch)
        assert scores["NIST"] == 85.0
        assert scores["ISO 27001"] == 70.0

    def test_derive_cost_range_zero(self):
        assert _derive_cost_range({}) == (0.0, 0.0)

    def test_derive_cost_range_calculation(self):
        arch = {"estimated_monthly_cost_usd": 1000}
        low, high = _derive_cost_range(arch)
        assert low == 850.0
        assert high == 1150.0

    def test_derive_cost_range_custom_multipliers(self):
        arch = {"estimated_monthly_cost_usd": 1000}
        low, high = _derive_cost_range(arch, 0.5, 2.0)
        assert low == 500.0
        assert high == 2000.0

    def test_derive_complexity_simple(self):
        arch = {"subscriptions": [{"name": "a"}], "security": {}}
        assert _derive_complexity(arch) == "simple"

    def test_derive_complexity_moderate(self):
        arch = {
            "subscriptions": [{"name": f"s{i}"} for i in range(5)],
            "security": {"sentinel": True, "ddos_protection": False},
        }
        assert _derive_complexity(arch) == "moderate"

    def test_derive_complexity_complex(self):
        arch = {
            "subscriptions": [{"name": f"s{i}"} for i in range(10)],
            "security": {"sentinel": True, "ddos_protection": True},
        }
        assert _derive_complexity(arch) == "complex"


# ---------------------------------------------------------------------------
# Variant transformation tests
# ---------------------------------------------------------------------------

class TestVariantTransformations:
    def test_cost_optimised_reduces_subscriptions(self):
        base = {"subscriptions": [{"name": f"s{i}", "budget_usd": 1000} for i in range(6)],
                "security": {}, "management": {}, "estimated_monthly_cost_usd": 5000}
        result = _make_cost_optimised(base)
        assert len(result["subscriptions"]) <= 3

    def test_cost_optimised_disables_sentinel(self):
        base = {"subscriptions": [], "security": {"sentinel": True},
                "management": {}, "estimated_monthly_cost_usd": 1000}
        result = _make_cost_optimised(base)
        assert result["security"]["sentinel"] is False

    def test_cost_optimised_disables_ddos(self):
        base = {"subscriptions": [], "security": {"ddos_protection": True},
                "management": {}, "estimated_monthly_cost_usd": 1000}
        result = _make_cost_optimised(base)
        assert result["security"]["ddos_protection"] is False

    def test_cost_optimised_reduces_retention(self):
        base = {"subscriptions": [], "security": {},
                "management": {"log_analytics": {"retention_days": 365}},
                "estimated_monthly_cost_usd": 1000}
        result = _make_cost_optimised(base)
        assert result["management"]["log_analytics"]["retention_days"] == 30

    def test_cost_optimised_reduces_cost(self):
        base = {"subscriptions": [], "security": {}, "management": {},
                "estimated_monthly_cost_usd": 10000}
        result = _make_cost_optimised(base)
        assert result["estimated_monthly_cost_usd"] < 10000

    def test_cost_optimised_reduces_budgets(self):
        base = {"subscriptions": [{"name": "s1", "budget_usd": 1000}],
                "security": {}, "management": {}, "estimated_monthly_cost_usd": 1000}
        result = _make_cost_optimised(base)
        assert result["subscriptions"][0]["budget_usd"] == 600

    def test_cost_optimised_does_not_mutate_original(self):
        base = {"subscriptions": [{"name": "s1", "budget_usd": 1000}],
                "security": {"sentinel": True}, "management": {},
                "estimated_monthly_cost_usd": 1000}
        _make_cost_optimised(base)
        assert base["security"]["sentinel"] is True
        assert base["subscriptions"][0]["budget_usd"] == 1000

    def test_enterprise_enables_sentinel(self):
        base = {"subscriptions": [], "security": {"sentinel": False},
                "identity": {}, "management": {}, "network_topology": {},
                "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert result["security"]["sentinel"] is True

    def test_enterprise_enables_ddos(self):
        base = {"subscriptions": [], "security": {"ddos_protection": False},
                "identity": {}, "management": {}, "network_topology": {},
                "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert result["security"]["ddos_protection"] is True

    def test_enterprise_enables_pim(self):
        base = {"subscriptions": [], "security": {},
                "identity": {"pim_enabled": False}, "management": {},
                "network_topology": {}, "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert result["identity"]["pim_enabled"] is True

    def test_enterprise_adds_secondary_region(self):
        base = {"subscriptions": [], "security": {}, "identity": {},
                "management": {}, "network_topology": {"type": "hub-spoke"},
                "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert result["network_topology"]["secondary_region"] == "westus2"

    def test_enterprise_extends_retention(self):
        base = {"subscriptions": [], "security": {}, "identity": {},
                "management": {"log_analytics": {"retention_days": 30}},
                "network_topology": {}, "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert result["management"]["log_analytics"]["retention_days"] == 365

    def test_enterprise_increases_cost(self):
        base = {"subscriptions": [], "security": {}, "identity": {},
                "management": {}, "network_topology": {},
                "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert result["estimated_monthly_cost_usd"] > 1000

    def test_enterprise_adds_extra_subscriptions(self):
        base = {"subscriptions": [{"name": "s1", "budget_usd": 500}],
                "security": {}, "identity": {}, "management": {},
                "network_topology": {}, "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert len(result["subscriptions"]) > 1

    def test_enterprise_does_not_mutate_original(self):
        base = {"subscriptions": [{"name": "s1", "budget_usd": 500}],
                "security": {"sentinel": False}, "identity": {},
                "management": {}, "network_topology": {},
                "estimated_monthly_cost_usd": 1000}
        _make_enterprise_grade(base)
        assert base["security"]["sentinel"] is False
        assert base["subscriptions"][0]["budget_usd"] == 500

    def test_enterprise_increases_budgets(self):
        base = {"subscriptions": [{"name": "s1", "budget_usd": 1000}],
                "security": {}, "identity": {}, "management": {},
                "network_topology": {}, "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert result["subscriptions"][0]["budget_usd"] == 1800

    def test_enterprise_enables_access_reviews(self):
        base = {"subscriptions": [], "security": {},
                "identity": {}, "management": {}, "network_topology": {},
                "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert result["identity"]["access_reviews"] is True

    def test_enterprise_break_glass_accounts(self):
        base = {"subscriptions": [], "security": {},
                "identity": {}, "management": {}, "network_topology": {},
                "estimated_monthly_cost_usd": 1000}
        result = _make_enterprise_grade(base)
        assert result["identity"]["break_glass_accounts"] == 2


# ---------------------------------------------------------------------------
# ArchitectureComparator tests
# ---------------------------------------------------------------------------

class TestArchitectureComparator:
    def test_singleton(self):
        a = ArchitectureComparator()
        b = ArchitectureComparator()
        assert a is b

    def test_generate_variants_returns_three(self, comparator, small_answers):
        variants = comparator.generate_variants(small_answers)
        assert len(variants) == 3

    def test_generate_variants_names(self, comparator, small_answers):
        variants = comparator.generate_variants(small_answers)
        names = [v.name for v in variants]
        assert names == ["Cost-Optimised", "Balanced", "Enterprise-Grade"]

    def test_generate_variants_cost_ordering(self, comparator, medium_answers):
        variants = comparator.generate_variants(medium_answers)
        costs = [v.estimated_monthly_cost_min for v in variants]
        assert costs[0] < costs[1] < costs[2]

    def test_generate_variants_cost_max_ordering(self, comparator, medium_answers):
        variants = comparator.generate_variants(medium_answers)
        costs = [v.estimated_monthly_cost_max for v in variants]
        assert costs[0] < costs[1] < costs[2]

    def test_cost_optimised_has_lowest_resources(self, comparator, medium_answers):
        variants = comparator.generate_variants(medium_answers)
        assert variants[0].resource_count <= variants[1].resource_count

    def test_enterprise_has_highest_resources(self, comparator, medium_answers):
        variants = comparator.generate_variants(medium_answers)
        assert variants[2].resource_count >= variants[1].resource_count

    def test_cost_optimised_complexity_is_simpler(self, comparator, small_answers):
        variants = comparator.generate_variants(small_answers)
        complexity_rank = {"simple": 0, "moderate": 1, "complex": 2}
        assert complexity_rank[variants[0].complexity] <= complexity_rank[variants[1].complexity]

    def test_enterprise_complexity_is_higher(self, comparator, medium_answers):
        variants = comparator.generate_variants(medium_answers)
        complexity_rank = {"simple": 0, "moderate": 1, "complex": 2}
        assert complexity_rank[variants[2].complexity] >= complexity_rank[variants[1].complexity]

    def test_variants_contain_architecture_dict(self, comparator, small_answers):
        variants = comparator.generate_variants(small_answers)
        for v in variants:
            assert isinstance(v.architecture, dict)
            assert "subscriptions" in v.architecture

    def test_balanced_uses_original_archetype(self, comparator, small_answers):
        variants = comparator.generate_variants(small_answers)
        balanced = variants[1]
        assert balanced.name == "Balanced"
        assert "management_groups" in balanced.architecture

    def test_compare_variants_returns_result(self, comparator, sample_variants):
        result = comparator.compare_variants(sample_variants)
        assert isinstance(result, ComparisonResult)
        assert len(result.variants) == 3

    def test_compare_variants_recommended_index(self, comparator, sample_variants):
        result = comparator.compare_variants(sample_variants)
        assert result.recommended_index == 1

    def test_compare_single_variant(self, comparator):
        variant = ArchitectureVariant(name="Solo", description="Only one")
        result = comparator.compare_variants([variant])
        assert result.recommended_index == 0

    def test_compare_includes_tradeoff(self, comparator, sample_variants):
        result = comparator.compare_variants(sample_variants)
        assert len(result.tradeoff_analysis) > 0

    def test_tradeoff_analysis_mock(self, comparator, sample_variants):
        analysis = comparator.generate_tradeoff_analysis(sample_variants)
        assert "Balanced" in analysis
        assert "Cost-Optimised" in analysis
        assert "Enterprise-Grade" in analysis

    def test_tradeoff_analysis_empty(self, comparator):
        analysis = comparator.generate_tradeoff_analysis([])
        assert "No variants" in analysis

    def test_generate_variants_with_enterprise_answers(self, comparator, enterprise_answers):
        variants = comparator.generate_variants(enterprise_answers)
        assert len(variants) == 3
        # Enterprise answers should still produce valid cost ordering
        costs = [v.estimated_monthly_cost_min for v in variants]
        assert costs[0] < costs[2]

    def test_generate_variants_with_options(self, comparator, small_answers):
        variants = comparator.generate_variants(small_answers, options={"include_compliance": True})
        assert len(variants) == 3

    def test_generate_variants_empty_answers(self, comparator):
        variants = comparator.generate_variants({})
        assert len(variants) == 3

    def test_variant_architecture_has_name(self, comparator, small_answers):
        variants = comparator.generate_variants(small_answers)
        for v in variants:
            assert "name" in v.architecture


# ---------------------------------------------------------------------------
# HTTP route tests
# ---------------------------------------------------------------------------

class TestCompareRoutes:
    def test_compare_returns_200(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "small"},
        })
        assert r.status_code == 200

    def test_compare_returns_three_variants(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "medium"},
        })
        data = r.json()
        assert len(data["variants"]) == 3

    def test_compare_recommended_index(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "medium"},
        })
        data = r.json()
        assert data["recommended_index"] == 1

    def test_compare_variant_structure(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "small"},
        })
        variant = r.json()["variants"][0]
        assert "name" in variant
        assert "description" in variant
        assert "architecture" in variant
        assert "resource_count" in variant
        assert "estimated_monthly_cost_min" in variant
        assert "estimated_monthly_cost_max" in variant
        assert "complexity" in variant
        assert "compliance_scores" in variant

    def test_compare_cost_ordering_via_route(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "medium"},
        })
        variants = r.json()["variants"]
        costs = [v["estimated_monthly_cost_min"] for v in variants]
        assert costs[0] < costs[1] < costs[2]

    def test_compare_with_options(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "small"},
            "options": {"include_compliance": True},
        })
        assert r.status_code == 200
        assert len(r.json()["variants"]) == 3

    def test_compare_enterprise_answers(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "enterprise", "compliance_frameworks": ["nist_800_53"]},
        })
        assert r.status_code == 200
        assert len(r.json()["variants"]) == 3

    def test_compare_empty_answers(self):
        r = client.post("/api/architecture/compare", json={"answers": {}})
        assert r.status_code == 200
        assert len(r.json()["variants"]) == 3

    def test_compare_includes_tradeoff_analysis(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "medium"},
        })
        data = r.json()
        assert len(data["tradeoff_analysis"]) > 0

    def test_tradeoffs_endpoint_returns_200(self):
        r = client.post("/api/architecture/compare/tradeoffs", json={
            "answers": {"org_size": "medium"},
        })
        assert r.status_code == 200

    def test_tradeoffs_endpoint_structure(self):
        r = client.post("/api/architecture/compare/tradeoffs", json={
            "answers": {"org_size": "small"},
        })
        data = r.json()
        assert "tradeoff_analysis" in data
        assert len(data["tradeoff_analysis"]) > 0

    def test_tradeoffs_mentions_variants(self):
        r = client.post("/api/architecture/compare/tradeoffs", json={
            "answers": {"org_size": "medium"},
        })
        analysis = r.json()["tradeoff_analysis"]
        assert "Cost-Optimised" in analysis
        assert "Balanced" in analysis

    def test_compare_variant_names(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "small"},
        })
        names = [v["name"] for v in r.json()["variants"]]
        assert names == ["Cost-Optimised", "Balanced", "Enterprise-Grade"]

    def test_compare_complexity_values(self):
        r = client.post("/api/architecture/compare", json={
            "answers": {"org_size": "medium"},
        })
        for v in r.json()["variants"]:
            assert v["complexity"] in ("simple", "moderate", "complex")
