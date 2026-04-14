"""Tests for deployment orchestrator."""

from app.services.deployment_orchestrator import (
    DeploymentOrchestrator,
    DeploymentStatus,
)


def test_create_deployment():
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": [{"name": "hub", "purpose": "connectivity"}, {"name": "prod", "purpose": "workload"}]}
    record = orch.create_deployment("proj-1", arch, ["sub-1"])
    assert record.status == DeploymentStatus.PENDING
    assert len(record.steps) >= 4
    assert len(record.audit_log) == 1


def test_start_deployment():
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-1", arch, ["sub-1"])
    result = orch.start_deployment(record.id)
    assert result.status == DeploymentStatus.SUCCEEDED
    assert all(s.status == DeploymentStatus.SUCCEEDED for s in result.steps)


def test_rollback_deployment():
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-1", arch, ["sub-1"])
    orch.start_deployment(record.id)
    result = orch.rollback_deployment(record.id)
    assert result.status == DeploymentStatus.ROLLED_BACK


def test_audit_log():
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-1", arch, ["sub-1"])
    orch.start_deployment(record.id)
    log = orch.get_audit_log(record.id)
    actions = [e["action"] for e in log]
    assert "created" in actions
    assert "started" in actions
    assert "completed" in actions


def test_list_deployments():
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    orch.create_deployment("proj-1", arch, ["sub-1"])
    orch.create_deployment("proj-1", arch, ["sub-2"])
    orch.create_deployment("proj-2", arch, ["sub-3"])
    assert len(orch.list_deployments()) == 3
    assert len(orch.list_deployments("proj-1")) == 2


def test_deployment_progress():
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-1", arch, ["sub-1"])
    d = record.to_dict()
    assert d["progress"] == 0.0
    orch.start_deployment(record.id)
    d = record.to_dict()
    assert d["progress"] == 100.0


def test_deployment_step_to_dict():
    """Test DeploymentStep serialization."""
    from app.services.deployment_orchestrator import DeploymentStep
    step = DeploymentStep("test_step", "Microsoft.Test/resources", "test.bicep")
    d = step.to_dict()
    assert d["name"] == "test_step"
    assert d["resource_type"] == "Microsoft.Test/resources"
    assert d["status"] == "pending"
    assert d["started_at"] is None
    assert d["completed_at"] is None
    assert d["error"] is None
    assert d["deployment_id"] is None


def test_deployment_record_to_dict_structure():
    """Test DeploymentRecord serialization structure."""
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": [{"name": "prod", "purpose": "workload"}]}
    record = orch.create_deployment("proj-struct", arch, ["sub-1"])
    d = record.to_dict()
    assert "id" in d
    assert "project_id" in d
    assert d["project_id"] == "proj-struct"
    assert "status" in d
    assert "steps" in d
    assert isinstance(d["steps"], list)
    assert "created_at" in d
    assert "audit_log" in d
    assert d["started_at"] is None
    assert d["completed_at"] is None


def test_deployment_with_spokes():
    """Test that spokes are added per non-connectivity subscription."""
    orch = DeploymentOrchestrator()
    arch = {
        "subscriptions": [
            {"name": "hub", "purpose": "connectivity"},
            {"name": "mgmt", "purpose": "management"},
            {"name": "prod", "purpose": "workload"},
            {"name": "dev", "purpose": "workload"},
        ]
    }
    record = orch.create_deployment("proj-spokes", arch, ["sub-1"])
    # 4 base steps + 2 spoke steps (prod and dev)
    assert len(record.steps) == 6
    spoke_steps = [s for s in record.steps if s.name.startswith("spoke-")]
    assert len(spoke_steps) == 2


def test_get_nonexistent_deployment():
    orch = DeploymentOrchestrator()
    assert orch.get_deployment("nonexistent") is None


def test_list_deployments_empty():
    orch = DeploymentOrchestrator()
    assert orch.list_deployments() == []


def test_rollback_sets_steps_to_rolled_back():
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-rb", arch, ["sub-1"])
    orch.start_deployment(record.id)
    result = orch.rollback_deployment(record.id)
    for step in result.steps:
        assert step.status == DeploymentStatus.ROLLED_BACK


def test_deployment_audit_log_entries():
    """Full lifecycle audit log entries."""
    orch = DeploymentOrchestrator()
    arch = {"subscriptions": []}
    record = orch.create_deployment("proj-audit", arch, ["sub-1"])
    orch.start_deployment(record.id)
    orch.rollback_deployment(record.id)
    actions = [e["action"] for e in record.audit_log]
    assert "created" in actions
    assert "started" in actions
    assert "completed" in actions
    assert "rollback" in actions
    assert "rollback_complete" in actions
    # Each entry should have timestamp and details
    for entry in record.audit_log:
        assert "timestamp" in entry
        assert "details" in entry
        assert "user" in entry
