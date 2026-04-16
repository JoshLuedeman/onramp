"""Cloud configuration service.

Provides helpers for resolving cloud-specific endpoints, metadata,
and validating service availability across Azure sovereign clouds.
"""

import logging

from app.models.cloud_environment import (
    CLOUD_ENDPOINTS,
    CloudEndpoints,
    CloudEnvironment,
)

logger = logging.getLogger(__name__)

# ── Metadata per environment ─────────────────────────────────────────────

_ENVIRONMENT_METADATA: dict[CloudEnvironment, dict] = {
    CloudEnvironment.COMMERCIAL: {
        "display_name": "Azure Commercial",
        "description": "Global Azure public cloud for commercial workloads",
        "regions": [
            "eastus",
            "eastus2",
            "westus",
            "westus2",
            "westus3",
            "centralus",
            "northeurope",
            "westeurope",
            "southeastasia",
            "eastasia",
            "japaneast",
            "australiaeast",
            "brazilsouth",
            "uksouth",
            "canadacentral",
        ],
        "restrictions": [],
    },
    CloudEnvironment.GOVERNMENT: {
        "display_name": "Azure Government",
        "description": (
            "Dedicated cloud for US government agencies and their partners"
        ),
        "regions": [
            "usgovvirginia",
            "usgovtexas",
            "usgovarizona",
            "usdodeast",
            "usdodcentral",
        ],
        "restrictions": [
            "Requires US government entity or sponsored partner",
            "FedRAMP High / DoD IL4-IL5 compliant",
            "AI Foundry services are not available",
        ],
    },
    CloudEnvironment.CHINA: {
        "display_name": "Azure China (21Vianet)",
        "description": (
            "Azure operated by 21Vianet for workloads in mainland China"
        ),
        "regions": [
            "chinaeast",
            "chinaeast2",
            "chinanorth",
            "chinanorth2",
            "chinanorth3",
        ],
        "restrictions": [
            "Operated by 21Vianet; separate identity and billing",
            "Requires a China-specific Azure subscription",
            "AI Foundry services are not available",
        ],
    },
}

# ── Service availability matrix ──────────────────────────────────────────

_SERVICE_AVAILABILITY: dict[CloudEnvironment, set[str]] = {
    CloudEnvironment.COMMERCIAL: {
        "compute",
        "storage",
        "sql",
        "keyvault",
        "ai_foundry",
        "cognitive_services",
        "app_service",
        "container_apps",
        "kubernetes",
        "functions",
        "cosmos_db",
        "redis",
        "service_bus",
        "event_grid",
        "monitor",
        "defender",
    },
    CloudEnvironment.GOVERNMENT: {
        "compute",
        "storage",
        "sql",
        "keyvault",
        "app_service",
        "container_apps",
        "kubernetes",
        "functions",
        "cosmos_db",
        "redis",
        "service_bus",
        "monitor",
        "defender",
    },
    CloudEnvironment.CHINA: {
        "compute",
        "storage",
        "sql",
        "keyvault",
        "app_service",
        "kubernetes",
        "functions",
        "cosmos_db",
        "redis",
        "monitor",
    },
}


class CloudConfigService:
    """Singleton service for cloud environment configuration.

    Provides endpoints, metadata, and service-availability checks for
    each supported Azure sovereign cloud.
    """

    def get_endpoints(self, env: CloudEnvironment) -> CloudEndpoints:
        """Return the service endpoints for *env*.

        Args:
            env: Target cloud environment.

        Returns:
            :class:`CloudEndpoints` with all URLs for the environment.
        """
        return CLOUD_ENDPOINTS[env]

    def get_default_environment(self) -> CloudEnvironment:
        """Return the default cloud environment.

        Returns:
            :data:`CloudEnvironment.COMMERCIAL` (the global public cloud).
        """
        return CloudEnvironment.COMMERCIAL

    def get_available_environments(self) -> list[CloudEnvironment]:
        """Return every supported cloud environment.

        Returns:
            A list of all :class:`CloudEnvironment` members.
        """
        return list(CloudEnvironment)

    def get_environment_metadata(self, env: CloudEnvironment) -> dict:
        """Return descriptive metadata for *env*.

        Args:
            env: Target cloud environment.

        Returns:
            A dict with ``display_name``, ``description``, ``regions``,
            and ``restrictions`` keys.
        """
        return _ENVIRONMENT_METADATA[env]

    def validate_environment_support(
        self,
        env: CloudEnvironment,
        required_services: list[str],
    ) -> dict:
        """Check whether *env* supports all *required_services*.

        Args:
            env: Target cloud environment.
            required_services: Service identifiers to check.

        Returns:
            A dict with ``supported`` (bool), ``missing_services``
            (list of unsupported service names), and ``warnings``
            (advisory messages).
        """
        available = _SERVICE_AVAILABILITY.get(env, set())
        missing = [s for s in required_services if s not in available]

        warnings: list[str] = []
        if env != CloudEnvironment.COMMERCIAL and not missing:
            warnings.append(
                f"Some features may have limited availability in "
                f"{_ENVIRONMENT_METADATA[env]['display_name']}"
            )

        return {
            "supported": len(missing) == 0,
            "missing_services": missing,
            "warnings": warnings,
        }


cloud_config_service = CloudConfigService()
