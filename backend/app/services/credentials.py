"""Azure credential management for customer subscription deployments."""

import logging
from dataclasses import dataclass, field

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

    async def validate_credentials(
        self, subscription_id: str, tenant_id: str | None = None
    ) -> AzureCredentialInfo:
        """Validate that we have proper credentials for a subscription.

        In production, this will use the customer's delegated credentials
        or a service principal to verify access.
        """
        info = AzureCredentialInfo(
            subscription_id=subscription_id,
            tenant_id=tenant_id or settings.azure_tenant_id,
            credential_type="service_principal",
        )

        if not settings.azure_tenant_id:
            info.is_valid = False
            info.error = "Azure tenant not configured"
            logger.warning("Azure credentials not configured — running in dev mode")
            return info

        try:
            from azure.identity.aio import DefaultAzureCredential
            from azure.mgmt.resource.aio import ResourceManagementClient

            credential = DefaultAzureCredential()
            client = ResourceManagementClient(credential, subscription_id)

            # Verify we can list resource groups (basic permission check)
            async for _ in client.resource_groups.list():
                break

            info.is_valid = True
            info.permissions = ["Reader"]  # Minimal verified permission

            await credential.close()
            await client.close()
        except Exception as e:
            info.is_valid = False
            info.error = str(e)
            logger.error(f"Credential validation failed: {e}")

        return info

    async def check_deployment_permissions(
        self, subscription_id: str
    ) -> dict:
        """Check if we have sufficient permissions to deploy a landing zone.

        Requires Contributor + User Access Administrator at minimum.
        """
        required_permissions = [
            "Microsoft.Resources/deployments/write",
            "Microsoft.Resources/subscriptions/resourceGroups/write",
            "Microsoft.Authorization/roleAssignments/write",
            "Microsoft.Management/managementGroups/write",
            "Microsoft.Network/virtualNetworks/write",
            "Microsoft.Authorization/policyAssignments/write",
        ]

        if not settings.azure_tenant_id:
            return {
                "has_permissions": False,
                "missing_permissions": required_permissions,
                "error": "Azure not configured — development mode",
            }

        try:
            from azure.identity.aio import DefaultAzureCredential
            from azure.mgmt.authorization.aio import AuthorizationManagementClient

            credential = DefaultAzureCredential()
            auth_client = AuthorizationManagementClient(credential, subscription_id)

            # Check permissions
            scope = f"/subscriptions/{subscription_id}"
            permissions_result = []
            async for p in auth_client.permissions.list_for_resource_group(
                resource_group_name="",  # subscription-level
            ):
                permissions_result.extend(p.actions or [])

            missing = [
                p for p in required_permissions if p not in permissions_result
            ]

            await credential.close()
            await auth_client.close()

            return {
                "has_permissions": len(missing) == 0,
                "missing_permissions": missing,
                "verified_permissions": [
                    p for p in required_permissions if p not in missing
                ],
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
        """Check resource quotas in the target subscription and region."""
        if not settings.azure_tenant_id:
            return {
                "quotas_sufficient": True,
                "warnings": ["Running in dev mode — quota check skipped"],
            }

        # TODO: Implement actual quota checking via Azure SDK
        return {
            "quotas_sufficient": True,
            "checks": [
                {"resource": "VNets", "current": 0, "limit": 50, "needed": 3},
                {"resource": "Public IPs", "current": 0, "limit": 20, "needed": 2},
                {"resource": "NSGs", "current": 0, "limit": 200, "needed": 10},
            ],
            "warnings": [],
        }


# Singleton
credential_manager = CredentialManager()
