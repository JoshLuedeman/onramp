"""Extended tests for deployment orchestrator."""
from app.services.deployment_orchestrator import (
    deployment_orchestrator,
    DeploymentOrchestrator,
    DeploymentStep,
    DeploymentRecord,
    DeploymentStatus,
)

def test_orchestrator_exists():
    assert deployment_orchestrator is not None

def test_create_and_start_deployment():
    orch = DeploymentOrchestrator()
    record = orch.create_deployment(
        project_id="test-proj",
        architecture={"management_groups": [{"name": "root"}]},
        subscription_ids=["sub-123"],
    )
    assert record.id is not None
    started = orch.start_deployment(record.id)
    assert started.status.value in ("succeeded", "deploying", "failed")

def test_get_deployment():
    orch = DeploymentOrchestrator()
    record = orch.create_deployment(
        project_id="test-proj-2",
        architecture={"management_groups": []},
        subscription_ids=["sub-456"],
    )
    fetched = orch.get_deployment(record.id)
    assert fetched is not None
    assert fetched.id == record.id

def test_get_unknown_deployment():
    orch = DeploymentOrchestrator()
    result = orch.get_deployment("nonexistent-id")
    assert result is None

def test_list_deployments():
    result = deployment_orchestrator.list_deployments()
    assert isinstance(result, (list, dict))


def test_deployment_step_to_dict():
    step = DeploymentStep("test-step", "Microsoft.Network/virtualNetworks", "test.bicep")
    d = step.to_dict()
    assert d["name"] == "test-step"
    assert d["resource_type"] == "Microsoft.Network/virtualNetworks"
    assert d["status"] == "pending"
    assert d["started_at"] is None
    assert d["completed_at"] is None
    assert d["error"] is None
    assert d["deployment_id"] is None


def test_deployment_record_to_dict():
    record = DeploymentRecord("proj-1", {"key": "val"}, ["sub-1"])
    d = record.to_dict()
    assert d["project_id"] == "proj-1"
    assert d["status"] == "pending"
    assert d["subscription_ids"] == ["sub-1"]
    assert d["progress"] == 0.0
    assert d["started_at"] is None
    assert d["completed_at"] is None
    assert d["error"] is None
    assert isinstance(d["audit_log"], list)
    assert isinstance(d["steps"], list)


def test_deployment_record_add_audit_entry():
    record = DeploymentRecord("proj-1", {}, ["sub-1"])
    record.add_audit_entry("test_action", "some details", user="tester")
    assert len(record.audit_log) == 1
    entry = record.audit_log[0]
    assert entry["action"] == "test_action"
    assert entry["details"] == "some details"
    assert entry["user"] == "tester"
    assert "timestamp" in entry


def test_deployment_record_calculate_progress_empty():
    record = DeploymentRecord("proj-1", {}, ["sub-1"])
    assert record._calculate_progress() == 0.0


def test_deployment_record_calculate_progress_partial():
    record = DeploymentRecord("proj-1", {}, ["sub-1"])
    step1 = DeploymentStep("s1", "type1", "t1.bicep")
    step2 = DeploymentStep("s2", "type2", "t2.bicep")
    step1.status = DeploymentStatus.SUCCEEDED
    step2.status = DeploymentStatus.PENDING
    record.steps = [step1, step2]
    assert record._calculate_progress() == 50.0


def test_create_deployment_with_workload_subscriptions():
    """Workload subscriptions add extra spoke steps."""
    orch = DeploymentOrchestrator()
    arch = {
        "subscriptions": [
            {"name": "hub", "purpose": "connectivity"},
            {"name": "mgmt", "purpose": "management"},
            {"name": "prod", "purpose": "workload"},
            {"name": "dev", "purpose": "development"},
        ]
    }
    record = orch.create_deployment("proj-spokes", arch, ["sub-1"])
    # 4 base steps + 2 spoke steps (prod and dev)
    assert len(record.steps) == 6


