"""Azure Government region registry.

Provides metadata for all Azure Government regions including DoD-restricted
regions, availability zones, paired-region mappings, and validation helpers.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Region Data ──────────────────────────────────────────────────────────────

GOVERNMENT_REGIONS: list[dict] = [
    {
        "name": "usgovvirginia",
        "display_name": "US Gov Virginia",
        "paired_region": "usgovtexas",
        "geography": "US Government",
        "available_zones": ["1", "2", "3"],
        "restricted": False,
    },
    {
        "name": "usgovtexas",
        "display_name": "US Gov Texas",
        "paired_region": "usgovvirginia",
        "geography": "US Government",
        "available_zones": ["1", "2", "3"],
        "restricted": False,
    },
    {
        "name": "usgoviowa",
        "display_name": "US Gov Iowa",
        "paired_region": "usgovvirginia",
        "geography": "US Government",
        "available_zones": [],
        "restricted": False,
    },
    {
        "name": "usgovarizona",
        "display_name": "US Gov Arizona",
        "paired_region": "usgovtexas",
        "geography": "US Government",
        "available_zones": ["1", "2", "3"],
        "restricted": False,
    },
    {
        "name": "usdodcentral",
        "display_name": "US DoD Central",
        "paired_region": "usdodeast",
        "geography": "US DoD",
        "available_zones": [],
        "restricted": True,
    },
    {
        "name": "usdodeast",
        "display_name": "US DoD East",
        "paired_region": "usdodcentral",
        "geography": "US DoD",
        "available_zones": [],
        "restricted": True,
    },
]


class GovernmentRegionService:
    """Registry of Azure Government regions with DoD awareness."""

    def get_regions(self) -> list[dict]:
        """Return all Azure Government regions.

        Returns:
            List of region dicts with name, display_name, paired_region,
            geography, available_zones, and restricted flag.
        """
        return [dict(r) for r in GOVERNMENT_REGIONS]

    def get_region(self, name: str) -> dict | None:
        """Return a single region by name (case-insensitive).

        Args:
            name: Region name such as ``usgovvirginia``.

        Returns:
            Region dict or ``None`` if not found.
        """
        name_lower = name.lower()
        for region in GOVERNMENT_REGIONS:
            if region["name"].lower() == name_lower:
                return dict(region)
        return None

    def get_dod_regions(self) -> list[dict]:
        """Return only DoD-restricted regions.

        Returns:
            List of region dicts where ``restricted`` is ``True``.
        """
        return [dict(r) for r in GOVERNMENT_REGIONS if r["restricted"]]

    def get_non_dod_regions(self) -> list[dict]:
        """Return only non-DoD regions.

        Returns:
            List of region dicts where ``restricted`` is ``False``.
        """
        return [dict(r) for r in GOVERNMENT_REGIONS if not r["restricted"]]

    def validate_region(self, name: str) -> bool:
        """Check whether *name* is a valid Government region.

        Args:
            name: Region name to validate.

        Returns:
            ``True`` if the region exists.
        """
        return self.get_region(name) is not None

    def get_paired_region(self, name: str) -> str | None:
        """Return the paired region for disaster-recovery planning.

        Args:
            name: Region name.

        Returns:
            Paired region name or ``None`` if the region is unknown.
        """
        region = self.get_region(name)
        if region is None:
            return None
        return region["paired_region"]


government_region_service = GovernmentRegionService()
