"""Comprehensive Azure SKU database service.

Provides structured SKU data for compute, storage, database and networking
resources with filtering, recommendation and comparison capabilities.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static SKU data
# ---------------------------------------------------------------------------

COMPUTE_SKUS: list[dict[str, Any]] = [
    # B-series (burstable)
    {
        "id": "b2s",
        "name": "Standard_B2s",
        "family": "B",
        "vcpus": 2,
        "ram_gb": 4,
        "disk_gb": 8,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "low",
        "use_case": "Dev/test, light workloads",
    },
    {
        "id": "b4ms",
        "name": "Standard_B4ms",
        "family": "B",
        "vcpus": 4,
        "ram_gb": 16,
        "disk_gb": 32,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "low",
        "use_case": "Dev/test, small web apps",
    },
    # D-series (general purpose)
    {
        "id": "d2s_v5",
        "name": "Standard_D2s_v5",
        "family": "D",
        "vcpus": 2,
        "ram_gb": 8,
        "disk_gb": 0,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "low",
        "use_case": "General purpose workloads",
    },
    {
        "id": "d4s_v5",
        "name": "Standard_D4s_v5",
        "family": "D",
        "vcpus": 4,
        "ram_gb": 16,
        "disk_gb": 0,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "medium",
        "use_case": "General purpose workloads",
    },
    {
        "id": "d8s_v5",
        "name": "Standard_D8s_v5",
        "family": "D",
        "vcpus": 8,
        "ram_gb": 32,
        "disk_gb": 0,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "medium",
        "use_case": "Medium workloads, app servers",
    },
    {
        "id": "d16s_v5",
        "name": "Standard_D16s_v5",
        "family": "D",
        "vcpus": 16,
        "ram_gb": 64,
        "disk_gb": 0,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "medium",
        "use_case": "Large app servers, caching",
    },
    # E-series (memory optimized)
    {
        "id": "e4s_v5",
        "name": "Standard_E4s_v5",
        "family": "E",
        "vcpus": 4,
        "ram_gb": 32,
        "disk_gb": 0,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "medium",
        "use_case": "Memory-intensive, databases",
    },
    {
        "id": "e8s_v5",
        "name": "Standard_E8s_v5",
        "family": "E",
        "vcpus": 8,
        "ram_gb": 64,
        "disk_gb": 0,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "medium",
        "use_case": "In-memory analytics",
    },
    {
        "id": "e16s_v5",
        "name": "Standard_E16s_v5",
        "family": "E",
        "vcpus": 16,
        "ram_gb": 128,
        "disk_gb": 0,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "high",
        "use_case": "Large databases, SAP",
    },
    # F-series (compute optimized)
    {
        "id": "f4s_v2",
        "name": "Standard_F4s_v2",
        "family": "F",
        "vcpus": 4,
        "ram_gb": 8,
        "disk_gb": 32,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "medium",
        "use_case": "Compute-intensive, batch processing",
    },
    {
        "id": "f8s_v2",
        "name": "Standard_F8s_v2",
        "family": "F",
        "vcpus": 8,
        "ram_gb": 16,
        "disk_gb": 64,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "medium",
        "use_case": "High-performance computing",
    },
    # H-series (HPC)
    {
        "id": "hb120rs_v3",
        "name": "Standard_HB120rs_v3",
        "family": "H",
        "vcpus": 120,
        "ram_gb": 448,
        "disk_gb": 960,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "premium",
        "use_case": "HPC, fluid dynamics, weather modeling",
    },
    # L-series (storage optimized)
    {
        "id": "l8s_v3",
        "name": "Standard_L8s_v3",
        "family": "L",
        "vcpus": 8,
        "ram_gb": 64,
        "disk_gb": 1600,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "high",
        "use_case": "Storage-intensive, big data",
    },
    # M-series (memory optimized — SAP certified)
    {
        "id": "m32ts",
        "name": "Standard_M32ts",
        "family": "M",
        "vcpus": 32,
        "ram_gb": 192,
        "disk_gb": 1000,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "premium",
        "use_case": "SAP HANA, large in-memory databases",
    },
    {
        "id": "m64s",
        "name": "Standard_M64s",
        "family": "M",
        "vcpus": 64,
        "ram_gb": 1024,
        "disk_gb": 2000,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "premium",
        "use_case": "SAP HANA, very large databases",
    },
    # N-series (GPU)
    {
        "id": "nc6s_v3",
        "name": "Standard_NC6s_v3",
        "family": "N",
        "vcpus": 6,
        "ram_gb": 112,
        "disk_gb": 736,
        "gpu": "V100",
        "gpu_count": 1,
        "price_tier": "high",
        "use_case": "ML training, inference",
    },
    {
        "id": "nc24s_v3",
        "name": "Standard_NC24s_v3",
        "family": "N",
        "vcpus": 24,
        "ram_gb": 448,
        "disk_gb": 2948,
        "gpu": "V100",
        "gpu_count": 4,
        "price_tier": "premium",
        "use_case": "Large-scale ML training",
    },
    # G-series (large memory)
    {
        "id": "g5",
        "name": "Standard_G5",
        "family": "G",
        "vcpus": 32,
        "ram_gb": 448,
        "disk_gb": 6144,
        "gpu": None,
        "gpu_count": 0,
        "price_tier": "premium",
        "use_case": "Large databases, data warehouses",
    },
]

STORAGE_SKUS: list[dict[str, Any]] = [
    {
        "id": "standard_hdd_lrs",
        "name": "Standard HDD LRS",
        "tier": "standard",
        "media": "hdd",
        "redundancy": "LRS",
        "max_iops": 500,
        "max_throughput_mbps": 60,
        "price_tier": "low",
        "use_case": "Backups, infrequent access",
    },
    {
        "id": "standard_ssd_lrs",
        "name": "Standard SSD LRS",
        "tier": "standard",
        "media": "ssd",
        "redundancy": "LRS",
        "max_iops": 6000,
        "max_throughput_mbps": 750,
        "price_tier": "medium",
        "use_case": "Web servers, light dev/test",
    },
    {
        "id": "premium_ssd_lrs",
        "name": "Premium SSD LRS",
        "tier": "premium",
        "media": "ssd",
        "redundancy": "LRS",
        "max_iops": 20000,
        "max_throughput_mbps": 900,
        "price_tier": "high",
        "use_case": "Production workloads, databases",
    },
    {
        "id": "premium_ssd_zrs",
        "name": "Premium SSD ZRS",
        "tier": "premium",
        "media": "ssd",
        "redundancy": "ZRS",
        "max_iops": 20000,
        "max_throughput_mbps": 900,
        "price_tier": "high",
        "use_case": "Zone-redundant production workloads",
    },
    {
        "id": "ultra_disk",
        "name": "Ultra Disk",
        "tier": "ultra",
        "media": "ssd",
        "redundancy": "LRS",
        "max_iops": 160000,
        "max_throughput_mbps": 4000,
        "price_tier": "premium",
        "use_case": "SAP HANA, high-perf databases",
    },
]

DATABASE_SKUS: list[dict[str, Any]] = [
    # Azure SQL — DTU model
    {
        "id": "sql_basic",
        "name": "Azure SQL Basic",
        "service": "azure_sql",
        "model": "dtu",
        "tier": "basic",
        "dtus": 5,
        "max_storage_gb": 2,
        "price_tier": "low",
        "use_case": "Light workloads, dev/test",
    },
    {
        "id": "sql_standard_s0",
        "name": "Azure SQL Standard S0",
        "service": "azure_sql",
        "model": "dtu",
        "tier": "standard",
        "dtus": 10,
        "max_storage_gb": 250,
        "price_tier": "low",
        "use_case": "Small production databases",
    },
    {
        "id": "sql_standard_s3",
        "name": "Azure SQL Standard S3",
        "service": "azure_sql",
        "model": "dtu",
        "tier": "standard",
        "dtus": 100,
        "max_storage_gb": 250,
        "price_tier": "medium",
        "use_case": "Medium production databases",
    },
    # Azure SQL — vCore model
    {
        "id": "sql_gp_2v",
        "name": "Azure SQL GP 2 vCores",
        "service": "azure_sql",
        "model": "vcore",
        "tier": "general_purpose",
        "vcores": 2,
        "max_storage_gb": 1024,
        "price_tier": "medium",
        "use_case": "General purpose workloads",
    },
    {
        "id": "sql_bc_4v",
        "name": "Azure SQL BC 4 vCores",
        "service": "azure_sql",
        "model": "vcore",
        "tier": "business_critical",
        "vcores": 4,
        "max_storage_gb": 1024,
        "price_tier": "high",
        "use_case": "Mission-critical, low latency",
    },
    # Cosmos DB
    {
        "id": "cosmos_serverless",
        "name": "Cosmos DB Serverless",
        "service": "cosmos_db",
        "model": "serverless",
        "tier": "serverless",
        "max_ru_per_request": 5000,
        "price_tier": "low",
        "use_case": "Sporadic traffic, dev/test",
    },
    {
        "id": "cosmos_provisioned_400",
        "name": "Cosmos DB 400 RU/s",
        "service": "cosmos_db",
        "model": "provisioned",
        "tier": "standard",
        "provisioned_rus": 400,
        "price_tier": "low",
        "use_case": "Small consistent workloads",
    },
    {
        "id": "cosmos_autoscale_4000",
        "name": "Cosmos DB Autoscale 4000 RU/s",
        "service": "cosmos_db",
        "model": "autoscale",
        "tier": "standard",
        "max_rus": 4000,
        "price_tier": "medium",
        "use_case": "Variable traffic patterns",
    },
    # PostgreSQL
    {
        "id": "pg_burstable_b1ms",
        "name": "PostgreSQL Burstable B1ms",
        "service": "postgresql",
        "model": "flexible",
        "tier": "burstable",
        "vcores": 1,
        "max_storage_gb": 32,
        "price_tier": "low",
        "use_case": "Dev/test, light workloads",
    },
    {
        "id": "pg_gp_d2s",
        "name": "PostgreSQL GP D2s v3",
        "service": "postgresql",
        "model": "flexible",
        "tier": "general_purpose",
        "vcores": 2,
        "max_storage_gb": 16384,
        "price_tier": "medium",
        "use_case": "Production workloads",
    },
]

NETWORKING_SKUS: list[dict[str, Any]] = [
    # VPN Gateway
    {
        "id": "vpn_basic",
        "name": "VPN Gateway Basic",
        "service": "vpn_gateway",
        "tier": "basic",
        "bandwidth_mbps": 100,
        "tunnels": 10,
        "price_tier": "low",
        "use_case": "Dev/test, small offices",
    },
    {
        "id": "vpn_vpngw1",
        "name": "VPN Gateway VpnGw1",
        "service": "vpn_gateway",
        "tier": "generation1",
        "bandwidth_mbps": 650,
        "tunnels": 30,
        "price_tier": "medium",
        "use_case": "Production site-to-site VPN",
    },
    {
        "id": "vpn_vpngw2",
        "name": "VPN Gateway VpnGw2",
        "service": "vpn_gateway",
        "tier": "generation1",
        "bandwidth_mbps": 1000,
        "tunnels": 30,
        "price_tier": "high",
        "use_case": "High-bandwidth site-to-site VPN",
    },
    # Application Gateway
    {
        "id": "appgw_standard_v2",
        "name": "Application Gateway Standard v2",
        "service": "app_gateway",
        "tier": "standard_v2",
        "max_capacity_units": 125,
        "waf": False,
        "price_tier": "medium",
        "use_case": "HTTP(S) load balancing, routing",
    },
    {
        "id": "appgw_waf_v2",
        "name": "Application Gateway WAF v2",
        "service": "app_gateway",
        "tier": "waf_v2",
        "max_capacity_units": 125,
        "waf": True,
        "price_tier": "high",
        "use_case": "Web application firewall",
    },
    # Load Balancer
    {
        "id": "lb_basic",
        "name": "Load Balancer Basic",
        "service": "load_balancer",
        "tier": "basic",
        "price_tier": "low",
        "use_case": "Dev/test, small-scale",
    },
    {
        "id": "lb_standard",
        "name": "Load Balancer Standard",
        "service": "load_balancer",
        "tier": "standard",
        "price_tier": "medium",
        "use_case": "Production, zone-redundant",
    },
]

# Regions where SKUs have known restrictions
SKU_REGION_RESTRICTIONS: dict[str, set[str]] = {
    "Standard_NC6s_v3": {"brazilsouth", "southafricanorth"},
    "Standard_NC24s_v3": {"brazilsouth", "southafricanorth"},
    "Standard_ND40rs_v2": {"brazilsouth", "southafricanorth", "southeastasia"},
    "Standard_HB120rs_v3": {"brazilsouth", "southafricanorth"},
    "ultra_disk": {"brazilsouth"},
}

# Cloud-specific SKU restrictions
CLOUD_SKU_RESTRICTIONS: dict[str, set[str]] = {
    "government": {
        "Standard_NC24s_v3",
        "Standard_ND40rs_v2",
        "Standard_HB120rs_v3",
    },
    "china": {
        "Standard_NC24s_v3",
        "Standard_ND40rs_v2",
        "Standard_HB120rs_v3",
        "Standard_G5",
    },
}


class SkuDatabaseService:
    """Service providing Azure SKU data with filtering and recommendations.

    Organizes compute, storage, database and networking SKUs and offers
    filtering, comparison and availability-validation helpers.
    """

    def __init__(self) -> None:
        self._compute = COMPUTE_SKUS
        self._storage = STORAGE_SKUS
        self._database = DATABASE_SKUS
        self._networking = NETWORKING_SKUS

    # -- filtering helpers -----------------------------------------------

    @staticmethod
    def _matches_filters(sku: dict[str, Any], filters: dict[str, Any] | None) -> bool:
        """Return True if *sku* passes all *filters*.

        Supported filter keys:
        - ``family``: exact match on family field
        - ``min_vcpus``: sku vcpus >= value
        - ``min_ram``: sku ram_gb >= value
        - ``gpu``: if truthy, sku must have a gpu
        - ``tier``: exact match on tier field
        - ``media``: exact match on media field
        - ``service``: exact match on service field
        - ``price_tier``: exact match on price_tier field
        """
        if not filters:
            return True
        if "family" in filters and sku.get("family") != filters["family"]:
            return False
        if "min_vcpus" in filters and sku.get("vcpus", 0) < filters["min_vcpus"]:
            return False
        if "min_ram" in filters and sku.get("ram_gb", 0) < filters["min_ram"]:
            return False
        if filters.get("gpu") and not sku.get("gpu"):
            return False
        if "tier" in filters and sku.get("tier") != filters["tier"]:
            return False
        if "media" in filters and sku.get("media") != filters["media"]:
            return False
        if "service" in filters and sku.get("service") != filters["service"]:
            return False
        if "price_tier" in filters and sku.get("price_tier") != filters["price_tier"]:
            return False
        return True

    # -- public API -------------------------------------------------------

    def get_compute_skus(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return compute SKUs, optionally filtered.

        Args:
            filters: Optional dict of filter criteria.

        Returns:
            List of matching compute SKU dicts.
        """
        return [s for s in self._compute if self._matches_filters(s, filters)]

    def get_storage_skus(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return storage SKUs, optionally filtered.

        Args:
            filters: Optional dict of filter criteria.

        Returns:
            List of matching storage SKU dicts.
        """
        return [s for s in self._storage if self._matches_filters(s, filters)]

    def get_database_skus(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return database SKUs, optionally filtered.

        Args:
            filters: Optional dict of filter criteria.

        Returns:
            List of matching database SKU dicts.
        """
        return [s for s in self._database if self._matches_filters(s, filters)]

    def get_networking_skus(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return networking SKUs, optionally filtered.

        Args:
            filters: Optional dict of filter criteria.

        Returns:
            List of matching networking SKU dicts.
        """
        return [s for s in self._networking if self._matches_filters(s, filters)]

    def recommend_sku(
        self, workload_type: str, requirements: dict[str, Any]
    ) -> dict[str, Any]:
        """Recommend the best-fit compute SKU for a workload.

        Args:
            workload_type: Workload category (``ai_ml``, ``sap``, ``avd``,
                ``iot``, ``general``).
            requirements: Dict with optional ``min_vcpus``, ``min_ram``,
                ``gpu``, ``budget`` keys.

        Returns:
            Dict with ``recommended_sku``, ``reason`` and ``alternatives``.
        """
        # Build filters from requirements
        filters: dict[str, Any] = {}
        if requirements.get("min_vcpus"):
            filters["min_vcpus"] = requirements["min_vcpus"]
        if requirements.get("min_ram"):
            filters["min_ram"] = requirements["min_ram"]
        if requirements.get("gpu"):
            filters["gpu"] = True

        # Workload-specific family preferences
        family_pref: dict[str, list[str]] = {
            "ai_ml": ["N", "D"],
            "sap": ["M", "E"],
            "avd": ["D", "B"],
            "iot": ["B", "D"],
            "general": ["D", "B", "E"],
        }
        preferred = family_pref.get(workload_type, ["D"])

        candidates = self.get_compute_skus(filters)
        if not candidates:
            # Relax filters and retry
            candidates = self._compute

        # Sort: preferred family first, then by vcpus ascending
        def sort_key(s: dict[str, Any]) -> tuple[int, int]:
            fam = s.get("family", "")
            prio = preferred.index(fam) if fam in preferred else len(preferred)
            return (prio, s.get("vcpus", 0))

        candidates = sorted(candidates, key=sort_key)

        best = candidates[0]
        alternatives = candidates[1:4]

        return {
            "recommended_sku": best,
            "reason": (
                f"Best match for {workload_type} workload with "
                f"{best.get('vcpus')} vCPUs and {best.get('ram_gb')} GB RAM."
            ),
            "alternatives": alternatives,
        }

    def get_sku_comparison(self, sku_ids: list[str]) -> list[dict[str, Any]]:
        """Return side-by-side data for the given SKU IDs.

        Args:
            sku_ids: List of SKU ``id`` strings to compare.

        Returns:
            List of matching SKU dicts (order matches input where found).
        """
        all_skus = self._compute + self._storage + self._database + self._networking
        lookup = {s["id"]: s for s in all_skus}
        return [lookup[sid] for sid in sku_ids if sid in lookup]

    def validate_sku_availability(
        self, sku: str, region: str, cloud_env: str = "commercial"
    ) -> dict[str, Any]:
        """Check whether a SKU is available in a region and cloud env.

        Args:
            sku: SKU name (e.g. ``Standard_NC6s_v3``).
            region: Azure region slug (e.g. ``eastus``).
            cloud_env: Cloud environment (``commercial``, ``government``,
                ``china``).

        Returns:
            Dict with ``available`` bool, ``sku``, ``region``,
            ``cloud_env`` and optional ``reason``.
        """
        region_lower = region.lower()

        # Check cloud-level restrictions
        cloud_restricted = CLOUD_SKU_RESTRICTIONS.get(cloud_env, set())
        if sku in cloud_restricted:
            return {
                "available": False,
                "sku": sku,
                "region": region,
                "cloud_env": cloud_env,
                "reason": f"{sku} is not available in {cloud_env} cloud.",
            }

        # Check region-level restrictions
        region_restricted = SKU_REGION_RESTRICTIONS.get(sku, set())
        if region_lower in region_restricted:
            return {
                "available": False,
                "sku": sku,
                "region": region,
                "cloud_env": cloud_env,
                "reason": f"{sku} is not available in region {region}.",
            }

        return {
            "available": True,
            "sku": sku,
            "region": region,
            "cloud_env": cloud_env,
        }


# Module-level singleton.
sku_database_service = SkuDatabaseService()
