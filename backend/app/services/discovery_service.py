"""Azure environment discovery service.

Scans customer Azure subscriptions and inventories resources, policies,
RBAC assignments, and networking configuration.
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.config import settings
from app.models.base import generate_uuid

logger = logging.getLogger(__name__)

# Categories for discovered entities
CATEGORY_RESOURCE = "resource"
CATEGORY_POLICY = "policy"
CATEGORY_RBAC = "rbac"
CATEGORY_NETWORK = "network"


def _mock_discovery_results() -> dict:
    """Return realistic mock discovery results for dev mode."""
    return {
        "subscription": {
            "id": "00000000-0000-0000-0000-000000000001",
            "display_name": "Dev Subscription",
            "state": "Enabled",
        },
        "resource_groups": [
            {"name": "rg-app-prod", "location": "eastus2", "resource_count": 8},
            {"name": "rg-network-prod", "location": "eastus2", "resource_count": 5},
            {"name": "rg-data-prod", "location": "eastus2", "resource_count": 3},
        ],
        "summary": {
            "total_resource_groups": 3,
            "total_resources": 16,
            "total_policies": 4,
            "total_role_assignments": 6,
            "total_vnets": 2,
        },
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


def _mock_discovered_resources() -> list[dict]:
    """Return mock discovered resources for dev mode."""
    base_id = "/subscriptions/00000000-0000-0000-0000-000000000001"
    return [
        {
            "id": generate_uuid(),
            "category": CATEGORY_RESOURCE,
            "resource_type": "Microsoft.Compute/virtualMachines",
            "resource_id": f"{base_id}/resourceGroups/rg-app-prod/providers"
                           "/Microsoft.Compute/virtualMachines/vm-web-01",
            "resource_group": "rg-app-prod",
            "name": "vm-web-01",
            "properties": {"location": "eastus2", "vm_size": "Standard_D2s_v3"},
        },
        {
            "id": generate_uuid(),
            "category": CATEGORY_RESOURCE,
            "resource_type": "Microsoft.Storage/storageAccounts",
            "resource_id": f"{base_id}/resourceGroups/rg-data-prod/providers"
                           "/Microsoft.Storage/storageAccounts/stproddata001",
            "resource_group": "rg-data-prod",
            "name": "stproddata001",
            "properties": {"location": "eastus2", "sku": "Standard_LRS"},
        },
        {
            "id": generate_uuid(),
            "category": CATEGORY_RESOURCE,
            "resource_type": "Microsoft.KeyVault/vaults",
            "resource_id": f"{base_id}/resourceGroups/rg-app-prod/providers"
                           "/Microsoft.KeyVault/vaults/kv-app-prod",
            "resource_group": "rg-app-prod",
            "name": "kv-app-prod",
            "properties": {"location": "eastus2"},
        },
        {
            "id": generate_uuid(),
            "category": CATEGORY_NETWORK,
            "resource_type": "Microsoft.Network/virtualNetworks",
            "resource_id": f"{base_id}/resourceGroups/rg-network-prod/providers"
                           "/Microsoft.Network/virtualNetworks/vnet-hub",
            "resource_group": "rg-network-prod",
            "name": "vnet-hub",
            "properties": {
                "location": "eastus2",
                "address_space": ["10.0.0.0/16"],
                "subnets": ["GatewaySubnet", "AzureFirewallSubnet", "default"],
            },
        },
        {
            "id": generate_uuid(),
            "category": CATEGORY_NETWORK,
            "resource_type": "Microsoft.Network/networkSecurityGroups",
            "resource_id": f"{base_id}/resourceGroups/rg-network-prod/providers"
                           "/Microsoft.Network/networkSecurityGroups/nsg-default",
            "resource_group": "rg-network-prod",
            "name": "nsg-default",
            "properties": {"location": "eastus2", "rule_count": 5},
        },
        {
            "id": generate_uuid(),
            "category": CATEGORY_POLICY,
            "resource_type": "Microsoft.Authorization/policyAssignments",
            "resource_id": f"{base_id}/providers/Microsoft.Authorization"
                           "/policyAssignments/require-tags",
            "resource_group": None,
            "name": "Require resource tags",
            "properties": {
                "policy_definition_id": "/providers/Microsoft.Authorization"
                                        "/policyDefinitions/require-tag",
                "scope": base_id,
                "enforcement_mode": "Default",
            },
        },
        {
            "id": generate_uuid(),
            "category": CATEGORY_POLICY,
            "resource_type": "Microsoft.Authorization/policyAssignments",
            "resource_id": f"{base_id}/providers/Microsoft.Authorization"
                           "/policyAssignments/allowed-locations",
            "resource_group": None,
            "name": "Allowed locations",
            "properties": {
                "scope": base_id,
                "enforcement_mode": "Default",
                "allowed_locations": ["eastus2", "westus2"],
            },
        },
        {
            "id": generate_uuid(),
            "category": CATEGORY_RBAC,
            "resource_type": "Microsoft.Authorization/roleAssignments",
            "resource_id": f"{base_id}/providers/Microsoft.Authorization"
                           "/roleAssignments/ra-owner-001",
            "resource_group": None,
            "name": "Owner — admin@contoso.com",
            "properties": {
                "role_definition_name": "Owner",
                "principal_type": "User",
                "scope": base_id,
            },
        },
        {
            "id": generate_uuid(),
            "category": CATEGORY_RBAC,
            "resource_type": "Microsoft.Authorization/roleAssignments",
            "resource_id": f"{base_id}/providers/Microsoft.Authorization"
                           "/roleAssignments/ra-contributor-001",
            "resource_group": None,
            "name": "Contributor — devteam@contoso.com",
            "properties": {
                "role_definition_name": "Contributor",
                "principal_type": "Group",
                "scope": base_id,
            },
        },
    ]


class DiscoveryService:
    """Scans Azure subscriptions to discover existing resources and configuration."""

    def _get_credential(self):
        """Get Azure credential, lazy import."""
        if not settings.is_dev_mode:
            try:
                from azure.identity import DefaultAzureCredential
                return DefaultAzureCredential()
            except Exception as e:
                logger.error("Failed to initialize Azure credentials: %s", e)
        return None

    async def start_scan(
        self,
        project_id: str,
        tenant_id: str,
        subscription_id: str,
        scan_config: dict | None = None,
    ) -> dict:
        """Create a discovery scan record and return its ID.

        In dev mode without a database, returns an immediate mock result.

        Args:
            project_id: The project this scan belongs to.
            tenant_id: The tenant performing the scan.
            subscription_id: Azure subscription ID to scan.
            scan_config: Optional scan configuration.

        Returns:
            Dict with scan_id, status, and optionally immediate results.
        """
        from app.db.session import get_session_factory

        factory = get_session_factory()

        if factory is None:
            # Dev mode without DB — return immediate mock
            mock_id = generate_uuid()
            return {
                "id": mock_id,
                "project_id": project_id,
                "subscription_id": subscription_id,
                "status": "completed",
                "results": _mock_discovery_results(),
                "resources": _mock_discovered_resources(),
                "resource_count": len(_mock_discovered_resources()),
            }

        from app.models.discovery import DiscoveryScan

        scan_id = generate_uuid()
        async with factory() as session:
            scan = DiscoveryScan(
                id=scan_id,
                project_id=project_id,
                tenant_id=tenant_id,
                subscription_id=subscription_id,
                status="pending",
                scan_config=scan_config,
            )
            session.add(scan)
            await session.commit()

        return {
            "id": scan_id,
            "project_id": project_id,
            "subscription_id": subscription_id,
            "status": "pending",
        }

    async def execute_scan(self, scan_id: str) -> None:
        """Execute the discovery scan in a background task.

        Creates its own database session (not request-scoped).
        Runs Azure SDK calls via asyncio.to_thread to avoid blocking.

        Args:
            scan_id: The ID of the scan to execute.
        """
        from app.db.session import get_session_factory
        from app.models.discovery import DiscoveredResource, DiscoveryScan

        factory = get_session_factory()
        if factory is None:
            return

        async with factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(DiscoveryScan).where(DiscoveryScan.id == scan_id)
            )
            scan = result.scalar_one_or_none()
            if scan is None:
                logger.error("Scan %s not found", scan_id)
                return

            # Update status to scanning
            scan.status = "scanning"
            await session.commit()

            try:
                if settings.is_dev_mode:
                    resources_data = _mock_discovered_resources()
                    summary = _mock_discovery_results()
                else:
                    resources_data, summary = await self._scan_azure(
                        scan.subscription_id, scan.scan_config
                    )

                # Store discovered resources
                for res_data in resources_data:
                    resource = DiscoveredResource(
                        id=res_data.get("id", generate_uuid()),
                        scan_id=scan_id,
                        category=res_data["category"],
                        resource_type=res_data["resource_type"],
                        resource_id=res_data["resource_id"],
                        resource_group=res_data.get("resource_group"),
                        name=res_data["name"],
                        properties=res_data.get("properties"),
                    )
                    session.add(resource)

                # Reassign whole dict to ensure SQLAlchemy detects the change
                scan.results = dict(summary)
                scan.status = "completed"
                await session.commit()
                logger.info("Discovery scan %s completed: %d resources",
                            scan_id, len(resources_data))

            except Exception as e:
                scan.status = "failed"
                scan.error_message = str(e)[:2000]
                await session.commit()
                logger.error("Discovery scan %s failed: %s", scan_id, e)

    async def _scan_azure(
        self, subscription_id: str, scan_config: dict | None
    ) -> tuple[list[dict], dict]:
        """Perform actual Azure SDK discovery calls.

        All SDK calls are synchronous, so we run them in a thread.

        Args:
            subscription_id: Azure subscription to scan.
            scan_config: Optional configuration to filter scan scope.

        Returns:
            Tuple of (list of resource dicts, summary dict).
        """
        credential = self._get_credential()
        if credential is None:
            raise RuntimeError("Azure credentials not available")

        def _do_scan() -> tuple[list[dict], dict]:
            return self._sync_scan(credential, subscription_id, scan_config)

        return await asyncio.to_thread(_do_scan)

    def _sync_scan(
        self, credential, subscription_id: str, scan_config: dict | None
    ) -> tuple[list[dict], dict]:
        """Synchronous Azure SDK scanning (runs in thread pool).

        Args:
            credential: Azure credential object.
            subscription_id: Subscription to scan.
            scan_config: Optional scan configuration.

        Returns:
            Tuple of (resources list, summary dict).
        """
        from azure.mgmt.authorization import AuthorizationManagementClient
        from azure.mgmt.network import NetworkManagementClient
        from azure.mgmt.resource import ResourceManagementClient
        from azure.mgmt.resource.policy import PolicyClient

        resources: list[dict] = []
        summary: dict = {}
        sub_scope = f"/subscriptions/{subscription_id}"

        # Discover resource groups and resources
        try:
            resource_client = ResourceManagementClient(credential, subscription_id)
            rg_list = list(resource_client.resource_groups.list())
            summary["total_resource_groups"] = len(rg_list)
            summary["resource_groups"] = [
                {
                    "name": rg.name,
                    "location": rg.location,
                    "tags": dict(rg.tags) if rg.tags else {},
                }
                for rg in rg_list
            ]

            all_resources = list(resource_client.resources.list())
            summary["total_resources"] = len(all_resources)
            for res in all_resources:
                rg_name = None
                if res.id:
                    parts = res.id.split("/")
                    rg_idx = next(
                        (i for i, p in enumerate(parts)
                         if p.lower() == "resourcegroups" and i + 1 < len(parts)),
                        None,
                    )
                    if rg_idx is not None:
                        rg_name = parts[rg_idx + 1]

                resources.append({
                    "id": generate_uuid(),
                    "category": CATEGORY_RESOURCE,
                    "resource_type": res.type or "Unknown",
                    "resource_id": res.id or "",
                    "resource_group": rg_name,
                    "name": res.name or "Unknown",
                    "properties": {
                        "location": res.location,
                        "kind": res.kind,
                        "tags": dict(res.tags) if res.tags else {},
                    },
                })
        except Exception as e:
            logger.warning("Resource discovery failed: %s", e)
            summary["resource_error"] = str(e)

        # Discover network configuration
        try:
            network_client = NetworkManagementClient(credential, subscription_id)
            vnets = list(network_client.virtual_networks.list_all())
            summary["total_vnets"] = len(vnets)
            for vnet in vnets:
                subnets = [s.name for s in (vnet.subnets or [])]
                resources.append({
                    "id": generate_uuid(),
                    "category": CATEGORY_NETWORK,
                    "resource_type": "Microsoft.Network/virtualNetworks",
                    "resource_id": vnet.id or "",
                    "resource_group": vnet.id.split("/")[4] if vnet.id else None,
                    "name": vnet.name or "Unknown",
                    "properties": {
                        "location": vnet.location,
                        "address_space": (
                            vnet.address_space.address_prefixes
                            if vnet.address_space else []
                        ),
                        "subnets": subnets,
                    },
                })

            nsgs = list(network_client.network_security_groups.list_all())
            summary["total_nsgs"] = len(nsgs)
            for nsg in nsgs:
                resources.append({
                    "id": generate_uuid(),
                    "category": CATEGORY_NETWORK,
                    "resource_type": "Microsoft.Network/networkSecurityGroups",
                    "resource_id": nsg.id or "",
                    "resource_group": nsg.id.split("/")[4] if nsg.id else None,
                    "name": nsg.name or "Unknown",
                    "properties": {
                        "location": nsg.location,
                        "rule_count": len(nsg.security_rules or []),
                    },
                })
        except Exception as e:
            logger.warning("Network discovery failed: %s", e)
            summary["network_error"] = str(e)

        # Discover policy assignments
        try:
            policy_client = PolicyClient(credential, subscription_id)
            assignments = list(
                policy_client.policy_assignments.list_for_subscription()
            )
            summary["total_policies"] = len(assignments)
            for pa in assignments:
                resources.append({
                    "id": generate_uuid(),
                    "category": CATEGORY_POLICY,
                    "resource_type": "Microsoft.Authorization/policyAssignments",
                    "resource_id": pa.id or "",
                    "resource_group": None,
                    "name": pa.display_name or pa.name or "Unknown",
                    "properties": {
                        "policy_definition_id": pa.policy_definition_id,
                        "scope": pa.scope,
                        "enforcement_mode": (
                            pa.enforcement_mode.value
                            if pa.enforcement_mode else "Default"
                        ),
                    },
                })
        except Exception as e:
            logger.warning("Policy discovery failed: %s", e)
            summary["policy_error"] = str(e)

        # Discover RBAC role assignments
        try:
            auth_client = AuthorizationManagementClient(
                credential, subscription_id
            )
            assignments = list(
                auth_client.role_assignments.list_for_scope(sub_scope)
            )
            summary["total_role_assignments"] = len(assignments)
            for ra in assignments:
                resources.append({
                    "id": generate_uuid(),
                    "category": CATEGORY_RBAC,
                    "resource_type": "Microsoft.Authorization/roleAssignments",
                    "resource_id": ra.id or "",
                    "resource_group": None,
                    "name": f"{ra.role_definition_id or 'Unknown'} — {ra.principal_id}",
                    "properties": {
                        "role_definition_id": ra.role_definition_id,
                        "principal_id": ra.principal_id,
                        "principal_type": (
                            ra.principal_type.value if ra.principal_type else None
                        ),
                        "scope": ra.scope,
                    },
                })
        except Exception as e:
            logger.warning("RBAC discovery failed: %s", e)
            summary["rbac_error"] = str(e)

        summary["scanned_at"] = datetime.now(timezone.utc).isoformat()
        return resources, summary

    async def get_scan(self, scan_id: str, db) -> dict | None:
        """Get a discovery scan by ID.

        Args:
            scan_id: The scan ID.
            db: AsyncSession or None.

        Returns:
            Scan data dict or None if not found.
        """
        if db is None:
            return None

        from sqlalchemy import func, select

        from app.models.discovery import DiscoveredResource, DiscoveryScan

        result = await db.execute(
            select(DiscoveryScan).where(DiscoveryScan.id == scan_id)
        )
        scan = result.scalar_one_or_none()
        if scan is None:
            return None

        # Count resources
        count_result = await db.execute(
            select(func.count(DiscoveredResource.id)).where(
                DiscoveredResource.scan_id == scan_id
            )
        )
        resource_count = count_result.scalar() or 0

        return {
            "id": scan.id,
            "project_id": scan.project_id,
            "tenant_id": scan.tenant_id,
            "subscription_id": scan.subscription_id,
            "status": scan.status,
            "scan_config": scan.scan_config,
            "results": scan.results,
            "error_message": scan.error_message,
            "resource_count": resource_count,
            "created_at": scan.created_at,
            "updated_at": scan.updated_at,
        }

    async def get_scan_resources(
        self, scan_id: str, db, category: str | None = None
    ) -> list[dict]:
        """Get discovered resources for a scan.

        Args:
            scan_id: The scan ID.
            db: AsyncSession or None.
            category: Optional category filter.

        Returns:
            List of resource dicts.
        """
        if db is None:
            return []

        from sqlalchemy import select

        from app.models.discovery import DiscoveredResource

        stmt = select(DiscoveredResource).where(
            DiscoveredResource.scan_id == scan_id
        )
        if category:
            stmt = stmt.where(DiscoveredResource.category == category)
        stmt = stmt.order_by(DiscoveredResource.category, DiscoveredResource.name)

        result = await db.execute(stmt)
        resources = result.scalars().all()

        return [
            {
                "id": r.id,
                "scan_id": r.scan_id,
                "category": r.category,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "resource_group": r.resource_group,
                "name": r.name,
                "properties": r.properties,
                "created_at": r.created_at,
            }
            for r in resources
        ]


# Singleton
discovery_service = DiscoveryService()
