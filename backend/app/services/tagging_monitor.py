"""Tagging compliance monitor — scans Azure resources for tag policy adherence."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from app.models.base import generate_uuid
from app.services.event_stream import event_stream
from app.services.task_scheduler import task_scheduler

logger = logging.getLogger(__name__)

# ── Default policy seed data ─────────────────────────────────────────────────

DEFAULT_REQUIRED_TAGS = [
    {
        "name": "Environment",
        "required": True,
        "allowed_values": ["dev", "staging", "prod"],
        "pattern": None,
    },
    {
        "name": "Owner",
        "required": True,
        "allowed_values": None,
        "pattern": r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    },
    {
        "name": "CostCenter",
        "required": True,
        "allowed_values": None,
        "pattern": r"^CC-\d{4,6}$",
    },
    {
        "name": "Application",
        "required": True,
        "allowed_values": None,
        "pattern": None,
    },
    {
        "name": "ManagedBy",
        "required": True,
        "allowed_values": ["terraform", "bicep", "manual", "pulumi"],
        "pattern": None,
    },
]

# ── Mock resource data for dev mode ──────────────────────────────────────────

MOCK_RESOURCES = [
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-app/providers/Microsoft.Compute/virtualMachines/vm-web-01",
        "type": "Microsoft.Compute/virtualMachines",
        "name": "vm-web-01",
        "tags": {
            "Environment": "prod",
            "Owner": "alice@contoso.com",
            "CostCenter": "CC-1001",
            "Application": "WebApp",
            "ManagedBy": "terraform",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-app/providers/Microsoft.Compute/virtualMachines/vm-web-02",
        "type": "Microsoft.Compute/virtualMachines",
        "name": "vm-web-02",
        "tags": {
            "Environment": "prod",
            "Owner": "alice@contoso.com",
            "CostCenter": "CC-1001",
            "Application": "WebApp",
            "ManagedBy": "terraform",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-app/providers/Microsoft.Storage/storageAccounts/stappdata01",
        "type": "Microsoft.Storage/storageAccounts",
        "name": "stappdata01",
        "tags": {
            "Environment": "prod",
            "Owner": "bob@contoso.com",
            "CostCenter": "CC-1002",
            "Application": "DataPipeline",
            "ManagedBy": "bicep",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-app/providers/Microsoft.Sql/servers/sql-main",
        "type": "Microsoft.Sql/servers",
        "name": "sql-main",
        "tags": {
            "Environment": "staging",
            "Owner": "carol@contoso.com",
            "CostCenter": "CC-1003",
            "Application": "MainDB",
            "ManagedBy": "bicep",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-app/providers/Microsoft.Web/sites/app-frontend",
        "type": "Microsoft.Web/sites",
        "name": "app-frontend",
        "tags": {
            "Environment": "dev",
            "Owner": "dave@contoso.com",
            "CostCenter": "CC-1004",
            "Application": "Frontend",
            "ManagedBy": "terraform",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-app/providers/Microsoft.Network/virtualNetworks/vnet-main",
        "type": "Microsoft.Network/virtualNetworks",
        "name": "vnet-main",
        "tags": {
            "Environment": "prod",
            "Owner": "netteam@contoso.com",
            "CostCenter": "CC-1005",
            "Application": "Networking",
            "ManagedBy": "terraform",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-app/providers/Microsoft.KeyVault/vaults/kv-secrets",
        "type": "Microsoft.KeyVault/vaults",
        "name": "kv-secrets",
        "tags": {
            "Environment": "prod",
            "Owner": "security@contoso.com",
            "CostCenter": "CC-1006",
            "Application": "SecretsMgmt",
            "ManagedBy": "bicep",
        },
    },
    # --- Resources with violations below ---
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-dev/providers/Microsoft.Compute/virtualMachines/vm-test-01",
        "type": "Microsoft.Compute/virtualMachines",
        "name": "vm-test-01",
        "tags": {
            "Environment": "dev",
            "Owner": "tester@contoso.com",
            # Missing CostCenter
            "Application": "Testing",
            "ManagedBy": "manual",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-dev/providers/Microsoft.Storage/storageAccounts/sttemp",
        "type": "Microsoft.Storage/storageAccounts",
        "name": "sttemp",
        "tags": {
            "Environment": "development",  # Invalid — not in allowed values
            "Owner": "temp-user",  # Invalid — not a valid email
            "CostCenter": "CC-1001",
            "Application": "Temp",
            "ManagedBy": "manual",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-dev/providers/Microsoft.Web/sites/app-legacy",
        "type": "Microsoft.Web/sites",
        "name": "app-legacy",
        "tags": {
            # Missing Environment
            "Owner": "legacy@contoso.com",
            "CostCenter": "INVALID",  # Invalid — doesn't match CC-NNNN pattern
            "Application": "Legacy",
            "ManagedBy": "manual",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-dev/providers/Microsoft.Network/networkSecurityGroups/nsg-open",
        "type": "Microsoft.Network/networkSecurityGroups",
        "name": "nsg-open",
        "tags": {
            "Environment": "prod",
            # Missing Owner
            # Missing CostCenter
            # Missing Application
            "ManagedBy": "manual",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-dev/providers/Microsoft.ContainerRegistry/registries/crmain",
        "type": "Microsoft.ContainerRegistry/registries",
        "name": "crmain",
        "tags": {},  # No tags at all
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-dev/providers/Microsoft.Compute/disks/disk-orphan",
        "type": "Microsoft.Compute/disks",
        "name": "disk-orphan",
        "tags": {
            "Environment": "prod",
            "Owner": "alice@contoso.com",
            "CostCenter": "CC-1001",
            "Application": "WebApp",
            "ManagedBy": "unknown-tool",  # Invalid — not in allowed values
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-dev/providers/Microsoft.Insights/components/ai-telemetry",
        "type": "Microsoft.Insights/components",
        "name": "ai-telemetry",
        "tags": {
            "Environment": "prod",
            "Owner": "alice@contoso.com",
            "CostCenter": "CC-1001",
            "Application": "Monitoring",
            "ManagedBy": "terraform",
        },
    },
    {
        "id": "/subscriptions/sub1/resourceGroups/rg-dev/providers/Microsoft.Compute/virtualMachines/vm-batch",
        "type": "Microsoft.Compute/virtualMachines",
        "name": "vm-batch",
        "tags": {
            "Environment": "staging",
            "Owner": "batch-runner",  # Invalid — not a valid email
            "CostCenter": "CC-2001",
            "Application": "BatchProcess",
            "ManagedBy": "terraform",
        },
    },
]


class TaggingMonitor:
    """Monitors Azure resource tagging compliance against configurable policies."""

    async def scan_tagging_compliance(
        self,
        project_id: str,
        subscription_id: str,
        tenant_id: str | None = None,
        db=None,
    ) -> dict:
        """Run a full tagging compliance scan.

        Fetches resources, evaluates them against the tagging policy,
        calculates a compliance score, persists results, and publishes an SSE event.
        """
        now = datetime.now(timezone.utc)

        # Get resources
        resources = await self.get_resource_tags(subscription_id)

        # Load or create policy
        policy_id = None
        tagging_policy = DEFAULT_REQUIRED_TAGS

        if db is not None:
            from sqlalchemy import select

            from app.models.tagging import TaggingPolicy

            result = await db.execute(
                select(TaggingPolicy).where(
                    TaggingPolicy.project_id == project_id
                ).order_by(TaggingPolicy.created_at.desc())
            )
            policy_row = result.scalar_one_or_none()
            if policy_row is not None:
                policy_id = policy_row.id
                tagging_policy = policy_row.required_tags

        # Evaluate compliance
        evaluation = await self.evaluate_compliance(resources, tagging_policy)

        # Calculate score
        score = await self.get_tagging_score(evaluation)

        # Build scan result
        scan_id = generate_uuid()
        scan_result = {
            "id": scan_id,
            "project_id": project_id,
            "policy_id": policy_id,
            "tenant_id": tenant_id,
            "total_resources": score["total_resources"],
            "compliant_count": score["compliant_count"],
            "non_compliant_count": score["non_compliant_count"],
            "compliance_percentage": score["compliance_percentage"],
            "scan_timestamp": now.isoformat(),
            "status": "completed",
            "violations": evaluation["violations"],
        }

        # Persist if DB is available
        if db is not None and policy_id is not None:
            from app.models.tagging import TaggingScanResult, TaggingViolation

            result_row = TaggingScanResult(
                id=scan_id,
                project_id=project_id,
                policy_id=policy_id,
                tenant_id=tenant_id,
                total_resources=score["total_resources"],
                compliant_count=score["compliant_count"],
                non_compliant_count=score["non_compliant_count"],
                compliance_percentage=score["compliance_percentage"],
                scan_timestamp=now,
                status="completed",
            )
            db.add(result_row)
            await db.flush()

            for v in evaluation["violations"]:
                db.add(TaggingViolation(
                    scan_result_id=scan_id,
                    resource_id=v["resource_id"],
                    resource_type=v["resource_type"],
                    resource_name=v.get("resource_name"),
                    violation_type=v["violation_type"],
                    tag_name=v["tag_name"],
                    expected_value=v.get("expected_value"),
                    actual_value=v.get("actual_value"),
                ))
            await db.flush()

        # Publish SSE event
        await event_stream.publish(
            event_type="governance_score_updated",
            data={
                "component": "tagging",
                "project_id": project_id,
                "compliance_percentage": score["compliance_percentage"],
                "total_resources": score["total_resources"],
                "non_compliant_count": score["non_compliant_count"],
            },
            tenant_id=tenant_id,
            project_id=project_id,
        )

        return scan_result

    async def get_resource_tags(self, subscription_id: str) -> list[dict]:
        """Fetch resource tags from Azure or return mock data in dev mode.

        In production this would use Azure Resource Graph to query tags.
        In dev mode it returns mock data with ~15 resources.
        """
        from app.config import settings

        if settings.is_dev_mode:
            return MOCK_RESOURCES

        # Production: Azure Resource Graph query (placeholder)
        logger.info(
            "Would query Azure Resource Graph for subscription %s",
            subscription_id,
        )
        return MOCK_RESOURCES

    async def evaluate_compliance(
        self, resources: list[dict], tagging_policy: list[dict]
    ) -> dict:
        """Evaluate resources against a tagging policy.

        Checks for:
        - Required tags being present (missing_tag)
        - Tag values matching allowed_values (invalid_value)
        - Tag values matching regex patterns (naming_violation)
        """
        violations: list[dict] = []
        compliant_resources: set[str] = set()
        non_compliant_resources: set[str] = set()

        for resource in resources:
            resource_id = resource.get("id", "")
            resource_type = resource.get("type", "")
            resource_name = resource.get("name")
            tags = resource.get("tags", {}) or {}
            resource_is_compliant = True

            for rule in tagging_policy:
                tag_name = rule["name"]
                is_required = rule.get("required", True)
                allowed_values = rule.get("allowed_values")
                pattern = rule.get("pattern")

                tag_value = tags.get(tag_name)

                # Check required tag presence
                if is_required and tag_value is None:
                    violations.append({
                        "resource_id": resource_id,
                        "resource_type": resource_type,
                        "resource_name": resource_name,
                        "violation_type": "missing_tag",
                        "tag_name": tag_name,
                        "expected_value": "Tag must be present",
                        "actual_value": None,
                    })
                    resource_is_compliant = False
                    continue

                if tag_value is None:
                    continue

                # Check allowed values
                if allowed_values and tag_value not in allowed_values:
                    violations.append({
                        "resource_id": resource_id,
                        "resource_type": resource_type,
                        "resource_name": resource_name,
                        "violation_type": "invalid_value",
                        "tag_name": tag_name,
                        "expected_value": f"One of: {', '.join(allowed_values)}",
                        "actual_value": tag_value,
                    })
                    resource_is_compliant = False

                # Check pattern
                if pattern and not re.match(pattern, tag_value):
                    violations.append({
                        "resource_id": resource_id,
                        "resource_type": resource_type,
                        "resource_name": resource_name,
                        "violation_type": "naming_violation",
                        "tag_name": tag_name,
                        "expected_value": f"Must match pattern: {pattern}",
                        "actual_value": tag_value,
                    })
                    resource_is_compliant = False

            if resource_is_compliant:
                compliant_resources.add(resource_id)
            else:
                non_compliant_resources.add(resource_id)

        return {
            "violations": violations,
            "compliant_resources": list(compliant_resources),
            "non_compliant_resources": list(non_compliant_resources),
            "total_resources": len(resources),
            "compliant_count": len(compliant_resources),
            "non_compliant_count": len(non_compliant_resources),
        }

    async def get_tagging_score(self, results: dict) -> dict:
        """Calculate compliance percentage from evaluation results."""
        total = results.get("total_resources", 0)
        compliant = results.get("compliant_count", 0)

        if total == 0:
            percentage = 100.0
        else:
            percentage = round((compliant / total) * 100, 2)

        return {
            "compliance_percentage": percentage,
            "total_resources": total,
            "compliant_count": compliant,
            "non_compliant_count": results.get("non_compliant_count", 0),
        }


# Singleton
tagging_monitor = TaggingMonitor()


# Register as periodic task
@task_scheduler.periodic(
    "tagging_compliance",
    interval_seconds=3600,
    description="Scan Azure resources for tagging policy compliance",
)
async def scan_tagging_periodic(**kwargs) -> dict:
    """Periodic tagging compliance scan."""
    project_id = kwargs.get("project_id")
    tenant_id = kwargs.get("tenant_id")

    if not project_id:
        return {"message": "No project_id provided — skipping tagging scan"}

    result = await tagging_monitor.scan_tagging_compliance(
        project_id=project_id,
        subscription_id="periodic-scan",
        tenant_id=tenant_id,
    )
    return {
        "message": "Tagging compliance scan completed",
        "compliance_percentage": result["compliance_percentage"],
        "total_resources": result["total_resources"],
        "non_compliant_count": result["non_compliant_count"],
    }
