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
