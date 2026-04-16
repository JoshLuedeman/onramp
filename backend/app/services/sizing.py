"""Right-sizing recommendation engine.

Maps workload profiles to specific Azure SKUs with cost estimates.  All
pricing data is embedded (no external API calls in dev mode).
"""

import logging

from app.schemas.sizing import (
    AppServiceRecommendation,
    AvailabilitySLA,
    CostEstimate,
    CostLineItem,
    CostPriority,
    DatabaseRecommendation,
    SKURecommendation,
    StorageRecommendation,
    VMRecommendation,
    WorkloadProfile,
    WorkloadType,
)
from app.services.pricing import pricing_service

logger = logging.getLogger(__name__)


class SizingEngine:
    """Singleton that produces right-sizing recommendations.

    The engine maps *WorkloadProfile* attributes (type, peak users,
    availability SLA, cost priority) to concrete Azure SKUs and
    estimates monthly costs using the embedded pricing data.
    """

    # ── Public API ───────────────────────────────────────────────────────

    def recommend_skus(
        self, workload_profile: WorkloadProfile
    ) -> list[SKURecommendation]:
        """Produce a full set of SKU recommendations for a workload profile."""
        recommendations: list[SKURecommendation] = []

        # VM recommendation
        vm = self.get_vm_recommendation(
            workload_profile.workload_type,
            workload_profile.peak_concurrent_users,
            workload_profile.cost_priority,
        )
        recommendations.append(
            SKURecommendation(
                resource_type="Microsoft.Compute/virtualMachines",
                recommended_sku=vm.sku,
                reasoning=vm.reasoning,
                monthly_cost_estimate=vm.monthly_cost_estimate,
                alternatives=self._vm_alternatives(
                    workload_profile.workload_type,
                    workload_profile.cost_priority,
                ),
            )
        )

        # App Service recommendation
        app_svc = self.get_app_service_recommendation(
            workload_profile.workload_type,
            workload_profile.peak_concurrent_users,
            workload_profile.cost_priority,
        )
        recommendations.append(
            SKURecommendation(
                resource_type="Microsoft.Web/serverFarms",
                recommended_sku=app_svc.sku,
                reasoning=app_svc.reasoning,
                monthly_cost_estimate=app_svc.monthly_cost_estimate,
                alternatives=self._app_service_alternatives(
                    workload_profile.cost_priority,
                ),
            )
        )

        # Database recommendation
        db = self.get_database_recommendation(
            workload_profile.workload_type,
            workload_profile.data_size_gb or 10.0,
            workload_profile.cost_priority,
        )
        recommendations.append(
            SKURecommendation(
                resource_type="Microsoft.Sql/servers/databases",
                recommended_sku=db.sku,
                reasoning=db.reasoning,
                monthly_cost_estimate=db.monthly_cost_estimate,
                alternatives=self._database_alternatives(
                    workload_profile.cost_priority,
                ),
            )
        )

        # Storage recommendation
        storage = self.get_storage_recommendation(
            workload_profile.availability,
            workload_profile.workload_type,
        )
        recommendations.append(
            SKURecommendation(
                resource_type="Microsoft.Storage/storageAccounts",
                recommended_sku=storage.sku,
                reasoning=storage.reasoning,
                monthly_cost_estimate=storage.monthly_cost_estimate,
                alternatives=self._storage_alternatives(
                    workload_profile.availability,
                ),
            )
        )

        return recommendations

    # ── VM recommendation ────────────────────────────────────────────────

    def get_vm_recommendation(
        self,
        workload_type: WorkloadType,
        peak_users: int,
        cost_priority: CostPriority,
    ) -> VMRecommendation:
        """Pick a VM SKU based on workload type, scale, and cost priority.

        Heuristics:
        * B-series for dev/test (low traffic, cost-optimized)
        * D-series for general purpose / web / API / microservices
        * E-series for memory-intensive (database, analytics)
        * N-series for GPU workloads (analytics + performance_first)
        """
        # GPU workloads
        if (
            workload_type == WorkloadType.ANALYTICS
            and cost_priority == CostPriority.PERFORMANCE_FIRST
        ):
            return VMRecommendation(
                sku="Standard_NC6s_v3",
                series="NC",
                vcpus=6,
                memory_gb=112,
                reasoning="GPU-accelerated analytics workload with performance priority",
                monthly_cost_estimate=pricing_service.get_price("Standard_NC6s_v3"),
            )

        # Memory-intensive
        if workload_type in (WorkloadType.DATABASE, WorkloadType.ANALYTICS):
            return self._memory_optimized_vm(peak_users, cost_priority)

        # Dev/test — cost-optimized
        if cost_priority == CostPriority.COST_OPTIMIZED and peak_users <= 100:
            return VMRecommendation(
                sku="Standard_B2s",
                series="B",
                vcpus=2,
                memory_gb=4,
                reasoning="Burstable B-series for cost-optimized low-traffic workloads",
                monthly_cost_estimate=pricing_service.get_price("Standard_B2s"),
            )

        # Batch workloads benefit from more vCPUs
        if workload_type == WorkloadType.BATCH:
            return self._batch_vm(peak_users, cost_priority)

        # General purpose (web_app, api, microservices)
        return self._general_purpose_vm(peak_users, cost_priority)

    # ── App Service recommendation ───────────────────────────────────────

    def get_app_service_recommendation(
        self,
        workload_type: WorkloadType,
        peak_users: int,
        cost_priority: CostPriority,
    ) -> AppServiceRecommendation:
        """Pick an App Service plan tier.

        F1/B1 for dev, S1 for small prod, P1v3 for high-traffic.
        """
        if cost_priority == CostPriority.COST_OPTIMIZED and peak_users <= 50:
            return AppServiceRecommendation(
                sku="F1",
                tier="Free",
                reasoning="Free tier sufficient for dev/test with very low traffic",
                monthly_cost_estimate=pricing_service.get_price("F1"),
            )

        if cost_priority == CostPriority.COST_OPTIMIZED:
            return AppServiceRecommendation(
                sku="B1",
                tier="Basic",
                reasoning="Basic tier for cost-optimized workloads with moderate traffic",
                monthly_cost_estimate=pricing_service.get_price("B1"),
            )

        if peak_users <= 500 and cost_priority != CostPriority.PERFORMANCE_FIRST:
            return AppServiceRecommendation(
                sku="S1",
                tier="Standard",
                reasoning="Standard S1 for small production workloads",
                monthly_cost_estimate=pricing_service.get_price("S1"),
            )

        if peak_users <= 2000:
            return AppServiceRecommendation(
                sku="P1v3",
                tier="PremiumV3",
                reasoning="Premium P1v3 for high-traffic production workloads",
                monthly_cost_estimate=pricing_service.get_price("P1v3"),
            )

        return AppServiceRecommendation(
            sku="P2v3",
            tier="PremiumV3",
            reasoning="Premium P2v3 for very high-traffic workloads exceeding 2000 concurrent users",
            monthly_cost_estimate=pricing_service.get_price("P2v3"),
        )

    # ── Database recommendation ──────────────────────────────────────────

    def get_database_recommendation(
        self,
        workload_type: WorkloadType,
        data_size: float,
        cost_priority: CostPriority,
    ) -> DatabaseRecommendation:
        """Pick an Azure SQL tier.

        Basic/Standard for dev, Premium for demanding workloads,
        Hyperscale for very large datasets.
        """
        if cost_priority == CostPriority.COST_OPTIMIZED and data_size <= 2:
            return DatabaseRecommendation(
                sku="SQL_Basic",
                tier="Basic",
                max_size_gb=2,
                reasoning="Basic tier for minimal dev/test databases",
                monthly_cost_estimate=pricing_service.get_price("SQL_Basic"),
            )

        if data_size > 500:
            return self._hyperscale_db(data_size, cost_priority)

        if cost_priority == CostPriority.PERFORMANCE_FIRST or data_size > 250:
            return DatabaseRecommendation(
                sku="SQL_P1",
                tier="Premium",
                max_size_gb=500,
                reasoning="Premium tier for performance-critical or large workloads",
                monthly_cost_estimate=pricing_service.get_price("SQL_P1"),
            )

        if data_size > 50 or cost_priority == CostPriority.BALANCED:
            return DatabaseRecommendation(
                sku="SQL_S2",
                tier="Standard",
                max_size_gb=250,
                reasoning="Standard S2 tier for balanced performance and cost",
                monthly_cost_estimate=pricing_service.get_price("SQL_S2"),
            )

        return DatabaseRecommendation(
            sku="SQL_S0",
            tier="Standard",
            max_size_gb=250,
            reasoning="Standard S0 for cost-optimized small databases",
            monthly_cost_estimate=pricing_service.get_price("SQL_S0"),
        )

    # ── Storage recommendation ───────────────────────────────────────────

    def get_storage_recommendation(
        self,
        redundancy_needs: AvailabilitySLA,
        access_pattern: WorkloadType | str = "general",
    ) -> StorageRecommendation:
        """Pick a storage SKU based on redundancy and access pattern.

        LRS for dev, ZRS for standard prod, GRS for high-availability,
        RA-GRS for mission-critical.
        """
        is_cool = access_pattern in (WorkloadType.BATCH, WorkloadType.ANALYTICS)

        if redundancy_needs == AvailabilitySLA.SLA_9999:
            sku = "Storage_GRS_Cool" if is_cool else "Storage_RAGRS_Hot"
            return StorageRecommendation(
                sku=sku,
                redundancy="RA-GRS" if not is_cool else "GRS",
                tier="Cool" if is_cool else "Hot",
                reasoning="Read-access geo-redundant storage for 99.99% SLA",
                monthly_cost_estimate=pricing_service.get_price(sku),
            )

        if redundancy_needs == AvailabilitySLA.SLA_9995:
            sku = "Storage_GRS_Cool" if is_cool else "Storage_GRS_Hot"
            return StorageRecommendation(
                sku=sku,
                redundancy="GRS",
                tier="Cool" if is_cool else "Hot",
                reasoning="Geo-redundant storage for 99.95% SLA",
                monthly_cost_estimate=pricing_service.get_price(sku),
            )

        # SLA_999 — zone-redundant or locally redundant
        if is_cool:
            return StorageRecommendation(
                sku="Storage_LRS_Cool",
                redundancy="LRS",
                tier="Cool",
                reasoning="Locally redundant cool storage for cost-effective infrequent access",
                monthly_cost_estimate=pricing_service.get_price("Storage_LRS_Cool"),
            )

        return StorageRecommendation(
            sku="Storage_ZRS_Hot",
            redundancy="ZRS",
            tier="Hot",
            reasoning="Zone-redundant hot storage for 99.9% SLA workloads",
            monthly_cost_estimate=pricing_service.get_price("Storage_ZRS_Hot"),
        )

    # ── Cost estimation ──────────────────────────────────────────────────

    def estimate_monthly_cost(
        self,
        recommendations: list[SKURecommendation],
        region: str = "eastus",
    ) -> CostEstimate:
        """Build a :class:`CostEstimate` from a list of SKU recommendations."""
        breakdown: list[CostLineItem] = []
        total = 0.0

        for rec in recommendations:
            cost = pricing_service.get_price(rec.recommended_sku, region)
            breakdown.append(
                CostLineItem(
                    resource_type=rec.resource_type,
                    sku=rec.recommended_sku,
                    monthly_cost=cost,
                )
            )
            total += cost

        return CostEstimate(
            total_monthly=round(total, 2),
            breakdown=breakdown,
            currency="USD",
        )

    # ── Private helpers ──────────────────────────────────────────────────

    def _memory_optimized_vm(
        self, peak_users: int, cost_priority: CostPriority
    ) -> VMRecommendation:
        """Select an E-series (memory-optimized) VM."""
        if cost_priority == CostPriority.COST_OPTIMIZED or peak_users <= 200:
            return VMRecommendation(
                sku="Standard_E2s_v3",
                series="E",
                vcpus=2,
                memory_gb=16,
                reasoning="Memory-optimized E2s for small database/analytics workloads",
                monthly_cost_estimate=pricing_service.get_price("Standard_E2s_v3"),
            )
        if peak_users <= 1000:
            return VMRecommendation(
                sku="Standard_E4s_v3",
                series="E",
                vcpus=4,
                memory_gb=32,
                reasoning="Memory-optimized E4s for medium database/analytics workloads",
                monthly_cost_estimate=pricing_service.get_price("Standard_E4s_v3"),
            )
        return VMRecommendation(
            sku="Standard_E8s_v3",
            series="E",
            vcpus=8,
            memory_gb=64,
            reasoning="Memory-optimized E8s for large database/analytics workloads",
            monthly_cost_estimate=pricing_service.get_price("Standard_E8s_v3"),
        )

    def _batch_vm(
        self, peak_users: int, cost_priority: CostPriority
    ) -> VMRecommendation:
        """Select a compute-optimized VM for batch jobs."""
        if cost_priority == CostPriority.COST_OPTIMIZED:
            return VMRecommendation(
                sku="Standard_D2s_v5",
                series="D",
                vcpus=2,
                memory_gb=8,
                reasoning="Cost-optimized D2s for light batch processing",
                monthly_cost_estimate=pricing_service.get_price("Standard_D2s_v5"),
            )
        if peak_users <= 500:
            return VMRecommendation(
                sku="Standard_D4s_v3",
                series="D",
                vcpus=4,
                memory_gb=16,
                reasoning="General-purpose D4s for medium batch workloads",
                monthly_cost_estimate=pricing_service.get_price("Standard_D4s_v3"),
            )
        return VMRecommendation(
            sku="Standard_D8s_v3",
            series="D",
            vcpus=8,
            memory_gb=32,
            reasoning="General-purpose D8s for large batch workloads",
            monthly_cost_estimate=pricing_service.get_price("Standard_D8s_v3"),
        )

    def _general_purpose_vm(
        self, peak_users: int, cost_priority: CostPriority
    ) -> VMRecommendation:
        """Select a D-series VM for general-purpose workloads."""
        if peak_users <= 200:
            return VMRecommendation(
                sku="Standard_D2s_v3",
                series="D",
                vcpus=2,
                memory_gb=8,
                reasoning="General-purpose D2s for small web/API workloads",
                monthly_cost_estimate=pricing_service.get_price("Standard_D2s_v3"),
            )
        if peak_users <= 1000:
            return VMRecommendation(
                sku="Standard_D4s_v3",
                series="D",
                vcpus=4,
                memory_gb=16,
                reasoning="General-purpose D4s for medium web/API workloads",
                monthly_cost_estimate=pricing_service.get_price("Standard_D4s_v3"),
            )
        if cost_priority == CostPriority.PERFORMANCE_FIRST:
            return VMRecommendation(
                sku="Standard_D16s_v3",
                series="D",
                vcpus=16,
                memory_gb=64,
                reasoning="High-performance D16s for demanding web/API workloads",
                monthly_cost_estimate=pricing_service.get_price("Standard_D16s_v3"),
            )
        return VMRecommendation(
            sku="Standard_D8s_v3",
            series="D",
            vcpus=8,
            memory_gb=32,
            reasoning="General-purpose D8s for large web/API workloads",
            monthly_cost_estimate=pricing_service.get_price("Standard_D8s_v3"),
        )

    def _hyperscale_db(
        self, data_size: float, cost_priority: CostPriority
    ) -> DatabaseRecommendation:
        """Select a Hyperscale-tier Azure SQL database."""
        if cost_priority == CostPriority.PERFORMANCE_FIRST or data_size > 1000:
            return DatabaseRecommendation(
                sku="SQL_Hyperscale_4vCore",
                tier="Hyperscale",
                max_size_gb=4096,
                reasoning="Hyperscale 4-vCore for very large, performance-critical databases",
                monthly_cost_estimate=pricing_service.get_price("SQL_Hyperscale_4vCore"),
            )
        return DatabaseRecommendation(
            sku="SQL_Hyperscale_2vCore",
            tier="Hyperscale",
            max_size_gb=4096,
            reasoning="Hyperscale 2-vCore for large databases with balanced cost",
            monthly_cost_estimate=pricing_service.get_price("SQL_Hyperscale_2vCore"),
        )

    # ── Alternatives helpers ─────────────────────────────────────────────

    @staticmethod
    def _vm_alternatives(
        workload_type: WorkloadType, cost_priority: CostPriority
    ) -> list[str]:
        if workload_type in (WorkloadType.DATABASE, WorkloadType.ANALYTICS):
            return ["Standard_E2s_v3", "Standard_E4s_v3", "Standard_E8s_v3"]
        if cost_priority == CostPriority.COST_OPTIMIZED:
            return ["Standard_B1s", "Standard_B2s", "Standard_B2ms"]
        return ["Standard_D2s_v3", "Standard_D4s_v3", "Standard_D8s_v3"]

    @staticmethod
    def _app_service_alternatives(cost_priority: CostPriority) -> list[str]:
        if cost_priority == CostPriority.COST_OPTIMIZED:
            return ["F1", "B1", "B2"]
        return ["S1", "P1v3", "P2v3"]

    @staticmethod
    def _database_alternatives(cost_priority: CostPriority) -> list[str]:
        if cost_priority == CostPriority.COST_OPTIMIZED:
            return ["SQL_Basic", "SQL_S0", "SQL_S1"]
        return ["SQL_S2", "SQL_P1", "SQL_P2"]

    @staticmethod
    def _storage_alternatives(availability: AvailabilitySLA) -> list[str]:
        if availability == AvailabilitySLA.SLA_9999:
            return ["Storage_RAGRS_Hot", "Storage_GRS_Hot", "Storage_ZRS_Hot"]
        if availability == AvailabilitySLA.SLA_9995:
            return ["Storage_GRS_Hot", "Storage_ZRS_Hot", "Storage_LRS_Hot"]
        return ["Storage_LRS_Hot", "Storage_ZRS_Hot", "Storage_LRS_Cool"]


# Module-level singleton
sizing_engine = SizingEngine()
