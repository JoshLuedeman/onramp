"""Government Bicep template customizer.

Transforms standard Azure Bicep templates for Azure Government cloud by
replacing commercial endpoints, injecting FedRAMP compliance tags,
adding diagnostic settings, and mapping commercial SKUs to Government
equivalents.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ── Endpoint Replacements ────────────────────────────────────────────────────

_ENDPOINT_REPLACEMENTS: list[tuple[str, str]] = [
    ("management.azure.com", "management.usgovcloudapi.net"),
    ("login.microsoftonline.com", "login.microsoftonline.us"),
    ("graph.microsoft.com", "graph.microsoft.us"),
    ("portal.azure.com", "portal.azure.us"),
    (".blob.core.windows.net", ".blob.core.usgovcloudapi.net"),
    (".database.windows.net", ".database.usgovcloudapi.net"),
    (".vault.azure.net", ".vault.usgovcloudapi.net"),
    (".azurewebsites.net", ".azurewebsites.us"),
    (".azure-api.net", ".azure-api.us"),
]

# ── SKU Mapping (commercial → government) ────────────────────────────────────

_SKU_MAPPING: dict[str, str] = {
    "Standard_GRS": "Standard_LRS",
    "Standard_RAGRS": "Standard_LRS",
    "Premium_ZRS": "Premium_LRS",
    "Standard_GZRS": "Standard_LRS",
    "Standard_RAGZRS": "Standard_LRS",
}

# ── FedRAMP Tag Payloads ─────────────────────────────────────────────────────

_FEDRAMP_TAGS: dict[str, dict[str, str]] = {
    "high": {
        "fedramp_level": "High",
        "compliance_framework": "FedRAMP High",
        "data_classification": "Controlled Unclassified Information",
        "managed_by": "OnRamp",
    },
    "moderate": {
        "fedramp_level": "Moderate",
        "compliance_framework": "FedRAMP Moderate",
        "data_classification": "Low-Moderate Impact",
        "managed_by": "OnRamp",
    },
    "low": {
        "fedramp_level": "Low",
        "compliance_framework": "FedRAMP Low",
        "data_classification": "Low Impact",
        "managed_by": "OnRamp",
    },
}

# ── Diagnostic Settings Block ────────────────────────────────────────────────

_DIAGNOSTIC_SETTINGS_BLOCK = """
// FedRAMP required diagnostic settings
resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'fedramp-diagnostics'
  scope: resourceGroup()
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 365
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 365
        }
      }
    ]
  }
}
"""


class GovernmentBicepService:
    """Transforms standard Bicep templates for Azure Government cloud."""

    def customize_for_government(
        self,
        bicep_content: str,
        region: str,
        compliance_level: str = "high",
    ) -> str:
        """Apply all Government customizations to a Bicep template.

        Args:
            bicep_content: Raw Bicep template string.
            region: Target Government region (e.g. ``usgovvirginia``).
            compliance_level: FedRAMP level — ``high``, ``moderate``, or
                ``low``.

        Returns:
            Customized Bicep template string.
        """
        result = bicep_content

        # 1. Replace commercial endpoints with .us equivalents
        result = self._replace_endpoints(result)

        # 2. Add environment property for Government
        result = self._add_environment_property(result)

        # 3. Inject FedRAMP compliance tags
        result = self.add_fedramp_tags(result, compliance_level)

        # 4. Inject diagnostic settings for FedRAMP logging
        result = self.inject_diagnostic_settings(result)

        # 5. Replace commercial SKUs with Government-available equivalents
        result = self._replace_skus(result)

        # 6. Set location to the target region
        result = self._set_region(result, region)

        return result

    def get_government_sku_mapping(self) -> dict:
        """Return the mapping of commercial SKUs to Government equivalents.

        Returns:
            Dict mapping commercial SKU names to Government SKU names.
        """
        return dict(_SKU_MAPPING)

    def add_fedramp_tags(self, bicep_content: str, level: str) -> str:
        """Inject FedRAMP compliance tags into all ``tags:`` blocks.

        Args:
            bicep_content: Bicep template content.
            level: FedRAMP level (``high``, ``moderate``, ``low``).

        Returns:
            Template with FedRAMP tags injected.
        """
        level_lower = level.lower()
        tags = _FEDRAMP_TAGS.get(level_lower, _FEDRAMP_TAGS["high"])

        tag_lines = "\n".join(
            f"    {key}: '{value}'" for key, value in tags.items()
        )
        tag_block = f"  tags: {{\n{tag_lines}\n  }}"

        # If a tags: block exists, append our tags into it
        # Use a bounded match to avoid ReDoS: match tag key-value lines explicitly
        pattern = re.compile(r"(  tags:\s*\{)((?:\n[^}]*?)*?)(\n  })", re.MULTILINE)
        match = pattern.search(bicep_content)
        if match:
            return pattern.sub(
                f"\\1\\2\n{tag_lines}\\3", bicep_content
            )

        # Otherwise, append a tags block before the closing brace of each
        # resource
        if "resource " in bicep_content and "}" in bicep_content:
            # Find the last closing brace and insert tags before it
            last_brace = bicep_content.rfind("}")
            return (
                bicep_content[:last_brace]
                + "\n"
                + tag_block
                + "\n"
                + bicep_content[last_brace:]
            )

        return bicep_content

    def inject_diagnostic_settings(self, bicep_content: str) -> str:
        """Append a FedRAMP-required diagnostic settings resource block.

        Args:
            bicep_content: Bicep template content.

        Returns:
            Template with diagnostic settings appended.
        """
        if "diagnosticSettings" in bicep_content:
            return bicep_content
        return bicep_content + "\n" + _DIAGNOSTIC_SETTINGS_BLOCK.strip() + "\n"

    # ── Private helpers ──────────────────────────────────────────────────

    @staticmethod
    def _replace_endpoints(content: str) -> str:
        """Replace all commercial endpoint strings with .us equivalents."""
        for commercial, government in _ENDPOINT_REPLACEMENTS:
            content = content.replace(commercial, government)
        return content

    @staticmethod
    def _add_environment_property(content: str) -> str:
        """Add ``environment: 'AzureUSGovernment'`` property to resources."""
        if "environment:" in content:
            return content
        if "properties:" in content:
            return content.replace(
                "properties:", "properties:\n    environment: 'AzureUSGovernment'"
            )
        return content

    @staticmethod
    def _replace_skus(content: str) -> str:
        """Replace commercial-only SKU references with Government equivalents."""
        for commercial_sku, gov_sku in _SKU_MAPPING.items():
            content = content.replace(commercial_sku, gov_sku)
        return content

    @staticmethod
    def _set_region(content: str, region: str) -> str:
        """Replace ``location`` parameter defaults with the target region."""
        pattern = re.compile(
            r"(param\s+location\s+string\s*=\s*')[^']*(')"
        )
        if pattern.search(content):
            return pattern.sub(f"\\g<1>{region}\\g<2>", content)
        return content


government_bicep_service = GovernmentBicepService()