def test_rollback_deployment_dev_mode():
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-rb", arch, ["sub-1"])
    orch.start_deployment(record.id)
    result = orch.rollback_deployment(record.id)
    assert result.status == DeploymentStatus.ROLLED_BACK
    assert result.completed_at is not None
    # All succeeded steps should be rolled back
    for step in result.steps:
        assert step.status == DeploymentStatus.ROLLED_BACK


def test_get_audit_log_nonexistent():
    orch = DeploymentOrchestrator()
    log = orch.get_audit_log("nonexistent-id")
    assert log == []


def test_list_deployments_filter_by_project():
    orch = DeploymentOrchestrator()
    orch.create_deployment("proj-a", {"subscriptions": []}, ["sub-1"])
    orch.create_deployment("proj-b", {"subscriptions": []}, ["sub-2"])
    orch.create_deployment("proj-a", {"subscriptions": []}, ["sub-3"])
    assert len(orch.list_deployments("proj-a")) == 2
    assert len(orch.list_deployments("proj-b")) == 1
    assert len(orch.list_deployments("proj-c")) == 0


def test_start_deployment_production_success():
    """Test production mode deployment with mocked credentials."""
    from unittest.mock import patch, MagicMock
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-prod", arch, ["sub-1"])

    mock_cred = MagicMock()
    mock_cred.is_configured = True

    mock_deploy_result = {"deployment_name": "deploy-001"}
    with patch(
        "app.services.credentials.credential_manager", mock_cred
    ), patch.object(orch, "_deploy_step", return_value=mock_deploy_result):
        result = orch.start_deployment(record.id)

    assert result.status == DeploymentStatus.SUCCEEDED
    assert result.completed_at is not None
    for step in result.steps:
        assert step.status == DeploymentStatus.SUCCEEDED
        assert step.deployment_id == "deploy-001"


def test_start_deployment_production_failure():
    """Test production mode deployment step failure."""
    from unittest.mock import patch, MagicMock
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-fail", arch, ["sub-1"])

    mock_cred = MagicMock()
    mock_cred.is_configured = True

    with patch(
        "app.services.credentials.credential_manager", mock_cred
    ), patch.object(orch, "_deploy_step", side_effect=Exception("ARM deploy failed")):
        result = orch.start_deployment(record.id)

    assert result.status == DeploymentStatus.FAILED
    assert "ARM deploy failed" in result.error
    failed = [s for s in result.steps if s.status == DeploymentStatus.FAILED]
    assert len(failed) >= 1
    assert failed[0].error == "ARM deploy failed"


def test_rollback_production_success():
    """Test production mode rollback with mocked resource client."""
    from unittest.mock import patch, MagicMock
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-rb-prod", arch, ["sub-1"])
    # Simulate started & succeeded
    for step in record.steps:
        step.status = DeploymentStatus.SUCCEEDED
    record.status = DeploymentStatus.SUCCEEDED

    mock_cred = MagicMock()
    mock_cred.is_configured = True
    mock_client = MagicMock()
    mock_poller = MagicMock()
    mock_client.resource_groups.begin_delete.return_value = mock_poller
    mock_cred.get_resource_client.return_value = mock_client

    with patch("app.services.credentials.credential_manager", mock_cred):
        result = orch.rollback_deployment(record.id)

    assert result.status == DeploymentStatus.ROLLED_BACK
    assert mock_client.resource_groups.begin_delete.called


def test_rollback_production_error_handling():
    """Test production mode rollback handles errors gracefully."""
    from unittest.mock import patch, MagicMock
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-rb-err", arch, ["sub-1"])
    for step in record.steps:
        step.status = DeploymentStatus.SUCCEEDED
    record.status = DeploymentStatus.SUCCEEDED

    mock_cred = MagicMock()
    mock_cred.is_configured = True
    mock_client = MagicMock()
    mock_client.resource_groups.begin_delete.side_effect = Exception("Cannot delete")
    mock_cred.get_resource_client.return_value = mock_client

    with patch("app.services.credentials.credential_manager", mock_cred):
        result = orch.rollback_deployment(record.id)

    assert result.status == DeploymentStatus.ROLLED_BACK
    errors = [e for e in result.audit_log if e["action"] == "rollback_error"]
    assert len(errors) > 0


