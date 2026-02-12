"""Tests for landing zone archetypes."""

from app.services.archetypes import get_archetype, get_archetype_for_answers, list_archetypes


def test_list_archetypes():
    archetypes = list_archetypes()
    assert len(archetypes) == 3
    sizes = [a["size"] for a in archetypes]
    assert "small" in sizes
    assert "medium" in sizes
    assert "enterprise" in sizes


def test_get_small_archetype():
    arch = get_archetype("small")
    assert arch is not None
    assert arch["organization_size"] == "small"
    assert len(arch["subscriptions"]) == 3
    assert arch["security"]["sentinel"] is False


def test_get_medium_archetype():
    arch = get_archetype("medium")
    assert arch is not None
    assert arch["organization_size"] == "medium"
    assert len(arch["subscriptions"]) == 6
    assert arch["identity"]["pim_enabled"] is True


def test_get_enterprise_archetype():
    arch = get_archetype("enterprise")
    assert arch is not None
    assert arch["organization_size"] == "enterprise"
    assert len(arch["subscriptions"]) == 10
    assert arch["security"]["ddos_protection"] is True


def test_get_archetype_for_answers_small():
    answers = {"org_size": "small", "primary_region": "westus2"}
    arch = get_archetype_for_answers(answers)
    assert arch["organization_size"] == "small"
    assert arch["network_topology"]["primary_region"] == "westus2"


def test_get_archetype_for_answers_customization():
    answers = {
        "org_size": "medium",
        "primary_region": "northeurope",
        "pim_required": "yes",
        "siem_integration": "sentinel",
        "network_topology": "vwan",
        "hybrid_connectivity": "expressroute",
        "compliance_frameworks": ["hipaa", "soc2"],
    }
    arch = get_archetype_for_answers(answers)
    assert arch["network_topology"]["primary_region"] == "northeurope"
    assert arch["network_topology"]["type"] == "vwan"
    assert arch["identity"]["pim_enabled"] is True
    assert arch["security"]["sentinel"] is True
    assert len(arch["compliance_frameworks"]) == 2
    assert arch["network_topology"]["hybrid_connectivity"]["type"] == "expressroute"


def test_archetype_returns_deep_copy():
    arch1 = get_archetype("small")
    arch2 = get_archetype("small")
    arch1["subscriptions"].append({"name": "new-sub"})
    assert len(arch1["subscriptions"]) != len(arch2["subscriptions"])
