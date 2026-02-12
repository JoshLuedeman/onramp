"""Tests for the Bicep template generator."""

from app.services.bicep_generator import bicep_generator
from app.services.archetypes import get_archetype


def test_list_templates():
    templates = bicep_generator.list_templates()
    assert len(templates) >= 4
    names = [t["name"] for t in templates]
    assert "management-groups" in names
    assert "hub-networking" in names
    assert "spoke-networking" in names
    assert "policy-assignments" in names


def test_get_template():
    template = bicep_generator.get_template("hub-networking.bicep")
    assert template is not None
    assert "vnet-hub" in template
    assert "AzureFirewallSubnet" in template


def test_generate_from_architecture():
    arch = get_archetype("medium")
    files = bicep_generator.generate_from_architecture(arch)
    assert "main.bicep" in files
    assert "hub-networking.bicep" in files
    assert "spoke-networking.bicep" in files
    assert "management-groups.bicep" in files
    assert "policy-assignments.bicep" in files
    assert "parameters.json" in files

    # Check main.bicep has spokes
    main = files["main.bicep"]
    assert "hub-networking" in main
    assert "spoke" in main.lower()


def test_generate_parameters():
    arch = get_archetype("small")
    files = bicep_generator.generate_from_architecture(arch)
    params = files["parameters.json"]
    assert "eastus2" in params
