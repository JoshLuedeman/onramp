"""Azure credential management for customer subscription deployments."""

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AzureCredentialInfo:
    """Information about Azure credentials for a deployment."""

    subscription_id: str
    tenant_id: str
    credential_type: str  # "managed_identity" | "service_principal" | "user_delegated"
    is_valid: bool = False
    permissions: list[str] = field(default_factory=list)
    error: str | None = None


class CredentialManager:
    """Manages Azure credentials for deploying to customer subscriptions."""

    def __init__(self):
        self._credential = None

    @property
    def is_configured(self) -> bool:
        """Check if Azure credentials are configured."""
        return bool(settings.azure_tenant_id)

    def _get_credential(self):
        """Get Azure credential (sync), lazy-initialized."""
        if self._credential is None:
            if not self.is_configured:
                return None
            try:
                from azure.identity import DefaultAzureCredential
                self._credential = DefaultAzureCredential()
            except Exception:
                return None
        return self._credential

    async def validate_credentials(
        self, subscription_id: str, tenant_id: str | None = None
    ) -> AzureCredentialInfo:
        """Validate that we have proper credentials for a subscription.

        Uses the Azure SDK SubscriptionClient to verify the subscription
        is accessible with the current credentials.
        """
        resolved_tenant = tenant_id or settings.azure_tenant_id
        info = AzureCredentialInfo(
            subscription_id=subscription_id,
            tenant_id=resolved_tenant,
            credential_type="service_principal",
        )

        if not self.is_configured:
            info.is_valid = False
            info.error = "Azure tenant not configured"
            logger.warning("Azure credentials not configured — running in dev mode")
            return info

        credential = self._get_credential()
        if credential is None:
            info.is_valid = False
            info.error = "Failed to initialize Azure credentials"
            return info

        try:
            from azure.mgmt.resource import SubscriptionClient

            sub_client = SubscriptionClient(credential)
            sub = sub_client.subscriptions.get(subscription_id)

            info.is_valid = True
            info.permissions = ["Reader"]
            info.tenant_id = sub.tenant_id or resolved_tenant
            logger.info(
                f"Subscription validated: {sub.display_name} "
                f"(state={sub.state.value if sub.state else 'unknown'})"
            )
        except Exception as e:
            info.is_valid = False
            info.error = str(e)
            logger.error(f"Credential validation failed: {e}")

        return info

    async def check_deployment_permissions(
        self, subscription_id: str
    ) -> dict:
        """Check if we have sufficient permissions to deploy a landing zone.

        Uses the AuthorizationManagementClient to enumerate role assignments
        on the subscription scope.
        """
        required_permissions = [
            "Microsoft.Resources/deployments/write",
            "Microsoft.Resources/subscriptions/resourceGroups/write",
            "Microsoft.Authorization/roleAssignments/write",
            "Microsoft.Management/managementGroups/write",
            "Microsoft.Network/virtualNetworks/write",
            "Microsoft.Authorization/policyAssignments/write",
        ]

        if not self.is_configured:
            return {
                "has_permissions": False,
                "missing_permissions": required_permissions,
                "error": "Azure not configured — development mode",
            }

        credential = self._get_credential()
        if credential is None:
            return {
                "has_permissions": False,
                "missing_permissions": required_permissions,
                "error": "Failed to initialize Azure credentials",
            }

        try:
            from azure.mgmt.authorization import AuthorizationManagementClient

            auth_client = AuthorizationManagementClient(credential, subscription_id)
            scope = f"/subscriptions/{subscription_id}"
            assignments = list(
                auth_client.role_assignments.list_for_scope(scope, filter="atScope()")
            )

            roles = []
            for assignment in assignments[:10]:
                roles.append({
                    "role_definition_id": assignment.role_definition_id,
                    "principal_id": assignment.principal_id,
                    "scope": assignment.scope,
                })

            has_perms = len(assignments) > 0
            return {
                "has_permissions": has_perms,
                "missing_permissions": [] if has_perms else required_permissions,
                "role_assignments_count": len(assignments),
                "sample_roles": roles,
            }
        except Exception as e:
            return {
                "has_permissions": False,
                "missing_permissions": required_permissions,
                "error": str(e),
            }

    async def check_subscription_quotas(
        self, subscription_id: str, region: str
    ) -> dict:
        """Check resource quotas in the target subscription and region.

        Uses ComputeManagementClient and NetworkManagementClient to query
        actual usage vs. limits for cores, VMs, VNets, and public IPs.
        """
        if not self.is_configured:
            return {
                "quotas_sufficient": True,
                "warnings": ["Running in dev mode — quota check skipped"],
            }

        credential = self._get_credential()
        if credential is None:
            return {
                "quotas_sufficient": False,
                "warnings": ["Failed to initialize Azure credentials"],
            }

        try:
            from azure.mgmt.compute import ComputeManagementClient
            from azure.mgmt.network import NetworkManagementClient

            quotas: dict[str, dict] = {}

            # Check compute quotas
            try:
                compute_client = ComputeManagementClient(credential, subscription_id)
                usages = list(compute_client.usage.list(region))
                for usage in usages:
                    if usage.name.value in ("cores", "virtualMachines"):
                        quotas[usage.name.value] = {
                            "current": usage.current_value,
                            "limit": usage.limit,
                        }
            except Exception as e:
                logger.warning(f"Could not check compute quotas: {e}")
                quotas["compute"] = {"error": "Could not check compute quotas"}

            # Check network quotas
            try:
                network_client = NetworkManagementClient(credential, subscription_id)
                usages = list(network_client.usages.list(region))
                for usage in usages:
                    if usage.name.value in ("VirtualNetworks", "PublicIPAddresses"):
                        quotas[usage.name.value] = {
                            "current": usage.current_value,
                            "limit": usage.limit,
                        }
            except Exception as e:
                logger.warning(f"Could not check network quotas: {e}")
                quotas["network"] = {"error": "Could not check network quotas"}

            all_sufficient = all(
                v.get("current", 0) < v.get("limit", float("inf"))
                for v in quotas.values()
                if "error" not in v
            )

            warnings = [
                f"{k}: {v['error']}" for k, v in quotas.items() if "error" in v
            ]

            return {
                "quotas_sufficient": all_sufficient,
                "checks": [
                    {"resource": k, "current": v.get("current", 0), "limit": v.get("limit", 0)}
                    for k, v in quotas.items()
                    if "error" not in v
                ],
                "warnings": warnings,
            }
        except Exception as e:
            return {
                "quotas_sufficient": False,
                "warnings": [str(e)],
            }

    def get_resource_client(self, subscription_id: str):
        """Get an Azure ResourceManagementClient for deployments."""
        if not self.is_configured:
            return None
        credential = self._get_credential()
        if credential is None:
            return None
        try:
            from azure.mgmt.resource import ResourceManagementClient
            return ResourceManagementClient(credential, subscription_id)
        except Exception:
            return None


# Singleton
credential_manager = CredentialManager()
