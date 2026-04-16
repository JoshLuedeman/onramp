"""Tests for IoT landing zone accelerator services and API routes."""

from starlette.testclient import TestClient

from app.main import app
from app.services.iot_accelerator import (
    IOT_BEST_PRACTICES,
    IOT_COMPONENTS,
    IOT_HUB_SKUS,
    IOT_QUESTIONS,
    IOT_REFERENCE_ARCHITECTURES,
    iot_accelerator,
)
from app.services.iot_bicep import iot_bicep_service

client = TestClient(app)


# ── Service Unit Tests: Questions ────────────────────────────────────────────


def test_get_questions_returns_list():
    questions = iot_accelerator.get_questions()
    assert isinstance(questions, list)
    assert len(questions) >= 10


def test_get_questions_has_required_fields():
    questions = iot_accelerator.get_questions()
    for q in questions:
        assert "id" in q
        assert "text" in q
        assert "type" in q
        assert "options" in q
        assert "category" in q


def test_questions_have_unique_ids():
    questions = iot_accelerator.get_questions()
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids))


def test_questions_have_device_count():
    questions = iot_accelerator.get_questions()
    ids = [q["id"] for q in questions]
    assert "device_count" in ids


def test_questions_include_all_categories():
    questions = iot_accelerator.get_questions()
    categories = {q["category"] for q in questions}
    assert "scale" in categories
    assert "device" in categories
    assert "connectivity" in categories
    assert "edge" in categories
    assert "analytics" in categories


def test_questions_have_defaults():
    questions = iot_accelerator.get_questions()
    for q in questions:
        assert "default" in q
        assert q["default"] in q["options"]


# ── Service Unit Tests: SKU Recommendations ──────────────────────────────────


def test_sku_recommendation_small_scale():
    result = iot_accelerator.get_sku_recommendations(
        {"device_count": "100", "message_frequency": "hours"}
    )
    assert result["recommended_tier"]["tier"] == "S1"
    assert result["units"] >= 1


def test_sku_recommendation_medium_scale():
    result = iot_accelerator.get_sku_recommendations(
        {"device_count": "10K", "message_frequency": "minutes"}
    )
    assert result["recommended_tier"]["tier"] in ("S1", "S2")
    assert result["units"] >= 1


def test_sku_recommendation_large_scale():
    result = iot_accelerator.get_sku_recommendations(
        {"device_count": "1M+", "message_frequency": "seconds"}
    )
    assert result["recommended_tier"]["tier"] == "S3"
    assert result["units"] >= 1


def test_sku_recommendation_has_required_fields():
    result = iot_accelerator.get_sku_recommendations(
        {"device_count": "1K", "message_frequency": "minutes"}
    )
    assert "recommended_tier" in result
    assert "units" in result
    assert "rationale" in result
    assert "alternatives" in result
    assert "estimated_daily_messages" in result


def test_sku_recommendation_alternatives_exclude_selected():
    result = iot_accelerator.get_sku_recommendations(
        {"device_count": "1K", "message_frequency": "minutes"}
    )
    selected_tier = result["recommended_tier"]["tier"]
    for alt in result["alternatives"]:
        assert alt["tier"] != selected_tier


def test_sku_recommendation_defaults():
    result = iot_accelerator.get_sku_recommendations({})
    assert "recommended_tier" in result
    assert result["units"] >= 1


# ── Service Unit Tests: Architecture Generation ──────────────────────────────


def test_generate_architecture_minimal():
    arch = iot_accelerator.generate_architecture(
        {"device_count": "100", "message_frequency": "hours"}
    )
    assert "components" in arch
    assert "connections" in arch
    component_ids = [c["id"] for c in arch["components"]]
    assert "iot_hub" in component_ids
    assert "storage_hot" in component_ids


