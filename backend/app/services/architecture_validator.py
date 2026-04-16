"""Architecture validation service.

Validates landing-zone architectures against workload requirements, cloud
constraints, compliance frameworks, networking rules and naming conventions.
"""

import logging
import re
from typing import Any

from app.services.sku_database import sku_database_service
from app.services.workload_extensions import workload_registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validation rule catalogue
# ---------------------------------------------------------------------------

VALIDATION_RULES: list[dict[str, Any]] = [
    {
        "id": "sku_availability",
        "category": "sku",
        "description": "All referenced SKUs must be available in the target region and cloud.",
        "severity": "error",
    },
    {
        "id": "compliance_encryption",
        "category": "compliance",
        "description": "Encryption at rest must be enabled for regulated frameworks.",
        "severity": "error",
    },
    {
        "id": "compliance_logging",
        "category": "compliance",
        "description": "Centralized logging must be enabled for compliance frameworks.",
        "severity": "error",
    },
    {
        "id": "compliance_mfa",
        "category": "compliance",
        "description": "MFA must be enforced for administrative access.",
        "severity": "error",
    },
    {
        "id": "network_hub_spoke",
        "category": "networking",
        "description": "Hub-spoke topology must define at least one hub VNet.",
        "severity": "error",
    },
    {
        "id": "network_dns",
        "category": "networking",
        "description": "Custom DNS should be configured for hybrid environments.",
        "severity": "warning",
    },
    {
        "id": "network_nsg",
        "category": "networking",
        "description": "Every spoke VNet should have an NSG attached.",
        "severity": "warning",
    },
    {
        "id": "naming_convention",
        "category": "naming",
        "description": "Resource names should follow Azure naming conventions.",
        "severity": "warning",
    },
    {
        "id": "naming_length",
        "category": "naming",
        "description": "Resource names must not exceed Azure length limits.",
        "severity": "error",
    },
    {
        "id": "workload_specific",
        "category": "workload",
        "description": "Architecture must satisfy workload-specific requirements.",
        "severity": "error",
    },
]

# Compliance requirements per framework
COMPLIANCE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "soc2": {
        "encryption_at_rest": True,
        "centralized_logging": True,
        "mfa_required": True,
        "network_segmentation": True,
    },
    "hipaa": {
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "centralized_logging": True,
        "mfa_required": True,
        "audit_trail": True,
    },
    "pci_dss": {
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "centralized_logging": True,
        "mfa_required": True,
        "network_segmentation": True,
        "waf_required": True,
    },
    "fedramp_high": {
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "centralized_logging": True,
        "mfa_required": True,
        "fips_140_2": True,
    },
    "nist_800_53": {
        "encryption_at_rest": True,
        "centralized_logging": True,
        "mfa_required": True,
        "continuous_monitoring": True,
    },
}

# Azure naming convention patterns
NAMING_PATTERNS: dict[str, dict[str, Any]] = {
    "resource_group": {
        "pattern": r"^rg-[a-z0-9\-]{1,85}$",
        "max_length": 90,
        "example": "rg-myapp-prod-eastus",
    },
    "virtual_network": {
        "pattern": r"^vnet-[a-z0-9\-]{1,59}$",
        "max_length": 64,
        "example": "vnet-hub-eastus",
    },
    "subnet": {
        "pattern": r"^snet-[a-z0-9\-]{1,76}$",
        "max_length": 80,
        "example": "snet-app-tier",
    },
    "storage_account": {
        "pattern": r"^st[a-z0-9]{1,22}$",
        "max_length": 24,
        "example": "stmyappprod",
    },
    "key_vault": {
        "pattern": r"^kv-[a-z0-9\-]{1,20}$",
        "max_length": 24,
        "example": "kv-myapp-prod",
    },
}


