"""Comprehensive tests for the DeploymentOrchestrator service.

Covers create, start, get, list, rollback, audit-log, and production-mode
paths with mocked Azure dependencies.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.deployment_orchestrator import (
    DeploymentOrchestrator,
    DeploymentRecord,
    DeploymentStatus,
    DeploymentStep,
    deployment_orchestrator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def orch() -> DeploymentOrchestrator:
    """Return a fresh orchestrator instance (isolated per test)."""
    return DeploymentOrchestrator()


@pytest.fixture()
def sample_architecture() -> dict:
    return {
        "subscriptions": [
            {"name": "hub", "purpose": "connectivity"},
            {"name": "prod", "purpose": "workload"},
        ],
        "network_topology": {"primary_region": "eastus2"},
    }


@pytest.fixture()
def simple_architecture() -> dict:
    """Architecture with no extra spoke subscriptions."""
    return {"subscriptions": []}


@pytest.fixture()
def created_deployment(orch: DeploymentOrchestrator, simple_architecture: dict):
    """A deployment that has been created but not started."""
    return orch.create_deployment("proj-1", simple_architecture, ["sub-1"])


@pytest.fixture()
def started_deployment(orch: DeploymentOrchestrator, simple_architecture: dict):
    """A deployment that has been created and started (dev-mode)."""
    record = orch.create_deployment("proj-started", simple_architecture, ["sub-1"])
    orch.start_deployment(record.id)
    return record


# ---------------------------------------------------------------------------
# Singleton sanity
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_module_level_singleton_exists(self):
        assert deployment_orchestrator is not None
        assert isinstance(deployment_orchestrator, DeploymentOrchestrator)


# ---------------------------------------------------------------------------
# create_deployment
# ---------------------------------------------------------------------------

class TestCreateDeployment:
    def test_returns_deployment_record(self, orch, simple_architecture):
        record = orch.create_deployment("proj-1", simple_architecture, ["sub-1"])
        assert isinstance(record, DeploymentRecord)

    def test_initial_status_is_pending(self, orch, simple_architecture):
        record = orch.create_deployment("proj-1", simple_architecture, ["sub-1"])
        assert record.status == DeploymentStatus.PENDING

    def test_stores_project_id(self, orch, simple_architecture):
        record = orch.create_deployment("my-proj", simple_architecture, ["sub-1"])
        assert record.project_id == "my-proj"

    def test_stores_subscription_ids(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-a", "sub-b"])
        assert record.subscription_ids == ["sub-a", "sub-b"]

    def test_stores_architecture(self, orch, sample_architecture):
        record = orch.create_deployment("p", sample_architecture, ["sub-1"])
        assert record.architecture is sample_architecture

    def test_generates_unique_ids(self, orch, simple_architecture):
        r1 = orch.create_deployment("p", simple_architecture, ["sub-1"])
        r2 = orch.create_deployment("p", simple_architecture, ["sub-1"])
        assert r1.id != r2.id

    def test_creates_base_steps(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        assert len(record.steps) == 4  # DEPLOYMENT_ORDER has 4 entries
        names = [s.name for s in record.steps]
        assert names == [
            "management_groups",
            "hub_networking",
            "spoke_networking",
            "policy_assignments",
        ]

    def test_adds_spoke_steps_for_workload_subscriptions(self, orch):
        arch = {
            "subscriptions": [
                {"name": "hub", "purpose": "connectivity"},
                {"name": "mgmt", "purpose": "management"},
                {"name": "prod", "purpose": "workload"},
                {"name": "dev", "purpose": "development"},
            ]
        }
        record = orch.create_deployment("p", arch, ["sub-1"])
        # 4 base + 2 spokes (prod and dev — neither connectivity nor management)
        assert len(record.steps) == 6
        spoke_names = [s.name for s in record.steps if s.name.startswith("spoke-")]
        assert "spoke-prod" in spoke_names
        assert "spoke-dev" in spoke_names

    def test_no_extra_spokes_for_connectivity_and_management(self, orch):
        arch = {
            "subscriptions": [
                {"name": "hub", "purpose": "connectivity"},
                {"name": "mgmt", "purpose": "management"},
            ]
        }
        record = orch.create_deployment("p", arch, ["sub-1"])
        assert len(record.steps) == 4  # only base steps

    def test_audit_entry_on_creation(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        assert len(record.audit_log) == 1
        assert record.audit_log[0]["action"] == "created"
        assert "4 steps" in record.audit_log[0]["details"]

    def test_deployment_is_retrievable_after_creation(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        assert orch.get_deployment(record.id) is record

    def test_created_at_is_set(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        assert isinstance(record.created_at, datetime)
        assert record.created_at.tzinfo is not None

    def test_started_and_completed_at_are_none(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        assert record.started_at is None
        assert record.completed_at is None


# ---------------------------------------------------------------------------
# start_deployment (dev mode — credential_manager.is_configured == False)
# ---------------------------------------------------------------------------

class TestStartDeploymentDevMode:
    def test_succeeds_in_dev_mode(self, orch, created_deployment):
        result = orch.start_deployment(created_deployment.id)
        assert result.status == DeploymentStatus.SUCCEEDED

    def test_all_steps_succeed(self, orch, created_deployment):
        result = orch.start_deployment(created_deployment.id)
        for step in result.steps:
            assert step.status == DeploymentStatus.SUCCEEDED

    def test_steps_have_timestamps(self, orch, created_deployment):
        result = orch.start_deployment(created_deployment.id)
        for step in result.steps:
            assert step.started_at is not None
            assert step.completed_at is not None

    def test_steps_get_deployment_ids(self, orch, created_deployment):
        result = orch.start_deployment(created_deployment.id)
        for step in result.steps:
            assert step.deployment_id is not None

    def test_record_timestamps(self, orch, created_deployment):
        result = orch.start_deployment(created_deployment.id)
        assert result.started_at is not None
        assert result.completed_at is not None

    def test_audit_log_entries(self, orch, created_deployment):
        orch.start_deployment(created_deployment.id)
        actions = [e["action"] for e in created_deployment.audit_log]
        assert "created" in actions
        assert "started" in actions
        assert "completed" in actions

    def test_nonexistent_deployment_raises_key_error(self, orch):
        with pytest.raises(KeyError):
            orch.start_deployment("nonexistent-id")


# ---------------------------------------------------------------------------
# start_deployment (production mode — credential_manager.is_configured == True)
# ---------------------------------------------------------------------------

class TestStartDeploymentProductionMode:
    def _mock_production(self):
        """Return mocks for credential_manager (configured) and a deploy result."""
        mock_cred = MagicMock()
        mock_cred.is_configured = True
        deploy_result = {"deployment_name": "deploy-abc"}
        return mock_cred, deploy_result

    def test_all_steps_succeed(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        mock_cred, deploy_result = self._mock_production()

        with patch("app.services.credentials.credential_manager", mock_cred), \
             patch.object(orch, "_deploy_step", return_value=deploy_result):
            result = orch.start_deployment(record.id)

        assert result.status == DeploymentStatus.SUCCEEDED
        assert result.completed_at is not None
        for step in result.steps:
            assert step.status == DeploymentStatus.SUCCEEDED
            assert step.deployment_id == "deploy-abc"

    def test_step_failure_stops_deployment(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        mock_cred, _ = self._mock_production()

        with patch("app.services.credentials.credential_manager", mock_cred), \
             patch.object(orch, "_deploy_step", side_effect=RuntimeError("boom")):
            result = orch.start_deployment(record.id)

        assert result.status == DeploymentStatus.FAILED
        assert "boom" in result.error
        # First step should be failed
        assert result.steps[0].status == DeploymentStatus.FAILED
        assert result.steps[0].error == "boom"
        # Remaining steps should still be pending (deployment stops on first failure)
        for step in result.steps[1:]:
            assert step.status == DeploymentStatus.PENDING

    def test_failure_audit_log(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        mock_cred, _ = self._mock_production()

        with patch("app.services.credentials.credential_manager", mock_cred), \
             patch.object(orch, "_deploy_step", side_effect=Exception("ARM fail")):
            orch.start_deployment(record.id)

        actions = [e["action"] for e in record.audit_log]
        assert "step_started" in actions
        assert "step_failed" in actions

    def test_partial_failure_leaves_succeeded_steps(self, orch, simple_architecture):
        """If step 2 fails, step 1 should remain SUCCEEDED."""
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        mock_cred, _ = self._mock_production()
        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("fail on step 2")
            return {"deployment_name": f"deploy-{call_count}"}

        with patch("app.services.credentials.credential_manager", mock_cred), \
             patch.object(orch, "_deploy_step", side_effect=_side_effect):
            result = orch.start_deployment(record.id)

        assert result.steps[0].status == DeploymentStatus.SUCCEEDED
        assert result.steps[1].status == DeploymentStatus.FAILED


# ---------------------------------------------------------------------------
# get_deployment
# ---------------------------------------------------------------------------

class TestGetDeployment:
    def test_returns_existing_deployment(self, orch, created_deployment):
        fetched = orch.get_deployment(created_deployment.id)
        assert fetched is not None
        assert fetched.id == created_deployment.id

    def test_returns_none_for_nonexistent(self, orch):
        assert orch.get_deployment("does-not-exist") is None

    def test_returns_same_object_reference(self, orch, created_deployment):
        """Returned record is the same object (in-memory store)."""
        assert orch.get_deployment(created_deployment.id) is created_deployment


# ---------------------------------------------------------------------------
# list_deployments
# ---------------------------------------------------------------------------

class TestListDeployments:
    def test_empty_when_none_created(self, orch):
        assert orch.list_deployments() == []

    def test_returns_all_deployments(self, orch, simple_architecture):
        orch.create_deployment("p1", simple_architecture, ["s1"])
        orch.create_deployment("p2", simple_architecture, ["s2"])
        assert len(orch.list_deployments()) == 2

    def test_filters_by_project_id(self, orch, simple_architecture):
        orch.create_deployment("alpha", simple_architecture, ["s1"])
        orch.create_deployment("beta", simple_architecture, ["s2"])
        orch.create_deployment("alpha", simple_architecture, ["s3"])
        assert len(orch.list_deployments("alpha")) == 2
        assert len(orch.list_deployments("beta")) == 1

    def test_filter_nonexistent_project_returns_empty(self, orch, simple_architecture):
        orch.create_deployment("alpha", simple_architecture, ["s1"])
        assert orch.list_deployments("nope") == []

    def test_sorted_newest_first(self, orch, simple_architecture):
        r1 = orch.create_deployment("p", simple_architecture, ["s1"])
        r2 = orch.create_deployment("p", simple_architecture, ["s2"])
        result = orch.list_deployments()
        # r2 created after r1, so r2 first
        assert result[0].id == r2.id
        assert result[1].id == r1.id

    def test_none_filter_returns_all(self, orch, simple_architecture):
        orch.create_deployment("p1", simple_architecture, ["s1"])
        orch.create_deployment("p2", simple_architecture, ["s2"])
        assert len(orch.list_deployments(None)) == 2


# ---------------------------------------------------------------------------
# rollback_deployment
# ---------------------------------------------------------------------------

class TestRollbackDeployment:
    def test_status_set_to_rolled_back(self, orch, started_deployment):
        result = orch.rollback_deployment(started_deployment.id)
        assert result.status == DeploymentStatus.ROLLED_BACK

    def test_succeeded_steps_marked_rolled_back(self, orch, started_deployment):
        result = orch.rollback_deployment(started_deployment.id)
        for step in result.steps:
            assert step.status == DeploymentStatus.ROLLED_BACK

    def test_completed_at_is_set(self, orch, started_deployment):
        result = orch.rollback_deployment(started_deployment.id)
        assert result.completed_at is not None

    def test_audit_log_contains_rollback_entries(self, orch, started_deployment):
        orch.rollback_deployment(started_deployment.id)
        actions = [e["action"] for e in started_deployment.audit_log]
        assert "rollback" in actions
        assert "rollback_complete" in actions

    def test_rollback_step_audit_per_succeeded_step(self, orch, started_deployment):
        orch.rollback_deployment(started_deployment.id)
        rollback_steps = [
            e for e in started_deployment.audit_log if e["action"] == "rollback_step"
        ]
        # Each of the 4 base steps should have a rollback_step entry
        assert len(rollback_steps) == len(started_deployment.steps)

    def test_nonexistent_deployment_raises(self, orch):
        with pytest.raises(KeyError):
            orch.rollback_deployment("nonexistent")

    def test_only_succeeded_steps_are_rolled_back(self, orch, simple_architecture):
        """Pending/failed steps should not be touched by rollback."""
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        # Manually set only the first step as succeeded
        record.steps[0].status = DeploymentStatus.SUCCEEDED
        record.steps[1].status = DeploymentStatus.FAILED
        # steps 2, 3 remain PENDING

        result = orch.rollback_deployment(record.id)
        assert result.steps[0].status == DeploymentStatus.ROLLED_BACK
        assert result.steps[1].status == DeploymentStatus.FAILED  # unchanged
        assert result.steps[2].status == DeploymentStatus.PENDING  # unchanged
        assert result.steps[3].status == DeploymentStatus.PENDING  # unchanged

    def test_rollback_production_deletes_resource_groups(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        for step in record.steps:
            step.status = DeploymentStatus.SUCCEEDED

        mock_cred = MagicMock()
        mock_cred.is_configured = True
        mock_client = MagicMock()
        mock_poller = MagicMock()
        mock_client.resource_groups.begin_delete.return_value = mock_poller
        mock_cred.get_resource_client.return_value = mock_client

        with patch("app.services.credentials.credential_manager", mock_cred):
            orch.rollback_deployment(record.id)

        assert mock_client.resource_groups.begin_delete.call_count == len(record.steps)

    def test_rollback_production_handles_delete_errors(self, orch, simple_architecture):
        record = orch.create_deployment("p", simple_architecture, ["sub-1"])
        for step in record.steps:
            step.status = DeploymentStatus.SUCCEEDED

        mock_cred = MagicMock()
        mock_cred.is_configured = True
        mock_client = MagicMock()
        mock_client.resource_groups.begin_delete.side_effect = Exception("Delete failed")
        mock_cred.get_resource_client.return_value = mock_client

        with patch("app.services.credentials.credential_manager", mock_cred):
            result = orch.rollback_deployment(record.id)

        # Should still complete (errors logged, not raised)
        assert result.status == DeploymentStatus.ROLLED_BACK
        errors = [e for e in result.audit_log if e["action"] == "rollback_error"]
        assert len(errors) == len(record.steps)


# ---------------------------------------------------------------------------
# get_audit_log
# ---------------------------------------------------------------------------

class TestGetAuditLog:
    def test_returns_entries_for_existing_deployment(self, orch, created_deployment):
        log = orch.get_audit_log(created_deployment.id)
        assert isinstance(log, list)
        assert len(log) >= 1

    def test_returns_empty_for_nonexistent(self, orch):
        assert orch.get_audit_log("no-such-id") == []

    def test_entries_have_required_fields(self, orch, created_deployment):
        log = orch.get_audit_log(created_deployment.id)
        for entry in log:
            assert "timestamp" in entry
            assert "action" in entry
            assert "details" in entry
            assert "user" in entry

    def test_default_user_is_system(self, orch, created_deployment):
        log = orch.get_audit_log(created_deployment.id)
        assert all(e["user"] == "system" for e in log)

    def test_full_lifecycle_actions(self, orch, started_deployment):
        orch.rollback_deployment(started_deployment.id)
        log = orch.get_audit_log(started_deployment.id)
        actions = [e["action"] for e in log]
        assert "created" in actions
        assert "started" in actions
        assert "completed" in actions
        assert "rollback" in actions
        assert "rollback_complete" in actions


# ---------------------------------------------------------------------------
# _deploy_step (private but critical — production Azure interaction)
# ---------------------------------------------------------------------------

class TestDeployStep:
    def test_raises_when_no_resource_client(self, orch):
        step = DeploymentStep("test", "Microsoft.Test/res", "test.bicep")
        mock_cred = MagicMock()
        mock_cred.get_resource_client.return_value = None

        with patch("app.services.credentials.credential_manager", mock_cred):
            with pytest.raises(RuntimeError, match="Cannot get Azure client"):
                orch._deploy_step(step, "sub-1", {})

    def test_raises_when_template_not_found(self, orch):
        step = DeploymentStep("test", "Microsoft.Test/res", "missing.bicep")
        mock_cred = MagicMock()
        mock_client = MagicMock()
        mock_cred.get_resource_client.return_value = mock_client
        mock_gen = MagicMock()
        mock_gen.get_template.return_value = None

        with patch("app.services.credentials.credential_manager", mock_cred), \
             patch("app.services.bicep_generator.bicep_generator", mock_gen):
            with pytest.raises(RuntimeError, match="Template.*not found"):
                orch._deploy_step(step, "sub-1", {})

    def test_successful_deployment(self, orch):
        step = DeploymentStep("hub", "Microsoft.Network/vn", "hub.bicep")
        mock_cred = MagicMock()
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.properties.provisioning_state = "Succeeded"
        mock_client.deployments.begin_create_or_update.return_value.result.return_value = mock_result
        mock_cred.get_resource_client.return_value = mock_client
        mock_gen = MagicMock()
        mock_gen.get_template.return_value = "bicep content"

        with patch("app.services.credentials.credential_manager", mock_cred), \
             patch("app.services.bicep_generator.bicep_generator", mock_gen):
            result = orch._deploy_step(
                step, "sub-1", {"network_topology": {"primary_region": "westus2"}}
            )

        assert "deployment_name" in result
        assert result["resource_group"] == "onramp-hub-rg"
        assert result["provisioning_state"] == "Succeeded"
        # Verify resource group created with correct region
        mock_client.resource_groups.create_or_update.assert_called_once_with(
            "onramp-hub-rg", {"location": "westus2"}
        )

    def test_default_region_is_eastus2(self, orch):
        step = DeploymentStep("hub", "Microsoft.Network/vn", "hub.bicep")
        mock_cred = MagicMock()
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.properties.provisioning_state = "Succeeded"
        mock_client.deployments.begin_create_or_update.return_value.result.return_value = mock_result
        mock_cred.get_resource_client.return_value = mock_client
        mock_gen = MagicMock()
        mock_gen.get_template.return_value = "content"

        with patch("app.services.credentials.credential_manager", mock_cred), \
             patch("app.services.bicep_generator.bicep_generator", mock_gen):
            orch._deploy_step(step, "sub-1", {})

        # No network_topology → default region
        mock_client.resource_groups.create_or_update.assert_called_once_with(
            "onramp-hub-rg", {"location": "eastus2"}
        )

    def test_arm_failure_raises_runtime_error(self, orch):
        step = DeploymentStep("hub", "Microsoft.Network/vn", "hub.bicep")
        mock_cred = MagicMock()
        mock_client = MagicMock()
        mock_client.deployments.begin_create_or_update.side_effect = Exception("ARM err")
        mock_cred.get_resource_client.return_value = mock_client
        mock_gen = MagicMock()
        mock_gen.get_template.return_value = "content"

        with patch("app.services.credentials.credential_manager", mock_cred), \
             patch("app.services.bicep_generator.bicep_generator", mock_gen):
            with pytest.raises(RuntimeError, match="ARM deployment failed"):
                orch._deploy_step(step, "sub-1", {})


# ---------------------------------------------------------------------------
# DeploymentRecord & DeploymentStep model tests
# ---------------------------------------------------------------------------

class TestDeploymentRecord:
    def test_to_dict_keys(self):
        record = DeploymentRecord("p1", {"k": "v"}, ["s1"])
        d = record.to_dict()
        expected_keys = {
            "id", "project_id", "status", "subscription_ids",
            "steps", "created_at", "started_at", "completed_at",
            "error", "audit_log", "progress",
        }
        assert set(d.keys()) == expected_keys

    def test_progress_zero_with_no_steps(self):
        record = DeploymentRecord("p1", {}, ["s1"])
        assert record._calculate_progress() == 0.0

    def test_progress_partial(self):
        record = DeploymentRecord("p1", {}, ["s1"])
        s1 = DeploymentStep("a", "t", "a.bicep")
        s2 = DeploymentStep("b", "t", "b.bicep")
        s1.status = DeploymentStatus.SUCCEEDED
        s2.status = DeploymentStatus.PENDING
        record.steps = [s1, s2]
        assert record._calculate_progress() == 50.0

    def test_progress_full(self):
        record = DeploymentRecord("p1", {}, ["s1"])
        s1 = DeploymentStep("a", "t", "a.bicep")
        s1.status = DeploymentStatus.SUCCEEDED
        record.steps = [s1]
        assert record._calculate_progress() == 100.0

    def test_add_audit_entry_custom_user(self):
        record = DeploymentRecord("p1", {}, ["s1"])
        record.add_audit_entry("test", "details", user="admin")
        assert record.audit_log[0]["user"] == "admin"


class TestDeploymentStep:
    def test_to_dict_keys(self):
        step = DeploymentStep("s", "t", "s.bicep")
        d = step.to_dict()
        expected_keys = {
            "id", "name", "resource_type", "status",
            "started_at", "completed_at", "error", "deployment_id",
        }
        assert set(d.keys()) == expected_keys

    def test_initial_state(self):
        step = DeploymentStep("test", "Microsoft.Test/res", "test.bicep")
        assert step.status == DeploymentStatus.PENDING
        assert step.started_at is None
        assert step.completed_at is None
        assert step.error is None
        assert step.deployment_id is None

    def test_unique_ids(self):
        s1 = DeploymentStep("a", "t", "a.bicep")
        s2 = DeploymentStep("b", "t", "b.bicep")
        assert s1.id != s2.id


# ---------------------------------------------------------------------------
# DeploymentStatus enum
# ---------------------------------------------------------------------------

class TestDeploymentStatus:
    def test_all_values_present(self):
        expected = {"pending", "validating", "deploying", "succeeded", "failed", "rolled_back", "cancelled"}
        actual = {s.value for s in DeploymentStatus}
        assert actual == expected

    def test_is_str_enum(self):
        assert isinstance(DeploymentStatus.PENDING, str)
        assert DeploymentStatus.PENDING == "pending"
