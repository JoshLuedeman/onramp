"""AI-powered Azure Policy generator.

Translates natural language governance descriptions into valid Azure Policy
JSON definitions, with validation and a built-in template library.
"""

import json
import logging

from app.config import settings
from app.schemas.policy import (
    PolicyDefinition,
    PolicyTemplate,
    PolicyValidationResult,
)
from app.services.ai_validator import ai_validator
from app.services.prompts import (
    POLICY_GENERATION_SYSTEM_PROMPT,
    POLICY_GENERATION_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in policy template library
# ---------------------------------------------------------------------------

POLICY_TEMPLATES: list[dict] = [
    {
        "id": "restrict-vm-sizes",
        "name": "Restrict VM Sizes",
        "description": "Only allow specific VM SKU sizes to control costs and standardise workloads.",
        "category": "Compute",
        "policy_json": {
            "name": "restrict-vm-sizes",
            "display_name": "Restrict Virtual Machine Sizes",
            "description": "Only allow specific VM SKU sizes.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "allOf": [
                        {"field": "type", "equals": "Microsoft.Compute/virtualMachines"},
                        {
                            "not": {
                                "field": "Microsoft.Compute/virtualMachines/sku.name",
                                "in": "[parameters('allowedSizes')]",
                            }
                        },
                    ]
                },
                "then": {"effect": "Deny"},
            },
            "parameters": {
                "allowedSizes": {
                    "type": "Array",
                    "metadata": {"displayName": "Allowed VM Sizes"},
                    "defaultValue": ["Standard_B2s", "Standard_D2s_v5"],
                }
            },
            "metadata": {"category": "Compute"},
        },
    },
    {
        "id": "require-tags",
        "name": "Require Resource Tags",
        "description": "Enforce that all resources have mandatory tags for cost tracking and ownership.",
        "category": "Tags",
        "policy_json": {
            "name": "require-tags",
            "display_name": "Require Mandatory Tags",
            "description": "Enforce mandatory tags on all resources.",
            "mode": "Indexed",
            "policy_rule": {
                "if": {
                    "field": "[concat('tags[', parameters('tagName'), ']')]",
                    "exists": "false",
                },
                "then": {"effect": "Deny"},
            },
            "parameters": {
                "tagName": {
                    "type": "String",
                    "metadata": {"displayName": "Tag Name"},
                    "defaultValue": "CostCenter",
                }
            },
            "metadata": {"category": "Tags"},
        },
    },
    {
        "id": "enforce-encryption",
        "name": "Enforce Storage Encryption",
        "description": "Require storage accounts to use customer-managed encryption keys.",
        "category": "Encryption",
        "policy_json": {
            "name": "enforce-encryption",
            "display_name": "Enforce Storage Encryption",
            "description": "Require encryption on storage accounts.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "allOf": [
                        {"field": "type", "equals": "Microsoft.Storage/storageAccounts"},
                        {
                            "field": "Microsoft.Storage/storageAccounts/encryption.keySource",
                            "notEquals": "Microsoft.Keyvault",
                        },
                    ]
                },
                "then": {"effect": "Audit"},
            },
            "parameters": {},
            "metadata": {"category": "Encryption"},
        },
    },
    {
        "id": "allowed-locations",
        "name": "Allowed Locations",
        "description": "Restrict resource deployment to a set of approved Azure regions.",
        "category": "General",
        "policy_json": {
            "name": "allowed-locations",
            "display_name": "Allowed Locations",
            "description": "Restrict deployment to specific Azure regions.",
            "mode": "Indexed",
            "policy_rule": {
                "if": {
                    "not": {
                        "field": "location",
                        "in": "[parameters('allowedLocations')]",
                    }
                },
                "then": {"effect": "Deny"},
            },
            "parameters": {
                "allowedLocations": {
                    "type": "Array",
                    "metadata": {"displayName": "Allowed Locations"},
                    "defaultValue": ["eastus", "westus2", "westeurope"],
                }
            },
            "metadata": {"category": "General"},
        },
    },
    {
        "id": "require-https-storage",
        "name": "Require HTTPS for Storage",
        "description": "Ensure that storage accounts only accept HTTPS traffic.",
        "category": "Network",
        "policy_json": {
            "name": "require-https-storage",
            "display_name": "Require HTTPS Traffic for Storage Accounts",
            "description": "Storage accounts must only accept HTTPS traffic.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "allOf": [
                        {"field": "type", "equals": "Microsoft.Storage/storageAccounts"},
                        {
                            "field": "Microsoft.Storage/storageAccounts/supportsHttpsTrafficOnly",
                            "notEquals": "true",
                        },
                    ]
                },
                "then": {"effect": "Deny"},
            },
            "parameters": {},
            "metadata": {"category": "Network"},
        },
    },
    {
        "id": "deny-public-ip",
        "name": "Deny Public IP Addresses",
        "description": "Prevent creation of public IP addresses to enforce private networking.",
        "category": "Network",
        "policy_json": {
            "name": "deny-public-ip",
            "display_name": "Deny Public IP Addresses",
            "description": "Prevent the creation of public IP addresses.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "field": "type",
                    "equals": "Microsoft.Network/publicIPAddresses",
                },
                "then": {"effect": "Deny"},
            },
            "parameters": {},
            "metadata": {"category": "Network"},
        },
    },
    {
        "id": "require-nsg-on-subnet",
        "name": "Require NSG on Subnets",
        "description": "Ensure every subnet has a Network Security Group attached.",
        "category": "Network",
        "policy_json": {
            "name": "require-nsg-on-subnet",
            "display_name": "Require NSG on Subnets",
            "description": "Ensure every subnet has an NSG associated.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "allOf": [
                        {
                            "field": "type",
                            "equals": "Microsoft.Network/virtualNetworks/subnets",
                        },
                        {
                            "field": "Microsoft.Network/virtualNetworks/subnets/networkSecurityGroup.id",
                            "exists": "false",
                        },
                    ]
                },
                "then": {"effect": "Deny"},
            },
            "parameters": {},
            "metadata": {"category": "Network"},
        },
    },
    {
        "id": "audit-sql-encryption",
        "name": "Audit SQL Transparent Data Encryption",
        "description": "Audit that SQL databases have Transparent Data Encryption enabled.",
        "category": "Encryption",
        "policy_json": {
            "name": "audit-sql-encryption",
            "display_name": "Audit SQL Transparent Data Encryption",
            "description": "Audit SQL databases for TDE status.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "allOf": [
                        {
                            "field": "type",
                            "equals": "Microsoft.Sql/servers/databases/transparentDataEncryption",
                        },
                        {"field": "Microsoft.Sql/transparentDataEncryption/status", "notEquals": "Enabled"},
                    ]
                },
                "then": {"effect": "Audit"},
            },
            "parameters": {},
            "metadata": {"category": "Encryption"},
        },
    },
    {
        "id": "require-diagnostic-settings",
        "name": "Require Diagnostic Settings",
        "description": "Ensure diagnostic settings are configured on key resources for monitoring.",
        "category": "Monitoring",
        "policy_json": {
            "name": "require-diagnostic-settings",
            "display_name": "Require Diagnostic Settings",
            "description": "Audit resources for diagnostic settings configuration.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "field": "type",
                    "equals": "Microsoft.KeyVault/vaults",
                },
                "then": {
                    "effect": "AuditIfNotExists",
                    "details": {
                        "type": "Microsoft.Insights/diagnosticSettings",
                        "existenceCondition": {
                            "field": "Microsoft.Insights/diagnosticSettings/logs.enabled",
                            "equals": "true",
                        },
                    },
                },
            },
            "parameters": {},
            "metadata": {"category": "Monitoring"},
        },
    },
    {
        "id": "enforce-resource-lock",
        "name": "Enforce Resource Locks",
        "description": "Require CanNotDelete resource locks on production resource groups.",
        "category": "Governance",
        "policy_json": {
            "name": "enforce-resource-lock",
            "display_name": "Enforce Resource Locks on Resource Groups",
            "description": "Audit resource groups for CanNotDelete locks.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "field": "type",
                    "equals": "Microsoft.Resources/subscriptions/resourceGroups",
                },
                "then": {
                    "effect": "AuditIfNotExists",
                    "details": {
                        "type": "Microsoft.Authorization/locks",
                        "existenceCondition": {
                            "field": "Microsoft.Authorization/locks/level",
                            "equals": "CanNotDelete",
                        },
                    },
                },
            },
            "parameters": {},
            "metadata": {"category": "Governance"},
        },
    },
    {
        "id": "deny-unapproved-resource-types",
        "name": "Deny Unapproved Resource Types",
        "description": "Only allow deployment of explicitly approved Azure resource types.",
        "category": "General",
        "policy_json": {
            "name": "deny-unapproved-resource-types",
            "display_name": "Deny Unapproved Resource Types",
            "description": "Only allow specific resource types to be deployed.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "not": {
                        "field": "type",
                        "in": "[parameters('allowedTypes')]",
                    }
                },
                "then": {"effect": "Deny"},
            },
            "parameters": {
                "allowedTypes": {
                    "type": "Array",
                    "metadata": {"displayName": "Allowed Resource Types"},
                    "defaultValue": [
                        "Microsoft.Compute/virtualMachines",
                        "Microsoft.Storage/storageAccounts",
                        "Microsoft.Network/virtualNetworks",
                    ],
                }
            },
            "metadata": {"category": "General"},
        },
    },
    {
        "id": "require-tls-12",
        "name": "Require TLS 1.2",
        "description": "Ensure storage accounts enforce a minimum TLS version of 1.2.",
        "category": "Network",
        "policy_json": {
            "name": "require-tls-12",
            "display_name": "Require TLS 1.2 on Storage Accounts",
            "description": "Storage accounts must use TLS 1.2 or higher.",
            "mode": "All",
            "policy_rule": {
                "if": {
                    "allOf": [
                        {"field": "type", "equals": "Microsoft.Storage/storageAccounts"},
                        {
                            "field": "Microsoft.Storage/storageAccounts/minimumTlsVersion",
                            "notEquals": "TLS1_2",
                        },
                    ]
                },
                "then": {"effect": "Deny"},
            },
            "parameters": {},
            "metadata": {"category": "Network"},
        },
    },
]


