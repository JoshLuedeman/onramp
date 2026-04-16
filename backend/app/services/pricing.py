"""Embedded pricing service — approximate Azure retail prices for dev mode.

No external API calls are made.  Prices are rough monthly estimates in USD
for the East US region and are used for right-sizing cost projections.
"""

import logging

from app.schemas.sizing import CostEstimate, CostLineItem

logger = logging.getLogger(__name__)


class PricingService:
    """Singleton providing embedded Azure pricing data.

    All prices are approximate monthly retail rates (USD, East US) sourced
    from public Azure pricing pages.  They are intentionally rounded and
    should **not** be used for billing — only for ballpark cost estimates
    during architecture planning.
    """

    # -- Embedded prices: SKU → monthly USD (East US) -------------------------
    EMBEDDED_PRICES: dict[str, float] = {
        # ── Virtual Machines ─────────────────────────────────────────────
        "Standard_B1s": 7.59,
        "Standard_B2s": 30.37,
        "Standard_B2ms": 60.74,
        "Standard_B4ms": 121.47,
        "Standard_D2s_v3": 70.08,
        "Standard_D4s_v3": 140.16,
        "Standard_D8s_v3": 280.32,
        "Standard_D16s_v3": 560.64,
        "Standard_D2s_v5": 70.08,
        "Standard_D4s_v5": 140.16,
        "Standard_E2s_v3": 91.98,
        "Standard_E4s_v3": 183.96,
        "Standard_E8s_v3": 367.92,
        "Standard_E16s_v3": 735.84,
        "Standard_NC6s_v3": 2190.00,
        "Standard_NC12s_v3": 4380.00,
        # ── App Service Plans ────────────────────────────────────────────
        "F1": 0.00,
        "B1": 13.14,
        "B2": 26.28,
        "B3": 52.56,
        "S1": 69.35,
        "S2": 138.70,
        "S3": 277.40,
        "P1v3": 138.70,
        "P2v3": 277.40,
        "P3v3": 554.80,
        # ── Azure SQL Database ───────────────────────────────────────────
        "SQL_Basic": 4.90,
        "SQL_S0": 15.03,
        "SQL_S1": 30.05,
        "SQL_S2": 75.13,
        "SQL_S3": 150.26,
        "SQL_P1": 465.00,
        "SQL_P2": 930.00,
        "SQL_P4": 1860.00,
        "SQL_Hyperscale_2vCore": 452.54,
        "SQL_Hyperscale_4vCore": 905.09,
        # ── Storage accounts ─────────────────────────────────────────────
        "Storage_LRS_Hot": 20.80,
        "Storage_ZRS_Hot": 26.00,
        "Storage_GRS_Hot": 43.30,
        "Storage_RAGRS_Hot": 50.05,
        "Storage_LRS_Cool": 10.00,
        "Storage_GRS_Cool": 20.00,
    }

    # Regional multipliers (relative to East US = 1.0)
    REGIONAL_MULTIPLIERS: dict[str, float] = {
        "eastus": 1.0,
        "eastus2": 1.0,
        "westus": 1.0,
        "westus2": 1.0,
        "westus3": 1.0,
        "centralus": 1.0,
        "northcentralus": 1.0,
        "southcentralus": 1.0,
        "canadacentral": 1.02,
        "northeurope": 1.08,
        "westeurope": 1.10,
        "uksouth": 1.06,
        "francecentral": 1.10,
        "germanywestcentral": 1.10,
        "swedencentral": 1.08,
        "australiaeast": 1.12,
        "southeastasia": 1.05,
        "japaneast": 1.15,
        "koreacentral": 1.10,
        "centralindia": 0.95,
        "brazilsouth": 1.30,
    }

    def get_price(self, sku: str, region: str = "eastus") -> float:
        """Return estimated monthly cost for *sku* in *region*.

        Returns 0.0 for unknown SKUs rather than raising.
        """
        base_price = self.EMBEDDED_PRICES.get(sku, 0.0)
        multiplier = self.REGIONAL_MULTIPLIERS.get(region.lower(), 1.0)
        return round(base_price * multiplier, 2)

    def estimate_total(
        self,
        recommendations: list[dict],
        region: str = "eastus",
    ) -> CostEstimate:
        """Build a :class:`CostEstimate` from a list of recommendation dicts.

        Each dict must have at least ``resource_type`` and ``recommended_sku``
        keys.
        """
        breakdown: list[CostLineItem] = []
        total = 0.0

        for rec in recommendations:
            sku = rec.get("recommended_sku", rec.get("sku", ""))
            resource_type = rec.get("resource_type", "unknown")
            cost = self.get_price(sku, region)
            breakdown.append(
                CostLineItem(resource_type=resource_type, sku=sku, monthly_cost=cost)
            )
            total += cost

        return CostEstimate(
            total_monthly=round(total, 2),
            breakdown=breakdown,
            currency="USD",
        )

    def list_all_skus(self, region: str = "eastus") -> list[dict]:
        """Return all known SKUs with their prices for *region*."""
        result = []
        for sku, base_price in self.EMBEDDED_PRICES.items():
            multiplier = self.REGIONAL_MULTIPLIERS.get(region.lower(), 1.0)
            resource_type = self._classify_sku(sku)
            result.append(
                {
                    "sku": sku,
                    "resource_type": resource_type,
                    "monthly_cost": round(base_price * multiplier, 2),
                    "region": region,
                }
            )
        return result

    @staticmethod
    def _classify_sku(sku: str) -> str:
        """Infer resource type from SKU naming convention."""
        if sku.startswith("Standard_"):
            return "Microsoft.Compute/virtualMachines"
        if sku.startswith("SQL_"):
            return "Microsoft.Sql/servers/databases"
        if sku.startswith("Storage_"):
            return "Microsoft.Storage/storageAccounts"
        # App Service tiers are single letters / short codes
        if sku in {"F1", "B1", "B2", "B3", "S1", "S2", "S3", "P1v3", "P2v3", "P3v3"}:
            return "Microsoft.Web/serverFarms"
        return "unknown"


# Module-level singleton
pricing_service = PricingService()
