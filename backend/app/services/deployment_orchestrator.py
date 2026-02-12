"""Deployment orchestration service for Azure landing zone deployments."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class DeploymentStep:
    def __init__(self, name: str, resource_type: str, template: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.resource_type = resource_type
        self.template = template
        self.status = DeploymentStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.deployment_id: Optional[str] = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "resource_type": self.resource_type,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "deployment_id": self.deployment_id,
        }


class DeploymentRecord:
    def __init__(self, project_id: str, architecture: dict, subscription_ids: list[str]):
        self.id = str(uuid.uuid4())
        self.project_id = project_id
        self.architecture = architecture
        self.subscription_ids = subscription_ids
        self.status = DeploymentStatus.PENDING
        self.steps: list[DeploymentStep] = []
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.audit_log: list[dict] = []

    def add_audit_entry(self, action: str, details: str, user: str = "system"):
        self.audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
            "user": user,
        })

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status.value,
            "subscription_ids": self.subscription_ids,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "audit_log": self.audit_log,
            "progress": self._calculate_progress(),
        }

    def _calculate_progress(self):
        if not self.steps:
            return 0.0
        done = sum(1 for s in self.steps if s.status == DeploymentStatus.SUCCEEDED)
        return round(done / len(self.steps) * 100, 1)


class DeploymentOrchestrator:
    """Orchestrates multi-step Azure landing zone deployments."""

    # Canonical deployment order
    DEPLOYMENT_ORDER = [
        ("management_groups", "Microsoft.Management/managementGroups", "management-groups.bicep"),
        ("hub_networking", "Microsoft.Network/virtualNetworks", "hub-networking.bicep"),
        ("spoke_networking", "Microsoft.Network/virtualNetworks", "spoke-networking.bicep"),
        ("policy_assignments", "Microsoft.Authorization/policyAssignments", "policy-assignments.bicep"),
    ]

    def __init__(self):
        self._deployments: dict[str, DeploymentRecord] = {}

    def create_deployment(
        self, project_id: str, architecture: dict, subscription_ids: list[str]
    ) -> DeploymentRecord:
        """Create a new deployment with ordered steps."""
        record = DeploymentRecord(project_id, architecture, subscription_ids)

        for name, resource_type, template in self.DEPLOYMENT_ORDER:
            step = DeploymentStep(name, resource_type, template)
            record.steps.append(step)

        # Add spoke steps per subscription
        subs = architecture.get("subscriptions", [])
        for sub in subs:
            if sub.get("purpose") not in ("connectivity", "management"):
                step = DeploymentStep(
                    f"spoke-{sub['name']}",
                    "Microsoft.Resources/deployments",
                    "spoke-networking.bicep",
                )
                record.steps.append(step)

        record.add_audit_entry("created", f"Deployment created with {len(record.steps)} steps")
        self._deployments[record.id] = record
        return record

    def start_deployment(self, deployment_id: str) -> DeploymentRecord:
        """Start executing a deployment."""
        record = self._deployments[deployment_id]
        record.status = DeploymentStatus.DEPLOYING
        record.started_at = datetime.now(timezone.utc)
        record.add_audit_entry("started", "Deployment execution started")

        # In dev mode, simulate by marking steps as succeeded
        for step in record.steps:
            step.status = DeploymentStatus.SUCCEEDED
            step.started_at = datetime.now(timezone.utc)
            step.completed_at = datetime.now(timezone.utc)
            step.deployment_id = str(uuid.uuid4())

        record.status = DeploymentStatus.SUCCEEDED
        record.completed_at = datetime.now(timezone.utc)
        record.add_audit_entry("completed", "All deployment steps succeeded")
        return record

    def get_deployment(self, deployment_id: str) -> Optional[DeploymentRecord]:
        return self._deployments.get(deployment_id)

    def list_deployments(self, project_id: Optional[str] = None) -> list[DeploymentRecord]:
        records = list(self._deployments.values())
        if project_id:
            records = [r for r in records if r.project_id == project_id]
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def rollback_deployment(self, deployment_id: str) -> DeploymentRecord:
        """Rollback a deployment by marking it and reversing completed steps."""
        record = self._deployments[deployment_id]
        record.status = DeploymentStatus.ROLLED_BACK
        record.add_audit_entry("rollback", "Deployment rollback initiated")

        # In dev mode, just mark steps as rolled back
        for step in reversed(record.steps):
            if step.status == DeploymentStatus.SUCCEEDED:
                step.status = DeploymentStatus.ROLLED_BACK
                record.add_audit_entry("rollback_step", f"Rolled back {step.name}")

        record.completed_at = datetime.now(timezone.utc)
        record.add_audit_entry("rollback_complete", "Rollback completed")
        return record

    def get_audit_log(self, deployment_id: str) -> list[dict]:
        record = self._deployments.get(deployment_id)
        if not record:
            return []
        return record.audit_log


# Singleton
deployment_orchestrator = DeploymentOrchestrator()