class ArchitectureValidatorService:
    """Validates architectures against rules, compliance and cloud constraints.

    Provides granular and full-architecture validation methods.
    """

    # -- SKU validation ---------------------------------------------------

    def validate_skus(
        self, architecture: dict[str, Any], region: str
    ) -> dict[str, Any]:
        """Validate that all SKUs in an architecture are available.

        Args:
            architecture: Architecture dict with optional ``resources`` list.
            region: Target Azure region.

        Returns:
            Dict with ``valid``, ``errors``, ``warnings``.
        """
        errors: list[str] = []
        warnings: list[str] = []
        cloud_env = architecture.get("cloud_environment", "commercial")

        resources = architecture.get("resources", [])
        for resource in resources:
            sku_name = resource.get("sku") if isinstance(resource, dict) else None
            if not sku_name:
                continue
            result = sku_database_service.validate_sku_availability(
                sku_name, region, cloud_env
            )
            if not result["available"]:
                errors.append(result.get("reason", f"SKU {sku_name} not available."))

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    # -- Compliance validation --------------------------------------------

    def validate_compliance(
        self, architecture: dict[str, Any], framework: str
    ) -> dict[str, Any]:
        """Validate architecture meets a compliance framework's requirements.

        Args:
            architecture: Architecture dict with ``security`` section.
            framework: Compliance framework key (e.g. ``soc2``).

        Returns:
            Dict with ``valid``, ``errors``, ``warnings``, ``framework``.
        """
        errors: list[str] = []
        warnings: list[str] = []

        requirements = COMPLIANCE_REQUIREMENTS.get(framework)
        if not requirements:
            return {
                "valid": True,
                "errors": [],
                "warnings": [f"Unknown compliance framework: {framework}"],
                "framework": framework,
            }

        security = architecture.get("security", {})

        if requirements.get("encryption_at_rest") and not security.get("encryption_at_rest"):
            errors.append(f"{framework}: Encryption at rest is required.")

        if requirements.get("encryption_in_transit") and not security.get("encryption_in_transit"):
            errors.append(f"{framework}: Encryption in transit is required.")

        if requirements.get("centralized_logging") and not security.get("centralized_logging"):
            errors.append(f"{framework}: Centralized logging is required.")

        if requirements.get("mfa_required") and not security.get("mfa_enabled"):
            errors.append(f"{framework}: MFA must be enforced.")

        if requirements.get("network_segmentation"):
            network = architecture.get("network_topology", {})
            if not network.get("segmentation"):
                warnings.append(f"{framework}: Network segmentation is recommended.")

        if requirements.get("waf_required") and not security.get("waf_enabled"):
            errors.append(f"{framework}: Web Application Firewall is required.")

        if requirements.get("fips_140_2") and not security.get("fips_140_2"):
            errors.append(f"{framework}: FIPS 140-2 compliant encryption is required.")

        if requirements.get("audit_trail") and not security.get("audit_trail"):
            warnings.append(f"{framework}: Audit trail is recommended.")

        if requirements.get("continuous_monitoring") and not security.get("continuous_monitoring"):
            warnings.append(f"{framework}: Continuous monitoring is recommended.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "framework": framework,
        }

    # -- Networking validation --------------------------------------------

    def validate_networking(self, architecture: dict[str, Any]) -> dict[str, Any]:
        """Validate networking configuration of an architecture.

        Args:
            architecture: Architecture dict with ``network_topology``.

        Returns:
            Dict with ``valid``, ``errors``, ``warnings``, ``suggestions``.
        """
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        network = architecture.get("network_topology", {})
        if not network:
            return {
                "valid": True,
                "errors": [],
                "warnings": ["No network topology defined."],
                "suggestions": ["Define a network topology for production workloads."],
            }

        topology_type = network.get("type", "")

        # Hub-spoke checks
        if topology_type == "hub_spoke":
            hubs = network.get("hubs", [])
            if not hubs:
                errors.append("Hub-spoke topology requires at least one hub VNet.")
            spokes = network.get("spokes", [])
            for spoke in spokes:
                if isinstance(spoke, dict) and not spoke.get("nsg"):
                    warnings.append(
                        f"Spoke '{spoke.get('name', 'unknown')}' has no NSG attached."
                    )

        # DNS checks
        if network.get("hybrid_connectivity") and not network.get("custom_dns"):
            warnings.append("Custom DNS should be configured for hybrid connectivity.")

        # Peering checks
        peerings = network.get("peerings", [])
        for peering in peerings:
            if isinstance(peering, dict) and not peering.get("allow_forwarded_traffic"):
                suggestions.append(
                    f"Enable forwarded traffic on peering "
                    f"'{peering.get('name', 'unknown')}'."
                )

        # Firewall recommendation
        if topology_type == "hub_spoke" and not network.get("firewall"):
            suggestions.append("Consider Azure Firewall in the hub for centralized egress control.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    # -- Naming validation ------------------------------------------------

    def validate_naming(self, architecture: dict[str, Any]) -> dict[str, Any]:
        """Validate resource naming conventions.

        Args:
            architecture: Architecture dict with ``resources`` list.

        Returns:
            Dict with ``valid``, ``errors``, ``warnings``.
        """
        errors: list[str] = []
        warnings: list[str] = []

        resources = architecture.get("resources", [])
        for resource in resources:
            if not isinstance(resource, dict):
                continue
            rtype = resource.get("type", "")
            rname = resource.get("name", "")

            if not rname:
                continue

            pattern_info = NAMING_PATTERNS.get(rtype)
            if not pattern_info:
                continue

            max_len = pattern_info["max_length"]
            if len(rname) > max_len:
                errors.append(
                    f"Resource '{rname}' exceeds max length {max_len} for type {rtype}."
                )

            pattern = pattern_info["pattern"]
            if not re.match(pattern, rname):
                warnings.append(
                    f"Resource '{rname}' does not match naming convention for {rtype}. "
                    f"Example: {pattern_info['example']}"
                )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    # -- Full validation --------------------------------------------------

    def validate_full(
        self,
        architecture: dict[str, Any],
        workload_type: str | None = None,
        cloud_env: str = "commercial",
    ) -> dict[str, Any]:
        """Run all validation checks on an architecture.

        Args:
            architecture: Full architecture dict.
            workload_type: Optional workload type for workload-specific checks.
            cloud_env: Target cloud environment.

        Returns:
            Aggregated dict with ``valid``, ``errors``, ``warnings``,
            ``suggestions``.
        """
        all_errors: list[str] = []
        all_warnings: list[str] = []
        all_suggestions: list[str] = []

        # Inject cloud_env into architecture for downstream checks
        arch_copy = {**architecture, "cloud_environment": cloud_env}

        # SKU validation
        region = architecture.get("region", "eastus")
        sku_result = self.validate_skus(arch_copy, region)
        all_errors.extend(sku_result["errors"])
        all_warnings.extend(sku_result["warnings"])

        # Compliance validation
        frameworks = architecture.get("compliance_frameworks", [])
        for fw in frameworks:
            comp_result = self.validate_compliance(arch_copy, fw)
            all_errors.extend(comp_result["errors"])
            all_warnings.extend(comp_result["warnings"])

        # Networking validation
        net_result = self.validate_networking(arch_copy)
        all_errors.extend(net_result["errors"])
        all_warnings.extend(net_result["warnings"])
        all_suggestions.extend(net_result.get("suggestions", []))

        # Naming validation
        name_result = self.validate_naming(arch_copy)
        all_errors.extend(name_result["errors"])
        all_warnings.extend(name_result["warnings"])

        # Workload-specific validation
        if workload_type:
            wl_result = workload_registry.validate_for_workload(workload_type, arch_copy)
            all_errors.extend(wl_result.get("errors", []))
            all_warnings.extend(wl_result.get("warnings", []))
            all_suggestions.extend(wl_result.get("suggestions", []))

        return {
            "valid": len(all_errors) == 0,
            "errors": all_errors,
            "warnings": all_warnings,
            "suggestions": all_suggestions,
        }

    def get_validation_rules(self) -> list[dict[str, Any]]:
        """Return the full catalogue of validation rules.

        Returns:
            List of rule dicts with ``id``, ``category``, ``description``,
            ``severity``.
        """
        return VALIDATION_RULES


# Module-level singleton.
architecture_validator_service = ArchitectureValidatorService()
