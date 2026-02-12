"""Tests for compliance scoring engine."""

from app.services.compliance_scoring import compliance_scorer
from app.services.archetypes import get_archetype


def test_score_small_architecture_soc2():
    arch = get_archetype("small")
    result = compliance_scorer.score_architecture(arch, ["SOC2"])
    assert "overall_score" in result
    assert result["overall_score"] >= 0
    assert result["overall_score"] <= 100
    assert len(result["frameworks"]) == 1
    assert result["frameworks"][0]["name"] == "SOC2"


def test_score_enterprise_architecture_multiple():
    arch = get_archetype("enterprise")
    result = compliance_scorer.score_architecture(arch, ["SOC2", "HIPAA", "NIST-800-53"])
    assert len(result["frameworks"]) == 3
    # Enterprise should score better than small
    assert result["overall_score"] > 0


def test_enterprise_scores_higher_than_small():
    small_arch = get_archetype("small")
    enterprise_arch = get_archetype("enterprise")

    small_score = compliance_scorer.score_architecture(small_arch, ["SOC2"])
    enterprise_score = compliance_scorer.score_architecture(enterprise_arch, ["SOC2"])

    assert enterprise_score["overall_score"] >= small_score["overall_score"]


def test_score_with_unknown_framework():
    arch = get_archetype("medium")
    result = compliance_scorer.score_architecture(arch, ["NONEXISTENT"])
    assert result["overall_score"] == 0
    assert len(result["frameworks"]) == 0


def test_gaps_have_remediation():
    arch = get_archetype("small")
    result = compliance_scorer.score_architecture(arch, ["HIPAA"])
    for fw in result["frameworks"]:
        for gap in fw.get("gaps", []):
            assert "remediation" in gap
            assert len(gap["remediation"]) > 0
