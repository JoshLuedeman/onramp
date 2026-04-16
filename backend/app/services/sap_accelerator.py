"""SAP on Azure landing zone accelerator.

Provides SAP-specific questionnaire, certified VM SKU catalogue,
architecture generation, sizing estimation, best-practice checklists,
and reference architectures for S/4HANA, ECC, and BW/4HANA workloads.
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

# ── SAP Questionnaire ────────────────────────────────────────────────────────

SAP_QUESTIONS: list[dict] = [
    {
        "id": "sap_product",
        "text": "Which SAP product are you deploying?",
        "type": "single_choice",
        "options": [
            {"value": "s4hana", "label": "SAP S/4HANA"},
            {"value": "ecc", "label": "SAP ECC"},
            {"value": "bw4hana", "label": "SAP BW/4HANA"},
            {"value": "business_suite", "label": "SAP Business Suite"},
            {"value": "crm", "label": "SAP CRM"},
        ],
        "required": True,
        "category": "sap",
        "help_text": "Select the primary SAP product for this deployment.",
    },
    {
        "id": "sap_database",
        "text": "Which database platform will you use?",
        "type": "single_choice",
        "options": [
            {"value": "hana", "label": "SAP HANA"},
            {"value": "sql_server", "label": "Microsoft SQL Server"},
            {"value": "oracle", "label": "Oracle"},
            {"value": "db2", "label": "IBM DB2"},
            {"value": "maxdb", "label": "SAP MaxDB"},
        ],
        "required": True,
        "category": "sap",
        "help_text": "Database engine for the SAP system.",
    },
    {
        "id": "deployment_type",
        "text": "What type of deployment is this?",
        "type": "single_choice",
        "options": [
            {"value": "greenfield", "label": "Greenfield (new installation)"},
            {"value": "brownfield", "label": "Brownfield (migration)"},
            {"value": "hybrid", "label": "Hybrid (phased migration)"},
        ],
        "required": True,
        "category": "sap",
        "help_text": "Greenfield is a fresh install; brownfield migrates an existing system.",
    },
    {
        "id": "hana_scale",
        "text": "Which HANA deployment model do you need?",
        "type": "single_choice",
        "options": [
            {"value": "scale_up", "label": "Scale-up (single node)"},
            {"value": "scale_out", "label": "Scale-out (multiple nodes)"},
        ],
        "required": False,
        "category": "sap",
        "help_text": "Scale-out is for very large HANA databases exceeding single-node memory.",
    },
    {
        "id": "high_availability",
        "text": "Do you require high availability?",
        "type": "single_choice",
        "options": [
            {"value": "yes", "label": "Yes"},
            {"value": "no", "label": "No"},
        ],
        "required": True,
        "category": "sap",
        "help_text": "HA uses HANA System Replication and Pacemaker clustering.",
    },
    {
        "id": "disaster_recovery",
        "text": "Do you require disaster recovery?",
        "type": "single_choice",
        "options": [
            {"value": "yes", "label": "Yes"},
            {"value": "no", "label": "No"},
        ],
        "required": True,
        "category": "sap",
        "help_text": "DR replicates to a secondary Azure region.",
    },
    {
        "id": "rpo_rto",
        "text": "What are your RPO/RTO targets?",
        "type": "single_choice",
        "options": [
            {"value": "rpo_0_rto_15", "label": "RPO < 1 min, RTO < 15 min"},
            {"value": "rpo_5_rto_30", "label": "RPO < 5 min, RTO < 30 min"},
            {"value": "rpo_15_rto_60", "label": "RPO < 15 min, RTO < 1 hour"},
            {"value": "rpo_60_rto_240", "label": "RPO < 1 hour, RTO < 4 hours"},
        ],
        "required": False,
        "category": "sap",
        "help_text": "Recovery Point / Recovery Time Objectives for DR planning.",
    },
    {
        "id": "saps_rating",
        "text": "What is your SAPS rating requirement?",
        "type": "numeric",
        "options": [],
        "required": True,
        "category": "sap",
        "help_text": "SAP Application Performance Standard benchmark score needed.",
    },
    {
        "id": "concurrent_users",
        "text": "How many concurrent users will access the system?",
        "type": "numeric",
        "options": [],
        "required": True,
        "category": "sap",
        "help_text": "Peak number of users simultaneously logged in.",
    },
    {
        "id": "data_volume",
        "text": "What is the expected data volume?",
        "type": "single_choice",
        "options": [
            {"value": "small", "label": "< 500 GB"},
            {"value": "medium", "label": "500 GB – 2 TB"},
            {"value": "large", "label": "2 TB – 6 TB"},
            {"value": "very_large", "label": "6 TB – 12 TB"},
            {"value": "ultra_large", "label": "> 12 TB"},
        ],
        "required": True,
        "category": "sap",
        "help_text": "Current database size plus projected 3-year growth.",
    },
    {
        "id": "integration_requirements",
        "text": "Which integration services do you need?",
        "type": "multi_choice",
        "options": [
            {"value": "btp", "label": "SAP Business Technology Platform"},
            {"value": "fiori", "label": "SAP Fiori / Web Dispatcher"},
            {"value": "interfaces", "label": "Third-party interfaces (RFC/IDoc)"},
            {"value": "analytics", "label": "Azure Synapse / Analytics"},
            {"value": "none", "label": "None"},
        ],
        "required": False,
        "category": "sap",
        "help_text": "Select all integration points for this deployment.",
    },
    {
        "id": "environment_type",
        "text": "What environment is this for?",
        "type": "single_choice",
        "options": [
            {"value": "production", "label": "Production"},
            {"value": "non_production", "label": "Non-Production (Dev/QA/Sandbox)"},
        ],
        "required": True,
        "category": "sap",
        "help_text": "Production environments require higher SLAs and HA.",
    },
]

# ── SAP-Certified VM SKUs ────────────────────────────────────────────────────

SAP_CERTIFIED_SKUS: list[dict] = [
    # M-series — HANA production
    {
        "name": "Standard_M32ts",
        "series": "M",
        "vcpus": 32,
        "memory_gb": 192,
        "saps_rating": 31_570,
        "max_hana_memory_gb": 192,
        "tier": "hana",
        "description": "Entry HANA workloads",
    },
    {
        "name": "Standard_M32ls",
        "series": "M",
        "vcpus": 32,
        "memory_gb": 256,
        "saps_rating": 31_570,
        "max_hana_memory_gb": 256,
        "tier": "hana",
        "description": "Small HANA workloads",
    },
    {
        "name": "Standard_M64ls",
        "series": "M",
        "vcpus": 64,
        "memory_gb": 512,
        "saps_rating": 63_140,
        "max_hana_memory_gb": 512,
        "tier": "hana",
        "description": "Medium HANA workloads",
    },
    {
        "name": "Standard_M64s",
        "series": "M",
        "vcpus": 64,
        "memory_gb": 1024,
        "saps_rating": 63_140,
        "max_hana_memory_gb": 1024,
        "tier": "hana",
        "description": "Large HANA workloads",
    },
    {
        "name": "Standard_M64ms",
        "series": "M",
        "vcpus": 64,
        "memory_gb": 1792,
        "saps_rating": 63_140,
        "max_hana_memory_gb": 1792,
        "tier": "hana",
        "description": "Memory-optimised HANA",
    },
    {
        "name": "Standard_M128s",
        "series": "M",
        "vcpus": 128,
        "memory_gb": 2048,
        "saps_rating": 126_280,
        "max_hana_memory_gb": 2048,
        "tier": "hana",
        "description": "Large production HANA",
    },
    {
        "name": "Standard_M128ms",
        "series": "M",
        "vcpus": 128,
        "memory_gb": 3892,
        "saps_rating": 126_280,
        "max_hana_memory_gb": 3892,
        "tier": "hana",
        "description": "Very large HANA workloads",
    },
    {
        "name": "Standard_M208s_v2",
        "series": "Mv2",
        "vcpus": 208,
        "memory_gb": 2850,
        "saps_rating": 260_000,
        "max_hana_memory_gb": 2850,
        "tier": "hana",
        "description": "Mv2 HANA scale-up",
    },
    {
        "name": "Standard_M208ms_v2",
        "series": "Mv2",
        "vcpus": 208,
        "memory_gb": 5700,
        "saps_rating": 260_000,
        "max_hana_memory_gb": 5700,
        "tier": "hana",
        "description": "Mv2 very large HANA",
    },
    # E-series — Application servers
    {
        "name": "Standard_E4s_v5",
        "series": "Ev5",
        "vcpus": 4,
        "memory_gb": 32,
        "saps_rating": 4_350,
        "max_hana_memory_gb": 0,
        "tier": "app",
        "description": "Small app server",
    },
    {
        "name": "Standard_E8s_v5",
        "series": "Ev5",
        "vcpus": 8,
        "memory_gb": 64,
        "saps_rating": 8_700,
        "max_hana_memory_gb": 0,
        "tier": "app",
        "description": "Medium app server",
    },
    {
        "name": "Standard_E16s_v5",
        "series": "Ev5",
        "vcpus": 16,
        "memory_gb": 128,
        "saps_rating": 17_400,
        "max_hana_memory_gb": 0,
        "tier": "app",
        "description": "Large app server",
    },
    {
        "name": "Standard_E32s_v5",
        "series": "Ev5",
        "vcpus": 32,
        "memory_gb": 256,
        "saps_rating": 34_800,
        "max_hana_memory_gb": 0,
        "tier": "app",
        "description": "Very large app server",
    },
    {
        "name": "Standard_E48s_v5",
        "series": "Ev5",
        "vcpus": 48,
        "memory_gb": 384,
        "saps_rating": 52_200,
        "max_hana_memory_gb": 0,
        "tier": "app",
        "description": "Extra-large app server",
    },
    {
        "name": "Standard_E64s_v5",
        "series": "Ev5",
        "vcpus": 64,
        "memory_gb": 512,
        "saps_rating": 69_600,
        "max_hana_memory_gb": 0,
        "tier": "app",
        "description": "Maximum E-series app server",
    },
]

# ── Data Volume → Memory Mapping ─────────────────────────────────────────────

_DATA_VOLUME_GB: dict[str, int] = {
    "small": 500,
    "medium": 2048,
    "large": 6144,
    "very_large": 12288,
    "ultra_large": 24576,
}

# ── Best Practices ───────────────────────────────────────────────────────────

SAP_BEST_PRACTICES: list[dict] = [
    {
        "id": "hana_sizing",
        "category": "sizing",
        "title": "Use SAP Quick Sizer for HANA memory estimation",
        "description": (
            "Run the SAP Quick Sizer tool to determine accurate SAPS"
            " and memory requirements before selecting VM SKUs."
        ),
        "severity": "critical",
        "link": "https://www.sap.com/about/benchmark/sizing.html",
    },
    {
        "id": "certified_vms",
        "category": "compute",
        "title": "Use only SAP-certified VM SKUs",
        "description": (
            "Azure M-series and Mv2-series VMs are certified for HANA."
            " E-series VMs are certified for SAP application servers."
        ),
        "severity": "critical",
        "link": "https://learn.microsoft.com/azure/sap/large-instances/",
    },
    {
        "id": "accelerated_networking",
        "category": "networking",
        "title": "Enable accelerated networking on all SAP VMs",
        "description": (
            "Accelerated networking reduces latency and jitter, critical"
            " for HANA System Replication and inter-tier communication."
        ),
        "severity": "high",
        "link": (
            "https://learn.microsoft.com/azure/virtual-network/"
            "accelerated-networking-overview"
        ),
    },
    {
        "id": "proximity_placement",
        "category": "compute",
        "title": "Use proximity placement groups",
        "description": (
            "Place SAP application servers and database VMs in the"
            " same proximity placement group for lowest network latency."
        ),
        "severity": "high",
        "link": (
            "https://learn.microsoft.com/azure/virtual-machines/"
            "co-location"
        ),
    },
    {
        "id": "anf_storage",
        "category": "storage",
        "title": "Use Azure NetApp Files for shared storage",
        "description": (
            "ANF provides high-performance NFS for /hana/shared,"
            " /sapmnt, and transport directories."
        ),
        "severity": "high",
        "link": (
            "https://learn.microsoft.com/azure/azure-netapp-files/"
            "azure-netapp-files-introduction"
        ),
    },
    {
        "id": "hana_hsr",
        "category": "availability",
        "title": "Configure HANA System Replication for HA",
        "description": (
            "Use synchronous HSR between primary and secondary HANA"
            " nodes with Pacemaker cluster for automatic failover."
        ),
        "severity": "critical",
        "link": (
            "https://learn.microsoft.com/azure/sap/"
            "workloads/sap-hana-high-availability"
        ),
    },
    {
        "id": "backup_policy",
        "category": "backup",
        "title": "Configure Azure Backup for SAP HANA",
        "description": (
            "Use Azure Backup with Backint to protect HANA databases"
            " with application-consistent snapshots."
        ),
        "severity": "high",
        "link": (
            "https://learn.microsoft.com/azure/backup/"
            "sap-hana-database-about"
        ),
    },
    {
        "id": "monitoring",
        "category": "operations",
        "title": "Deploy Azure Monitor for SAP solutions",
        "description": (
            "Use Azure Monitor for SAP to collect telemetry from HANA,"
            " OS, high-availability clusters, and SQL."
        ),
        "severity": "high",
        "link": (
            "https://learn.microsoft.com/azure/sap/"
            "monitor/about-azure-monitor-sap-solutions"
        ),
    },
    {
        "id": "load_balancer",
        "category": "networking",
        "title": "Use Azure Standard Load Balancer for clustering",
        "description": (
            "Standard LB with HA ports is required for ASCS/SCS and"
            " HANA cluster virtual IP addresses."
        ),
        "severity": "critical",
        "link": (
            "https://learn.microsoft.com/azure/load-balancer/"
            "load-balancer-overview"
        ),
    },
    {
        "id": "os_tuning",
        "category": "compute",
        "title": "Apply SAP-recommended OS tuning parameters",
        "description": (
            "Configure kernel parameters, I/O scheduler, and memory"
            " settings per SAP Note 2382421 (SLES) or 2772999 (RHEL)."
        ),
        "severity": "high",
        "link": "https://launchpad.support.sap.com/",
    },
]

# ── Reference Architectures ──────────────────────────────────────────────────

SAP_REFERENCE_ARCHITECTURES: list[dict] = [
    {
        "id": "s4hana_ha",
        "name": "SAP S/4HANA High Availability",
        "description": (
            "Production S/4HANA on Azure with HANA System Replication,"
            " Pacemaker clustering, Standard Load Balancer, Azure"
            " NetApp Files, and Azure Backup."
        ),
        "product": "s4hana",
        "database": "hana",
        "ha_enabled": True,
        "dr_enabled": True,
        "components": [
            "HANA DB (M-series, HA with HSR)",
            "SAP Application Servers (E-series, clustered)",
            "ASCS/SCS cluster (Pacemaker)",
            "Web Dispatcher (load-balanced)",
            "Azure NetApp Files (/hana/shared, /sapmnt)",
            "Standard Load Balancers (ASCS + HANA)",
            "Proximity Placement Group",
            "Azure Backup for SAP HANA",
            "Azure Monitor for SAP",
        ],
        "link": (
            "https://learn.microsoft.com/azure/architecture/"
            "guide/sap/sap-s4hana"
        ),
    },
    {
        "id": "ecc_migration",
        "name": "SAP ECC Migration to Azure",
        "description": (
            "Brownfield migration of SAP ECC to Azure with database"
            " migration to HANA or SQL Server, minimal downtime"
            " approach, and Azure Site Recovery for cutover."
        ),
        "product": "ecc",
        "database": "hana",
        "ha_enabled": True,
        "dr_enabled": False,
        "components": [
            "HANA DB (M-series, optional HA)",
            "SAP Application Servers (E-series)",
            "ASCS/SCS instance",
            "Azure Site Recovery (migration cutover)",
            "Azure Migrate (discovery & assessment)",
            "Standard Load Balancer",
            "Azure Backup for SAP",
        ],
        "link": (
            "https://learn.microsoft.com/azure/architecture/"
            "guide/sap/sap-on-azure-architecture-guide"
        ),
    },
    {
        "id": "bw4hana",
        "name": "SAP BW/4HANA on Azure",
        "description": (
            "BW/4HANA analytics workload on Azure with scale-out HANA"
            " for large data volumes, Azure Synapse integration, and"
            " Azure NetApp Files for persistence."
        ),
        "product": "bw4hana",
        "database": "hana",
        "ha_enabled": True,
        "dr_enabled": True,
        "components": [
            "HANA DB (Mv2-series, scale-out optional)",
            "BW/4HANA Application Server (E-series)",
            "ASCS/SCS cluster",
            "Azure NetApp Files",
            "Azure Synapse Analytics (integration)",
            "Standard Load Balancer",
            "Azure Monitor for SAP",
        ],
        "link": (
            "https://learn.microsoft.com/azure/architecture/"
            "guide/sap/sap-s4hana"
        ),
    },
]


class SapAccelerator:
    """SAP on Azure landing zone accelerator.

    Provides questionnaire, certified SKU catalogue, architecture
    generation, sizing estimation, best practices, and reference
    architectures for SAP workloads on Azure.
    """

    # ── Questionnaire ────────────────────────────────────────────────

    def get_questions(self) -> list[dict]:
        """Return SAP-specific questionnaire questions.

        Returns:
            List of question dicts with id, text, type, options, etc.
        """
        return [dict(q) for q in SAP_QUESTIONS]

    # ── Certified SKUs ───────────────────────────────────────────────

    def get_certified_skus(self, requirements: dict) -> list[dict]:
        """Return SAP-certified VM SKUs filtered by requirements.

        Args:
            requirements: Optional filters — ``tier`` (hana|app),
                ``min_memory_gb``, ``min_saps``, ``series``.

        Returns:
            List of matching certified SKU dicts.
        """
        tier = requirements.get("tier")
        min_mem = requirements.get("min_memory_gb", 0)
        min_saps = requirements.get("min_saps", 0)
        series = requirements.get("series")

        results = []
        for sku in SAP_CERTIFIED_SKUS:
            if tier and sku["tier"] != tier:
                continue
            if sku["memory_gb"] < min_mem:
                continue
            if sku["saps_rating"] < min_saps:
                continue
            if series and sku["series"] != series:
                continue
            results.append(dict(sku))
        return results

    # ── Architecture Generation ──────────────────────────────────────

    def generate_architecture(self, answers: dict) -> dict:
        """Generate an SAP landing zone architecture from answers.

        Args:
            answers: Dict of questionnaire answer values keyed by
                question id.

        Returns:
            Architecture dict with tiers, components, and config.
        """
        product = answers.get("sap_product", "s4hana")
        database = answers.get("sap_database", "hana")
        ha = answers.get("high_availability", "no") == "yes"
        dr = answers.get("disaster_recovery", "no") == "yes"
        data_vol = answers.get("data_volume", "medium")
        saps = int(answers.get("saps_rating", 0))
        integrations = answers.get(
            "integration_requirements", []
        )
        env_type = answers.get("environment_type", "production")

        # Size the DB tier
        db_sku = self._select_hana_sku(saps, data_vol)
        # Size the app tier
        app_sku = self._select_app_sku(saps)

        architecture: dict = {
            "name": f"SAP {product.upper()} on Azure",
            "product": product,
            "database": database,
            "environment": env_type,
            "tiers": {},
            "shared_services": [],
            "networking": {},
            "operations": {},
        }

        # DB tier
        db_tier: dict = {
            "vm_sku": db_sku["name"],
            "vm_count": 2 if ha else 1,
            "os": "SUSE Linux Enterprise Server 15 SP5",
            "accelerated_networking": True,
        }
        if database == "hana":
            db_tier["hsr_enabled"] = ha
            db_tier["hsr_mode"] = "sync" if ha else "none"
        architecture["tiers"]["database"] = db_tier

        # App server tier
        app_count = max(2, math.ceil(saps / app_sku["saps_rating"])
                        ) if saps > 0 else 2
        architecture["tiers"]["application"] = {
            "vm_sku": app_sku["name"],
            "vm_count": app_count,
            "os": "SUSE Linux Enterprise Server 15 SP5",
            "clustered": True,
            "accelerated_networking": True,
        }

        # ASCS/SCS cluster
        architecture["tiers"]["ascs"] = {
            "vm_sku": "Standard_E4s_v5",
            "vm_count": 2 if ha else 1,
            "clustered": ha,
            "cluster_type": "Pacemaker" if ha else "none",
            "accelerated_networking": True,
        }

        # Web Dispatcher
        if isinstance(integrations, list) and "fiori" in integrations:
            architecture["tiers"]["web_dispatcher"] = {
                "vm_sku": "Standard_E4s_v5",
                "vm_count": 2,
                "load_balanced": True,
            }

        # Shared services
        architecture["shared_services"] = [
            {
                "type": "azure_netapp_files",
                "purpose": "/hana/shared, /sapmnt, transport",
                "tier": "Premium",
            },
            {
                "type": "standard_load_balancer",
                "purpose": "ASCS + HANA cluster VIPs",
                "ha_ports": True,
            },
            {
                "type": "proximity_placement_group",
                "purpose": "Co-locate SAP tiers for low latency",
            },
        ]

        # Networking
        architecture["networking"] = {
            "vnet": "sap-vnet",
            "subnets": [
                {"name": "sap-db", "prefix": "10.1.1.0/24"},
                {"name": "sap-app", "prefix": "10.1.2.0/24"},
                {"name": "sap-web", "prefix": "10.1.3.0/24"},
            ],
            "nsg_enabled": True,
            "accelerated_networking": True,
        }

        # Operations
        architecture["operations"] = {
            "backup": {
                "type": "azure_backup_sap_hana"
                if database == "hana"
                else "azure_backup",
                "enabled": True,
            },
            "monitoring": {
                "type": "azure_monitor_for_sap",
                "enabled": True,
            },
        }

        # DR
        if dr:
            rpo_rto = answers.get("rpo_rto", "rpo_15_rto_60")
            architecture["disaster_recovery"] = {
                "enabled": True,
                "rpo_rto": rpo_rto,
                "strategy": (
                    "HANA System Replication (async)"
                    if database == "hana"
                    else "Azure Site Recovery"
                ),
                "secondary_region": "paired",
            }

        return architecture

    # ── Best Practices ───────────────────────────────────────────────

    def get_best_practices(self) -> list[dict]:
        """Return the SAP on Azure best-practice checklist.

        Returns:
            List of best-practice dicts.
        """
        return [dict(bp) for bp in SAP_BEST_PRACTICES]

    # ── Sizing Estimation ────────────────────────────────────────────

    def estimate_sizing(self, requirements: dict) -> dict:
        """Estimate SAP VM sizing from workload requirements.

        Args:
            requirements: Dict with ``saps``, ``memory_gb`` or
                ``data_volume``, and ``concurrent_users``.

        Returns:
            Dict with recommended DB and app server SKUs and counts.
        """
        saps = int(requirements.get("saps", 0))
        data_volume = requirements.get("data_volume", "medium")
        users = int(requirements.get("concurrent_users", 100))

        # Estimate SAPS from users if not provided
        if saps == 0:
            saps = users * 100  # rough heuristic

        db_sku = self._select_hana_sku(saps, data_volume)
        app_sku = self._select_app_sku(saps)
        app_count = max(2, math.ceil(saps / app_sku["saps_rating"])
                        ) if saps > 0 else 2

        return {
            "database_sku": db_sku,
            "app_server_sku": app_sku,
            "app_server_count": app_count,
            "total_saps": saps,
            "estimated_memory_gb": _DATA_VOLUME_GB.get(
                data_volume, 2048
            ),
        }

    # ── Architecture Validation ──────────────────────────────────────

    def validate_architecture(self, architecture: dict) -> dict:
        """Validate an SAP architecture against best practices.

        Args:
            architecture: Architecture dict (from generate_architecture).

        Returns:
            Dict with ``valid``, ``errors``, ``warnings``.
        """
        errors: list[str] = []
        warnings: list[str] = []

        tiers = architecture.get("tiers", {})

        # Check DB tier exists
        if "database" not in tiers:
            errors.append("Missing database tier.")

        # Check DB SKU is certified HANA
        db_tier = tiers.get("database", {})
        db_sku_name = db_tier.get("vm_sku", "")
        certified_names = {s["name"] for s in SAP_CERTIFIED_SKUS
                          if s["tier"] == "hana"}
        if db_sku_name and db_sku_name not in certified_names:
            app_names = {s["name"] for s in SAP_CERTIFIED_SKUS
                         if s["tier"] == "app"}
            if db_sku_name not in app_names:
                errors.append(
                    f"VM SKU '{db_sku_name}' is not SAP-certified."
                )

        # Check HA configuration
        if db_tier.get("vm_count", 1) >= 2 and not db_tier.get(
            "hsr_enabled", False
        ):
            warnings.append(
                "Multiple DB VMs without HANA System Replication."
            )

        # Check app tier exists
        if "application" not in tiers:
            errors.append("Missing application server tier.")

        # Check ASCS tier exists
        if "ascs" not in tiers:
            warnings.append("Missing ASCS/SCS tier.")

        # Check accelerated networking
        for tier_name, tier_cfg in tiers.items():
            if not tier_cfg.get("accelerated_networking", False):
                warnings.append(
                    f"Tier '{tier_name}' missing accelerated networking."
                )

        # Check shared services
        shared = architecture.get("shared_services", [])
        shared_types = {s.get("type") for s in shared}
        if "proximity_placement_group" not in shared_types:
            warnings.append("Missing proximity placement group.")
        if "standard_load_balancer" not in shared_types:
            warnings.append("Missing Standard Load Balancer.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    # ── Reference Architectures ──────────────────────────────────────

    def get_reference_architectures(self) -> list[dict]:
        """Return SAP reference architecture patterns.

        Returns:
            List of reference architecture dicts.
        """
        return [dict(ra) for ra in SAP_REFERENCE_ARCHITECTURES]

    # ── Private helpers ──────────────────────────────────────────────

    def _select_hana_sku(self, saps: int, data_volume: str) -> dict:
        """Pick the smallest HANA-certified SKU that fits.

        Args:
            saps: Required SAPS rating.
            data_volume: Data volume key (small..ultra_large).

        Returns:
            SKU dict for the recommended HANA VM.
        """
        needed_mem = _DATA_VOLUME_GB.get(data_volume, 2048)
        hana_skus = [
            s for s in SAP_CERTIFIED_SKUS if s["tier"] == "hana"
        ]
        # Sort by memory ascending
        hana_skus.sort(key=lambda s: s["memory_gb"])
        for sku in hana_skus:
            if (
                sku["memory_gb"] >= needed_mem
                and sku["saps_rating"] >= saps
            ):
                return dict(sku)
        # Default to largest if nothing fits
        return dict(hana_skus[-1])

    def _select_app_sku(self, saps: int) -> dict:
        """Pick the smallest app-tier SKU that fits.

        Args:
            saps: Required total SAPS.

        Returns:
            SKU dict for the recommended app server VM.
        """
        app_skus = [
            s for s in SAP_CERTIFIED_SKUS if s["tier"] == "app"
        ]
        app_skus.sort(key=lambda s: s["saps_rating"])
        for sku in app_skus:
            if sku["saps_rating"] >= saps:
                return dict(sku)
        # Default to largest
        return dict(app_skus[-1])


sap_accelerator = SapAccelerator()
