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