def test_rollback_production_no_resource_client():
    """Test rollback when resource client returns None."""
    from unittest.mock import patch, MagicMock
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-rb-none", arch, ["sub-1"])
    for step in record.steps:
        step.status = DeploymentStatus.SUCCEEDED

    mock_cred = MagicMock()
    mock_cred.is_configured = True
    mock_cred.get_resource_client.return_value = None

    with patch("app.services.credentials.credential_manager", mock_cred):
        result = orch.rollback_deployment(record.id)

    assert result.status == DeploymentStatus.ROLLED_BACK


def test_deploy_step_no_resource_client():
    """_deploy_step raises when resource client is None."""
    from unittest.mock import patch, MagicMock
    import pytest
    orch = DeploymentOrchestrator()
    step = DeploymentStep("test", "Microsoft.Test/res", "test.bicep")
    mock_cred = MagicMock()
    mock_cred.get_resource_client.return_value = None
    with patch("app.services.credentials.credential_manager", mock_cred):
        with pytest.raises(RuntimeError, match="Cannot get Azure client"):
            orch._deploy_step(step, "sub-1", {})


def test_deploy_step_no_template():
    """_deploy_step raises when template not found."""
    from unittest.mock import patch, MagicMock
    import pytest
    orch = DeploymentOrchestrator()
    step = DeploymentStep("test", "Microsoft.Test/res", "nonexistent.bicep")
    mock_client = MagicMock()
    mock_cred = MagicMock()
    mock_cred.get_resource_client.return_value = mock_client
    mock_gen = MagicMock()
    mock_gen.get_template.return_value = None
    with patch("app.services.credentials.credential_manager", mock_cred), \
         patch("app.services.bicep_generator.bicep_generator", mock_gen):
        with pytest.raises(RuntimeError, match="Template.*not found"):
            orch._deploy_step(step, "sub-1", {})


def test_deploy_step_success():
    """_deploy_step succeeds with mocked Azure clients."""
    from unittest.mock import patch, MagicMock
    orch = DeploymentOrchestrator()
    step = DeploymentStep("hub", "Microsoft.Network/vn", "hub.bicep")
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.properties.provisioning_state = "Succeeded"
    mock_client.deployments.begin_create_or_update.return_value.result.return_value = mock_result
    mock_cred = MagicMock()
    mock_cred.get_resource_client.return_value = mock_client
    mock_gen = MagicMock()
    mock_gen.get_template.return_value = "some bicep content"
    with patch("app.services.credentials.credential_manager", mock_cred), \
         patch("app.services.bicep_generator.bicep_generator", mock_gen):
        result = orch._deploy_step(step, "sub-1", {"network_topology": {"primary_region": "westus2"}})
    assert "deployment_name" in result
    assert result["resource_group"] == "onramp-hub-rg"
    assert result["provisioning_state"] == "Succeeded"


def test_deploy_step_arm_failure():
    """_deploy_step raises on ARM deployment failure."""
    from unittest.mock import patch, MagicMock
    import pytest
    orch = DeploymentOrchestrator()
    step = DeploymentStep("hub", "Microsoft.Network/vn", "hub.bicep")
    mock_client = MagicMock()
    mock_client.deployments.begin_create_or_update.side_effect = Exception("ARM error")
    mock_cred = MagicMock()
    mock_cred.get_resource_client.return_value = mock_client
    mock_gen = MagicMock()
    mock_gen.get_template.return_value = "bicep content"
    with patch("app.services.credentials.credential_manager", mock_cred), \
         patch("app.services.bicep_generator.bicep_generator", mock_gen):
        with pytest.raises(RuntimeError, match="ARM deployment failed"):
            orch._deploy_step(step, "sub-1", {})
