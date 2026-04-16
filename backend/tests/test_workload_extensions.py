"""Tests for the workload extension framework."""

from app.services.workload_extensions import (
    AiMlExtension,
    AvdExtension,
    IoTExtension,
    SapExtension,
    WorkloadExtensionRegistry,
    workload_registry,
)


# ---------------------------------------------------------------------------
# WorkloadExtension base class / concrete extensions
# ---------------------------------------------------------------------------


def test_ai_ml_workload_type():
    ext = AiMlExtension()
    assert ext.workload_type == "ai_ml"


def test_ai_ml_display_name():
    ext = AiMlExtension()
    assert ext.display_name == "AI / Machine Learning"


def test_ai_ml_description_non_empty():
    ext = AiMlExtension()
    assert len(ext.description) > 10


def test_ai_ml_get_questions_returns_list():
    ext = AiMlExtension()
    questions = ext.get_questions()
    assert isinstance(questions, list)
    assert len(questions) >= 3


def test_ai_ml_questions_have_required_keys():
    ext = AiMlExtension()
    for q in ext.get_questions():
        assert "id" in q
        assert "text" in q
        assert "type" in q


def test_ai_ml_get_sku_database():
    ext = AiMlExtension()
    skus = ext.get_sku_database()
    assert isinstance(skus, list)
    assert len(skus) >= 2
    assert all("id" in s for s in skus)


def test_ai_ml_validate_architecture_valid():
    ext = AiMlExtension()
    arch = {
        "services": [
            {"name": "Azure Machine Learning"},
            {"name": "Azure Storage"},
        ],
        "network_topology": {"private_endpoints": True},
    }
    result = ext.validate_architecture(arch)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_ai_ml_validate_architecture_missing_storage():
    ext = AiMlExtension()
    arch = {
        "services": [{"name": "Azure Machine Learning"}],
        "network_topology": {},
    }
    result = ext.validate_architecture(arch)
    assert result["valid"] is False
    assert any("Storage" in e or "Data Lake" in e for e in result["errors"])


def test_ai_ml_best_practices():
    ext = AiMlExtension()
    bps = ext.get_best_practices()
    assert isinstance(bps, list)
    assert len(bps) >= 2
    assert all("id" in bp and "title" in bp for bp in bps)


def test_ai_ml_estimate_sizing_gpu():
    ext = AiMlExtension()
    result = ext.estimate_sizing({"gpu_required": True, "data_size": "large"})
    assert "compute_sku" in result
    assert "NC" in result["compute_sku"]


def test_ai_ml_estimate_sizing_no_gpu():
    ext = AiMlExtension()
    result = ext.estimate_sizing({"gpu_required": False})
    assert "D8s" in result["compute_sku"]


def test_sap_workload_type():
    ext = SapExtension()
    assert ext.workload_type == "sap"


def test_sap_questions_have_sap_product():
    ext = SapExtension()
    ids = [q["id"] for q in ext.get_questions()]
    assert "sap_product" in ids


def test_sap_sku_database_has_m_series():
    ext = SapExtension()
    families = {s.get("family") for s in ext.get_sku_database()}
    assert "M" in families


def test_sap_validate_architecture_missing_storage():
    ext = SapExtension()
    result = ext.validate_architecture({"services": [], "network_topology": {}})
    assert result["valid"] is False


def test_sap_estimate_sizing_ha():
    ext = SapExtension()
    result = ext.estimate_sizing({"db_size": "medium", "ha_required": True})
    assert result["compute_count"] == 2


def test_avd_workload_type():
    ext = AvdExtension()
    assert ext.workload_type == "avd"


def test_avd_questions_user_count():
    ext = AvdExtension()
    ids = [q["id"] for q in ext.get_questions()]
    assert "avd_user_count" in ids


def test_avd_validate_no_vnet():
    ext = AvdExtension()
    result = ext.validate_architecture(
        {"services": [], "network_topology": {}}
    )
    assert result["valid"] is False


def test_avd_estimate_sizing_light():
    ext = AvdExtension()
    result = ext.estimate_sizing({"user_count": "small", "workload_type": "light"})
    assert result["compute_sku"] == "Standard_D2s_v5"


def test_iot_workload_type():
    ext = IoTExtension()
    assert ext.workload_type == "iot"


def test_iot_validate_missing_hub():
    ext = IoTExtension()
    result = ext.validate_architecture({"services": [], "network_topology": {}})
    assert result["valid"] is False
    assert any("IoT Hub" in e for e in result["errors"])


def test_iot_estimate_sizing_large():
    ext = IoTExtension()
    result = ext.estimate_sizing({"device_count": "large", "telemetry_frequency": "high"})
    assert result["hub_sku"] == "IoT Hub S2"


# ---------------------------------------------------------------------------
# WorkloadExtensionRegistry
# ---------------------------------------------------------------------------


def test_registry_list_extensions():
    extensions = workload_registry.list_extensions()
    assert isinstance(extensions, list)
    assert len(extensions) >= 4
    types = {e["workload_type"] for e in extensions}
    assert {"ai_ml", "sap", "avd", "iot"} <= types


def test_registry_get_extension_existing():
    ext = workload_registry.get_extension("ai_ml")
    assert ext is not None
    assert ext.workload_type == "ai_ml"


def test_registry_get_extension_missing():
    ext = workload_registry.get_extension("nonexistent")
    assert ext is None


def test_registry_get_questions_for_workload():
    questions = workload_registry.get_questions_for_workload("sap")
    assert isinstance(questions, list)
    assert len(questions) >= 2


def test_registry_get_questions_for_unknown_workload():
    questions = workload_registry.get_questions_for_workload("unknown")
    assert questions == []


def test_registry_validate_for_workload():
    result = workload_registry.validate_for_workload("ai_ml", {
        "services": [{"name": "Azure Machine Learning"}, {"name": "Azure Storage"}],
        "network_topology": {"private_endpoints": True},
    })
    assert result["valid"] is True


def test_registry_validate_for_unknown_workload():
    result = workload_registry.validate_for_workload("unknown", {})
    assert result["valid"] is False
    assert any("Unknown" in e for e in result["errors"])


def test_registry_register_duplicate_raises():
    reg = WorkloadExtensionRegistry()
    reg.register(AiMlExtension())
    try:
        reg.register(AiMlExtension())
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_registry_register_new_extension():
    reg = WorkloadExtensionRegistry()
    ext = AiMlExtension()
    reg.register(ext)
    assert reg.get_extension("ai_ml") is ext
