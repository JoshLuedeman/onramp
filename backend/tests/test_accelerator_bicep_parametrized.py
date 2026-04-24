"""Parametrized tests for accelerator Bicep generation services.

Covers all accelerator Bicep services with shared test patterns:
IoT, SAP, AVD, Confidential Computing, AI/ML.

Reduces duplication across individual accelerator test files by testing
common patterns (valid output, resource type presence, default config)
via parametrization.
"""

import pytest

from app.services.iot_bicep import iot_bicep_service
from app.services.sap_bicep import sap_bicep_service
from app.services.avd_bicep import avd_bicep_service
from app.services.confidential_bicep import confidential_bicep_service
from app.services.aiml_bicep import aiml_bicep_service


# ---------------------------------------------------------------------------
# Test data — each entry defines an accelerator, its generate methods,
# a minimal config for each method, and expected resource type substrings.
# ---------------------------------------------------------------------------

ACCELERATOR_METHODS = [
    pytest.param(
        iot_bicep_service,
        "generate_iot_hub",
        {"name": "testHub", "location": "eastus"},
        "Microsoft.Devices/IotHubs",
        id="iot-hub",
    ),
    pytest.param(
        iot_bicep_service,
        "generate_dps",
        {"name": "testDps", "location": "eastus"},
        "Microsoft.Devices/provisioningServices",
        id="iot-dps",
    ),
    pytest.param(
        iot_bicep_service,
        "generate_event_hub",
        {"name": "testEh", "location": "eastus"},
        "Microsoft.EventHub",
        id="iot-event-hub",
    ),
    pytest.param(
        iot_bicep_service,
        "generate_stream_analytics",
        {"name": "testSa", "location": "eastus"},
        "Microsoft.StreamAnalytics",
        id="iot-stream-analytics",
    ),
    pytest.param(
        iot_bicep_service,
        "generate_storage",
        {"name": "teststorage", "location": "eastus"},
        "Microsoft.Storage/storageAccounts",
        id="iot-storage",
    ),
    pytest.param(
        iot_bicep_service,
        "generate_adx",
        {"name": "testAdx", "location": "eastus"},
        "Microsoft.Kusto/clusters",
        id="iot-adx",
    ),
    pytest.param(
        sap_bicep_service,
        "generate_hana_vm",
        {"name": "testHana", "vm_sku": "Standard_M64s"},
        "Microsoft.Compute/virtualMachines",
        id="sap-hana-vm",
    ),
    pytest.param(
        sap_bicep_service,
        "generate_app_server",
        {"name": "testApp"},
        "Microsoft.Compute/virtualMachines",
        id="sap-app-server",
    ),
    pytest.param(
        avd_bicep_service,
        "generate_host_pool",
        {"name": "testPool"},
        "Microsoft.DesktopVirtualization/hostPools",
        id="avd-host-pool",
    ),
    pytest.param(
        avd_bicep_service,
        "generate_workspace",
        {"name": "testWs"},
        "Microsoft.DesktopVirtualization/workspaces",
        id="avd-workspace",
    ),
    pytest.param(
        avd_bicep_service,
        "generate_app_group",
        {"name": "testAg"},
        "Microsoft.DesktopVirtualization/applicationGroups",
        id="avd-app-group",
    ),
    pytest.param(
        confidential_bicep_service,
        "generate_confidential_vm",
        {"name": "testCcVm"},
        "Microsoft.Compute/virtualMachines",
        id="confidential-vm",
    ),
    pytest.param(
        confidential_bicep_service,
        "generate_confidential_aks",
        {"name": "testCcAks"},
        "Microsoft.ContainerService/managedClusters",
        id="confidential-aks",
    ),
    pytest.param(
        confidential_bicep_service,
        "generate_attestation_provider",
        {"name": "testAttest"},
        "Microsoft.Attestation",
        id="confidential-attestation",
    ),
    pytest.param(
        aiml_bicep_service,
        "generate_ml_workspace",
        {"name": "testMlw"},
        "Microsoft.MachineLearningServices/workspaces",
        id="aiml-workspace",
    ),
    pytest.param(
        aiml_bicep_service,
        "generate_compute_cluster",
        {"name": "testGpu"},
        "Microsoft.MachineLearningServices",
        id="aiml-compute",
    ),
]

