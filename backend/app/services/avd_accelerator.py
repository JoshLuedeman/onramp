"""Azure Virtual Desktop landing zone accelerator.

Provides questionnaire, SKU recommendations, architecture generation,
best practices, sizing estimation, validation, and reference
architectures for AVD deployments.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── AVD Questionnaire ────────────────────────────────────────────────────────

AVD_QUESTIONS: list[dict] = [
    {
        "id": "avd_user_count",
        "category": "capacity",
        "text": "How many concurrent users will use AVD?",
        "type": "single_choice",
        "options": [
            {"value": "10-50", "label": "10–50 users"},
            {"value": "50-200", "label": "50–200 users"},
            {"value": "200-1000", "label": "200–1,000 users"},
            {"value": "1000+", "label": "1,000+ users"},
        ],
        "required": True,
        "order": 1,
    },
    {
        "id": "avd_user_type",
        "category": "workload",
        "text": "What type of users will be using AVD?",
        "type": "single_choice",
        "options": [
            {"value": "task_worker", "label": "Task worker"},
            {"value": "knowledge_worker", "label": "Knowledge worker"},
            {"value": "power_user", "label": "Power user"},
            {"value": "developer", "label": "Developer"},
        ],
        "required": True,
        "order": 2,
    },
    {
        "id": "avd_application_type",
        "category": "workload",
        "text": "What type of applications will users run?",
        "type": "single_choice",
        "options": [
            {"value": "desktop_apps", "label": "Desktop applications"},
            {"value": "web_apps", "label": "Web applications"},
            {"value": "cad_3d", "label": "CAD / 3D rendering"},
            {"value": "office_productivity", "label": "Office productivity"},
        ],
        "required": True,
        "order": 3,
    },
    {
        "id": "avd_fslogix_storage",
        "category": "storage",
        "text": "Which storage solution for FSLogix profile containers?",
        "type": "single_choice",
        "options": [
            {"value": "azure_files", "label": "Azure Files"},
            {"value": "azure_netapp_files", "label": "Azure NetApp Files"},
        ],
        "required": True,
        "order": 4,
    },
    {
        "id": "avd_image_management",
        "category": "compute",
        "text": "How will you manage session host images?",
        "type": "single_choice",
        "options": [
            {"value": "marketplace", "label": "Azure Marketplace image"},
            {"value": "custom", "label": "Custom image"},
            {
                "value": "shared_image_gallery",
                "label": "Azure Compute Gallery (Shared Image Gallery)",
            },
        ],
        "required": True,
        "order": 5,
    },
    {
        "id": "avd_authentication",
        "category": "identity",
        "text": "What identity provider will be used for authentication?",
        "type": "single_choice",
        "options": [
            {"value": "entra_id", "label": "Microsoft Entra ID (cloud-only)"},
            {
                "value": "ad_ds",
                "label": "Active Directory Domain Services (on-prem)",
            },
            {
                "value": "hybrid",
                "label": "Hybrid (Entra ID + AD DS)",
            },
        ],
        "required": True,
        "order": 6,
    },
    {
        "id": "avd_desktop_type",
        "category": "compute",
        "text": "Multi-session (pooled) or personal desktops?",
        "type": "single_choice",
        "options": [
            {"value": "multi_session", "label": "Multi-session (pooled)"},
            {"value": "personal", "label": "Personal desktops"},
        ],
        "required": True,
        "order": 7,
    },
    {
        "id": "avd_geographic_distribution",
        "category": "networking",
        "text": "What is the geographic distribution of your users?",
        "type": "single_choice",
        "options": [
            {"value": "single_region", "label": "Single Azure region"},
            {"value": "multi_region", "label": "Multiple Azure regions"},
        ],
        "required": True,
        "order": 8,
    },
    {
        "id": "avd_scaling_behavior",
        "category": "capacity",
        "text": "What scaling behavior do you need for session hosts?",
        "type": "single_choice",
        "options": [
            {"value": "fixed", "label": "Fixed (always-on)"},
            {"value": "autoscale", "label": "Autoscale (demand-based)"},
            {"value": "peak_hours", "label": "Peak-hours scaling plan"},
        ],
        "required": True,
        "order": 9,
    },
    {
        "id": "avd_printing",
        "category": "peripherals",
        "text": "What printing solution is required?",
        "type": "single_choice",
        "options": [
            {"value": "local_redirect", "label": "Local printer redirection"},
            {"value": "universal_print", "label": "Microsoft Universal Print"},
            {"value": "none", "label": "No printing required"},
        ],
        "required": True,
        "order": 10,
    },
    {
        "id": "avd_monitoring",
        "category": "operations",
        "text": "What monitoring strategy do you want?",
        "type": "single_choice",
        "options": [
            {"value": "basic", "label": "Basic (VM metrics only)"},
            {"value": "avd_insights", "label": "AVD Insights (full dashboard)"},
        ],
        "required": False,
        "order": 11,
    },
    {
        "id": "avd_bcdr",
        "category": "resilience",
        "text": "Do you need business-continuity / disaster recovery?",
        "type": "single_choice",
        "options": [
            {"value": "none", "label": "No DR required"},
            {"value": "active_passive", "label": "Active-passive failover"},
            {"value": "active_active", "label": "Active-active multi-region"},
        ],
        "required": False,
        "order": 12,
    },
]

# ── AVD-Optimised SKUs ───────────────────────────────────────────────────────

AVD_SKUS: list[dict] = [
    # D-series — general purpose
    {
        "name": "Standard_D2s_v5",
        "series": "Dsv5",
        "family": "general_purpose",
        "vcpus": 2,
        "memory_gb": 8,
        "gpu": False,
        "users_per_vm": {"task_worker": 4, "knowledge_worker": 2},
        "description": "General-purpose, 2 vCPUs, 8 GiB RAM.",
    },
    {
        "name": "Standard_D4s_v5",
        "series": "Dsv5",
        "family": "general_purpose",
        "vcpus": 4,
        "memory_gb": 16,
        "gpu": False,
        "users_per_vm": {"task_worker": 6, "knowledge_worker": 4},
        "description": "General-purpose, 4 vCPUs, 16 GiB RAM.",
    },
    {
        "name": "Standard_D8s_v5",
        "series": "Dsv5",
        "family": "general_purpose",
        "vcpus": 8,
        "memory_gb": 32,
        "gpu": False,
        "users_per_vm": {
            "task_worker": 12,
            "knowledge_worker": 8,
            "power_user": 4,
        },
        "description": "General-purpose, 8 vCPUs, 32 GiB RAM.",
    },
    {
        "name": "Standard_D16s_v5",
        "series": "Dsv5",
        "family": "general_purpose",
        "vcpus": 16,
        "memory_gb": 64,
        "gpu": False,
        "users_per_vm": {
            "task_worker": 24,
            "knowledge_worker": 16,
            "power_user": 8,
        },
        "description": "General-purpose, 16 vCPUs, 64 GiB RAM.",
    },
    # E-series — memory-intensive (multi-session)
    {
        "name": "Standard_E2s_v5",
        "series": "Esv5",
        "family": "memory_optimized",
        "vcpus": 2,
        "memory_gb": 16,
        "gpu": False,
        "users_per_vm": {"task_worker": 4, "knowledge_worker": 3},
        "description": "Memory-optimized, 2 vCPUs, 16 GiB RAM.",
    },
    {
        "name": "Standard_E4s_v5",
        "series": "Esv5",
        "family": "memory_optimized",
        "vcpus": 4,
        "memory_gb": 32,
        "gpu": False,
        "users_per_vm": {
            "task_worker": 8,
            "knowledge_worker": 6,
            "power_user": 3,
        },
        "description": "Memory-optimized, 4 vCPUs, 32 GiB RAM.",
    },
    {
        "name": "Standard_E8s_v5",
        "series": "Esv5",
        "family": "memory_optimized",
        "vcpus": 8,
        "memory_gb": 64,
        "gpu": False,
        "users_per_vm": {
            "task_worker": 16,
            "knowledge_worker": 10,
            "power_user": 6,
        },
        "description": "Memory-optimized, 8 vCPUs, 64 GiB RAM.",
    },
    {
        "name": "Standard_E16s_v5",
        "series": "Esv5",
        "family": "memory_optimized",
        "vcpus": 16,
        "memory_gb": 128,
        "gpu": False,
        "users_per_vm": {
            "task_worker": 32,
            "knowledge_worker": 20,
            "power_user": 10,
        },
        "description": "Memory-optimized, 16 vCPUs, 128 GiB RAM.",
    },
    # NV-series — GPU (CAD/3D)
    {
        "name": "Standard_NV6ads_A10_v5",
        "series": "NVadsA10v5",
        "family": "gpu",
        "vcpus": 6,
        "memory_gb": 55,
        "gpu": True,
        "users_per_vm": {"developer": 2, "power_user": 2},
        "description": "GPU-accelerated, 6 vCPUs, 55 GiB RAM, NVIDIA A10.",
    },
    {
        "name": "Standard_NV12ads_A10_v5",
        "series": "NVadsA10v5",
        "family": "gpu",
        "vcpus": 12,
        "memory_gb": 110,
        "gpu": True,
        "users_per_vm": {"developer": 4, "power_user": 4},
        "description": "GPU-accelerated, 12 vCPUs, 110 GiB RAM, NVIDIA A10.",
    },
    {
        "name": "Standard_NV36ads_A10_v5",
        "series": "NVadsA10v5",
        "family": "gpu",
        "vcpus": 36,
        "memory_gb": 440,
        "gpu": True,
        "users_per_vm": {"developer": 8, "power_user": 6},
        "description": "GPU-accelerated, 36 vCPUs, 440 GiB RAM, NVIDIA A10.",
    },
]

# ── Best Practices ───────────────────────────────────────────────────────────

AVD_BEST_PRACTICES: list[dict] = [
    {
        "id": "bp_fslogix_separate_storage",
        "title": "Use dedicated storage for FSLogix profiles",
        "description": (
            "Place FSLogix profile containers on a separate Azure Files"
            " Premium or Azure NetApp Files volume to isolate profile"
            " IOPS from session host workloads."
        ),
        "category": "storage",
        "severity": "high",
    },
    {
        "id": "bp_golden_image_pipeline",
        "title": "Automate golden image builds",
        "description": (
            "Use Azure Image Builder or a DevOps pipeline to produce"
            " versioned golden images stored in Azure Compute Gallery."
        ),
        "category": "compute",
        "severity": "high",
    },
    {
        "id": "bp_scaling_plan",
        "title": "Configure an autoscale scaling plan",
        "description": (
            "Use the built-in AVD scaling plan to power session hosts"
            " on/off based on demand, reducing costs outside peak hours."
        ),
        "category": "capacity",
        "severity": "medium",
    },
    {
        "id": "bp_monitoring",
        "title": "Enable AVD Insights workbook",
        "description": (
            "Deploy the AVD Insights workbook in Azure Monitor to"
            " track connection reliability, session latency, and host"
            " health at a glance."
        ),
        "category": "operations",
        "severity": "high",
    },
    {
        "id": "bp_drain_mode",
        "title": "Use drain mode for maintenance",
        "description": (
            "Enable drain mode on session hosts before patching to"
            " prevent new connections while existing sessions complete."
        ),
        "category": "operations",
        "severity": "medium",
    },
    {
        "id": "bp_private_endpoints",
        "title": "Use Private Link for AVD control plane",
        "description": (
            "Configure Private Link for AVD host pools to keep"
            " control-plane traffic off the public internet."
        ),
        "category": "networking",
        "severity": "high",
    },
    {
        "id": "bp_conditional_access",
        "title": "Apply Conditional Access policies",
        "description": (
            "Require compliant devices, MFA, and restrict sign-in"
            " locations using Entra ID Conditional Access for AVD."
        ),
        "category": "identity",
        "severity": "high",
    },
    {
        "id": "bp_session_time_limits",
        "title": "Set session time limits",
        "description": (
            "Configure idle, disconnect, and max-session timeouts to"
            " reclaim resources from inactive sessions promptly."
        ),
        "category": "capacity",
        "severity": "medium",
    },
]

# ── Reference Architectures ──────────────────────────────────────────────────

AVD_REFERENCE_ARCHITECTURES: list[dict] = [
    {
        "id": "small_team",
        "name": "Small Team",
        "description": (
            "Pooled multi-session desktops for up to 50 users with"
            " Azure Files for FSLogix profiles and a single host pool."
        ),
        "user_count": "10-50",
        "host_pool_type": "pooled",
        "session_host_count": 3,
        "vm_sku": "Standard_D4s_v5",
        "fslogix_storage": "azure_files",
        "regions": 1,
        "scaling": "autoscale",
        "components": [
            "host_pool",
            "workspace",
            "desktop_app_group",
            "azure_files",
            "vnet",
            "nsg",
            "log_analytics",
        ],
    },
    {
        "id": "enterprise_pooled",
        "name": "Enterprise Pooled",
        "description": (
            "Large-scale pooled deployment for 200–1,000 knowledge"
            " workers with Azure NetApp Files, multiple host pools,"
            " autoscale, and AVD Insights."
        ),
        "user_count": "200-1000",
        "host_pool_type": "pooled",
        "session_host_count": 25,
        "vm_sku": "Standard_E8s_v5",
        "fslogix_storage": "azure_netapp_files",
        "regions": 2,
        "scaling": "autoscale",
        "components": [
            "host_pool",
            "workspace",
            "desktop_app_group",
            "remoteapp_app_group",
            "azure_netapp_files",
            "vnet",
            "nsg",
            "private_endpoints",
            "log_analytics",
            "avd_insights",
            "scaling_plan",
            "image_gallery",
        ],
    },
    {
        "id": "developer_personal",
        "name": "Developer Personal Desktops",
        "description": (
            "Personal desktops with GPU-enabled VMs for developers"
            " and power users running CAD/3D or heavy compilation"
            " workloads."
        ),
        "user_count": "10-50",
        "host_pool_type": "personal",
        "session_host_count": 10,
        "vm_sku": "Standard_NV12ads_A10_v5",
        "fslogix_storage": "azure_files",
        "regions": 1,
        "scaling": "fixed",
        "components": [
            "host_pool",
            "workspace",
            "desktop_app_group",
            "azure_files",
            "vnet",
            "nsg",
            "log_analytics",
            "image_gallery",
        ],
    },
]


class AvdAccelerator:
    """Azure Virtual Desktop landing zone accelerator (singleton)."""

    def get_questions(self) -> list[dict]:
        """Return AVD-specific questionnaire questions.

        Returns:
            List of question dicts with id, category, text, type,
            options, required, and order fields.
        """
        return list(AVD_QUESTIONS)

    def get_sku_recommendations(
        self,
        user_type: str = "knowledge_worker",
        application_type: str = "office_productivity",
    ) -> list[dict]:
        """Return AVD-optimised VM SKU recommendations.

        Args:
            user_type: One of task_worker, knowledge_worker,
                power_user, developer.
            application_type: One of desktop_apps, web_apps,
                cad_3d, office_productivity.

        Returns:
            Filtered and sorted list of SKU dicts suitable for
            the given workload profile.
        """
        needs_gpu = application_type == "cad_3d"
        results: list[dict] = []
        for sku in AVD_SKUS:
            if needs_gpu and not sku["gpu"]:
                continue
            if not needs_gpu and sku["gpu"]:
                continue
            users = sku["users_per_vm"].get(user_type)
            if users is None:
                continue
            results.append({**sku, "recommended_users": users})
        results.sort(
            key=lambda s: s.get("recommended_users", 0), reverse=True
        )
        return results

    def generate_architecture(self, answers: dict) -> dict:
        """Generate an AVD landing-zone architecture from answers.

        Args:
            answers: Dict of questionnaire answer values keyed by
                question id.

        Returns:
            Architecture dict with host_pool, session_hosts,
            fslogix, workspace, app_groups, network, monitoring,
            image_management, and conditional_access sections.
        """
        user_count = answers.get("avd_user_count", "50-200")
        user_type = answers.get("avd_user_type", "knowledge_worker")
        app_type = answers.get(
            "avd_application_type", "office_productivity"
        )
        storage = answers.get("avd_fslogix_storage", "azure_files")
        image = answers.get("avd_image_management", "marketplace")
        auth = answers.get("avd_authentication", "entra_id")
        desktop = answers.get("avd_desktop_type", "multi_session")
        geo = answers.get(
            "avd_geographic_distribution", "single_region"
        )
        scaling = answers.get("avd_scaling_behavior", "autoscale")
        printing = answers.get("avd_printing", "none")
        monitoring = answers.get("avd_monitoring", "avd_insights")

        skus = self.get_sku_recommendations(user_type, app_type)
        recommended_sku = skus[0]["name"] if skus else "Standard_D4s_v5"

        sizing = self.estimate_sizing(
            {"user_count": user_count, "user_type": user_type}
        )
        host_count = sizing.get("session_host_count", 4)

        pool_type = (
            "Personal" if desktop == "personal" else "Pooled"
        )
        lb_type = (
            "Persistent" if desktop == "personal" else "BreadthFirst"
        )

        return {
            "host_pool": {
                "type": pool_type,
                "load_balancer_type": lb_type,
                "max_session_limit": sizing.get(
                    "users_per_host", 8
                ),
                "scaling_plan_enabled": scaling != "fixed",
                "validation_environment": False,
            },
            "session_hosts": {
                "count": host_count,
                "vm_sku": recommended_sku,
                "os": "Windows 11 Enterprise multi-session"
                if desktop == "multi_session"
                else "Windows 11 Enterprise",
                "image_source": image,
                "availability_zone_balanced": True,
            },
            "fslogix": {
                "storage_type": storage,
                "container_type": "Profile + Office",
                "share_name": "fslogix-profiles",
            },
            "workspace": {
                "name": "avd-workspace",
                "friendly_name": "Azure Virtual Desktop",
            },
            "app_groups": self._build_app_groups(desktop),
            "network": {
                "vnet_address_space": "10.0.0.0/16",
                "session_host_subnet": "10.0.1.0/24",
                "private_endpoint_subnet": "10.0.2.0/24",
                "nsg_enabled": True,
                "private_endpoints": True,
            },
            "monitoring": {
                "log_analytics": True,
                "avd_insights": monitoring == "avd_insights",
                "diagnostics_enabled": True,
            },
            "image_management": {
                "source": image,
                "compute_gallery": image == "shared_image_gallery",
                "image_builder_pipeline": image != "marketplace",
            },
            "conditional_access": {
                "mfa_required": True,
                "compliant_device_required": auth != "ad_ds",
                "authentication_method": auth,
            },
            "printing": {
                "method": printing,
            },
            "geographic_distribution": geo,
        }

    def get_best_practices(self) -> list[dict]:
        """Return AVD deployment best practices.

        Returns:
            List of best-practice dicts.
        """
        return list(AVD_BEST_PRACTICES)

    def estimate_sizing(self, requirements: dict) -> dict:
        """Estimate session-host sizing from requirements.

        Args:
            requirements: Dict with user_count range string and
                optional user_type.

        Returns:
            Dict with session_host_count, users_per_host,
            recommended_sku, and storage_gb estimates.
        """
        count_str = requirements.get("user_count", "50-200")
        user_type = requirements.get(
            "user_type", "knowledge_worker"
        )

        count_map = {
            "10-50": 30,
            "50-200": 125,
            "200-1000": 600,
            "1000+": 1500,
        }
        user_count = count_map.get(count_str, 125)

        users_per_host_map = {
            "task_worker": 12,
            "knowledge_worker": 8,
            "power_user": 4,
            "developer": 4,
        }
        users_per_host = users_per_host_map.get(user_type, 8)

        host_count = max(
            2, -(-user_count // users_per_host)  # ceiling division
        )

        sku_map = {
            "task_worker": "Standard_D8s_v5",
            "knowledge_worker": "Standard_E8s_v5",
            "power_user": "Standard_E16s_v5",
            "developer": "Standard_NV12ads_A10_v5",
        }
        recommended_sku = sku_map.get(
            user_type, "Standard_E8s_v5"
        )

        # ~30 GiB per profile
        storage_gb = user_count * 30

        return {
            "session_host_count": host_count,
            "users_per_host": users_per_host,
            "recommended_sku": recommended_sku,
            "total_users": user_count,
            "storage_gb": storage_gb,
        }

    def validate_architecture(self, architecture: dict) -> dict:
        """Validate an AVD architecture dict.

        Args:
            architecture: Architecture dict as returned by
                generate_architecture.

        Returns:
            Dict with valid bool, errors list, and warnings list.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if "host_pool" not in architecture:
            errors.append("Missing host_pool configuration.")
        if "session_hosts" not in architecture:
            errors.append("Missing session_hosts configuration.")
        if "fslogix" not in architecture:
            errors.append("Missing fslogix configuration.")
        if "network" not in architecture:
            errors.append("Missing network configuration.")

        hp = architecture.get("host_pool", {})
        if hp.get("type") not in ("Pooled", "Personal"):
            errors.append(
                "host_pool.type must be 'Pooled' or 'Personal'."
            )

        sh = architecture.get("session_hosts", {})
        count = sh.get("count", 0)
        if count < 1:
            errors.append("session_hosts.count must be >= 1.")
        if count < 2:
            warnings.append(
                "Single session host has no redundancy."
            )

        net = architecture.get("network", {})
        if not net.get("nsg_enabled"):
            warnings.append(
                "NSG is disabled; consider enabling for security."
            )
        if not net.get("private_endpoints"):
            warnings.append(
                "Private endpoints not configured; traffic will"
                " traverse the public internet."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def get_reference_architectures(self) -> list[dict]:
        """Return pre-built AVD reference architectures.

        Returns:
            List of reference architecture dicts.
        """
        return list(AVD_REFERENCE_ARCHITECTURES)

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _build_app_groups(desktop_type: str) -> list[dict]:
        """Return application groups for the deployment."""
        groups = [
            {
                "name": "avd-dag",
                "friendly_name": "Desktop",
                "type": "Desktop",
            },
        ]
        if desktop_type == "multi_session":
            groups.append(
                {
                    "name": "avd-rag",
                    "friendly_name": "RemoteApps",
                    "type": "RemoteApp",
                }
            )
        return groups


avd_accelerator = AvdAccelerator()