def test_generate_architecture_with_edge():
    arch = iot_accelerator.generate_architecture(
        {"edge_computing": "Yes"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "iot_edge" in component_ids


def test_generate_architecture_with_opcua():
    arch = iot_accelerator.generate_architecture(
        {"protocol": "OPC-UA"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "iot_edge" in component_ids


def test_generate_architecture_with_dps():
    arch = iot_accelerator.generate_architecture(
        {"provisioning_method": "DPS"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "dps" in component_ids


def test_generate_architecture_with_digital_twins():
    arch = iot_accelerator.generate_architecture(
        {"digital_twins": "Yes"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "digital_twins" in component_ids


def test_generate_architecture_with_time_series():
    arch = iot_accelerator.generate_architecture(
        {"time_series_analysis": "Yes"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "adx" in component_ids


def test_generate_architecture_with_realtime():
    arch = iot_accelerator.generate_architecture(
        {"real_time_analytics": "Yes"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "stream_analytics" in component_ids


def test_generate_architecture_high_scale_includes_event_hubs():
    arch = iot_accelerator.generate_architecture(
        {"device_count": "1M+"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "event_hubs" in component_ids


def test_generate_architecture_cold_storage():
    arch = iot_accelerator.generate_architecture(
        {"data_retention": "years"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "storage_cold" in component_ids


def test_generate_architecture_location_tracking():
    arch = iot_accelerator.generate_architecture(
        {"location_tracking": "Yes"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "azure_maps" in component_ids


def test_generate_architecture_hardware_security():
    arch = iot_accelerator.generate_architecture(
        {"security_level": "hardware-root-of-trust"}
    )
    component_ids = [c["id"] for c in arch["components"]]
    assert "azure_sphere" in component_ids


def test_generate_architecture_has_description():
    arch = iot_accelerator.generate_architecture(
        {"device_count": "10K", "protocol": "MQTT"}
    )
    assert "description" in arch
    assert len(arch["description"]) > 0


# ── Service Unit Tests: Best Practices ───────────────────────────────────────


def test_get_best_practices_returns_list():
    practices = iot_accelerator.get_best_practices()
    assert isinstance(practices, list)
    assert len(practices) >= 5


def test_best_practices_have_required_fields():
    practices = iot_accelerator.get_best_practices()
    for bp in practices:
        assert "id" in bp
        assert "title" in bp
        assert "category" in bp
        assert "priority" in bp


# ── Service Unit Tests: Sizing Estimation ────────────────────────────────────


def test_estimate_sizing_basic():
    result = iot_accelerator.estimate_sizing(
        {"device_count": 1000, "message_frequency": "minutes"}
    )
    assert "iot_hub" in result
    assert "storage" in result
    assert "edge" in result
    assert "event_hubs" in result
    assert "stream_analytics" in result


def test_estimate_sizing_with_edge():
    result = iot_accelerator.estimate_sizing(
        {"device_count": 500, "edge_nodes": 5}
    )
    assert result["edge"]["node_count"] == 5
    assert result["edge"]["recommended_sku"] == "Standard_DS3_v2"


def test_estimate_sizing_no_edge():
    result = iot_accelerator.estimate_sizing(
        {"device_count": 500, "edge_nodes": 0}
    )
    assert result["edge"]["recommended_sku"] == "N/A"


def test_estimate_sizing_storage_retention():
    result = iot_accelerator.estimate_sizing(
        {"device_count": 1000, "retention_days": 365}
    )
    assert result["storage"]["retention_days"] == 365
    assert result["storage"]["total_retention_gb"] > 0


# ── Service Unit Tests: Validation ───────────────────────────────────────────


def test_validate_architecture_valid():
    arch = {
        "components": [
            {"id": "iot_hub"},
            {"id": "storage_hot"},
            {"id": "dps"},
            {"id": "adx"},
        ]
    }
    result = iot_accelerator.validate_architecture(arch)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_architecture_missing_hub():
    arch = {"components": [{"id": "storage_hot"}]}
    result = iot_accelerator.validate_architecture(arch)
    assert result["valid"] is False
    assert any("IoT Hub" in e for e in result["errors"])


def test_validate_architecture_missing_storage():
    arch = {"components": [{"id": "iot_hub"}]}
    result = iot_accelerator.validate_architecture(arch)
    assert result["valid"] is False
    assert any("storage" in e.lower() for e in result["errors"])


def test_validate_architecture_warnings():
    arch = {
        "components": [
            {"id": "iot_hub"},
            {"id": "storage_hot"},
            {"id": "dps"},
            {"id": "event_hubs"},
        ]
    }
    result = iot_accelerator.validate_architecture(arch)
    assert result["valid"] is True
    # Should warn about missing analytics
    assert len(result["warnings"]) >= 1


# ── Service Unit Tests: Reference Architectures ─────────────────────────────


def test_get_reference_architectures_returns_list():
    archs = iot_accelerator.get_reference_architectures()
    assert isinstance(archs, list)
    assert len(archs) >= 3


def test_reference_architectures_have_required_fields():
    archs = iot_accelerator.get_reference_architectures()
    for a in archs:
        assert "id" in a
        assert "name" in a
        assert "description" in a
        assert "components" in a
        assert "use_cases" in a


def test_reference_architectures_include_iiot():
    archs = iot_accelerator.get_reference_architectures()
    ids = [a["id"] for a in archs]
    assert "industrial_iot" in ids


def test_reference_architectures_include_smart_building():
    archs = iot_accelerator.get_reference_architectures()
    ids = [a["id"] for a in archs]
    assert "smart_building" in ids


def test_reference_architectures_include_connected_vehicles():
    archs = iot_accelerator.get_reference_architectures()
    ids = [a["id"] for a in archs]
    assert "connected_vehicles" in ids


# ── Data Integrity Tests ─────────────────────────────────────────────────────


def test_iot_hub_skus_have_required_fields():
    for sku in IOT_HUB_SKUS:
        assert "tier" in sku
        assert "name" in sku
        assert "messages_per_day_per_unit" in sku
        assert "max_units" in sku


def test_iot_components_have_required_fields():
    for comp in IOT_COMPONENTS:
        assert "id" in comp
        assert "name" in comp
        assert "category" in comp


def test_iot_components_have_unique_ids():
    ids = [c["id"] for c in IOT_COMPONENTS]
    assert len(ids) == len(set(ids))


# ── Bicep Generation Tests ──────────────────────────────────────────────────


def test_bicep_iot_hub():
    result = iot_bicep_service.generate_iot_hub({"name": "myHub"})
    assert "Microsoft.Devices/IotHubs" in result
    assert "myHub" in result


def test_bicep_dps():
    result = iot_bicep_service.generate_dps({"name": "myDps"})
    assert "Microsoft.Devices/provisioningServices" in result
    assert "myDps" in result


def test_bicep_event_hub():
    result = iot_bicep_service.generate_event_hub(
        {"name": "myEh", "throughput_units": 2}
    )
    assert "Microsoft.EventHub" in result
    assert "myEh" in result


def test_bicep_stream_analytics():
    result = iot_bicep_service.generate_stream_analytics(
        {"name": "myJob"}
    )
    assert "Microsoft.StreamAnalytics" in result
    assert "myJob" in result


def test_bicep_storage():
    result = iot_bicep_service.generate_storage(
        {"name": "mystore"}
    )
    assert "Microsoft.Storage" in result
    assert "mystore" in result


def test_bicep_storage_with_cold_tier():
    result = iot_bicep_service.generate_storage(
        {"name": "mystore", "enable_cold_tier": True}
    )
    assert "tierToArchive" in result


def test_bicep_adx():
    result = iot_bicep_service.generate_adx({"name": "myadx"})
    assert "Microsoft.Kusto" in result
    assert "myadx" in result


def test_bicep_full_stack():
    result = iot_bicep_service.generate_full_iot_stack(
        {"name_prefix": "test", "include_dps": True}
    )
    assert "IoT Landing Zone" in result
    assert "Microsoft.Devices/IotHubs" in result
    assert "Microsoft.Storage" in result
    assert "Microsoft.Devices/provisioningServices" in result


def test_bicep_full_stack_with_all_options():
    result = iot_bicep_service.generate_full_iot_stack({
        "name_prefix": "full",
        "include_dps": True,
        "include_event_hubs": True,
        "include_stream_analytics": True,
        "include_adx": True,
        "include_cold_storage": True,
    })
    assert "Microsoft.EventHub" in result
    assert "Microsoft.StreamAnalytics" in result
    assert "Microsoft.Kusto" in result
    assert "tierToArchive" in result


def test_bicep_full_stack_minimal():
    result = iot_bicep_service.generate_full_iot_stack(
        {"include_dps": False}
    )
    assert "Microsoft.Devices/IotHubs" in result
    assert "provisioningServices" not in result


# ── Route Tests: GET /api/accelerators/iot/questions ─────────────────────────


def test_route_questions():
    response = client.get("/api/accelerators/iot/questions")
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert "total" in data
    assert data["total"] >= 10


# ── Route Tests: POST /api/accelerators/iot/sku-recommendations ──────────────


def test_route_sku_recommendations():
    response = client.post(
        "/api/accelerators/iot/sku-recommendations",
        json={"answers": {"device_count": "10K", "message_frequency": "minutes"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommended_tier" in data
    assert "units" in data


# ── Route Tests: POST /api/accelerators/iot/architecture ─────────────────────


def test_route_architecture():
    response = client.post(
        "/api/accelerators/iot/architecture",
        json={"answers": {"device_count": "1K", "edge_computing": "Yes"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "components" in data
    assert "connections" in data


# ── Route Tests: GET /api/accelerators/iot/best-practices ────────────────────


def test_route_best_practices():
    response = client.get("/api/accelerators/iot/best-practices")
    assert response.status_code == 200
    data = response.json()
    assert "best_practices" in data
    assert data["total"] >= 5


# ── Route Tests: POST /api/accelerators/iot/sizing ───────────────────────────


def test_route_sizing():
    response = client.post(
        "/api/accelerators/iot/sizing",
        json={"requirements": {"device_count": 5000, "message_frequency": "minutes"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "iot_hub" in data
    assert "storage" in data


# ── Route Tests: POST /api/accelerators/iot/validate ─────────────────────────


def test_route_validate():
    response = client.post(
        "/api/accelerators/iot/validate",
        json={
            "architecture": {
                "components": [{"id": "iot_hub"}, {"id": "storage_hot"}]
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data


# ── Route Tests: GET /api/accelerators/iot/reference-architectures ───────────


def test_route_reference_architectures():
    response = client.get(
        "/api/accelerators/iot/reference-architectures"
    )
    assert response.status_code == 200
    data = response.json()
    assert "architectures" in data
    assert data["total"] >= 3


# ── Route Tests: POST /api/accelerators/iot/bicep ────────────────────────────


def test_route_bicep_iot_hub():
    response = client.post(
        "/api/accelerators/iot/bicep",
        json={"template_type": "iot_hub", "config": {"name": "myHub"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert "bicep_template" in data
    assert "Microsoft.Devices/IotHubs" in data["bicep_template"]


def test_route_bicep_invalid_type():
    response = client.post(
        "/api/accelerators/iot/bicep",
        json={"template_type": "invalid_type", "config": {}},
    )
    assert response.status_code == 400
