"""Cost management service — Azure Cost Management integration.

Provides cost visibility by querying Azure Cost Management APIs.

**Status:** Production Azure Cost Management API integration is NOT yet
implemented.  In dev mode, returns realistic mock data.  In production
mode, the ``_fetch_*`` methods log a warning and return empty/zero-value
placeholders.  A future milestone should implement the real REST calls
(see ``_fetch_cost_summary`` et al. for the target endpoints).
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.models.base import generate_uuid

logger = logging.getLogger(__name__)

# Cache TTL in seconds (1 hour)
CACHE_TTL_SECONDS = 3600

# Azure services used for mock data generation
MOCK_SERVICES = [
    "Microsoft.Compute/virtualMachines",
    "Microsoft.Storage/storageAccounts",
    "Microsoft.Sql/servers",
    "Microsoft.Network/virtualNetworks",
    "Microsoft.Web/sites",
    "Microsoft.ContainerService/managedClusters",
    "Microsoft.KeyVault/vaults",
    "Microsoft.Cache/Redis",
    "Microsoft.CognitiveServices/accounts",
    "Microsoft.Monitor/accounts",
]

MOCK_RESOURCE_GROUPS = [
    "rg-production-eastus",
    "rg-staging-eastus",
    "rg-shared-services",
    "rg-data-platform",
    "rg-networking",
]


class CostManager:
    """Manages cost visibility and anomaly detection.

    Uses in-memory caching with a 1-hour TTL to avoid hitting
    Azure Cost Management API throttle limits.
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, Any]] = {}

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_key(self, *parts: str) -> str:
        return ":".join(parts)

    def _get_cached(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._cache[key]
            return None
        return value

    def _set_cached(self, key: str, value: Any) -> None:
        self._cache[key] = (time.monotonic() + CACHE_TTL_SECONDS, value)

    def clear_cache(self) -> None:
        """Clear all cached cost data."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_cost_summary(
        self,
        project_id: str,
        subscription_id: str,
        time_range: str = "last_30_days",
    ) -> dict:
        """Get cost summary — total, by service, by resource group.

        Returns cached data if available (1-hour TTL).
        """
        cache_key = self._cache_key("summary", project_id, subscription_id, time_range)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        if settings.is_dev_mode:
            result = self._mock_cost_summary(project_id, subscription_id, time_range)
        else:
            result = await self._fetch_cost_summary(
                project_id, subscription_id, time_range
            )

        self._set_cached(cache_key, result)
        return result

    async def get_cost_trend(
        self,
        project_id: str,
        subscription_id: str,
        granularity: str = "daily",
        days: int = 30,
    ) -> dict:
        """Get cost trend data with daily/weekly/monthly data points."""
        cache_key = self._cache_key(
            "trend", project_id, subscription_id, granularity, str(days)
        )
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        if settings.is_dev_mode:
            result = self._mock_cost_trend(
                project_id, subscription_id, granularity, days
            )
        else:
            result = await self._fetch_cost_trend(
                project_id, subscription_id, granularity, days
            )

        self._set_cached(cache_key, result)
        return result

    async def get_budget_status(
        self,
        project_id: str,
        subscription_id: str,
    ) -> dict:
        """Get budget vs actual spend."""
        cache_key = self._cache_key("budget", project_id, subscription_id)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        if settings.is_dev_mode:
            result = self._mock_budget_status(project_id, subscription_id)
        else:
            result = await self._fetch_budget_status(project_id, subscription_id)

        self._set_cached(cache_key, result)
        return result

    async def check_cost_anomalies(
        self,
        project_id: str,
        subscription_id: str,
    ) -> dict:
        """Detect cost spikes (>20% increase over previous period).

        If anomalies are detected, publishes a ``cost_alert`` SSE event.
        """
        cache_key = self._cache_key("anomalies", project_id, subscription_id)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        if settings.is_dev_mode:
            result = self._mock_cost_anomalies(project_id, subscription_id)
        else:
            result = await self._fetch_cost_anomalies(project_id, subscription_id)

        # Publish SSE event if anomalies found
        if result.get("anomalies"):
            await self._publish_cost_alert(project_id, result["anomalies"])

        self._set_cached(cache_key, result)
        return result

    # ------------------------------------------------------------------
    # SSE integration
    # ------------------------------------------------------------------

    async def _publish_cost_alert(
        self, project_id: str, anomalies: list[dict]
    ) -> None:
        """Publish a cost_alert SSE event for detected anomalies."""
        try:
            from app.services.event_stream import event_stream

            await event_stream.publish(
                "cost_alert",
                {
                    "anomaly_count": len(anomalies),
                    "anomalies": anomalies[:5],  # Limit payload size
                    "message": f"Detected {len(anomalies)} cost anomalie(s)",
                },
                project_id=project_id,
            )
        except Exception:
            logger.exception("Failed to publish cost_alert event")

    # ------------------------------------------------------------------
    # Mock data generators (dev mode)
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_cost_summary(
        project_id: str, subscription_id: str, time_range: str
    ) -> dict:
        """Generate realistic mock cost summary."""
        now = datetime.now(timezone.utc)

        days = 30
        if time_range == "last_7_days":
            days = 7
        elif time_range == "last_90_days":
            days = 90

        period_start = now - timedelta(days=days)

        # Generate cost breakdown by service (10 services)
        service_costs = []
        total = 0.0
        for svc in MOCK_SERVICES:
            cost = round(random.uniform(50.0, 800.0), 2)
            service_costs.append({"service_name": svc, "cost": cost})
            total += cost

        # Calculate percentages
        for entry in service_costs:
            entry["percentage"] = round((entry["cost"] / total) * 100, 1)

        # Sort by cost descending
        service_costs.sort(key=lambda x: x["cost"], reverse=True)

        # Generate cost by resource group
        rg_costs = []
        remaining = total
        for i, rg in enumerate(MOCK_RESOURCE_GROUPS):
            if i == len(MOCK_RESOURCE_GROUPS) - 1:
                cost = round(remaining, 2)
            else:
                cost = round(random.uniform(total * 0.1, total * 0.35), 2)
                remaining -= cost
            rg_costs.append({
                "resource_group": rg,
                "cost": cost,
                "percentage": round((cost / total) * 100, 1),
            })

        return {
            "project_id": project_id,
            "subscription_id": subscription_id,
            "period_start": period_start.isoformat(),
            "period_end": now.isoformat(),
            "total_cost": round(total, 2),
            "currency": "USD",
            "cost_by_service": service_costs,
            "cost_by_resource_group": rg_costs,
        }

    @staticmethod
    def _mock_cost_trend(
        project_id: str,
        subscription_id: str,
        granularity: str,
        days: int,
    ) -> dict:
        """Generate realistic mock cost trend with daily data points."""
        now = datetime.now(timezone.utc)
        data_points = []
        total_cost = 0.0

        # Determine number of data points based on granularity
        if granularity == "weekly":
            num_points = max(1, days // 7)
        elif granularity == "monthly":
            num_points = max(1, days // 30)
        else:  # daily
            num_points = days

        base_daily_cost = random.uniform(80.0, 150.0)

        for i in range(num_points):
            date = now - timedelta(days=(num_points - 1 - i))
            # Add some random variation (+/- 20%)
            variation = random.uniform(0.8, 1.2)
            cost = round(base_daily_cost * variation, 2)
            total_cost += cost
            data_points.append({
                "date": date.strftime("%Y-%m-%d"),
                "cost": cost,
                "currency": "USD",
            })

        avg_daily = round(total_cost / max(num_points, 1), 2)

        return {
            "project_id": project_id,
            "subscription_id": subscription_id,
            "granularity": granularity,
            "days": days,
            "data_points": data_points,
            "total_cost": round(total_cost, 2),
            "average_daily_cost": avg_daily,
        }

    @staticmethod
    def _mock_budget_status(project_id: str, subscription_id: str) -> dict:
        """Generate mock budget at ~65% utilisation."""
        budget_amount = 10000.0
        current_spend = round(budget_amount * 0.65, 2)
        utilization = round((current_spend / budget_amount) * 100, 1)

        return {
            "project_id": project_id,
            "budget_name": "Monthly Cloud Budget",
            "budget_amount": budget_amount,
            "current_spend": current_spend,
            "currency": "USD",
            "utilization_percentage": utilization,
            "threshold_percentage": 80.0,
            "alert_enabled": True,
            "is_over_threshold": utilization >= 80.0,
            "is_over_budget": utilization >= 100.0,
        }

    @staticmethod
    def _mock_cost_anomalies(project_id: str, subscription_id: str) -> dict:
        """Generate mock cost anomalies — one spike anomaly."""
        now = datetime.now(timezone.utc)
        previous_cost = 120.0
        current_cost = 168.0  # 40% increase
        pct_change = round(((current_cost - previous_cost) / previous_cost) * 100, 1)

        anomalies = [
            {
                "id": generate_uuid(),
                "project_id": project_id,
                "cost_snapshot_id": generate_uuid(),
                "anomaly_type": "spike",
                "description": (
                    f"Daily cost spiked from ${previous_cost:.2f} to "
                    f"${current_cost:.2f} ({pct_change}% increase) "
                    "for Microsoft.Compute/virtualMachines"
                ),
                "previous_cost": previous_cost,
                "current_cost": current_cost,
                "percentage_change": pct_change,
                "severity": "high",
                "detected_at": now.isoformat(),
            }
        ]

        return {
            "anomalies": anomalies,
            "total": len(anomalies),
        }

    # ------------------------------------------------------------------
    # Production API calls (Azure Cost Management REST API)
    # ------------------------------------------------------------------

    async def _fetch_cost_summary(
        self, project_id: str, subscription_id: str, time_range: str
    ) -> dict:
        """Query Azure Cost Management API for cost summary.

        TODO: Implement production Azure Cost Management REST call.
        Endpoint: POST /subscriptions/{id}/providers/Microsoft.CostManagement/query
        """
        logger.warning(
            "Production cost API not yet implemented — returning empty summary"
        )
        return {
            "project_id": project_id,
            "subscription_id": subscription_id,
            "period_start": datetime.now(timezone.utc).isoformat(),
            "period_end": datetime.now(timezone.utc).isoformat(),
            "total_cost": 0.0,
            "currency": "USD",
            "cost_by_service": [],
            "cost_by_resource_group": [],
        }

    async def _fetch_cost_trend(
        self,
        project_id: str,
        subscription_id: str,
        granularity: str,
        days: int,
    ) -> dict:
        """Query Azure Cost Management API for cost trend.

        TODO: Implement production Azure Cost Management REST call.
        """
        logger.warning(
            "Production cost trend API not yet implemented — returning empty trend"
        )
        return {
            "project_id": project_id,
            "subscription_id": subscription_id,
            "granularity": granularity,
            "days": days,
            "data_points": [],
            "total_cost": 0.0,
            "average_daily_cost": 0.0,
        }

    async def _fetch_budget_status(
        self, project_id: str, subscription_id: str
    ) -> dict:
        """Query Azure Budgets API for budget status.

        TODO: Implement production Azure Budgets REST call.
        Endpoint: GET /subscriptions/{id}/providers/Microsoft.Consumption/budgets
        """
        logger.warning(
            "Production budget API not yet implemented — returning empty budget"
        )
        return {
            "project_id": project_id,
            "budget_name": "",
            "budget_amount": 0.0,
            "current_spend": 0.0,
            "currency": "USD",
            "utilization_percentage": 0.0,
            "threshold_percentage": 80.0,
            "alert_enabled": True,
            "is_over_threshold": False,
            "is_over_budget": False,
        }

    async def _fetch_cost_anomalies(
        self, project_id: str, subscription_id: str
    ) -> dict:
        """Detect cost anomalies from Azure Cost Management data.

        TODO: Implement production anomaly detection using Azure
        Cost Management Anomaly API or manual threshold comparison.
        """
        logger.warning(
            "Production anomaly detection not yet implemented — returning empty"
        )
        return {"anomalies": [], "total": 0}


# Module-level singleton
cost_manager = CostManager()


# ------------------------------------------------------------------
# Register periodic anomaly check with task scheduler
# ------------------------------------------------------------------

def _register_periodic_task() -> None:
    """Register the cost anomaly check as a periodic governance task."""
    try:
        from app.services.task_scheduler import task_scheduler

        @task_scheduler.periodic(
            "cost_anomaly_check",
            interval_seconds=3600,
            description="Periodic cost anomaly detection scan",
        )
        async def check_cost_anomalies(**kwargs: Any) -> dict:
            """Scheduled task: check all projects for cost anomalies."""
            project_id = kwargs.get("project_id", "default")
            subscription_id = kwargs.get("subscription_id", "dev-subscription")
            result = await cost_manager.check_cost_anomalies(
                project_id, subscription_id
            )
            return {
                "message": "Cost anomaly check completed",
                "anomalies_found": result.get("total", 0),
            }

    except Exception:
        logger.exception("Failed to register cost anomaly periodic task")


_register_periodic_task()
