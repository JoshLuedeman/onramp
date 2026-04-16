"""Azure China (21Vianet) Bicep template customizer.

Transforms standard Azure Bicep templates for deployment in Azure China
by replacing endpoints, injecting compliance tags, and handling service
substitutions required by the 21Vianet-operated cloud.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── Endpoint Mapping ─────────────────────────────────────────────────────────

_ENDPOINT_REPLACEMENTS: list[tuple[str, str]] = [
    ("management.azure.com", "management.chinacloudapi.cn"),
    ("login.microsoftonline.com", "login.chinacloudapi.cn"),
    ("graph.microsoft.com", "microsoftgraph.chinacloudapi.cn"),
    ("portal.azure.com", "portal.azure.cn"),
    (".blob.core.windows.net", ".blob.core.chinacloudapi.cn"),
    (".queue.core.windows.net", ".queue.core.chinacloudapi.cn"),
    (".table.core.windows.net", ".table.core.chinacloudapi.cn"),
    (".file.core.windows.net", ".file.core.chinacloudapi.cn"),
    (".database.windows.net", ".database.chinacloudapi.cn"),
    (".vault.azure.net", ".vault.azure.cn"),
    (".azurecr.io", ".azurecr.cn"),
    (".servicebus.windows.net", ".servicebus.chinacloudapi.cn"),
    (".azurewebsites.net", ".chinacloudsites.cn"),
]

# ── Service Mapping ──────────────────────────────────────────────────────────

_CHINA_SERVICE_MAPPING: dict[str, dict] = {
    "Azure Active Directory": {
        "china_equivalent": "Azure AD (China)",
        "endpoint": "login.chinacloudapi.cn",
        "notes": "Separate tenant; no federation with global Azure AD",
    },
    "Azure Front Door": {
        "china_equivalent": "Application Gateway with WAF",
        "endpoint": None,
        "notes": "Azure Front Door is not available in Azure China",
    },
    "Azure DevOps": {
        "china_equivalent": "GitHub or self-hosted CI/CD",
        "endpoint": None,
        "notes": "Azure DevOps is not available in Azure China",
    },
    "Microsoft Defender for Cloud": {
        "china_equivalent": "Third-party CSPM or manual monitoring",
        "endpoint": None,
        "notes": "Defender for Cloud is not available in Azure China",
    },
    "Microsoft Sentinel": {
        "china_equivalent": "Azure Monitor with custom alerts",
        "endpoint": None,
        "notes": "Microsoft Sentinel is not available in Azure China",
    },
    "Azure OpenAI Service": {
        "china_equivalent": "Partner AI services or self-hosted models",
        "endpoint": None,
        "notes": "Azure OpenAI is not available in Azure China",
    },
    "Container Apps": {
        "china_equivalent": "Azure Kubernetes Service",
        "endpoint": None,
        "notes": "Container Apps is not available in Azure China",
    },
}

# ── MLPS Tags ────────────────────────────────────────────────────────────────

_MLPS_TAGS: dict[str, dict[str, str]] = {
    "mlps2": {
        "compliance-framework": "MLPS-Level-2",
        "data-classification": "general",
        "security-level": "standard",
    },
    "mlps3": {
        "compliance-framework": "MLPS-Level-3",
        "data-classification": "important",
        "security-level": "enhanced",
    },
    "mlps4": {
        "compliance-framework": "MLPS-Level-4",
        "data-classification": "critical",
        "security-level": "high",
    },
}

# ── ICP Requirements ─────────────────────────────────────────────────────────

_ICP_RESOURCE_TYPES: list[str] = [
    "Microsoft.Web/sites",
    "Microsoft.Cdn/profiles",
    "Microsoft.Network/applicationGateways",
    "Microsoft.Network/frontDoors",
    "Microsoft.ApiManagement/service",
    "Microsoft.Network/publicIPAddresses",
]


# ── Service ──────────────────────────────────────────────────────────────────


class ChinaBicepService:
    """Transforms Bicep templates for Azure China (21Vianet) deployment.

    Handles endpoint replacement, compliance tagging, service substitution,
    and ICP license requirement identification.
    """

    def customize_for_china(
        self,
        bicep_content: str,
        region: str,
        compliance_level: str = "mlps3",
    ) -> str:
        """Transform a Bicep template for China cloud deployment.

        Args:
            bicep_content: Original Bicep template content.
            region: Target Azure China region (e.g. ``chinanorth2``).
            compliance_level: MLPS compliance tier (``mlps2``, ``mlps3``,
                or ``mlps4``).

        Returns:
            The transformed Bicep template as a string.
        """
        result = bicep_content

        # Replace commercial endpoints with China equivalents
        for commercial, china in _ENDPOINT_REPLACEMENTS:
            result = result.replace(commercial, china)

        # Add 21Vianet environment property
        result = self._add_environment_property(result, region)

        # Inject MLPS compliance tags
        result = self.add_mlps_tags(result, compliance_level)

        return result

    def get_china_service_mapping(self) -> dict:
        """Return the mapping of commercial services to China equivalents.

        Returns:
            A dict keyed by commercial service name, with values
            containing ``china_equivalent``, ``endpoint``, and ``notes``.
        """
        return dict(_CHINA_SERVICE_MAPPING)

    def add_mlps_tags(
        self,
        bicep_content: str,
        compliance_level: str = "mlps3",
    ) -> str:
        """Inject MLPS compliance tags into Bicep resource blocks.

        Args:
            bicep_content: Bicep template content.
            compliance_level: One of ``mlps2``, ``mlps3``, ``mlps4``.

        Returns:
            Bicep content with MLPS tags injected into ``tags:`` blocks.
        """
        level_key = compliance_level.lower().replace("-", "").replace("_", "")
        tags = _MLPS_TAGS.get(level_key, _MLPS_TAGS["mlps3"])

        tag_lines = "\n".join(
            f"    '{k}': '{v}'" for k, v in tags.items()
        )
        tag_block = f"  tags: {{\n{tag_lines}\n  }}"

        # If there are existing tags blocks, append our tags to them
        if "tags:" in bicep_content:
            pattern = r"(tags:\s*\{)"
            replacement = (
                "tags: {\n"
                + "\n".join(f"    '{k}': '{v}'" for k, v in tags.items())
                + "\n"
            )
            result = re.sub(pattern, replacement, bicep_content)
            return result

        # If no tags block exists, add one before closing braces of resources
        if "resource " in bicep_content:
            # Add tags block before the last closing brace of each resource
            result = re.sub(
                r"(resource\s+\w+\s+'[^']+'\s*=\s*\{)",
                rf"\1\n{tag_block}",
                bicep_content,
            )
            return result

        return bicep_content

    def get_icp_requirements(self, architecture: dict) -> dict:
        """Identify resources in an architecture that need an ICP license.

        An ICP (Internet Content Provider) license is required for any
        web-facing resource hosted in mainland China.

        Args:
            architecture: Architecture dict with a ``resources`` list
                containing dicts that have a ``type`` key.

        Returns:
            A dict with ``requires_icp``, ``affected_resources``, and
            ``guidance``.
        """
        resources = architecture.get("resources", [])
        if not isinstance(resources, list):
            resources = []

        affected: list[str] = []
        for resource in resources:
            resource_type = resource.get("type", "")
            if resource_type in _ICP_RESOURCE_TYPES:
                affected.append(resource_type)

        return {
            "requires_icp": len(affected) > 0,
            "affected_resources": affected,
            "resource_types_checked": len(resources),
            "guidance": (
                "An ICP license (ICP备案) is required for any website or "
                "web-facing service hosted in mainland China. Apply through "
                "21Vianet's ICP filing portal before deploying public endpoints."
                if affected
                else "No web-facing resources detected; ICP license may not be required."
            ),
            "icp_types": [
                {
                    "type": "ICP Filing (ICP备案)",
                    "description": "Required for all websites hosted in China",
                    "applies_to": "informational websites",
                },
                {
                    "type": "ICP Commercial License (ICP经营许可证)",
                    "description": "Required for commercial online services",
                    "applies_to": "e-commerce, SaaS, paid services",
                },
            ],
        }

    def get_data_residency_config(self) -> dict:
        """Return data residency configuration for Bicep deployments.

        Returns:
            A dict with allowed regions, storage replication policies,
            and backup constraints for China deployments.
        """
        return {
            "allowed_regions": [
                "chinanorth",
                "chinanorth2",
                "chinanorth3",
                "chinaeast",
                "chinaeast2",
                "chinaeast3",
            ],
            "storage_replication": {
                "allowed": ["LRS", "ZRS", "GRS", "RA-GRS"],
                "geo_pairs_only": True,
                "note": (
                    "Geo-replication stays within mainland China "
                    "paired regions"
                ),
            },
            "backup_policy": {
                "cross_region_restore": True,
                "geo_restriction": "mainland_china_only",
                "note": "Backups must remain within mainland China",
            },
            "sql_geo_replication": {
                "allowed_secondary_regions": [
                    "chinanorth",
                    "chinanorth2",
                    "chinanorth3",
                    "chinaeast",
                    "chinaeast2",
                    "chinaeast3",
                ],
                "note": "SQL geo-replication is restricted to China regions",
            },
        }

    # ── Private Helpers ──────────────────────────────────────────────────

    def _add_environment_property(
        self, bicep_content: str, region: str
    ) -> str:
        """Insert the 21Vianet cloud environment and region metadata."""
        header = (
            f"// Azure China (21Vianet) - Region: {region}\n"
            f"// Operator: 21Vianet (Shanghai Blue Cloud Technology)\n"
            f"// Environment: AzureChinaCloud\n\n"
        )
        return header + bicep_content


# Singleton
china_bicep_service = ChinaBicepService()
