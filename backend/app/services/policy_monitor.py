"""Runtime policy compliance monitor.

Checks Azure Policy compliance state for deployed resources and maps
violations back to compliance framework controls.  In dev mode the
service generates mock policy state so the feature is testable without
an Azure subscription.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone

from app.config import settings
from app.models.base import generate_uuid
from app.services.compliance_data import COMPLIANCE_FRAMEWORKS

logger = logging.getLogger(__name__)

# ── Mock data for dev mode ───────────────────────────────────────────────────

_MOCK_RESOURCE_TYPES = [
    "Microsoft.Compute/virtualMachines",
    "Microsoft.Storage/storageAccounts",
    "Microsoft.Network/networkSecurityGroups",
    "Microsoft.Sql/servers",
    "Microsoft.KeyVault/vaults",
    "Microsoft.Web/sites",
]

_MOCK_POLICY_VIOLATIONS = [
    {
        "policy_name": "require-nsg",
        "policy_description": "Network security groups should be associated with subnets",
        "severity": "high",
        "resource_type": "Microsoft.Network/networkSecurityGroups",
        "remediation": "Associate an NSG with each subnet in your virtual network.",
    },
    {
        "policy_name": "require-encryption-at-rest",
        "policy_description": "Storage accounts should use customer-managed keys for encryption",
        "severity": "high",
        "resource_type": "Microsoft.Storage/storageAccounts",
        "remediation": "Enable customer-managed key encryption on the storage account.",
    },
    {
        "policy_name": "require-tls",
        "policy_description": "Web apps should require TLS 1.2 or higher",
        "severity": "critical",
        "resource_type": "Microsoft.Web/sites",
        "remediation": "Set the minimum TLS version to 1.2 in app service configuration.",
    },
    {
        "policy_name": "require-diagnostics",
        "policy_description": "Diagnostic logs should be enabled on all supported resources",
        "severity": "medium",
        "resource_type": "Microsoft.Sql/servers",
        "remediation": "Enable diagnostic settings and send logs to a Log Analytics workspace.",
    },
    {
        "policy_name": "require-rbac",
        "policy_description": "Role-based access control should be used on resources",
        "severity": "high",
        "resource_type": "Microsoft.KeyVault/vaults",
        "remediation": "Switch Key Vault to RBAC authorization model.",
    },
    {
        "policy_name": "require-backup",
        "policy_description": "Azure Backup should be enabled for virtual machines",
        "severity": "medium",
        "resource_type": "Microsoft.Compute/virtualMachines",
        "remediation": "Enable Azure Backup and configure a backup policy.",
    },
    {
        "policy_name": "enable-defender",
        "policy_description": "Microsoft Defender for Cloud should be enabled",
        "severity": "high",
        "resource_type": "Microsoft.Sql/servers",
        "remediation": "Enable Microsoft Defender for the resource type.",
    },
    {
        "policy_name": "require-key-vault",
        "policy_description": "Key Vault should be used to store secrets",
        "severity": "medium",
        "resource_type": "Microsoft.KeyVault/vaults",
        "remediation": "Store application secrets in Azure Key Vault instead of config files.",
    },
]


class PolicyMonitor:
    """Monitors Azure Policy compliance and maps violations to frameworks."""

    # ── Core scan ────────────────────────────────────────────────────────

    async def check_compliance(
        self,
        project_id: str,
        tenant_id: str | None = None,
        db=None,
    ) -> dict:
        """Run a policy compliance check for a project.

        Returns a dict describing the scan result (suitable for SSE and
        for persisting as a ``PolicyComplianceResult``).
        """
        scan_id = generate_uuid()
        now = datetime.now(timezone.utc)

        try:
            # Get policy state (mock in dev, real Azure in prod)
            subscription_id = f"sub-{project_id}"
            policy_state = await self.get_policy_state(subscription_id)

            violations_raw = policy_state.get("non_compliant_resources", [])
            total_resources = policy_state.get("total_resources", 0)
            compliant = total_resources - len(violations_raw)

            # Map violations to framework controls
            mapped = await self.map_violations_to_frameworks(
                violations_raw, architecture_data={}
            )

            result = {
                "id": scan_id,
                "project_id": project_id,
                "tenant_id": tenant_id,
                "scan_timestamp": now.isoformat(),
                "total_resources": total_resources,
                "compliant_count": max(compliant, 0),
                "non_compliant_count": len(violations_raw),
                "status": "completed",
                "violations": mapped,
            }

            # Persist if DB available
            if db is not None:
                await self._persist_result(result, db)

            # Publish SSE event
            await self._publish_event(result)

            return result

        except Exception as exc:
            logger.exception("Policy compliance check failed for %s", project_id)
            error_result = {
                "id": scan_id,
                "project_id": project_id,
                "tenant_id": tenant_id,
                "scan_timestamp": now.isoformat(),
                "total_resources": 0,
                "compliant_count": 0,
                "non_compliant_count": 0,
                "status": "failed",
                "error_message": str(exc),
                "violations": [],
            }
            return error_result

    # ── Policy state retrieval ───────────────────────────────────────────

    async def get_policy_state(self, subscription_id: str) -> dict:
        """Query Azure Policy Insights for non-compliant resources.

        In dev mode returns mock data; in production would call:
        ``GET /subscriptions/{id}/providers/Microsoft.PolicyInsights/
        policyStates/latest/queryResults``
        """
        if not settings.is_dev_mode:
            # Production: call Azure Policy Insights REST API
            logger.info(
                "Production Azure Policy query for %s (not yet implemented)",
                subscription_id,
            )
            return {"total_resources": 0, "non_compliant_resources": []}

        # Dev mode: generate deterministic mock data
        return self._generate_mock_policy_state(subscription_id)

    def _generate_mock_policy_state(self, subscription_id: str) -> dict:
        """Generate realistic mock Azure Policy state for dev/testing."""
        rng = random.Random(subscription_id)

        total = rng.randint(15, 40)
        num_violations = rng.randint(3, min(8, total))

        violations = []
        available = list(_MOCK_POLICY_VIOLATIONS)
        rng.shuffle(available)

        for i in range(num_violations):
            template = available[i % len(available)]
            violations.append({
                "resource_id": (
                    f"/subscriptions/{subscription_id}"
                    f"/resourceGroups/rg-onramp"
                    f"/providers/{template['resource_type']}"
                    f"/resource-{i}"
                ),
                "resource_type": template["resource_type"],
                "policy_name": template["policy_name"],
                "policy_description": template["policy_description"],
                "severity": template["severity"],
                "remediation": template["remediation"],
            })

        return {
            "total_resources": total,
            "non_compliant_resources": violations,
        }

    # ── Violation → framework mapping ────────────────────────────────────

    async def map_violations_to_frameworks(
        self,
        violations: list[dict],
        architecture_data: dict,
    ) -> list[dict]:
        """Map Azure Policy violations back to compliance framework controls.

        For each violation, find which framework controls reference the same
        policy key and attach the mapping.
        """
        # Build a reverse index: policy_name → list of (framework, control)
        policy_index: dict[str, list[dict]] = {}
        for fw in COMPLIANCE_FRAMEWORKS:
            for ctrl in fw["controls"]:
                for policy_key in ctrl.get("azure_policies", []):
                    policy_index.setdefault(policy_key, []).append({
                        "framework": fw["short_name"],
                        "control_id": ctrl["control_id"],
                        "control_title": ctrl["title"],
                        "severity": ctrl["severity"],
                    })

        now = datetime.now(timezone.utc)
        mapped: list[dict] = []

        for v in violations:
            policy_name = v.get("policy_name", "")
            matching_controls = policy_index.get(policy_name, [])

            # Pick the highest-severity control mapping (or None)
            framework_control = None
            if matching_controls:
                severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                matching_controls.sort(
                    key=lambda c: severity_order.get(c["severity"], 99)
                )
                framework_control = matching_controls[0]

            mapped.append({
                "id": generate_uuid(),
                "resource_id": v.get("resource_id", ""),
                "resource_type": v.get("resource_type", ""),
                "policy_name": policy_name,
                "policy_description": v.get("policy_description"),
                "severity": v.get("severity", "medium"),
                "framework_control_id": None,  # DB FK populated at persist time
                "framework_mapping": framework_control,
                "remediation_suggestion": v.get("remediation"),
                "detected_at": now.isoformat(),
            })

        return mapped

    # ── Persistence ──────────────────────────────────────────────────────

    async def _persist_result(self, result: dict, db) -> None:
        """Persist a scan result and its violations to the database."""
        from app.models.policy_compliance import (
            PolicyComplianceResult,
            PolicyViolation,
        )

        scan = PolicyComplianceResult(
            id=result["id"],
            project_id=result["project_id"],
            tenant_id=result.get("tenant_id"),
            scan_timestamp=datetime.fromisoformat(result["scan_timestamp"]),
            total_resources=result["total_resources"],
            compliant_count=result["compliant_count"],
            non_compliant_count=result["non_compliant_count"],
            status=result["status"],
        )
        db.add(scan)
        await db.flush()

        for v in result.get("violations", []):
            violation = PolicyViolation(
                id=v["id"],
                compliance_result_id=scan.id,
                resource_id=v["resource_id"],
                resource_type=v["resource_type"],
                policy_name=v["policy_name"],
                policy_description=v.get("policy_description"),
                severity=v["severity"],
                framework_control_id=v.get("framework_control_id"),
                remediation_suggestion=v.get("remediation_suggestion"),
                detected_at=datetime.fromisoformat(v["detected_at"]),
            )
            db.add(violation)

        await db.flush()

    # ── SSE event publishing ─────────────────────────────────────────────

    async def _publish_event(self, result: dict) -> None:
        """Publish a compliance_changed SSE event."""
        try:
            from app.services.event_stream import event_stream

            await event_stream.publish(
                event_type="compliance_changed",
                data={
                    "scan_id": result["id"],
                    "project_id": result["project_id"],
                    "status": result["status"],
                    "total_resources": result["total_resources"],
                    "non_compliant_count": result["non_compliant_count"],
                },
                project_id=result["project_id"],
                tenant_id=result.get("tenant_id"),
            )
        except Exception:
            logger.warning("Failed to publish compliance_changed event")


# Singleton
policy_monitor = PolicyMonitor()


# ── Register as periodic governance task ─────────────────────────────────────

from app.services.task_scheduler import task_scheduler  # noqa: E402


@task_scheduler.periodic(
    "policy_compliance",
    interval_seconds=3600,
    description="Check Azure Policy compliance for deployed resources",
)
async def run_periodic_policy_scan(
    tenant_id: str | None = None,
    project_id: str | None = None,
    **kwargs,
) -> dict:
    """Periodic task entry point invoked by the task scheduler."""
    if project_id is None:
        logger.info("Policy compliance scan skipped — no project_id provided")
        return {"message": "skipped", "reason": "no project_id"}

    result = await policy_monitor.check_compliance(
        project_id=project_id,
        tenant_id=tenant_id,
    )
    return {
        "message": "completed",
        "scan_id": result["id"],
        "status": result["status"],
        "total_resources": result["total_resources"],
        "non_compliant_count": result["non_compliant_count"],
    }
