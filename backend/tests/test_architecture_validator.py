"""Tests for the architecture validator service."""

from app.services.architecture_validator import (
    COMPLIANCE_REQUIREMENTS,
    NAMING_PATTERNS,
    VALIDATION_RULES,
    ArchitectureValidatorService,
    architecture_validator_service,
)


# ---------------------------------------------------------------------------
# Static data integrity
# ---------------------------------------------------------------------------


def test_validation_rules_non_empty():
    assert len(VALIDATION_RULES) >= 8


def test_compliance_requirements_keys():
    assert "soc2" in COMPLIANCE_REQUIREMENTS
    assert "hipaa" in COMPLIANCE_REQUIREMENTS
    assert "pci_dss" in COMPLIANCE_REQUIREMENTS


def test_naming_patterns_keys():
    assert "resource_group" in NAMING_PATTERNS
    assert "virtual_network" in NAMING_PATTERNS
    assert "storage_account" in NAMING_PATTERNS


# ---------------------------------------------------------------------------
# SKU validation
# ---------------------------------------------------------------------------


def test_validate_skus_all_available():
    arch = {
        "resources": [{"sku": "Standard_D4s_v5"}, {"sku": "Standard_B2s"}],
        "cloud_environment": "commercial",
    }
    result = architecture_validator_service.validate_skus(arch, "eastus")
    assert result["valid"] is True


def test_validate_skus_restricted_region():
    arch = {
        "resources": [{"sku": "Standard_NC6s_v3"}],
        "cloud_environment": "commercial",
    }
    result = architecture_validator_service.validate_skus(arch, "brazilsouth")
    assert result["valid"] is False
    assert len(result["errors"]) >= 1


def test_validate_skus_no_resources():
    arch = {"resources": [], "cloud_environment": "commercial"}
    result = architecture_validator_service.validate_skus(arch, "eastus")
    assert result["valid"] is True


def test_validate_skus_missing_resources_key():
    result = architecture_validator_service.validate_skus({}, "eastus")
    assert result["valid"] is True


# ---------------------------------------------------------------------------
# Compliance validation
# ---------------------------------------------------------------------------


def test_validate_compliance_soc2_pass():
    arch = {
        "security": {
            "encryption_at_rest": True,
            "centralized_logging": True,
            "mfa_enabled": True,
        },
        "network_topology": {"segmentation": True},
    }
    result = architecture_validator_service.validate_compliance(arch, "soc2")
    assert result["valid"] is True


def test_validate_compliance_soc2_missing_mfa():
    arch = {
        "security": {
            "encryption_at_rest": True,
            "centralized_logging": True,
        },
    }
    result = architecture_validator_service.validate_compliance(arch, "soc2")
    assert result["valid"] is False
    assert any("MFA" in e for e in result["errors"])


def test_validate_compliance_hipaa_missing_encryption():
    arch = {"security": {}}
    result = architecture_validator_service.validate_compliance(arch, "hipaa")
    assert result["valid"] is False
    assert len(result["errors"]) >= 2


def test_validate_compliance_pci_dss_waf_required():
    arch = {
        "security": {
            "encryption_at_rest": True,
            "encryption_in_transit": True,
            "centralized_logging": True,
            "mfa_enabled": True,
        },
        "network_topology": {"segmentation": True},
    }
    result = architecture_validator_service.validate_compliance(arch, "pci_dss")
    assert result["valid"] is False
    assert any("WAF" in e or "Firewall" in e for e in result["errors"])


def test_validate_compliance_unknown_framework():
    result = architecture_validator_service.validate_compliance({}, "unknown_fw")
    assert result["valid"] is True
    assert len(result["warnings"]) >= 1


def test_validate_compliance_returns_framework():
    result = architecture_validator_service.validate_compliance({}, "soc2")
    assert result["framework"] == "soc2"


