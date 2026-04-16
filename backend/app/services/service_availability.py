"""Azure service availability matrix across sovereign & specialized clouds."""

import logging

logger = logging.getLogger(__name__)

# ── Availability Data ────────────────────────────────────────────────────────
# Each entry tracks a key Azure service and its availability across cloud
# environments.  Values: True (available), False (not available), or a str
# note indicating limited availability.

AZURE_SERVICES: list[dict] = [
    {
        "service_name": "Virtual Machines",
        "category": "Compute",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "Some VM SKUs unavailable in Government and China.",
    },
    {
        "service_name": "App Service",
        "category": "Compute",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Azure Kubernetes Service",
        "category": "Containers",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "Feature parity may lag in sovereign clouds.",
    },
    {
        "service_name": "Container Apps",
        "category": "Containers",
        "commercial": True,
        "government": True,
        "china": False,
        "notes": "Not yet available in Azure China.",
    },
    {
        "service_name": "Container Instances",
        "category": "Containers",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Azure Functions",
        "category": "Compute",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "Consumption plan limited in some sovereign regions.",
    },
    {
        "service_name": "Azure SQL Database",
        "category": "Databases",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Cosmos DB",
        "category": "Databases",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "Some APIs may not be available in all regions.",
    },
    {
        "service_name": "Azure Database for PostgreSQL",
        "category": "Databases",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Azure Database for MySQL",
        "category": "Databases",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Storage Accounts",
        "category": "Storage",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Azure Blob Storage",
        "category": "Storage",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Key Vault",
        "category": "Security",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "Managed HSM may be limited in sovereign clouds.",
    },
    {
        "service_name": "Microsoft Defender for Cloud",
        "category": "Security",
        "commercial": True,
        "government": True,
        "china": False,
        "notes": "Limited or unavailable in Azure China.",
    },
    {
        "service_name": "Microsoft Sentinel",
        "category": "Security",
        "commercial": True,
        "government": True,
        "china": False,
        "notes": "Not available in Azure China.",
    },
    {
        "service_name": "Azure Active Directory",
        "category": "Identity",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "Separate tenant for each sovereign cloud.",
    },
    {
        "service_name": "Azure Monitor",
        "category": "Management",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Log Analytics",
        "category": "Management",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Virtual Network",
        "category": "Networking",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Azure Firewall",
        "category": "Networking",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Application Gateway",
        "category": "Networking",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Azure Front Door",
        "category": "Networking",
        "commercial": True,
        "government": True,
        "china": False,
        "notes": "Not available in Azure China.",
    },
    {
        "service_name": "Azure OpenAI Service",
        "category": "AI",
        "commercial": True,
        "government": True,
        "china": False,
        "notes": "AI services limited in Government; unavailable in China.",
    },
    {
        "service_name": "Azure Cognitive Services",
        "category": "AI",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "Limited model availability outside commercial cloud.",
    },
    {
        "service_name": "Azure Machine Learning",
        "category": "AI",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "Feature parity may lag in sovereign clouds.",
    },
    {
        "service_name": "Azure DevOps",
        "category": "DevOps",
        "commercial": True,
        "government": True,
        "china": False,
        "notes": "Not available in Azure China.",
    },
    {
        "service_name": "Event Hubs",
        "category": "Integration",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Service Bus",
        "category": "Integration",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Azure Policy",
        "category": "Governance",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
    {
        "service_name": "Azure Backup",
        "category": "Management",
        "commercial": True,
        "government": True,
        "china": True,
        "notes": "",
    },
]

# ── Alternatives Mapping ─────────────────────────────────────────────────────
# Suggested replacements when a service is not available in a target cloud.

_ALTERNATIVES: dict[str, dict[str, str]] = {
    "Container Apps": {
        "china": "Azure Kubernetes Service",
    },
    "Microsoft Defender for Cloud": {
        "china": "Third-party CSPM or manual security monitoring",
    },
    "Microsoft Sentinel": {
        "china": "Third-party SIEM or Azure Monitor with custom alerts",
    },
    "Azure Front Door": {
        "china": "Application Gateway with WAF",
    },
    "Azure OpenAI Service": {
        "china": "Partner AI services or self-hosted models",
    },
    "Azure DevOps": {
        "china": "GitHub or self-hosted CI/CD (e.g., Jenkins)",
    },
}


# ── Service ──────────────────────────────────────────────────────────────────


class ServiceAvailabilityService:
    """Tracks Azure service availability across cloud environments."""

    def get_all_services(self) -> list[dict]:
        """Return all tracked services with availability information."""
        return list(AZURE_SERVICES)

    def get_service(self, service_name: str) -> dict | None:
        """Return availability details for a specific service."""
        name_lower = service_name.lower()
        for svc in AZURE_SERVICES:
            if svc["service_name"].lower() == name_lower:
                return dict(svc)
        return None

    def get_services_for_environment(self, env: str) -> list[dict]:
        """Return services available in a given cloud environment."""
        env_lower = env.lower()
        if env_lower not in ("commercial", "government", "china"):
            return []
        return [
            dict(svc)
            for svc in AZURE_SERVICES
            if svc.get(env_lower) is True
        ]

    def check_architecture_compatibility(
        self, architecture: dict, target_env: str
    ) -> dict:
        """Check whether an architecture's services are available in the target env.

        Args:
            architecture: A dict with a ``services`` list of service name strings.
            target_env: One of ``commercial``, ``government``, ``china``.

        Returns:
            Dict with ``compatible``, ``missing_services``, ``warnings``, and
            ``alternatives`` keys.
        """
        env_lower = target_env.lower()
        services_requested = architecture.get("services", [])
        if not isinstance(services_requested, list):
            services_requested = []

        missing: list[str] = []
        warnings: list[str] = []
        alternatives: dict[str, str] = {}

        for svc_name in services_requested:
            svc = self.get_service(svc_name)
            if svc is None:
                warnings.append(f"Unknown service: {svc_name}")
                continue

            available = svc.get(env_lower)
            if available is False:
                missing.append(svc_name)
                alt = _ALTERNATIVES.get(svc_name, {}).get(env_lower)
                if alt:
                    alternatives[svc_name] = alt
            elif svc.get("notes"):
                warnings.append(f"{svc_name}: {svc['notes']}")

        return {
            "compatible": len(missing) == 0,
            "target_environment": target_env,
            "services_checked": len(services_requested),
            "missing_services": missing,
            "warnings": warnings,
            "alternatives": alternatives,
        }

    def get_availability_matrix(self) -> dict:
        """Return the full availability matrix suitable for display."""
        environments = ["commercial", "government", "china"]
        rows: list[dict] = []
        for svc in AZURE_SERVICES:
            row = {
                "service_name": svc["service_name"],
                "category": svc["category"],
                "notes": svc.get("notes", ""),
            }
            for env in environments:
                row[env] = svc.get(env, False)
            rows.append(row)

        # Group by category for structured display
        categories: dict[str, list[dict]] = {}
        for row in rows:
            cat = row["category"]
            categories.setdefault(cat, []).append(row)

        return {
            "environments": environments,
            "services": rows,
            "by_category": categories,
            "total_services": len(rows),
        }


# Singleton
service_availability_service = ServiceAvailabilityService()