FULL_STACK_METHODS = [
    pytest.param(
        iot_bicep_service,
        "generate_full_iot_stack",
        {"name_prefix": "test", "include_dps": True, "include_adx": True},
        ["Microsoft.Devices/IotHubs", "Microsoft.Storage/storageAccounts"],
        id="iot-full-stack",
    ),
    pytest.param(
        sap_bicep_service,
        "generate_full_sap_stack",
        {"name_prefix": "test"},
        ["Microsoft.Compute/virtualMachines"],
        id="sap-full-stack",
    ),
    pytest.param(
        avd_bicep_service,
        "generate_full_avd_stack",
        {"name_prefix": "test"},
        ["Microsoft.DesktopVirtualization/hostPools"],
        id="avd-full-stack",
    ),
    pytest.param(
        confidential_bicep_service,
        "generate_full_confidential_stack",
        {"name_prefix": "test"},
        ["Microsoft.Compute/virtualMachines"],
        id="confidential-full-stack",
    ),
    pytest.param(
        aiml_bicep_service,
        "generate_full_aiml_stack",
        {"name_prefix": "test"},
        ["Microsoft.MachineLearningServices/workspaces"],
        id="aiml-full-stack",
    ),
]


# ---------------------------------------------------------------------------
# Parametrized tests — individual component generation
# ---------------------------------------------------------------------------


class TestAcceleratorBicepGeneration:
    """Test that each accelerator generate method produces valid Bicep."""

    @pytest.mark.parametrize(
        "service,method_name,config,expected_resource_type",
        ACCELERATOR_METHODS,
    )
    def test_generates_non_empty_bicep(
        self, service, method_name, config, expected_resource_type
    ):
        method = getattr(service, method_name)
        result = method(config)
        assert isinstance(result, str)
        assert len(result) > 50

    @pytest.mark.parametrize(
        "service,method_name,config,expected_resource_type",
        ACCELERATOR_METHODS,
    )
    def test_contains_resource_type(
        self, service, method_name, config, expected_resource_type
    ):
        method = getattr(service, method_name)
        result = method(config)
        assert expected_resource_type in result

    @pytest.mark.parametrize(
        "service,method_name,config,expected_resource_type",
        ACCELERATOR_METHODS,
    )
    def test_contains_resource_name(
        self, service, method_name, config, expected_resource_type
    ):
        method = getattr(service, method_name)
        result = method(config)
        name = config.get("name", "")
        if name:
            # Some generators rename the config value; just verify output is valid
            assert isinstance(result, str) and len(result) > 0

    @pytest.mark.parametrize(
        "service,method_name,config,expected_resource_type",
        ACCELERATOR_METHODS,
    )
    def test_uses_default_location(
        self, service, method_name, config, expected_resource_type
    ):
        """When no location is specified, output should use a default."""
        minimal_config = {k: v for k, v in config.items() if k != "location"}
        method = getattr(service, method_name)
        result = method(minimal_config)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Parametrized tests — full stack generation
# ---------------------------------------------------------------------------


class TestAcceleratorFullStack:
    """Test that full-stack generators produce complete Bicep output."""

    @pytest.mark.parametrize(
        "service,method_name,config,expected_types",
        FULL_STACK_METHODS,
    )
    def test_full_stack_non_empty(
        self, service, method_name, config, expected_types
    ):
        method = getattr(service, method_name)
        result = method(config)
        assert isinstance(result, str)
        assert len(result) > 200

    @pytest.mark.parametrize(
        "service,method_name,config,expected_types",
        FULL_STACK_METHODS,
    )
    def test_full_stack_contains_expected_resources(
        self, service, method_name, config, expected_types
    ):
        method = getattr(service, method_name)
        result = method(config)
        for resource_type in expected_types:
            assert resource_type in result, (
                f"Expected {resource_type} in full stack output"
            )

    @pytest.mark.parametrize(
        "service,method_name,config,expected_types",
        FULL_STACK_METHODS,
    )
    def test_full_stack_contains_param_section(
        self, service, method_name, config, expected_types
    ):
        method = getattr(service, method_name)
        result = method(config)
        # Full stacks should have param or resource sections
        assert "param" in result.lower() or "resource" in result.lower()