def test_validate_compliance_fedramp_fips():
    arch = {
        "security": {
            "encryption_at_rest": True,
            "encryption_in_transit": True,
            "centralized_logging": True,
            "mfa_enabled": True,
        },
    }
    result = architecture_validator_service.validate_compliance(arch, "fedramp_high")
    assert result["valid"] is False
    assert any("FIPS" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# Networking validation
# ---------------------------------------------------------------------------


def test_validate_networking_empty():
    result = architecture_validator_service.validate_networking({})
    assert result["valid"] is True
    assert len(result["warnings"]) >= 1


def test_validate_networking_hub_spoke_with_hub():
    arch = {
        "network_topology": {
            "type": "hub_spoke",
            "hubs": [{"name": "hub-vnet"}],
            "spokes": [{"name": "spoke-1", "nsg": True}],
        },
    }
    result = architecture_validator_service.validate_networking(arch)
    assert result["valid"] is True


def test_validate_networking_hub_spoke_no_hub():
    arch = {
        "network_topology": {
            "type": "hub_spoke",
            "hubs": [],
        },
    }
    result = architecture_validator_service.validate_networking(arch)
    assert result["valid"] is False
    assert any("hub" in e.lower() for e in result["errors"])


def test_validate_networking_spoke_no_nsg():
    arch = {
        "network_topology": {
            "type": "hub_spoke",
            "hubs": [{"name": "hub"}],
            "spokes": [{"name": "spoke-1"}],
        },
    }
    result = architecture_validator_service.validate_networking(arch)
    assert any("NSG" in w for w in result["warnings"])


def test_validate_networking_hybrid_no_dns():
    arch = {
        "network_topology": {
            "type": "flat",
            "hybrid_connectivity": True,
        },
    }
    result = architecture_validator_service.validate_networking(arch)
    assert any("DNS" in w for w in result["warnings"])


def test_validate_networking_firewall_suggestion():
    arch = {
        "network_topology": {
            "type": "hub_spoke",
            "hubs": [{"name": "hub"}],
            "spokes": [],
        },
    }
    result = architecture_validator_service.validate_networking(arch)
    assert any("Firewall" in s for s in result.get("suggestions", []))


# ---------------------------------------------------------------------------
# Naming validation
# ---------------------------------------------------------------------------


def test_validate_naming_valid_resources():
    arch = {
        "resources": [
            {"type": "resource_group", "name": "rg-myapp-prod"},
            {"type": "storage_account", "name": "stmyappprod"},
        ],
    }
    result = architecture_validator_service.validate_naming(arch)
    assert result["valid"] is True


def test_validate_naming_too_long():
    arch = {
        "resources": [
            {"type": "storage_account", "name": "st" + "a" * 30},
        ],
    }
    result = architecture_validator_service.validate_naming(arch)
    assert result["valid"] is False
    assert any("exceeds" in e for e in result["errors"])


def test_validate_naming_bad_convention():
    arch = {
        "resources": [
            {"type": "resource_group", "name": "MyResourceGroup"},
        ],
    }
    result = architecture_validator_service.validate_naming(arch)
    assert any("naming convention" in w for w in result["warnings"])


def test_validate_naming_no_resources():
    result = architecture_validator_service.validate_naming({})
    assert result["valid"] is True


def test_validate_naming_unknown_type():
    arch = {
        "resources": [
            {"type": "unknown_type", "name": "anything"},
        ],
    }
    result = architecture_validator_service.validate_naming(arch)
    assert result["valid"] is True


# ---------------------------------------------------------------------------
# Full validation
# ---------------------------------------------------------------------------


def test_validate_full_minimal_valid():
    arch = {
        "region": "eastus",
        "resources": [],
        "network_topology": {},
    }
    result = architecture_validator_service.validate_full(arch)
    assert result["valid"] is True


def test_validate_full_with_workload():
    arch = {
        "region": "eastus",
        "services": [{"name": "Azure Machine Learning"}, {"name": "Azure Storage"}],
        "network_topology": {"private_endpoints": True},
        "resources": [],
    }
    result = architecture_validator_service.validate_full(arch, workload_type="ai_ml")
    assert result["valid"] is True


def test_validate_full_with_compliance():
    arch = {
        "region": "eastus",
        "compliance_frameworks": ["soc2"],
        "security": {
            "encryption_at_rest": True,
            "centralized_logging": True,
            "mfa_enabled": True,
        },
        "network_topology": {"segmentation": True},
        "resources": [],
    }
    result = architecture_validator_service.validate_full(arch)
    assert result["valid"] is True


def test_validate_full_aggregates_errors():
    arch = {
        "region": "brazilsouth",
        "resources": [{"sku": "Standard_NC6s_v3"}],
        "compliance_frameworks": ["hipaa"],
        "security": {},
        "network_topology": {
            "type": "hub_spoke",
            "hubs": [],
        },
    }
    result = architecture_validator_service.validate_full(arch)
    assert result["valid"] is False
    assert len(result["errors"]) >= 3


def test_get_validation_rules():
    rules = architecture_validator_service.get_validation_rules()
    assert isinstance(rules, list)
    assert len(rules) >= 8
    assert all("id" in r and "severity" in r for r in rules)
