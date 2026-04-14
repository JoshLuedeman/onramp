"""Tests for the Azure environment discovery feature."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.discovery_service import (
    CATEGORY_NETWORK,
    CATEGORY_POLICY,
    CATEGORY_RBAC,
    CATEGORY_RESOURCE,
    DiscoveryService,
    _mock_discovered_resources,
    _mock_discovery_results,
    discovery_service,
)


# ---------------------------------------------------------------------------
# Unit tests: mock data generators
# ---------------------------------------------------------------------------

class TestMockData:
    """Tests for mock data generation functions."""

    def test_mock_discovery_results_structure(self):
        """Mock results contain expected top-level keys."""
        results = _mock_discovery_results()
        assert "subscription" in results
        assert "resource_groups" in results
        assert "summary" in results
        assert "scanned_at" in results

    def test_mock_discovery_results_subscription(self):
        """Mock subscription has id, display_name, state."""
        results = _mock_discovery_results()
        sub = results["subscription"]
        assert sub["id"] is not None
        assert sub["display_name"] is not None
        assert sub["state"] == "Enabled"

    def test_mock_discovery_results_resource_groups(self):
        """Mock results include resource groups."""
        results = _mock_discovery_results()
        rgs = results["resource_groups"]
        assert len(rgs) >= 1
        assert all("name" in rg and "location" in rg for rg in rgs)

    def test_mock_discovery_results_summary(self):
        """Summary contains totals."""
        results = _mock_discovery_results()
        summary = results["summary"]
        assert summary["total_resource_groups"] > 0
        assert summary["total_resources"] > 0

    def test_mock_discovered_resources_not_empty(self):
        """Mock resources list is non-empty."""
        resources = _mock_discovered_resources()
        assert len(resources) >= 5

    def test_mock_discovered_resources_categories(self):
        """Mock resources cover all categories."""
        resources = _mock_discovered_resources()
        categories = {r["category"] for r in resources}
        assert CATEGORY_RESOURCE in categories
        assert CATEGORY_NETWORK in categories
        assert CATEGORY_POLICY in categories
        assert CATEGORY_RBAC in categories

    def test_mock_discovered_resources_fields(self):
        """Each mock resource has the required fields."""
        resources = _mock_discovered_resources()
        for res in resources:
            assert "id" in res
            assert "category" in res
            assert "resource_type" in res
            assert "resource_id" in res
            assert "name" in res

    def test_mock_resources_have_unique_ids(self):
        """Each mock resource has a unique ID."""
        resources = _mock_discovered_resources()
        ids = [r["id"] for r in resources]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Unit tests: DiscoveryService
# ---------------------------------------------------------------------------

class TestDiscoveryService:
    """Tests for the DiscoveryService class."""

    def test_singleton_exists(self):
        """discovery_service singleton is available."""
        assert discovery_service is not None
        assert isinstance(discovery_service, DiscoveryService)

    def test_get_credential_dev_mode(self):
        """In dev mode, _get_credential returns None."""
        # Dev mode: settings.is_dev_mode is True
        cred = discovery_service._get_credential()
        assert cred is None

    @pytest.mark.asyncio
    async def test_start_scan_dev_mode_no_db(self):
        """In dev mode without DB, start_scan returns immediate mock results."""
        result = await discovery_service.start_scan(
            project_id="test-project",
            tenant_id="test-tenant",
            subscription_id="00000000-0000-0000-0000-000000000001",
        )
        assert result["status"] == "completed"
        assert result["results"] is not None
        assert result["resources"] is not None
        assert len(result["resources"]) > 0

    @pytest.mark.asyncio
    async def test_start_scan_dev_mode_returns_id(self):
        """In dev mode, returned scan has an ID."""
        result = await discovery_service.start_scan(
            project_id="proj-1",
            tenant_id="tenant-1",
            subscription_id="sub-1",
        )
        assert "id" in result
        assert len(result["id"]) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_start_scan_dev_mode_resource_count(self):
        """In dev mode, resource_count matches the resources list."""
        result = await discovery_service.start_scan(
            project_id="proj-1",
            tenant_id="tenant-1",
            subscription_id="sub-1",
        )
        assert result["resource_count"] == len(result["resources"])

    @pytest.mark.asyncio
    async def test_start_scan_with_config(self):
        """Scan accepts optional scan_config."""
        config = {"include_types": ["Microsoft.Compute/virtualMachines"]}
        result = await discovery_service.start_scan(
            project_id="proj-1",
            tenant_id="tenant-1",
            subscription_id="sub-1",
            scan_config=config,
        )
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_scan_no_db(self):
        """get_scan with db=None returns None."""
        result = await discovery_service.get_scan("nonexistent", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_scan_resources_no_db(self):
        """get_scan_resources with db=None returns empty list."""
        result = await discovery_service.get_scan_resources("nonexistent", None)
        assert result == []


# ---------------------------------------------------------------------------
# Route integration tests
# ---------------------------------------------------------------------------

class TestDiscoveryRoutes:
    """Integration tests for discovery API routes."""

    @pytest.mark.asyncio
    async def test_start_scan_returns_200(self):
        """POST /api/discovery/scan returns 200 with scan data."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/discovery/scan",
                json={
                    "project_id": "test-project",
                    "subscription_id": "00000000-0000-0000-0000-000000000001",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["subscription_id"] == "00000000-0000-0000-0000-000000000001"

    @pytest.mark.asyncio
    async def test_start_scan_dev_mode_completed(self):
        """In dev mode, scan returns completed status immediately."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/discovery/scan",
                json={
                    "project_id": "test-project",
                    "subscription_id": "sub-123",
                },
            )
        data = response.json()
        assert data["status"] == "completed"
        assert data["results"] is not None

    @pytest.mark.asyncio
    async def test_start_scan_dev_mode_resource_count(self):
        """In dev mode, response includes resource_count."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/discovery/scan",
                json={
                    "project_id": "proj-1",
                    "subscription_id": "sub-1",
                },
            )
        data = response.json()
        assert data["resource_count"] > 0

    @pytest.mark.asyncio
    async def test_start_scan_missing_fields(self):
        """POST /api/discovery/scan without required fields returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/discovery/scan", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_start_scan_missing_subscription(self):
        """Missing subscription_id returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/discovery/scan",
                json={"project_id": "test-project"},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_start_scan_with_config(self):
        """Scan accepts scan_config."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/discovery/scan",
                json={
                    "project_id": "proj-1",
                    "subscription_id": "sub-1",
                    "scan_config": {"scope": "limited"},
                },
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_scan_not_found(self):
        """GET /api/discovery/scan/{id} with unknown ID returns 404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/discovery/scan/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_scan_resources_not_found(self):
        """GET /api/discovery/scan/{id}/resources with unknown scan returns 404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/discovery/scan/nonexistent/resources")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_start_scan_response_shape(self):
        """Scan response has all expected fields."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/discovery/scan",
                json={
                    "project_id": "proj-1",
                    "subscription_id": "sub-1",
                },
            )
        data = response.json()
        assert "id" in data
        assert "project_id" in data
        assert "subscription_id" in data
        assert "status" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_start_scan_results_contain_summary(self):
        """In dev mode, results contain summary data."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/discovery/scan",
                json={
                    "project_id": "proj-1",
                    "subscription_id": "sub-1",
                },
            )
        data = response.json()
        results = data["results"]
        assert "subscription" in results
        assert "resource_groups" in results
        assert "summary" in results


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestDiscoverySchemas:
    """Tests for discovery Pydantic schemas."""

    def test_scan_create_valid(self):
        """DiscoveryScanCreate accepts valid input."""
        from app.schemas.discovery import DiscoveryScanCreate
        scan = DiscoveryScanCreate(
            project_id="proj-1",
            subscription_id="sub-1",
        )
        assert scan.project_id == "proj-1"
        assert scan.subscription_id == "sub-1"
        assert scan.scan_config is None

    def test_scan_create_with_config(self):
        """DiscoveryScanCreate accepts scan_config."""
        from app.schemas.discovery import DiscoveryScanCreate
        scan = DiscoveryScanCreate(
            project_id="proj-1",
            subscription_id="sub-1",
            scan_config={"scope": "limited"},
        )
        assert scan.scan_config == {"scope": "limited"}

    def test_scan_status_enum(self):
        """ScanStatus enum has correct values."""
        from app.schemas.discovery import ScanStatus
        assert ScanStatus.PENDING == "pending"
        assert ScanStatus.SCANNING == "scanning"
        assert ScanStatus.COMPLETED == "completed"
        assert ScanStatus.FAILED == "failed"

    def test_resource_category_enum(self):
        """ResourceCategory enum has correct values."""
        from app.schemas.discovery import ResourceCategory
        assert ResourceCategory.RESOURCE == "resource"
        assert ResourceCategory.POLICY == "policy"
        assert ResourceCategory.RBAC == "rbac"
        assert ResourceCategory.NETWORK == "network"

    def test_scan_response_model(self):
        """DiscoveryScanResponse accepts all fields."""
        from datetime import datetime, timezone
        from app.schemas.discovery import DiscoveryScanResponse
        now = datetime.now(timezone.utc)
        resp = DiscoveryScanResponse(
            id="scan-1",
            project_id="proj-1",
            subscription_id="sub-1",
            status="completed",
            results={"key": "value"},
            resource_count=5,
            created_at=now,
            updated_at=now,
        )
        assert resp.id == "scan-1"
        assert resp.resource_count == 5

    def test_discovered_resource_response(self):
        """DiscoveredResourceResponse accepts valid data."""
        from datetime import datetime, timezone
        from app.schemas.discovery import DiscoveredResourceResponse
        now = datetime.now(timezone.utc)
        res = DiscoveredResourceResponse(
            id="res-1",
            scan_id="scan-1",
            category="resource",
            resource_type="Microsoft.Compute/virtualMachines",
            resource_id="/subscriptions/sub/resourceGroups/rg/...",
            name="vm-01",
            created_at=now,
        )
        assert res.category == "resource"

    def test_discovered_resource_list(self):
        """DiscoveredResourceList holds list with total."""
        from app.schemas.discovery import DiscoveredResourceList
        lst = DiscoveredResourceList(
            resources=[],
            total=0,
            scan_id="scan-1",
        )
        assert lst.total == 0
        assert lst.scan_id == "scan-1"


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestDiscoveryModels:
    """Tests for discovery SQLAlchemy models."""

    def test_discovery_scan_table_name(self):
        """DiscoveryScan has correct table name."""
        from app.models.discovery import DiscoveryScan
        assert DiscoveryScan.__tablename__ == "discovery_scans"

    def test_discovered_resource_table_name(self):
        """DiscoveredResource has correct table name."""
        from app.models.discovery import DiscoveredResource
        assert DiscoveredResource.__tablename__ == "discovered_resources"

    def test_discovery_scan_in_all_models(self):
        """DiscoveryScan is exported from models __init__."""
        from app.models import DiscoveryScan
        assert DiscoveryScan is not None

    def test_discovered_resource_in_all_models(self):
        """DiscoveredResource is exported from models __init__."""
        from app.models import DiscoveredResource
        assert DiscoveredResource is not None

    def test_scan_has_timestamp_columns(self):
        """DiscoveryScan includes TimestampMixin columns."""
        from app.models.discovery import DiscoveryScan
        columns = {c.name for c in DiscoveryScan.__table__.columns}
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_scan_has_required_columns(self):
        """DiscoveryScan has all expected columns."""
        from app.models.discovery import DiscoveryScan
        columns = {c.name for c in DiscoveryScan.__table__.columns}
        assert "id" in columns
        assert "project_id" in columns
        assert "tenant_id" in columns
        assert "subscription_id" in columns
        assert "status" in columns
        assert "scan_config" in columns
        assert "results" in columns
        assert "error_message" in columns

    def test_resource_has_required_columns(self):
        """DiscoveredResource has all expected columns."""
        from app.models.discovery import DiscoveredResource
        columns = {c.name for c in DiscoveredResource.__table__.columns}
        assert "id" in columns
        assert "scan_id" in columns
        assert "category" in columns
        assert "resource_type" in columns
        assert "resource_id" in columns
        assert "resource_group" in columns
        assert "name" in columns
        assert "properties" in columns


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------

class TestDiscoveryMigration:
    """Tests for the discovery migration file."""

    def _load_migration(self):
        """Load the migration module (filename starts with a digit)."""
        import importlib.util
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "app", "db", "migrations", "versions",
            "004_add_discovery_tables.py",
        )
        spec = importlib.util.spec_from_file_location("migration_004", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_migration_revision(self):
        """Migration 004 has correct revision chain."""
        m = self._load_migration()
        assert m.revision == "004"
        assert m.down_revision == "003"

    def test_migration_has_upgrade(self):
        """Migration has upgrade function."""
        m = self._load_migration()
        assert callable(m.upgrade)

    def test_migration_has_downgrade(self):
        """Migration has downgrade function."""
        m = self._load_migration()
        assert callable(m.downgrade)


# ---------------------------------------------------------------------------
# Azure SDK mock tests — covers _sync_scan and _scan_azure paths
# ---------------------------------------------------------------------------

class TestDiscoveryServiceAzureMock:
    """Tests for Azure SDK scanning with mocked SDK clients."""

    def _setup_azure_mocks(self):
        """Set up mock Azure SDK modules in sys.modules."""
        import sys

        mock_modules = {}
        for mod_name in [
            "azure", "azure.mgmt", "azure.mgmt.resource",
            "azure.mgmt.resource.policy",
            "azure.mgmt.network", "azure.mgmt.authorization",
            "azure.identity",
        ]:
            mock_modules[mod_name] = MagicMock()

        originals = {}
        for name, mock_mod in mock_modules.items():
            originals[name] = sys.modules.get(name)
            sys.modules[name] = mock_mod

        return originals, mock_modules

    def _teardown_azure_mocks(self, originals):
        """Restore original sys.modules state."""
        import sys
        for name, orig in originals.items():
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig

    def _make_mock_resource(self, name, rtype, rid, location="eastus2", tags=None):
        """Create a mock Azure resource object."""
        res = MagicMock()
        res.name = name
        res.type = rtype
        res.id = rid
        res.location = location
        res.kind = None
        res.tags = tags or {}
        return res

    def _make_mock_rg(self, name, location="eastus2", tags=None):
        """Create a mock Azure resource group object."""
        rg = MagicMock()
        rg.name = name
        rg.location = location
        rg.tags = tags or {}
        return rg

    def _make_mock_vnet(self, name, vid, subnets=None):
        """Create a mock VNet object."""
        vnet = MagicMock()
        vnet.name = name
        vnet.id = vid
        vnet.location = "eastus2"
        vnet.address_space = MagicMock()
        vnet.address_space.address_prefixes = ["10.0.0.0/16"]
        if subnets:
            subnet_mocks = []
            for s in subnets:
                sm = MagicMock()
                sm.name = s
                subnet_mocks.append(sm)
            vnet.subnets = subnet_mocks
        else:
            vnet.subnets = []
        return vnet

    def _make_mock_nsg(self, name, nid, rule_count=3):
        """Create a mock NSG object."""
        nsg = MagicMock()
        nsg.name = name
        nsg.id = nid
        nsg.location = "eastus2"
        nsg.security_rules = [MagicMock() for _ in range(rule_count)]
        return nsg

    def _make_mock_policy_assignment(self, name, display_name, pa_id):
        """Create a mock policy assignment object."""
        pa = MagicMock()
        pa.name = name
        pa.display_name = display_name
        pa.id = pa_id
        pa.policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/test"
        pa.scope = "/subscriptions/sub-1"
        pa.enforcement_mode = MagicMock()
        pa.enforcement_mode.value = "Default"
        return pa

    def _make_mock_role_assignment(self, ra_id, role_def_id, principal_id):
        """Create a mock RBAC role assignment object."""
        ra = MagicMock()
        ra.id = ra_id
        ra.role_definition_id = role_def_id
        ra.principal_id = principal_id
        ra.principal_type = MagicMock()
        ra.principal_type.value = "User"
        ra.scope = "/subscriptions/sub-1"
        return ra

    def _run_sync_scan_with_mocks(
        self, resource_groups=None, resources=None,
        vnets=None, nsgs=None, policies=None, rbac_assignments=None,
        resource_error=None, network_error=None,
        policy_error=None, rbac_error=None,
    ):
        """Helper that patches Azure SDK modules and runs _sync_scan."""
        originals, mock_modules = self._setup_azure_mocks()
        try:
            mock_rmc = MagicMock()
            mock_nmc = MagicMock()
            mock_pc = MagicMock()
            mock_amc = MagicMock()

            if resource_error:
                mock_rmc.resource_groups.list.side_effect = resource_error
            else:
                mock_rmc.resource_groups.list.return_value = resource_groups or []
                mock_rmc.resources.list.return_value = resources or []

            if network_error:
                mock_nmc.virtual_networks.list_all.side_effect = network_error
            else:
                mock_nmc.virtual_networks.list_all.return_value = vnets or []
                mock_nmc.network_security_groups.list_all.return_value = nsgs or []

            if policy_error:
                mock_pc.policy_assignments.list_for_subscription.side_effect = policy_error
            else:
                mock_pc.policy_assignments.list_for_subscription.return_value = (
                    policies or []
                )

            if rbac_error:
                mock_amc.role_assignments.list_for_scope.side_effect = rbac_error
            else:
                mock_amc.role_assignments.list_for_scope.return_value = (
                    rbac_assignments or []
                )

            # Wire up constructors
            mock_modules["azure.mgmt.resource"].ResourceManagementClient.return_value = (
                mock_rmc
            )
            mock_modules["azure.mgmt.network"].NetworkManagementClient.return_value = (
                mock_nmc
            )
            mock_modules["azure.mgmt.resource.policy"].PolicyClient.return_value = (
                mock_pc
            )
            mock_modules[
                "azure.mgmt.authorization"
            ].AuthorizationManagementClient.return_value = mock_amc

            svc = DiscoveryService()
            credential = MagicMock()
            return svc._sync_scan(credential, "sub-1", None)
        finally:
            self._teardown_azure_mocks(originals)

    def test_sync_scan_resources(self):
        """_sync_scan discovers resources from ResourceManagementClient."""
        base_id = "/subscriptions/sub-1/resourceGroups/rg-test"
        mock_resource = self._make_mock_resource(
            "vm-01", "Microsoft.Compute/virtualMachines",
            f"{base_id}/providers/Microsoft.Compute/virtualMachines/vm-01"
        )
        mock_rg = self._make_mock_rg("rg-test")

        resources, summary = self._run_sync_scan_with_mocks(
            resource_groups=[mock_rg], resources=[mock_resource],
        )

        assert summary["total_resource_groups"] == 1
        assert summary["total_resources"] == 1
        assert any(r["name"] == "vm-01" for r in resources)

    def test_sync_scan_networks(self):
        """_sync_scan discovers VNets and NSGs."""
        mock_vnet = self._make_mock_vnet(
            "vnet-hub",
            "/subscriptions/sub-1/resourceGroups/rg-net/providers"
            "/Microsoft.Network/virtualNetworks/vnet-hub",
            subnets=["default", "GatewaySubnet"],
        )
        mock_nsg = self._make_mock_nsg(
            "nsg-01",
            "/subscriptions/sub-1/resourceGroups/rg-net/providers"
            "/Microsoft.Network/networkSecurityGroups/nsg-01",
        )

        resources, summary = self._run_sync_scan_with_mocks(
            vnets=[mock_vnet], nsgs=[mock_nsg],
        )

        assert summary["total_vnets"] == 1
        assert summary["total_nsgs"] == 1
        network_resources = [r for r in resources if r["category"] == CATEGORY_NETWORK]
        assert len(network_resources) == 2

    def test_sync_scan_policies(self):
        """_sync_scan discovers policy assignments."""
        mock_pa = self._make_mock_policy_assignment(
            "require-tags", "Require Tags",
            "/subscriptions/sub-1/providers/Microsoft.Authorization"
            "/policyAssignments/require-tags"
        )

        resources, summary = self._run_sync_scan_with_mocks(policies=[mock_pa])

        assert summary["total_policies"] == 1
        policy_resources = [r for r in resources if r["category"] == CATEGORY_POLICY]
        assert len(policy_resources) == 1
        assert policy_resources[0]["name"] == "Require Tags"

    def test_sync_scan_rbac(self):
        """_sync_scan discovers RBAC role assignments."""
        mock_ra = self._make_mock_role_assignment(
            "/subscriptions/sub-1/providers/ra-1",
            "/providers/Microsoft.Authorization/roleDefinitions/owner-id",
            "principal-123",
        )

        resources, summary = self._run_sync_scan_with_mocks(
            rbac_assignments=[mock_ra],
        )

        assert summary["total_role_assignments"] == 1
        rbac_resources = [r for r in resources if r["category"] == CATEGORY_RBAC]
        assert len(rbac_resources) == 1

    def test_sync_scan_resource_error_handled(self):
        """_sync_scan handles errors in resource discovery gracefully."""
        _, summary = self._run_sync_scan_with_mocks(
            resource_error=Exception("Auth error"),
        )
        assert "resource_error" in summary

    def test_sync_scan_network_error_handled(self):
        """_sync_scan handles network discovery errors gracefully."""
        _, summary = self._run_sync_scan_with_mocks(
            network_error=Exception("Net fail"),
        )
        assert "network_error" in summary

    def test_sync_scan_policy_error_handled(self):
        """_sync_scan handles policy discovery errors gracefully."""
        _, summary = self._run_sync_scan_with_mocks(
            policy_error=Exception("Policy error"),
        )
        assert "policy_error" in summary

    def test_sync_scan_rbac_error_handled(self):
        """_sync_scan handles RBAC discovery errors gracefully."""
        _, summary = self._run_sync_scan_with_mocks(
            rbac_error=Exception("RBAC error"),
        )
        assert "rbac_error" in summary

    @pytest.mark.asyncio
    async def test_scan_azure_no_credential_raises(self):
        """_scan_azure raises RuntimeError when credential is None."""
        svc = DiscoveryService()
        with pytest.raises(RuntimeError, match="Azure credentials not available"):
            await svc._scan_azure("sub-1", None)

    @pytest.mark.asyncio
    async def test_scan_azure_with_mock_credential(self):
        """_scan_azure calls _sync_scan in a thread."""
        svc = DiscoveryService()
        mock_resources = [{"id": "r1", "category": "resource",
                          "resource_type": "t", "resource_id": "rid", "name": "n"}]
        mock_summary = {"total": 1}

        with patch.object(svc, "_get_credential", return_value=MagicMock()), \
             patch.object(
                 svc, "_sync_scan",
                 return_value=(mock_resources, mock_summary),
             ):
            resources, summary = await svc._scan_azure("sub-1", None)

        assert resources == mock_resources
        assert summary == mock_summary

    def test_sync_scan_full_integration(self):
        """_sync_scan processes all four discovery sections together."""
        base_id = "/subscriptions/sub-1"
        mock_rg = self._make_mock_rg("rg-app")
        mock_resource = self._make_mock_resource(
            "kv-01", "Microsoft.KeyVault/vaults",
            f"{base_id}/resourceGroups/rg-app/providers"
            "/Microsoft.KeyVault/vaults/kv-01"
        )
        mock_vnet = self._make_mock_vnet(
            "vnet-01",
            f"{base_id}/resourceGroups/rg-net/providers"
            "/Microsoft.Network/virtualNetworks/vnet-01",
        )
        mock_nsg = self._make_mock_nsg(
            "nsg-01",
            f"{base_id}/resourceGroups/rg-net/providers"
            "/Microsoft.Network/networkSecurityGroups/nsg-01",
        )
        mock_pa = self._make_mock_policy_assignment(
            "p1", "Policy 1", f"{base_id}/providers/p1"
        )
        mock_ra = self._make_mock_role_assignment(
            f"{base_id}/providers/ra1", "role-def-1", "principal-1"
        )

        resources, summary = self._run_sync_scan_with_mocks(
            resource_groups=[mock_rg], resources=[mock_resource],
            vnets=[mock_vnet], nsgs=[mock_nsg],
            policies=[mock_pa], rbac_assignments=[mock_ra],
        )

        assert len(resources) == 5
        assert summary["total_resource_groups"] == 1
        assert summary["total_resources"] == 1
        assert summary["total_vnets"] == 1
        assert summary["total_nsgs"] == 1
        assert summary["total_policies"] == 1
        assert summary["total_role_assignments"] == 1
        assert "scanned_at" in summary

    def test_sync_scan_resource_group_extraction(self):
        """_sync_scan correctly extracts resource group from resource ID."""
        mock_resource = self._make_mock_resource(
            "sa-01", "Microsoft.Storage/storageAccounts",
            "/subscriptions/sub-1/resourceGroups/my-rg-name/providers"
            "/Microsoft.Storage/storageAccounts/sa-01"
        )
        mock_rg = self._make_mock_rg("my-rg-name")

        resources, _ = self._run_sync_scan_with_mocks(
            resource_groups=[mock_rg], resources=[mock_resource],
        )

        resource = next(r for r in resources if r["name"] == "sa-01")
        assert resource["resource_group"] == "my-rg-name"

    def test_sync_scan_resource_with_tags(self):
        """_sync_scan preserves resource tags in properties."""
        mock_resource = self._make_mock_resource(
            "vm-tagged", "Microsoft.Compute/virtualMachines",
            "/subscriptions/sub-1/resourceGroups/rg/providers"
            "/Microsoft.Compute/virtualMachines/vm-tagged",
            tags={"environment": "prod", "team": "platform"},
        )

        resources, _ = self._run_sync_scan_with_mocks(
            resources=[mock_resource],
        )

        resource = next(r for r in resources if r["name"] == "vm-tagged")
        assert resource["properties"]["tags"]["environment"] == "prod"
