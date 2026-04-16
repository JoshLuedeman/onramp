"""Centralized IaC provider and API version pinning registry.

Provides a single source of truth for recommended provider versions,
SDK versions, and Azure API versions used across all OnRamp IaC generators
(Terraform, Pulumi, ARM, Bicep).

Uses a singleton pattern so every generator and route shares the same
registry instance.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Literal

from app.schemas.version_pinning import (
    ApiVersion,
    ProviderVersion,
    VersionFreshnessItem,
    VersionReport,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Staleness threshold (days). Versions older than this trigger a warning.
# ---------------------------------------------------------------------------
STALENESS_THRESHOLD_DAYS = 180

# ---------------------------------------------------------------------------
# Terraform provider versions
# ---------------------------------------------------------------------------
_TERRAFORM_CLI_VERSION = ">= 1.5.0"

_TERRAFORM_PROVIDERS: list[dict] = [
    {
        "name": "azurerm",
        "source": "hashicorp/azurerm",
        "version_constraint": "~> 3.100",
        "release_date": "2024-03-15",
        "notes": "Azure Resource Manager provider",
    },
    {
        "name": "azapi",
        "source": "azure/azapi",
        "version_constraint": "~> 1.12",
        "release_date": "2024-02-20",
        "notes": "Azure API provider for preview/unstable resources",
    },
    {
        "name": "random",
        "source": "hashicorp/random",
        "version_constraint": "~> 3.6",
        "release_date": "2024-01-10",
        "notes": "Random value generation for naming",
    },
    {
        "name": "azuread",
        "source": "hashicorp/azuread",
        "version_constraint": "~> 2.47",
        "release_date": "2024-02-01",
        "notes": "Azure Active Directory provider",
    },
    {
        "name": "null",
        "source": "hashicorp/null",
        "version_constraint": "~> 3.2",
        "release_date": "2023-10-15",
        "notes": "Null resource for provisioners",
    },
    {
        "name": "local",
        "source": "hashicorp/local",
        "version_constraint": "~> 2.5",
        "release_date": "2024-01-05",
        "notes": "Local file and resource management",
    },
]

# ---------------------------------------------------------------------------
# Pulumi SDK versions
# ---------------------------------------------------------------------------
_PULUMI_TYPESCRIPT_PACKAGES: list[dict] = [
    {
        "name": "@pulumi/pulumi",
        "source": "npm",
        "version_constraint": "3.110.0",
        "release_date": "2024-03-01",
        "notes": "Core Pulumi SDK for TypeScript",
    },
    {
        "name": "@pulumi/azure-native",
        "source": "npm",
        "version_constraint": "2.35.0",
        "release_date": "2024-03-10",
        "notes": "Azure Native provider for Pulumi",
    },
    {
        "name": "@pulumi/azuread",
        "source": "npm",
        "version_constraint": "5.47.0",
        "release_date": "2024-02-15",
        "notes": "Azure AD provider for Pulumi",
    },
    {
        "name": "@pulumi/random",
        "source": "npm",
        "version_constraint": "4.16.0",
        "release_date": "2024-01-20",
        "notes": "Random resource provider",
    },
]

_PULUMI_PYTHON_PACKAGES: list[dict] = [
    {
        "name": "pulumi",
        "source": "pypi",
        "version_constraint": "3.110.0",
        "release_date": "2024-03-01",
        "notes": "Core Pulumi SDK for Python",
    },
    {
        "name": "pulumi-azure-native",
        "source": "pypi",
        "version_constraint": "2.35.0",
        "release_date": "2024-03-10",
        "notes": "Azure Native provider for Pulumi",
    },
    {
        "name": "pulumi-azuread",
        "source": "pypi",
        "version_constraint": "5.47.0",
        "release_date": "2024-02-15",
        "notes": "Azure AD provider for Pulumi",
    },
    {
        "name": "pulumi-random",
        "source": "pypi",
        "version_constraint": "4.16.0",
        "release_date": "2024-01-20",
        "notes": "Random resource provider",
    },
]

# ---------------------------------------------------------------------------
# ARM / Bicep API versions per resource type
# ---------------------------------------------------------------------------
_ARM_API_VERSIONS: list[dict] = [
    {
        "resource_type": "Microsoft.Resources/resourceGroups",
        "api_version": "2024-03-01",
        "release_date": "2024-03-01",
        "notes": "Resource group management",
    },
    {
        "resource_type": "Microsoft.Network/virtualNetworks",
        "api_version": "2023-09-01",
        "release_date": "2023-09-01",
        "notes": "Virtual network and subnets",
    },
    {
        "resource_type": "Microsoft.Network/networkSecurityGroups",
        "api_version": "2023-09-01",
        "release_date": "2023-09-01",
        "notes": "Network security groups",
    },
    {
        "resource_type": "Microsoft.Network/publicIPAddresses",
        "api_version": "2023-09-01",
        "release_date": "2023-09-01",
        "notes": "Public IP addresses",
    },
    {
        "resource_type": "Microsoft.Network/loadBalancers",
        "api_version": "2023-09-01",
        "release_date": "2023-09-01",
        "notes": "Load balancers",
    },
    {
        "resource_type": "Microsoft.Network/applicationGateways",
        "api_version": "2023-09-01",
        "release_date": "2023-09-01",
        "notes": "Application gateways / WAF",
    },
    {
        "resource_type": "Microsoft.Network/azureFirewalls",
        "api_version": "2023-09-01",
        "release_date": "2023-09-01",
        "notes": "Azure Firewall",
    },
    {
        "resource_type": "Microsoft.Network/privateDnsZones",
        "api_version": "2020-06-01",
        "release_date": "2020-06-01",
        "notes": "Private DNS zones",
    },
    {
        "resource_type": "Microsoft.Compute/virtualMachines",
        "api_version": "2024-03-01",
        "release_date": "2024-03-01",
        "notes": "Virtual machines",
    },
    {
        "resource_type": "Microsoft.ContainerService/managedClusters",
        "api_version": "2024-02-01",
        "release_date": "2024-02-01",
        "notes": "AKS managed clusters",
    },
    {
        "resource_type": "Microsoft.Storage/storageAccounts",
        "api_version": "2023-05-01",
        "release_date": "2023-05-01",
        "notes": "Storage accounts",
    },
    {
        "resource_type": "Microsoft.KeyVault/vaults",
        "api_version": "2023-07-01",
        "release_date": "2023-07-01",
        "notes": "Key Vault",
    },
    {
        "resource_type": "Microsoft.Sql/servers",
        "api_version": "2023-08-01-preview",
        "release_date": "2023-08-01",
        "notes": "Azure SQL servers",
    },
    {
        "resource_type": "Microsoft.Web/sites",
        "api_version": "2023-12-01",
        "release_date": "2023-12-01",
        "notes": "App Service / Function Apps",
    },
    {
        "resource_type": "Microsoft.ManagedIdentity/userAssignedIdentities",
        "api_version": "2023-01-31",
        "release_date": "2023-01-31",
        "notes": "User-assigned managed identities",
    },
    {
        "resource_type": "Microsoft.Authorization/roleAssignments",
        "api_version": "2022-04-01",
        "release_date": "2022-04-01",
        "notes": "RBAC role assignments",
    },
    {
        "resource_type": "Microsoft.OperationalInsights/workspaces",
        "api_version": "2023-09-01",
        "release_date": "2023-09-01",
        "notes": "Log Analytics workspaces",
    },
    {
        "resource_type": "Microsoft.Insights/diagnosticSettings",
        "api_version": "2021-05-01-preview",
        "release_date": "2021-05-01",
        "notes": "Diagnostic settings",
    },
    {
        "resource_type": "Microsoft.Security/pricings",
        "api_version": "2024-01-01",
        "release_date": "2024-01-01",
        "notes": "Defender for Cloud pricing tiers",
    },
    {
        "resource_type": "Microsoft.App/managedEnvironments",
        "api_version": "2024-03-01",
        "release_date": "2024-03-01",
        "notes": "Container Apps managed environments",
    },
]

# Bicep uses the same API versions as ARM by default. A separate registry
# allows overrides when Bicep-specific preview API versions differ.
_BICEP_API_OVERRIDES: dict[str, dict] = {
    # Example override — uncomment to diverge from ARM:
    # "Microsoft.App/managedEnvironments": {
    #     "api_version": "2024-08-02-preview",
    #     "release_date": "2024-08-02",
    #     "notes": "Bicep preview API for Container Apps",
    # },
}

# Default API version when a resource type is not found in the registry.
_DEFAULT_API_VERSION = "2023-09-01"
_DEFAULT_RELEASE_DATE = "2023-09-01"


class VersionPinningService:
    """Singleton service providing pinned IaC versions for all generators.

    Usage::

        from app.services.version_pinning import version_pinning

        providers = version_pinning.get_terraform_providers()
        api_ver = version_pinning.get_arm_api_version(
            "Microsoft.Network/virtualNetworks"
        )
    """

    _instance: VersionPinningService | None = None

    def __new__(cls) -> VersionPinningService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # -- Terraform ----------------------------------------------------------

    @property
    def terraform_cli_version(self) -> str:
        """Return the minimum required Terraform CLI version constraint."""
        return _TERRAFORM_CLI_VERSION

    def get_terraform_providers(self) -> list[ProviderVersion]:
        """Return recommended Terraform provider versions."""
        return [ProviderVersion(**p) for p in _TERRAFORM_PROVIDERS]

    def get_terraform_provider(self, name: str) -> ProviderVersion | None:
        """Look up a single Terraform provider by name."""
        for p in _TERRAFORM_PROVIDERS:
            if p["name"] == name:
                return ProviderVersion(**p)
        return None

    # -- Pulumi -------------------------------------------------------------

    def get_pulumi_versions(
        self, language: Literal["typescript", "python"]
    ) -> list[ProviderVersion]:
        """Return recommended Pulumi SDK versions for the given language."""
        if language == "typescript":
            return [ProviderVersion(**p) for p in _PULUMI_TYPESCRIPT_PACKAGES]
        if language == "python":
            return [ProviderVersion(**p) for p in _PULUMI_PYTHON_PACKAGES]
        raise ValueError(
            f"Unsupported Pulumi language '{language}'. "
            "Supported: typescript, python"
        )

    # -- ARM ----------------------------------------------------------------

    def get_arm_api_versions(self) -> list[ApiVersion]:
        """Return all recommended ARM API versions."""
        return [ApiVersion(**v) for v in _ARM_API_VERSIONS]

    def get_arm_api_version(self, resource_type: str) -> str:
        """Return the recommended ARM API version for a resource type.

        Falls back to a sensible default when the type is unknown.
        """
        for v in _ARM_API_VERSIONS:
            if v["resource_type"].lower() == resource_type.lower():
                return v["api_version"]
        logger.debug(
            "No pinned ARM API version for %s; using default %s",
            resource_type,
            _DEFAULT_API_VERSION,
        )
        return _DEFAULT_API_VERSION

    # -- Bicep --------------------------------------------------------------

    def get_bicep_api_versions(self) -> list[ApiVersion]:
        """Return all recommended Bicep API versions.

        Uses ARM versions as the base, with Bicep-specific overrides applied.
        """
        results: list[ApiVersion] = []
        for v in _ARM_API_VERSIONS:
            rt = v["resource_type"]
            if rt in _BICEP_API_OVERRIDES:
                override = _BICEP_API_OVERRIDES[rt]
                results.append(
                    ApiVersion(
                        resource_type=rt,
                        api_version=override["api_version"],
                        release_date=override["release_date"],
                        notes=override.get("notes", ""),
                    )
                )
            else:
                results.append(ApiVersion(**v))
        return results

    def get_bicep_api_version(self, resource_type: str) -> str:
        """Return the recommended Bicep API version for a resource type.

        Checks Bicep-specific overrides first, then falls back to ARM versions.
        """
        rt_lower = resource_type.lower()
        # Check overrides first
        for rt, override in _BICEP_API_OVERRIDES.items():
            if rt.lower() == rt_lower:
                return override["api_version"]
        # Fall back to ARM registry
        return self.get_arm_api_version(resource_type)

    # -- Freshness / Reporting ----------------------------------------------

    def check_freshness(
        self,
        release_date_str: str,
        threshold_days: int = STALENESS_THRESHOLD_DAYS,
    ) -> tuple[int, bool]:
        """Return (age_days, is_stale) for a release date string.

        Args:
            release_date_str: ISO-8601 date string (YYYY-MM-DD).
            threshold_days: Number of days after which a version is stale.

        Returns:
            Tuple of (age in days, whether it exceeds the threshold).
        """
        release = date.fromisoformat(release_date_str)
        today = datetime.now(timezone.utc).date()
        age = (today - release).days
        return age, age > threshold_days

    def _build_freshness_items(
        self,
        entries: list[ProviderVersion] | list[ApiVersion],
        threshold_days: int,
    ) -> list[VersionFreshnessItem]:
        """Build freshness items from a list of provider or API versions."""
        items: list[VersionFreshnessItem] = []
        for entry in entries:
            if isinstance(entry, ProviderVersion):
                name = entry.name
                version = entry.version_constraint
                rd = entry.release_date
            else:
                name = entry.resource_type
                version = entry.api_version
                rd = entry.release_date
            age_days, is_stale = self.check_freshness(rd, threshold_days)
            items.append(
                VersionFreshnessItem(
                    name=name,
                    version=version,
                    release_date=rd,
                    age_days=age_days,
                    is_stale=is_stale,
                )
            )
        return items

    def get_version_report(
        self, threshold_days: int = STALENESS_THRESHOLD_DAYS
    ) -> VersionReport:
        """Generate a full version freshness report across all IaC formats."""
        tf = self._build_freshness_items(
            self.get_terraform_providers(), threshold_days
        )
        pulumi_ts = self._build_freshness_items(
            self.get_pulumi_versions("typescript"), threshold_days
        )
        pulumi_py = self._build_freshness_items(
            self.get_pulumi_versions("python"), threshold_days
        )
        arm = self._build_freshness_items(
            self.get_arm_api_versions(), threshold_days
        )
        bicep = self._build_freshness_items(
            self.get_bicep_api_versions(), threshold_days
        )

        all_items = tf + pulumi_ts + pulumi_py + arm + bicep
        stale_count = sum(1 for item in all_items if item.is_stale)

        if stale_count:
            logger.warning(
                "%d of %d version entries are stale (>%d days old)",
                stale_count,
                len(all_items),
                threshold_days,
            )

        return VersionReport(
            staleness_threshold_days=threshold_days,
            terraform=tf,
            pulumi_typescript=pulumi_ts,
            pulumi_python=pulumi_py,
            arm=arm,
            bicep=bicep,
            total_entries=len(all_items),
            stale_count=stale_count,
        )


# Module-level singleton
version_pinning = VersionPinningService()
