"""IoT landing zone accelerator service.

Provides IoT-specific questionnaire questions, architecture generation,
SKU recommendations, best practices, sizing estimation, validation,
and reference architectures for Azure IoT deployments.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── IoT Questionnaire Questions ──────────────────────────────────────────────

IOT_QUESTIONS: list[dict] = [
    {
        "id": "device_count",
        "text": "How many devices will connect to the platform?",
        "type": "single_choice",
        "options": ["100", "1K", "10K", "100K", "1M+"],
        "default": "1K",
        "category": "scale",
        "help_text": (
            "Device count determines IoT Hub tier and partition"
            " configuration for ingestion throughput."
        ),
    },
    {
        "id": "device_type",
        "text": "What type of devices will you connect?",
        "type": "single_choice",
        "options": [
            "sensors",
            "gateways",
            "industrial",
            "consumer",
            "vehicles",
        ],
        "default": "sensors",
        "category": "device",
        "help_text": (
            "Device type influences protocol selection, edge"
            " requirements, and security posture."
        ),
    },
    {
        "id": "message_frequency",
        "text": "How often do devices send messages?",
        "type": "single_choice",
        "options": ["seconds", "minutes", "hours"],
        "default": "minutes",
        "category": "scale",
        "help_text": (
            "Message frequency drives IoT Hub unit count and"
            " downstream processing capacity."
        ),
    },
    {
        "id": "protocol",
        "text": "Which communication protocol will devices use?",
        "type": "single_choice",
        "options": ["MQTT", "AMQP", "HTTPS", "Modbus", "OPC-UA"],
        "default": "MQTT",
        "category": "connectivity",
        "help_text": (
            "MQTT is recommended for constrained devices; OPC-UA"
            " and Modbus require an IoT Edge gateway."
        ),
    },
    {
        "id": "edge_computing",
        "text": "Do you need edge computing capabilities?",
        "type": "single_choice",
        "options": ["Yes", "No"],
        "default": "No",
        "category": "edge",
        "help_text": (
            "Edge computing enables local processing, filtering,"
            " and offline operation via Azure IoT Edge."
        ),
    },
    {
        "id": "digital_twins",
        "text": "Do you need digital twin modeling?",
        "type": "single_choice",
        "options": ["Yes", "No"],
        "default": "No",
        "category": "analytics",
        "help_text": (
            "Azure Digital Twins provides a spatial intelligence"
            " graph for modeling physical environments."
        ),
    },
    {
        "id": "time_series_analysis",
        "text": "Do you need time series analysis?",
        "type": "single_choice",
        "options": ["Yes", "No"],
        "default": "Yes",
        "category": "analytics",
        "help_text": (
            "Time series analysis enables trend detection,"
            " anomaly detection, and historical queries."
        ),
    },
    {
        "id": "provisioning_method",
        "text": "How will devices be provisioned?",
        "type": "single_choice",
        "options": ["manual", "DPS", "zero-touch"],
        "default": "DPS",
        "category": "provisioning",
        "help_text": (
            "Device Provisioning Service (DPS) automates device"
            " registration and supports zero-touch enrollment."
        ),
    },
    {
        "id": "data_retention",
        "text": "How long should telemetry data be retained?",
        "type": "single_choice",
        "options": ["days", "months", "years"],
        "default": "months",
        "category": "storage",
        "help_text": (
            "Retention period determines storage tier strategy:"
            " hot for days, warm for months, cold for years."
        ),
    },
    {
        "id": "real_time_analytics",
        "text": "Do you need real-time stream analytics?",
        "type": "single_choice",
        "options": ["Yes", "No"],
        "default": "No",
        "category": "analytics",
        "help_text": (
            "Azure Stream Analytics provides real-time windowed"
            " aggregations, anomaly detection, and alerting."
        ),
    },
    {
        "id": "security_level",
        "text": "What level of device security is required?",
        "type": "single_choice",
        "options": ["standard", "enhanced", "hardware-root-of-trust"],
        "default": "standard",
        "category": "security",
        "help_text": (
            "Enhanced security uses X.509 certificates; hardware"
            " root-of-trust leverages Azure Sphere or HSM."
        ),
    },
    {
        "id": "location_tracking",
        "text": "Do you need geospatial / location tracking?",
        "type": "single_choice",
        "options": ["Yes", "No"],
        "default": "No",
        "category": "analytics",
        "help_text": (
            "Azure Maps provides geofencing, routing, and"
            " spatial analytics for location-aware IoT."
        ),
    },
]

# ── IoT Hub SKU Tiers ────────────────────────────────────────────────────────

IOT_HUB_SKUS: list[dict] = [
    {
        "tier": "S1",
        "name": "Standard S1",
        "messages_per_day_per_unit": 400_000,
        "max_units": 200,
        "max_devices": 500_000,
        "message_size_kb": 4,
        "device_to_cloud_partitions": 4,
        "description": (
            "Standard tier for production workloads up to 500K"
            " devices with 400K messages/day/unit."
        ),
    },
    {
        "tier": "S2",
        "name": "Standard S2",
        "messages_per_day_per_unit": 6_000_000,
        "max_units": 200,
        "max_devices": 500_000,
        "message_size_kb": 4,
        "device_to_cloud_partitions": 4,
        "description": (
            "High-throughput tier with 6M messages/day/unit for"
            " large-scale telemetry ingestion."
        ),
    },
    {
        "tier": "S3",
        "name": "Standard S3",
        "messages_per_day_per_unit": 300_000_000,
        "max_units": 10,
        "max_devices": 500_000,
        "message_size_kb": 4,
        "device_to_cloud_partitions": 4,
        "description": (
            "Ultra-high throughput with 300M messages/day/unit"
            " for massive IoT deployments."
        ),
    },
]

# ── IoT Architecture Components ──────────────────────────────────────────────

IOT_COMPONENTS: list[dict] = [
    {
        "id": "iot_hub",
        "name": "Azure IoT Hub",
        "category": "ingestion",
        "description": (
            "Cloud-hosted managed service for bi-directional"
            " communication between IoT devices and Azure."
        ),
        "required": True,
    },
    {
        "id": "iot_edge",
        "name": "Azure IoT Edge",
        "category": "edge",
        "description": (
            "Extends cloud intelligence to edge devices for"
            " local processing, filtering, and AI inference."
        ),
        "required": False,
    },
    {
        "id": "dps",
        "name": "Device Provisioning Service",
        "category": "provisioning",
        "description": (
            "Zero-touch device provisioning with automatic"
            " registration and multi-hub load balancing."
        ),
        "required": False,
    },
    {
        "id": "event_hubs",
        "name": "Azure Event Hubs",
        "category": "ingestion",
        "description": (
            "High-throughput event streaming platform for"
            " secondary ingestion and fan-out patterns."
        ),
        "required": False,
    },
    {
        "id": "stream_analytics",
        "name": "Azure Stream Analytics",
        "category": "processing",
        "description": (
            "Real-time stream processing engine for windowed"
            " aggregations, anomaly detection, and alerting."
        ),
        "required": False,
    },
    {
        "id": "adx",
        "name": "Azure Data Explorer",
        "category": "analytics",
        "description": (
            "Fast, fully managed data analytics service for"
            " real-time analysis on large volumes of telemetry."
        ),
        "required": False,
    },
    {
        "id": "digital_twins",
        "name": "Azure Digital Twins",
        "category": "modeling",
        "description": (
            "Live execution environment for modeling physical"
            " environments with spatial intelligence graphs."
        ),
        "required": False,
    },
    {
        "id": "storage_hot",
        "name": "Azure Blob Storage (Hot)",
        "category": "storage",
        "description": (
            "Hot-tier storage for frequently accessed telemetry"
            " data and recent device state."
        ),
        "required": True,
    },
    {
        "id": "storage_cold",
        "name": "Azure Blob Storage (Cold/Archive)",
        "category": "storage",
        "description": (
            "Cold or archive tier storage for long-term"
            " telemetry retention and compliance."
        ),
        "required": False,
    },
    {
        "id": "azure_maps",
        "name": "Azure Maps",
        "category": "analytics",
        "description": (
            "Geospatial APIs for mapping, routing, geofencing,"
            " and spatial analytics."
        ),
        "required": False,
    },
    {
        "id": "azure_sphere",
        "name": "Azure Sphere",
        "category": "security",
        "description": (
            "Secured, high-level application platform with"
            " built-in communication and hardware root-of-trust."
        ),
        "required": False,
    },
]

# ── Best Practices ───────────────────────────────────────────────────────────

IOT_BEST_PRACTICES: list[dict] = [
    {
        "id": "bp_use_dps",
        "category": "provisioning",
        "title": "Use Device Provisioning Service for at-scale enrollment",
        "description": (
            "DPS automates device registration and supports symmetric"
            " key, X.509, and TPM attestation methods."
        ),
        "priority": "high",
    },
    {
        "id": "bp_edge_filtering",
        "category": "edge",
        "title": "Filter and aggregate data at the edge",
        "description": (
            "Reduce cloud ingestion costs and latency by performing"
            " initial data filtering on IoT Edge devices."
        ),
        "priority": "high",
    },
    {
        "id": "bp_message_routing",
        "category": "ingestion",
        "title": "Configure IoT Hub message routing for fan-out",
        "description": (
            "Route messages to Event Hubs, Service Bus, Blob Storage,"
            " or custom endpoints based on message properties."
        ),
        "priority": "medium",
    },
    {
        "id": "bp_tiered_storage",
        "category": "storage",
        "title": "Implement hot/warm/cold storage tiering",
        "description": (
            "Use hot storage for recent data, warm for operational"
            " queries, and cold/archive for long-term retention."
        ),
        "priority": "medium",
    },
    {
        "id": "bp_x509_auth",
        "category": "security",
        "title": "Use X.509 certificate authentication for production",
        "description": (
            "X.509 certificates provide stronger security than"
            " symmetric keys and support certificate-based DPS."
        ),
        "priority": "high",
    },
    {
        "id": "bp_monitor_hub",
        "category": "operations",
        "title": "Monitor IoT Hub metrics and set up alerts",
        "description": (
            "Track connected devices, throttling errors, and message"
            " latency with Azure Monitor and diagnostic logs."
        ),
        "priority": "high",
    },
    {
        "id": "bp_stream_analytics",
        "category": "processing",
        "title": "Use Stream Analytics for real-time anomaly detection",
        "description": (
            "Configure tumbling/hopping windows for aggregation and"
            " built-in ML functions for anomaly detection."
        ),
        "priority": "medium",
    },
    {
        "id": "bp_network_isolation",
        "category": "security",
        "title": "Enable private endpoints for IoT Hub",
        "description": (
            "Use Azure Private Link to isolate IoT Hub traffic"
            " within the virtual network and disable public access."
        ),
        "priority": "high",
    },
]

# ── Reference Architectures ──────────────────────────────────────────────────

IOT_REFERENCE_ARCHITECTURES: list[dict] = [
    {
        "id": "industrial_iot",
        "name": "Industrial IoT (IIoT)",
        "description": (
            "End-to-end architecture for manufacturing and industrial"
            " automation with OPC-UA protocol translation, IoT Edge"
            " gateways, and Azure Data Explorer for time series."
        ),
        "components": [
            "iot_hub",
            "iot_edge",
            "dps",
            "event_hubs",
            "stream_analytics",
            "adx",
            "storage_hot",
            "storage_cold",
        ],
        "device_types": ["industrial", "gateways"],
        "protocols": ["OPC-UA", "Modbus", "MQTT"],
        "scale": "10K-100K devices",
        "use_cases": [
            "Predictive maintenance",
            "Quality control monitoring",
            "Overall equipment effectiveness (OEE)",
            "Supply chain visibility",
        ],
    },
    {
        "id": "smart_building",
        "name": "Smart Building",
        "description": (
            "Architecture for building management systems with HVAC"
            " monitoring, occupancy tracking, energy optimization,"
            " and Azure Digital Twins for spatial modeling."
        ),
        "components": [
            "iot_hub",
            "dps",
            "digital_twins",
            "stream_analytics",
            "adx",
            "storage_hot",
            "azure_maps",
        ],
        "device_types": ["sensors", "gateways"],
        "protocols": ["MQTT", "HTTPS"],
        "scale": "1K-10K devices",
        "use_cases": [
            "HVAC optimization",
            "Occupancy tracking",
            "Energy management",
            "Predictive maintenance for building systems",
        ],
    },
    {
        "id": "connected_vehicles",
        "name": "Connected Vehicles",
        "description": (
            "Architecture for fleet management and connected vehicle"
            " telemetry with real-time location tracking, geofencing,"
            " over-the-air (OTA) updates, and driver analytics."
        ),
        "components": [
            "iot_hub",
            "iot_edge",
            "dps",
            "event_hubs",
            "stream_analytics",
            "adx",
            "storage_hot",
            "storage_cold",
            "azure_maps",
            "azure_sphere",
        ],
        "device_types": ["vehicles", "gateways"],
        "protocols": ["MQTT", "AMQP"],
        "scale": "100K-1M+ devices",
        "use_cases": [
            "Fleet management and tracking",
            "Predictive vehicle maintenance",
            "Driver behavior analytics",
            "Over-the-air firmware updates",
        ],
    },
]


class IotAccelerator:
    """IoT landing zone accelerator.

    Provides IoT-specific questionnaire questions, architecture generation,
    SKU recommendations, best practices, sizing estimation, architecture
    validation, and reference architectures for Azure IoT deployments.
    """

    def get_questions(self) -> list[dict]:
        """Return IoT-specific questionnaire questions.

        Returns:
            List of question dicts with id, text, type, options,
            default, category, and help_text.
        """
        return IOT_QUESTIONS

    def get_sku_recommendations(self, answers: dict) -> dict:
        """Recommend IoT Hub SKU tier based on questionnaire answers.

        Args:
            answers: Dict mapping question IDs to selected values,
                e.g. {"device_count": "10K", "message_frequency": "seconds"}.

        Returns:
            Dict with recommended_tier, units, rationale, and
            alternative tiers.
        """
        device_count = answers.get("device_count", "1K")
        message_frequency = answers.get("message_frequency", "minutes")

        # Map device counts to numeric values
        count_map = {
            "100": 100,
            "1K": 1_000,
            "10K": 10_000,
            "100K": 100_000,
            "1M+": 1_000_000,
        }
        num_devices = count_map.get(device_count, 1_000)

        # Estimate daily messages per device
        freq_map = {
            "seconds": 86_400,
            "minutes": 1_440,
            "hours": 24,
        }
        msgs_per_device = freq_map.get(message_frequency, 1_440)
        total_daily_messages = num_devices * msgs_per_device

        # Select tier
        if total_daily_messages <= 400_000:
            tier = "S1"
            units = 1
        elif total_daily_messages <= 400_000 * 200:
            tier = "S1"
            units = max(1, -(-total_daily_messages // 400_000))
        elif total_daily_messages <= 6_000_000 * 200:
            tier = "S2"
            units = max(1, -(-total_daily_messages // 6_000_000))
        else:
            tier = "S3"
            units = max(
                1, -(-total_daily_messages // 300_000_000)
            )

        sku_info = next(
            (s for s in IOT_HUB_SKUS if s["tier"] == tier),
            IOT_HUB_SKUS[0],
        )

        alternatives = [
            s for s in IOT_HUB_SKUS if s["tier"] != tier
        ]

        return {
            "recommended_tier": sku_info,
            "units": units,
            "estimated_daily_messages": total_daily_messages,
            "device_count": num_devices,
            "rationale": (
                f"Based on {num_devices:,} devices sending"
                f" ~{msgs_per_device:,} messages/day each"
                f" ({total_daily_messages:,} total/day),"
                f" {tier} with {units} unit(s) is recommended."
            ),
            "alternatives": alternatives,
        }

    def generate_architecture(self, answers: dict) -> dict:
        """Generate IoT architecture based on questionnaire answers.

        Args:
            answers: Dict mapping question IDs to selected values.

        Returns:
            Dict with components list, connections, tier info,
            and architecture description.
        """
        components: list[dict] = []
        connections: list[dict] = []

        # Always include IoT Hub
        components.append(
            _find_component("iot_hub")
        )

        # Always include hot storage
        components.append(
            _find_component("storage_hot")
        )

        # Edge computing
        edge_needed = answers.get("edge_computing", "No")
        protocol = answers.get("protocol", "MQTT")
        if edge_needed == "Yes" or protocol in ("Modbus", "OPC-UA"):
            components.append(_find_component("iot_edge"))
            connections.append({
                "from": "iot_edge",
                "to": "iot_hub",
                "label": "Device telemetry via edge gateway",
            })

        # Provisioning
        provisioning = answers.get("provisioning_method", "DPS")
        if provisioning in ("DPS", "zero-touch"):
            components.append(_find_component("dps"))
            connections.append({
                "from": "dps",
                "to": "iot_hub",
                "label": "Automated device registration",
            })

        # High-throughput ingestion
        device_count = answers.get("device_count", "1K")
        if device_count in ("100K", "1M+"):
            components.append(_find_component("event_hubs"))
            connections.append({
                "from": "iot_hub",
                "to": "event_hubs",
                "label": "Message routing for fan-out",
            })

        # Real-time analytics
        real_time = answers.get("real_time_analytics", "No")
        if real_time == "Yes":
            components.append(_find_component("stream_analytics"))
            connections.append({
                "from": "iot_hub",
                "to": "stream_analytics",
                "label": "Real-time stream processing",
            })

        # Time series analysis
        time_series = answers.get("time_series_analysis", "Yes")
        if time_series == "Yes":
            components.append(_find_component("adx"))
            connections.append({
                "from": "iot_hub",
                "to": "adx",
                "label": "Telemetry ingestion for time series",
            })

        # Digital twins
        twins = answers.get("digital_twins", "No")
        if twins == "Yes":
            components.append(_find_component("digital_twins"))
            connections.append({
                "from": "iot_hub",
                "to": "digital_twins",
                "label": "Device state synchronization",
            })

        # Cold storage for long retention
        retention = answers.get("data_retention", "months")
        if retention in ("months", "years"):
            components.append(_find_component("storage_cold"))
            connections.append({
                "from": "storage_hot",
                "to": "storage_cold",
                "label": "Lifecycle tiering policy",
            })

        # Location tracking
        location = answers.get("location_tracking", "No")
        if location == "Yes":
            components.append(_find_component("azure_maps"))

        # Security
        security_level = answers.get(
            "security_level", "standard"
        )
        if security_level == "hardware-root-of-trust":
            components.append(_find_component("azure_sphere"))

        # SKU recommendation
        sku_rec = self.get_sku_recommendations(answers)

        return {
            "components": components,
            "connections": connections,
            "iot_hub_tier": sku_rec["recommended_tier"],
            "iot_hub_units": sku_rec["units"],
            "estimated_daily_messages": (
                sku_rec["estimated_daily_messages"]
            ),
            "description": (
                f"IoT architecture with {len(components)} components"
                f" for {answers.get('device_count', '1K')} devices"
                f" using {answers.get('protocol', 'MQTT')} protocol."
            ),
        }

    def get_best_practices(self) -> list[dict]:
        """Return IoT best practices and recommendations.

        Returns:
            List of best-practice dicts with id, category, title,
            description, and priority.
        """
        return IOT_BEST_PRACTICES

    def estimate_sizing(self, requirements: dict) -> dict:
        """Estimate IoT infrastructure sizing.

        Args:
            requirements: Dict with device_count, message_frequency,
                message_size_kb, retention_days, edge_nodes.

        Returns:
            Dict with estimated resource sizing for each component.
        """
        device_count = requirements.get("device_count", 1_000)
        msg_frequency = requirements.get(
            "message_frequency", "minutes"
        )
        message_size_kb = requirements.get("message_size_kb", 1)
        retention_days = requirements.get("retention_days", 30)
        edge_nodes = requirements.get("edge_nodes", 0)

        freq_map = {
            "seconds": 86_400,
            "minutes": 1_440,
            "hours": 24,
        }
        msgs_per_device = freq_map.get(msg_frequency, 1_440)
        total_daily_msgs = device_count * msgs_per_device
        daily_data_gb = (
            total_daily_msgs * message_size_kb / 1_048_576
        )
        total_storage_gb = daily_data_gb * retention_days

        return {
            "iot_hub": {
                "daily_messages": total_daily_msgs,
                "message_size_kb": message_size_kb,
                "estimated_throughput_mb_per_hour": round(
                    daily_data_gb * 1024 / 24, 2
                ),
            },
            "storage": {
                "daily_ingestion_gb": round(daily_data_gb, 2),
                "total_retention_gb": round(total_storage_gb, 2),
                "retention_days": retention_days,
            },
            "edge": {
                "node_count": edge_nodes,
                "recommended_sku": (
                    "Standard_DS3_v2"
                    if edge_nodes > 0
                    else "N/A"
                ),
            },
            "event_hubs": {
                "throughput_units": max(
                    1,
                    -(-total_daily_msgs // 1_000_000),
                ),
                "partitions": min(
                    32,
                    max(4, -(-device_count // 10_000)),
                ),
            },
            "stream_analytics": {
                "streaming_units": max(
                    1,
                    -(-total_daily_msgs // 5_000_000),
                ),
            },
        }

    def validate_architecture(
        self, architecture: dict
    ) -> dict:
        """Validate an IoT architecture for completeness.

        Args:
            architecture: Dict with a 'components' list of dicts
                containing 'id' fields.

        Returns:
            Dict with valid bool, errors list, and warnings list.
        """
        errors: list[str] = []
        warnings: list[str] = []

        component_ids = {
            c.get("id", "") if isinstance(c, dict) else c
            for c in architecture.get("components", [])
        }

        # IoT Hub is required
        if "iot_hub" not in component_ids:
            errors.append(
                "IoT Hub is required for any IoT architecture."
            )

        # Storage is required
        if (
            "storage_hot" not in component_ids
            and "storage_cold" not in component_ids
        ):
            errors.append(
                "At least one storage component is required."
            )

        # Warn if DPS is missing with many components
        if "dps" not in component_ids and len(component_ids) > 3:
            warnings.append(
                "Consider adding Device Provisioning Service"
                " for automated device enrollment."
            )

        # Warn if no analytics
        analytics = {"adx", "stream_analytics", "digital_twins"}
        if not component_ids & analytics:
            warnings.append(
                "No analytics component found. Consider adding"
                " Azure Data Explorer or Stream Analytics."
            )

        # Edge warning for industrial protocols
        if "iot_edge" not in component_ids:
            warnings.append(
                "IoT Edge is recommended for protocol translation"
                " and local processing."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def get_reference_architectures(self) -> list[dict]:
        """Return IoT reference architectures.

        Returns:
            List of reference architecture dicts with id, name,
            description, components, device_types, protocols,
            scale, and use_cases.
        """
        return IOT_REFERENCE_ARCHITECTURES


def _find_component(component_id: str) -> dict:
    """Look up a component by ID from the global list.

    Args:
        component_id: The component identifier string.

    Returns:
        Copy of the matching component dict, or a stub dict
        if not found.
    """
    for comp in IOT_COMPONENTS:
        if comp["id"] == component_id:
            return dict(comp)
    return {"id": component_id, "name": component_id}


iot_accelerator = IotAccelerator()
