"""Azure China (21Vianet) region registry.

Provides detailed region metadata, pairing information, and data residency
requirements for Azure China operated by 21Vianet.
"""

import logging

logger = logging.getLogger(__name__)

# ── Region Data ──────────────────────────────────────────────────────────────

CHINA_REGIONS: list[dict] = [
    {
        "name": "chinanorth",
        "display_name": "China North (Beijing)",
        "paired_region": "chinaeast",
        "geography": "China",
        "available_zones": [],
    },
    {
        "name": "chinanorth2",
        "display_name": "China North 2 (Beijing)",
        "paired_region": "chinaeast2",
        "geography": "China",
        "available_zones": ["1", "2", "3"],
    },
    {
        "name": "chinanorth3",
        "display_name": "China North 3 (Hebei)",
        "paired_region": "chinaeast3",
        "geography": "China",
        "available_zones": ["1", "2", "3"],
    },
    {
        "name": "chinaeast",
        "display_name": "China East (Shanghai)",
        "paired_region": "chinanorth",
        "geography": "China",
        "available_zones": [],
    },
    {
        "name": "chinaeast2",
        "display_name": "China East 2 (Shanghai)",
        "paired_region": "chinanorth2",
        "geography": "China",
        "available_zones": ["1", "2", "3"],
    },
    {
        "name": "chinaeast3",
        "display_name": "China East 3 (Jiangsu)",
        "paired_region": "chinanorth3",
        "geography": "China",
        "available_zones": ["1", "2", "3"],
    },
]

# ── Data Residency ───────────────────────────────────────────────────────────

_DATA_RESIDENCY_REQUIREMENTS: dict = {
    "jurisdiction": "People's Republic of China",
    "data_boundary": "mainland_china",
    "cross_border_transfer": False,
    "regulations": [
        "Cybersecurity Law of the People's Republic of China",
        "Data Security Law (DSL)",
        "Personal Information Protection Law (PIPL)",
        "MLPS 2.0 (GB/T 22239-2019)",
    ],
    "requirements": [
        "All data must remain within mainland China borders",
        "Cross-border data transfers require security assessment",
        "Personal information requires explicit consent for processing",
        "Critical data infrastructure operators must store data domestically",
        "Data localization applies to all customer content and metadata",
    ],
    "operator": "21Vianet (Shanghai Blue Cloud Technology Co., Ltd.)",
    "operator_relationship": "Microsoft technology, 21Vianet operations",
}


# ── Service ──────────────────────────────────────────────────────────────────


class ChinaRegionService:
    """Registry of Azure China (21Vianet) regions.

    Provides region metadata, pairing relationships, and data residency
    rules for workloads deployed in Azure China.
    """

    def get_regions(self) -> list[dict]:
        """Return all Azure China regions.

        Returns:
            A list of region dicts with ``name``, ``display_name``,
            ``paired_region``, ``geography``, and ``available_zones``.
        """
        return [dict(r) for r in CHINA_REGIONS]

    def get_region(self, name: str) -> dict | None:
        """Return metadata for a specific China region.

        Args:
            name: Region identifier (e.g. ``chinanorth2``).

        Returns:
            A dict of region metadata, or ``None`` if not found.
        """
        name_lower = name.lower()
        for region in CHINA_REGIONS:
            if region["name"] == name_lower:
                return dict(region)
        return None

    def validate_region(self, name: str) -> bool:
        """Check whether *name* is a valid Azure China region.

        Args:
            name: Region identifier to validate.

        Returns:
            ``True`` if the region exists, ``False`` otherwise.
        """
        return self.get_region(name) is not None

    def get_paired_region(self, name: str) -> str | None:
        """Return the paired region for disaster recovery.

        Args:
            name: Source region identifier.

        Returns:
            The paired region name, or ``None`` if the source is unknown.
        """
        region = self.get_region(name)
        if region is None:
            return None
        return region["paired_region"]

    def get_data_residency_requirements(self) -> dict:
        """Return China-specific data residency requirements.

        Returns:
            A dict describing jurisdictional boundaries, regulations,
            and data-handling requirements for Azure China.
        """
        return dict(_DATA_RESIDENCY_REQUIREMENTS)


# Singleton
china_region_service = ChinaRegionService()
