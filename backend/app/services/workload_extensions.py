"""Pluggable workload extension framework for specialized landing zones.

Provides a registry/plugin system that lets specialized workload types
(AI/ML, SAP, AVD, IoT) contribute their own questionnaire questions,
SKU recommendations, architecture validators and best-practice rules.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class WorkloadExtension(ABC):
    """Base class for workload-specific extensions.

    Subclass this to register a new workload type with the
    ``WorkloadExtensionRegistry``.
    """

    @property
    @abstractmethod
    def workload_type(self) -> str:
        """Machine-readable identifier (e.g. ``ai_ml``, ``sap``)."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable label shown in the UI."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of this workload type."""

    @abstractmethod
    def get_questions(self) -> list[dict[str, Any]]:
        """Return workload-specific questionnaire questions.

        Returns:
            List of question dicts compatible with the questionnaire engine.
        """

    @abstractmethod
    def get_sku_database(self) -> list[dict[str, Any]]:
        """Return recommended SKUs for this workload type.

        Returns:
            List of SKU dicts with id, name, family, specs, etc.
        """

    @abstractmethod
    def validate_architecture(self, architecture: dict[str, Any]) -> dict[str, Any]:
        """Validate an architecture meets this workload's requirements.

        Args:
            architecture: The full architecture dict to validate.

        Returns:
            Dict with ``valid``, ``errors``, ``warnings``, ``suggestions``.
        """

    @abstractmethod
    def get_best_practices(self) -> list[dict[str, Any]]:
        """Return workload-specific best-practice rules.

        Returns:
            List of best-practice dicts with id, title, description, etc.
        """

    @abstractmethod
    def estimate_sizing(self, requirements: dict[str, Any]) -> dict[str, Any]:
        """Estimate resource sizing for this workload.

        Args:
            requirements: A dict of workload sizing requirements.

        Returns:
            Dict with recommended resource sizes and estimated costs.
        """


# ---------------------------------------------------------------------------
# Built-in workload extensions
# ---------------------------------------------------------------------------


class AiMlExtension(WorkloadExtension):
    """AI / Machine Learning workload extension."""

    @property
    def workload_type(self) -> str:
        return "ai_ml"

    @property
    def display_name(self) -> str:
        return "AI / Machine Learning"

    @property
    def description(self) -> str:
        return "GPU-accelerated compute, model training, inference endpoints and MLOps pipelines."

    def get_questions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "ai_ml_framework",
                "category": "workload",
                "text": "Which ML framework will you primarily use?",
                "type": "single_choice",
                "options": [
                    {"value": "pytorch", "label": "PyTorch"},
                    {"value": "tensorflow", "label": "TensorFlow"},
                    {"value": "azure_ml", "label": "Azure Machine Learning"},
                    {"value": "other", "label": "Other"},
                ],
                "required": True,
                "order": 1,
            },
            {
                "id": "ai_ml_gpu_required",
                "category": "workload",
                "text": "Do you need GPU-accelerated compute?",
                "type": "single_choice",
                "options": [
                    {"value": "yes", "label": "Yes"},
                    {"value": "no", "label": "No"},
                ],
                "required": True,
                "order": 2,
            },
            {
                "id": "ai_ml_data_size",
                "category": "workload",
                "text": "What is the approximate size of your training data?",
                "type": "single_choice",
                "options": [
                    {"value": "small", "label": "Small (< 10 GB)"},
                    {"value": "medium", "label": "Medium (10-100 GB)"},
                    {"value": "large", "label": "Large (100 GB - 1 TB)"},
                    {"value": "very_large", "label": "Very large (> 1 TB)"},
                ],
                "required": True,
                "order": 3,
            },
            {
                "id": "ai_ml_inference",
                "category": "workload",
                "text": "Do you need real-time inference endpoints?",
                "type": "single_choice",
                "options": [
                    {"value": "yes", "label": "Yes — real-time inference"},
                    {"value": "batch", "label": "Batch inference only"},
                    {"value": "no", "label": "No inference needed"},
                ],
                "required": True,
                "order": 4,
            },
        ]

    def get_sku_database(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "nc6s_v3",
                "name": "Standard_NC6s_v3",
                "family": "N",
                "vcpus": 6,
                "ram_gb": 112,
                "gpu": "V100",
                "gpu_count": 1,
                "price_tier": "high",
                "use_case": "Model training and inference",
            },
            {
                "id": "nc24s_v3",
                "name": "Standard_NC24s_v3",
                "family": "N",
                "vcpus": 24,
                "ram_gb": 448,
                "gpu": "V100",
                "gpu_count": 4,
                "price_tier": "premium",
                "use_case": "Large-scale distributed training",
            },
            {
                "id": "nd40rs_v2",
                "name": "Standard_ND40rs_v2",
                "family": "N",
                "vcpus": 40,
                "ram_gb": 672,
                "gpu": "A100",
                "gpu_count": 8,
                "price_tier": "premium",
                "use_case": "Large language model training",
            },
        ]

    def validate_architecture(self, architecture: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        services = architecture.get("services", [])
        service_names = {s.get("name", "") if isinstance(s, dict) else s for s in services}

        if not service_names & {"Azure Machine Learning", "Cognitive Services", "OpenAI Service"}:
            warnings.append("No AI/ML service detected — consider adding Azure Machine Learning.")

        if "Azure Storage" not in service_names and "Data Lake" not in service_names:
            errors.append("AI/ML workloads require Azure Storage or Data Lake for training data.")

        network = architecture.get("network_topology", {})
        if not network.get("private_endpoints"):
            suggestions.append(
                "Enable private endpoints for ML workspace to secure model artifacts."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def get_best_practices(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "aiml_bp_1",
                "title": "Use GPU-optimized VM families",
                "description": "Use N-series VMs (NC, ND, NV) for training workloads.",
                "category": "compute",
                "severity": "high",
            },
            {
                "id": "aiml_bp_2",
                "title": "Implement MLOps pipelines",
                "description": "Automate model training, evaluation, and deployment.",
                "category": "operations",
                "severity": "medium",
            },
            {
                "id": "aiml_bp_3",
                "title": "Secure model endpoints",
                "description": "Use private endpoints and managed identity for inference.",
                "category": "security",
                "severity": "high",
            },
        ]

    def estimate_sizing(self, requirements: dict[str, Any]) -> dict[str, Any]:
        data_size = requirements.get("data_size", "small")
        gpu_required = requirements.get("gpu_required", False)
        concurrent_experiments = requirements.get("concurrent_experiments", 1)

        if gpu_required:
            if data_size in ("large", "very_large"):
                compute_sku = "Standard_NC24s_v3"
                monthly_cost = 8500
            else:
                compute_sku = "Standard_NC6s_v3"
                monthly_cost = 2800
        else:
            compute_sku = "Standard_D8s_v5"
            monthly_cost = 380

        return {
            "compute_sku": compute_sku,
            "compute_count": max(1, concurrent_experiments),
            "storage_type": "Premium_LRS" if data_size in ("large", "very_large") else "Standard_LRS",
            "estimated_monthly_cost_usd": monthly_cost * max(1, concurrent_experiments),
        }


class SapExtension(WorkloadExtension):
    """SAP workload extension."""

    @property
    def workload_type(self) -> str:
        return "sap"

    @property
    def display_name(self) -> str:
        return "SAP"

    @property
    def description(self) -> str:
        return "SAP HANA, S/4HANA and NetWeaver workloads with certified VM families."

    def get_questions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "sap_product",
                "category": "workload",
                "text": "Which SAP product will you deploy?",
                "type": "single_choice",
                "options": [
                    {"value": "s4hana", "label": "S/4HANA"},
                    {"value": "ecc", "label": "ECC on HANA"},
                    {"value": "bw4hana", "label": "BW/4HANA"},
                    {"value": "netweaver", "label": "NetWeaver (non-HANA)"},
                ],
                "required": True,
                "order": 1,
            },
            {
                "id": "sap_ha_required",
                "category": "workload",
                "text": "Do you need high availability for SAP?",
                "type": "single_choice",
                "options": [
                    {"value": "yes", "label": "Yes — HA with Pacemaker/WSFC"},
                    {"value": "no", "label": "No"},
                ],
                "required": True,
                "order": 2,
            },
            {
                "id": "sap_db_size",
                "category": "workload",
                "text": "What is your estimated HANA database size?",
                "type": "single_choice",
                "options": [
                    {"value": "small", "label": "Small (< 256 GB)"},
                    {"value": "medium", "label": "Medium (256 GB - 1 TB)"},
                    {"value": "large", "label": "Large (1 - 4 TB)"},
                    {"value": "very_large", "label": "Very large (> 4 TB)"},
                ],
                "required": True,
                "order": 3,
            },
        ]

    def get_sku_database(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "m32ts",
                "name": "Standard_M32ts",
                "family": "M",
                "vcpus": 32,
                "ram_gb": 192,
                "sap_certified": True,
                "price_tier": "premium",
                "use_case": "Small SAP HANA databases",
            },
            {
                "id": "m64s",
                "name": "Standard_M64s",
                "family": "M",
                "vcpus": 64,
                "ram_gb": 1024,
                "sap_certified": True,
                "price_tier": "premium",
                "use_case": "Medium SAP HANA databases",
            },
            {
                "id": "m128s",
                "name": "Standard_M128s",
                "family": "M",
                "vcpus": 128,
                "ram_gb": 2048,
                "sap_certified": True,
                "price_tier": "premium",
                "use_case": "Large SAP HANA databases",
            },
        ]

    def validate_architecture(self, architecture: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        services = architecture.get("services", [])
        service_names = {s.get("name", "") if isinstance(s, dict) else s for s in services}

        if "Azure Storage" not in service_names:
            errors.append("SAP workloads require Azure Storage for backups and transport.")

        network = architecture.get("network_topology", {})
        if not network.get("express_route") and not network.get("vpn_gateway"):
            warnings.append(
                "SAP workloads typically require ExpressRoute or VPN for on-prem connectivity."
            )

        if not network.get("proximity_placement_groups"):
            suggestions.append(
                "Consider proximity placement groups for SAP application and database tiers."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def get_best_practices(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "sap_bp_1",
                "title": "Use SAP-certified VM families",
                "description": "Only M-series and E-series VMs are certified for SAP HANA.",
                "category": "compute",
                "severity": "critical",
            },
            {
                "id": "sap_bp_2",
                "title": "Enable Accelerated Networking",
                "description": "Required for SAP HANA inter-node communication.",
                "category": "networking",
                "severity": "high",
            },
            {
                "id": "sap_bp_3",
                "title": "Configure ANF for HANA storage",
                "description": "Azure NetApp Files provides optimal performance for HANA.",
                "category": "storage",
                "severity": "medium",
            },
        ]

    def estimate_sizing(self, requirements: dict[str, Any]) -> dict[str, Any]:
        db_size = requirements.get("db_size", "small")
        ha_required = requirements.get("ha_required", False)

        sku_map = {
            "small": ("Standard_M32ts", 3200),
            "medium": ("Standard_M64s", 7500),
            "large": ("Standard_M128s", 15000),
            "very_large": ("Standard_M128s", 15000),
        }

        compute_sku, monthly_cost = sku_map.get(db_size, ("Standard_M32ts", 3200))
        multiplier = 2 if ha_required else 1

        return {
            "compute_sku": compute_sku,
            "compute_count": multiplier,
            "storage_type": "Premium_LRS",
            "estimated_monthly_cost_usd": monthly_cost * multiplier,
        }


class AvdExtension(WorkloadExtension):
    """Azure Virtual Desktop workload extension."""

    @property
    def workload_type(self) -> str:
        return "avd"

    @property
    def display_name(self) -> str:
        return "Azure Virtual Desktop"

    @property
    def description(self) -> str:
        return "Desktop and app virtualization with session hosts, profiles and FSLogix."

    def get_questions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "avd_user_count",
                "category": "workload",
                "text": "How many concurrent users will use AVD?",
                "type": "single_choice",
                "options": [
                    {"value": "small", "label": "Small (< 50 users)"},
                    {"value": "medium", "label": "Medium (50-200 users)"},
                    {"value": "large", "label": "Large (200-1000 users)"},
                    {"value": "very_large", "label": "Very large (> 1000 users)"},
                ],
                "required": True,
                "order": 1,
            },
            {
                "id": "avd_workload_type",
                "category": "workload",
                "text": "What type of desktop workload?",
                "type": "single_choice",
                "options": [
                    {"value": "light", "label": "Light (Office, web browsing)"},
                    {"value": "medium", "label": "Medium (Business apps, light dev)"},
                    {"value": "heavy", "label": "Heavy (CAD, development, video editing)"},
                    {"value": "gpu", "label": "GPU (3D rendering, ML notebooks)"},
                ],
                "required": True,
                "order": 2,
            },
            {
                "id": "avd_profile_solution",
                "category": "workload",
                "text": "Which profile management solution?",
                "type": "single_choice",
                "options": [
                    {"value": "fslogix", "label": "FSLogix"},
                    {"value": "local", "label": "Local profiles"},
                ],
                "required": True,
                "order": 3,
            },
        ]

    def get_sku_database(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "d2s_v5",
                "name": "Standard_D2s_v5",
                "family": "D",
                "vcpus": 2,
                "ram_gb": 8,
                "price_tier": "low",
                "use_case": "Light desktop users",
            },
            {
                "id": "d4s_v5",
                "name": "Standard_D4s_v5",
                "family": "D",
                "vcpus": 4,
                "ram_gb": 16,
                "price_tier": "medium",
                "use_case": "Medium desktop users",
            },
            {
                "id": "d8s_v5",
                "name": "Standard_D8s_v5",
                "family": "D",
                "vcpus": 8,
                "ram_gb": 32,
                "price_tier": "medium",
                "use_case": "Power desktop users",
            },
        ]

    def validate_architecture(self, architecture: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        network = architecture.get("network_topology", {})
        if not network.get("vnet"):
            errors.append("AVD requires a VNet for session host deployment.")

        services = architecture.get("services", [])
        service_names = {s.get("name", "") if isinstance(s, dict) else s for s in services}

        if "Azure Active Directory" not in service_names and "Entra ID" not in service_names:
            warnings.append("AVD requires Azure AD / Entra ID for user authentication.")

        if "Azure Storage" not in service_names:
            suggestions.append("Add Azure Storage for FSLogix profile containers.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def get_best_practices(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "avd_bp_1",
                "title": "Use FSLogix for profile management",
                "description": "FSLogix provides optimal user experience for roaming profiles.",
                "category": "profiles",
                "severity": "high",
            },
            {
                "id": "avd_bp_2",
                "title": "Enable autoscale for session hosts",
                "description": "Scale session hosts based on user demand to optimize costs.",
                "category": "operations",
                "severity": "medium",
            },
            {
                "id": "avd_bp_3",
                "title": "Configure RDP Shortpath",
                "description": "Use UDP-based transport for lower latency connections.",
                "category": "networking",
                "severity": "medium",
            },
        ]

    def estimate_sizing(self, requirements: dict[str, Any]) -> dict[str, Any]:
        user_count_str = requirements.get("user_count", "small")
        workload_type = requirements.get("workload_type", "light")

        user_map = {"small": 25, "medium": 100, "large": 500, "very_large": 1000}
        users = user_map.get(user_count_str, 25)

        users_per_host = {"light": 8, "medium": 4, "heavy": 2, "gpu": 1}
        per_host = users_per_host.get(workload_type, 4)

        sku_map = {
            "light": ("Standard_D2s_v5", 85),
            "medium": ("Standard_D4s_v5", 170),
            "heavy": ("Standard_D8s_v5", 340),
            "gpu": ("Standard_NV6ads_A10_v5", 950),
        }
        compute_sku, cost_per_host = sku_map.get(workload_type, ("Standard_D4s_v5", 170))

        host_count = max(1, -(-users // per_host))  # ceiling division

        return {
            "compute_sku": compute_sku,
            "compute_count": host_count,
            "storage_type": "Premium_LRS",
            "estimated_monthly_cost_usd": cost_per_host * host_count,
        }


class IoTExtension(WorkloadExtension):
    """IoT / Edge workload extension."""

    @property
    def workload_type(self) -> str:
        return "iot"

    @property
    def display_name(self) -> str:
        return "IoT / Edge"

    @property
    def description(self) -> str:
        return "IoT Hub, Edge devices, time-series ingestion and device management."

    def get_questions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "iot_device_count",
                "category": "workload",
                "text": "How many IoT devices will connect?",
                "type": "single_choice",
                "options": [
                    {"value": "small", "label": "Small (< 100 devices)"},
                    {"value": "medium", "label": "Medium (100-10,000 devices)"},
                    {"value": "large", "label": "Large (10,000-100,000 devices)"},
                    {"value": "very_large", "label": "Very large (> 100,000 devices)"},
                ],
                "required": True,
                "order": 1,
            },
            {
                "id": "iot_edge_required",
                "category": "workload",
                "text": "Do you need IoT Edge for local processing?",
                "type": "single_choice",
                "options": [
                    {"value": "yes", "label": "Yes"},
                    {"value": "no", "label": "No"},
                ],
                "required": True,
                "order": 2,
            },
            {
                "id": "iot_telemetry_frequency",
                "category": "workload",
                "text": "What is the expected telemetry message frequency?",
                "type": "single_choice",
                "options": [
                    {"value": "low", "label": "Low (< 1 msg/min per device)"},
                    {"value": "medium", "label": "Medium (1-10 msg/min per device)"},
                    {"value": "high", "label": "High (> 10 msg/min per device)"},
                ],
                "required": True,
                "order": 3,
            },
        ]

    def get_sku_database(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "iot_hub_s1",
                "name": "IoT Hub S1",
                "type": "iot_hub",
                "tier": "standard",
                "messages_per_day": 400000,
                "price_tier": "low",
                "use_case": "Small to medium device fleets",
            },
            {
                "id": "iot_hub_s2",
                "name": "IoT Hub S2",
                "type": "iot_hub",
                "tier": "standard",
                "messages_per_day": 6000000,
                "price_tier": "medium",
                "use_case": "Large device fleets",
            },
            {
                "id": "iot_hub_s3",
                "name": "IoT Hub S3",
                "type": "iot_hub",
                "tier": "standard",
                "messages_per_day": 300000000,
                "price_tier": "high",
                "use_case": "Very large device fleets",
            },
        ]

    def validate_architecture(self, architecture: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        services = architecture.get("services", [])
        service_names = {s.get("name", "") if isinstance(s, dict) else s for s in services}

        if "IoT Hub" not in service_names:
            errors.append("IoT workloads require Azure IoT Hub.")

        if "Azure Storage" not in service_names:
            warnings.append("Consider Azure Storage for telemetry archival.")

        if "Stream Analytics" not in service_names and "Event Hubs" not in service_names:
            suggestions.append(
                "Add Stream Analytics or Event Hubs for real-time telemetry processing."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def get_best_practices(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "iot_bp_1",
                "title": "Use DPS for device provisioning",
                "description": "Device Provisioning Service automates zero-touch device onboarding.",
                "category": "devices",
                "severity": "high",
            },
            {
                "id": "iot_bp_2",
                "title": "Implement device-to-cloud security",
                "description": "Use X.509 certificates or TPM attestation for device auth.",
                "category": "security",
                "severity": "critical",
            },
            {
                "id": "iot_bp_3",
                "title": "Plan for message routing",
                "description": "Route telemetry to appropriate storage and processing services.",
                "category": "architecture",
                "severity": "medium",
            },
        ]

    def estimate_sizing(self, requirements: dict[str, Any]) -> dict[str, Any]:
        device_count_str = requirements.get("device_count", "small")
        frequency = requirements.get("telemetry_frequency", "low")

        tier_map = {
            "small": ("IoT Hub S1", 25),
            "medium": ("IoT Hub S1", 25),
            "large": ("IoT Hub S2", 250),
            "very_large": ("IoT Hub S3", 2500),
        }
        hub_sku, hub_cost = tier_map.get(device_count_str, ("IoT Hub S1", 25))

        freq_multiplier = {"low": 1, "medium": 2, "high": 5}
        units = freq_multiplier.get(frequency, 1)

        return {
            "hub_sku": hub_sku,
            "hub_units": units,
            "storage_type": "Standard_LRS",
            "estimated_monthly_cost_usd": hub_cost * units,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class WorkloadExtensionRegistry:
    """Singleton registry that manages workload extensions.

    Extensions are looked up by ``workload_type`` string and provide
    questions, SKU databases, validators and best-practice rules.
    """

    def __init__(self) -> None:
        self._extensions: dict[str, WorkloadExtension] = {}

    def register(self, extension: WorkloadExtension) -> None:
        """Register a new workload extension.

        Args:
            extension: An instance of a ``WorkloadExtension`` subclass.

        Raises:
            ValueError: If an extension with the same workload type is
                already registered.
        """
        wtype = extension.workload_type
        if wtype in self._extensions:
            raise ValueError(f"Extension already registered for workload type: {wtype}")
        self._extensions[wtype] = extension
        logger.info("Registered workload extension: %s", wtype)

    def get_extension(self, workload_type: str) -> WorkloadExtension | None:
        """Return the extension for *workload_type*, or ``None``.

        Args:
            workload_type: Machine-readable identifier.

        Returns:
            The matching ``WorkloadExtension`` or ``None``.
        """
        return self._extensions.get(workload_type)

    def list_extensions(self) -> list[dict[str, str]]:
        """Return metadata for every registered extension.

        Returns:
            List of dicts with ``workload_type``, ``display_name``,
            ``description``.
        """
        return [
            {
                "workload_type": ext.workload_type,
                "display_name": ext.display_name,
                "description": ext.description,
            }
            for ext in self._extensions.values()
        ]

    def get_questions_for_workload(self, workload_type: str) -> list[dict[str, Any]]:
        """Return questionnaire questions for *workload_type*.

        Args:
            workload_type: Machine-readable identifier.

        Returns:
            List of question dicts, or empty list if extension not found.
        """
        ext = self.get_extension(workload_type)
        if ext is None:
            return []
        return ext.get_questions()

    def validate_for_workload(
        self, workload_type: str, architecture: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate an architecture against the given workload type.

        Args:
            workload_type: Machine-readable identifier.
            architecture: Architecture dict to validate.

        Returns:
            Validation result dict with ``valid``, ``errors``,
            ``warnings``, ``suggestions``.
        """
        ext = self.get_extension(workload_type)
        if ext is None:
            return {
                "valid": False,
                "errors": [f"Unknown workload type: {workload_type}"],
                "warnings": [],
                "suggestions": [],
            }
        return ext.validate_architecture(architecture)


# Module-level singleton with built-in extensions pre-registered.
workload_registry = WorkloadExtensionRegistry()
workload_registry.register(AiMlExtension())
workload_registry.register(SapExtension())
workload_registry.register(AvdExtension())
workload_registry.register(IoTExtension())