def _mock_policy(description: str, context: dict | None = None) -> dict:
    """Return a realistic mock Azure Policy for dev / no-AI mode."""
    name = description.lower().replace(" ", "-")[:50]
    return {
        "name": name,
        "display_name": description[:100],
        "description": description,
        "mode": "All",
        "policy_rule": {
            "if": {
                "field": "type",
                "equals": "Microsoft.Resources/subscriptions/resourceGroups",
            },
            "then": {"effect": "Audit"},
        },
        "parameters": {},
        "metadata": {
            "category": "General",
            "generated_from": description,
            "context": context or {},
        },
    }


class PolicyGenerator:
    """Generates Azure Policy definitions from natural language descriptions."""

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def generate_policy(
        self, description: str, context: dict | None = None
    ) -> PolicyDefinition:
        """Generate an Azure Policy from a natural language description.

        In dev mode (AI not configured), returns a realistic mock policy.
        """
        # Content safety — check for prompt injection in the description
        from app.services.content_safety import content_safety_service

        safety_result = content_safety_service.check_input(description)
        if not safety_result.safe:
            content_safety_service.log_security_event(
                "policy_input_blocked",
                user_id="unknown",
                details={
                    "patterns": safety_result.flagged_patterns,
                    "risk_level": safety_result.risk_level,
                },
            )
            raise ValueError(
                "Policy description was flagged by content safety: "
                + ", ".join(safety_result.flagged_patterns)
            )

        if settings.is_dev_mode or not settings.ai_foundry_endpoint:
            logger.info("Dev mode — returning mock policy for: %s", description)
            data = _mock_policy(description, context)
            return PolicyDefinition(**data)

        # Production path: call AI
        try:
            from app.services.ai_foundry import ai_client

            user_prompt = POLICY_GENERATION_USER_TEMPLATE.format(
                description=description,
                context=json.dumps(context or {}, indent=2),
            )

            response = await ai_client.generate_completion_async(
                system_prompt=POLICY_GENERATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )

            # Parse JSON from the AI response
            policy_data = json.loads(response)

            # Validate through the AI validator
            validation = ai_validator.validate_policy(policy_data)
            if not validation.success:
                logger.warning(
                    "AI-generated policy failed validation, falling back to mock: %s",
                    [e.message for e in validation.errors],
                )
                data = _mock_policy(description, context)
                return PolicyDefinition(**data)

            return PolicyDefinition(**policy_data)

        except Exception as e:
            logger.warning("AI policy generation failed, using mock: %s", e)
            data = _mock_policy(description, context)
            return PolicyDefinition(**data)

    def validate_policy_json(self, policy: dict) -> PolicyValidationResult:
        """Validate a policy dict against Azure Policy schema conventions.

        Checks for required if/then/effect structure in the policy_rule.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Top-level fields
        if not policy.get("name"):
            errors.append("Missing required field: name")

        policy_rule = policy.get("policy_rule")
        if not policy_rule:
            errors.append("Missing required field: policy_rule")
        elif not isinstance(policy_rule, dict):
            errors.append("policy_rule must be a JSON object")
        else:
            # Validate if/then structure
            if "if" not in policy_rule:
                errors.append("policy_rule must contain an 'if' condition")
            if "then" not in policy_rule:
                errors.append("policy_rule must contain a 'then' action")
            else:
                then_block = policy_rule["then"]
                if isinstance(then_block, dict):
                    effect = then_block.get("effect", "")
                    valid_effects = {
                        "deny", "audit", "append", "modify",
                        "deployifnotexists", "auditifnotexists",
                        "disabled", "denyaction",
                    }
                    if effect and effect.lower() not in valid_effects:
                        warnings.append(
                            f"Effect '{effect}' is not a standard Azure Policy effect"
                        )
                    if not effect:
                        errors.append("policy_rule.then must specify an 'effect'")
                else:
                    errors.append("policy_rule.then must be a JSON object")

        # Mode validation
        mode = policy.get("mode", "")
        if mode:
            valid_modes = {
                "all", "indexed",
                "microsoft.kubernetes.data",
                "microsoft.keyvault.data",
                "microsoft.network.data",
            }
            if mode.lower() not in valid_modes:
                warnings.append(f"Mode '{mode}' is not a standard Azure Policy mode")

        return PolicyValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def get_policy_library(self) -> list[PolicyTemplate]:
        """Return the built-in policy template library."""
        return [PolicyTemplate(**t) for t in POLICY_TEMPLATES]


# Module-level singleton
policy_generator = PolicyGenerator()
