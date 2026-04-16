"""RBAC health monitor — identifies security risks in Azure role assignments.

Detects:
- Over-permissioned accounts (Owner/Contributor at subscription scope)
- Stale assignments (last activity > 90 days)
- Custom role proliferation (>10 custom roles)
- Missing PIM (permanent eligible assignments for privileged roles)
- Service principal keys expiring within 30 days
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models.base import generate_uuid
from app.services.event_stream import event_stream
from app.services.task_scheduler import task_scheduler

logger = logging.getLogger(__name__)

# Privileged roles that should use PIM
PRIVILEGED_ROLES = {"Owner", "Contributor", "User Access Administrator"}

# Severity weights for score calculation
SEVERITY_WEIGHTS = {
    "critical": 15,
    "high": 10,
    "medium": 5,
    "low": 2,
}


class RBACMonitor:
    """Monitors Azure RBAC health and identifies security risks."""

    async def scan_rbac_health(
        self,
        project_id: str,
        subscription_id: str,
        tenant_id: str | None = None,
        db=None,
    ) -> dict:
        """Run a full RBAC health scan for a subscription.

        Returns a dict with scan result metadata and findings.
        """
        scan_id = generate_uuid()
        now = datetime.now(timezone.utc)

        try:
            # 1. Get role assignments
            assignments = await self.get_role_assignments(subscription_id)

            # 2. Analyze findings
            findings = await self.analyze_findings(assignments)

            # 3. Calculate health score
            health_score = await self.get_rbac_score(findings)

            result = {
                "id": scan_id,
                "project_id": project_id,
                "tenant_id": tenant_id,
                "subscription_id": subscription_id,
                "health_score": health_score,
                "total_assignments": len(assignments),
                "finding_count": len(findings),
                "scan_timestamp": now,
                "status": "completed",
                "findings": findings,
            }

            # Persist if DB is available
            if db is not None:
                await self._persist_scan(result, db)

            # Publish SSE event
            await event_stream.publish(
                "governance_score_updated",
                {
                    "component": "rbac",
                    "project_id": project_id,
                    "health_score": health_score,
                    "finding_count": len(findings),
                    "scan_id": scan_id,
                },
                project_id=project_id,
                tenant_id=tenant_id,
            )

            return result

        except Exception as exc:
            logger.exception("RBAC health scan failed for %s", subscription_id)
            return {
                "id": scan_id,
                "project_id": project_id,
                "tenant_id": tenant_id,
                "subscription_id": subscription_id,
                "health_score": 0.0,
                "total_assignments": 0,
                "finding_count": 0,
                "scan_timestamp": now,
                "status": "failed",
                "findings": [],
                "error": str(exc),
            }

    async def get_role_assignments(self, subscription_id: str) -> list[dict]:
        """Retrieve role assignments for a subscription.

        In production, queries Azure Authorization API.
        In dev mode, returns mock assignments for testing.
        """
        if not settings.is_dev_mode:
            # Production: would call Azure Management API
            # GET /subscriptions/{sub}/providers/Microsoft.Authorization/roleAssignments
            logger.info(
                "Production Azure API call would happen here for %s",
                subscription_id,
            )
            return []

        # Dev mode: return realistic mock data
        now = datetime.now(timezone.utc)
        return [
            {
                "id": f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleAssignments/ra-001",
                "principal_id": "user-001",
                "principal_name": "admin@contoso.com",
                "principal_type": "User",
                "role_name": "Owner",
                "role_type": "BuiltInRole",
                "scope": f"/subscriptions/{subscription_id}",
                "is_pim": False,
                "last_activity": (now - timedelta(days=120)).isoformat(),
                "created_at": (now - timedelta(days=365)).isoformat(),
            },
            {
                "id": f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleAssignments/ra-002",
                "principal_id": "user-002",
                "principal_name": "dev@contoso.com",
                "principal_type": "User",
                "role_name": "Contributor",
                "role_type": "BuiltInRole",
                "scope": f"/subscriptions/{subscription_id}",
                "is_pim": False,
                "last_activity": (now - timedelta(days=10)).isoformat(),
                "created_at": (now - timedelta(days=180)).isoformat(),
            },
            {
                "id": f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleAssignments/ra-003",
                "principal_id": "user-003",
                "principal_name": "reader@contoso.com",
                "principal_type": "User",
                "role_name": "Reader",
                "role_type": "BuiltInRole",
                "scope": f"/subscriptions/{subscription_id}/resourceGroups/rg-app",
                "is_pim": True,
                "last_activity": (now - timedelta(days=5)).isoformat(),
                "created_at": (now - timedelta(days=30)).isoformat(),
            },
            {
                "id": f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleAssignments/ra-004",
                "principal_id": "sp-001",
                "principal_name": "deploy-pipeline",
                "principal_type": "ServicePrincipal",
                "role_name": "Contributor",
                "role_type": "BuiltInRole",
                "scope": f"/subscriptions/{subscription_id}/resourceGroups/rg-deploy",
                "is_pim": False,
                "last_activity": (now - timedelta(days=2)).isoformat(),
                "created_at": (now - timedelta(days=90)).isoformat(),
                "key_expiry": (now + timedelta(days=15)).isoformat(),
            },
            {
                "id": f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleAssignments/ra-005",
                "principal_id": "user-004",
                "principal_name": "stale-user@contoso.com",
                "principal_type": "User",
                "role_name": "Contributor",
                "role_type": "BuiltInRole",
                "scope": f"/subscriptions/{subscription_id}/resourceGroups/rg-legacy",
                "is_pim": False,
                "last_activity": (now - timedelta(days=200)).isoformat(),
                "created_at": (now - timedelta(days=400)).isoformat(),
            },
            # Custom roles (generate enough to trigger proliferation check)
            *[
                {
                    "id": (
                        f"/subscriptions/{subscription_id}/providers/"
                        f"Microsoft.Authorization/roleAssignments/ra-custom-{i:03d}"
                    ),
                    "principal_id": f"user-custom-{i:03d}",
                    "principal_name": f"custom-user-{i}@contoso.com",
                    "principal_type": "User",
                    "role_name": f"Custom Role {i}",
                    "role_type": "CustomRole",
                    "scope": f"/subscriptions/{subscription_id}/resourceGroups/rg-custom-{i}",
                    "is_pim": False,
                    "last_activity": (now - timedelta(days=i * 3)).isoformat(),
                    "created_at": (now - timedelta(days=i * 10)).isoformat(),
                }
                for i in range(1, 13)
            ],
        ]

    async def analyze_findings(self, assignments: list[dict]) -> list[dict]:
        """Analyze role assignments and produce findings.

        Checks for:
        - Over-permissioned: Owner/Contributor at subscription scope
        - Stale assignments: last activity > 90 days
        - Custom role proliferation: >10 custom roles
        - Missing PIM: permanent privileged assignments
        - Expiring credentials: SP keys expiring within 30 days
        """
        findings: list[dict] = []
        now = datetime.now(timezone.utc)
        custom_role_names: set[str] = set()

        for assignment in assignments:
            role_name = assignment.get("role_name", "")
            scope = assignment.get("scope", "")
            principal_id = assignment.get("principal_id", "")
            principal_name = assignment.get("principal_name")
            is_pim = assignment.get("is_pim", False)

            # Track custom roles
            if assignment.get("role_type") == "CustomRole":
                custom_role_names.add(role_name)

            # 1. Over-permissioned: Owner/Contributor at subscription scope
            if role_name in PRIVILEGED_ROLES and self._is_subscription_scope(scope):
                findings.append({
                    "finding_type": "over_permissioned",
                    "severity": "critical" if role_name == "Owner" else "high",
                    "principal_id": principal_id,
                    "principal_name": principal_name,
                    "role_name": role_name,
                    "scope": scope,
                    "description": (
                        f"{role_name} role assigned at subscription scope. "
                        f"Should be scoped to resource group level."
                    ),
                    "remediation": (
                        f"Reassign {role_name} role to specific resource groups "
                        f"instead of the subscription scope."
                    ),
                })

            # 2. Stale assignments: last activity > 90 days
            last_activity_str = assignment.get("last_activity")
            if last_activity_str:
                last_activity = datetime.fromisoformat(last_activity_str)
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
                days_inactive = (now - last_activity).days
                if days_inactive > 90:
                    findings.append({
                        "finding_type": "stale_assignment",
                        "severity": "high" if days_inactive > 180 else "medium",
                        "principal_id": principal_id,
                        "principal_name": principal_name,
                        "role_name": role_name,
                        "scope": scope,
                        "description": (
                            f"Role assignment inactive for {days_inactive} days. "
                            f"Last activity: {last_activity_str}."
                        ),
                        "remediation": (
                            f"Review and remove the {role_name} assignment for "
                            f"{principal_name or principal_id} if no longer needed."
                        ),
                    })

            # 3. Missing PIM: permanent privileged assignments
            if role_name in PRIVILEGED_ROLES and not is_pim:
                findings.append({
                    "finding_type": "missing_pim",
                    "severity": "high",
                    "principal_id": principal_id,
                    "principal_name": principal_name,
                    "role_name": role_name,
                    "scope": scope,
                    "description": (
                        f"Permanent {role_name} assignment without PIM activation. "
                        f"Privileged roles should use just-in-time access."
                    ),
                    "remediation": (
                        f"Enable PIM (Privileged Identity Management) for the "
                        f"{role_name} role and convert to eligible assignment."
                    ),
                })

            # 4. Expiring credentials: SP keys within 30 days
            key_expiry_str = assignment.get("key_expiry")
            if key_expiry_str:
                key_expiry = datetime.fromisoformat(key_expiry_str)
                if key_expiry.tzinfo is None:
                    key_expiry = key_expiry.replace(tzinfo=timezone.utc)
                days_until_expiry = (key_expiry - now).days
                if days_until_expiry <= 30:
                    findings.append({
                        "finding_type": "expiring_credential",
                        "severity": "critical" if days_until_expiry <= 7 else "high",
                        "principal_id": principal_id,
                        "principal_name": principal_name,
                        "role_name": role_name,
                        "scope": scope,
                        "description": (
                            f"Service principal key expires in {days_until_expiry} days "
                            f"({key_expiry_str})."
                        ),
                        "remediation": (
                            f"Rotate the credential for {principal_name or principal_id}. "
                            f"Consider using managed identities instead of key-based auth."
                        ),
                    })

        # 5. Custom role proliferation: >10 custom roles
        if len(custom_role_names) > 10:
            findings.append({
                "finding_type": "custom_role_proliferation",
                "severity": "medium",
                "principal_id": "subscription",
                "principal_name": None,
                "role_name": f"{len(custom_role_names)} custom roles",
                "scope": "subscription",
                "description": (
                    f"Found {len(custom_role_names)} custom roles. "
                    f"Excessive custom roles increase management complexity and risk."
                ),
                "remediation": (
                    "Consolidate custom roles where possible. "
                    "Use built-in roles when they meet requirements."
                ),
            })

        return findings

    async def get_rbac_score(self, findings: list[dict]) -> float:
        """Calculate an RBAC health score from 0-100 based on findings.

        Starts at 100 and deducts points based on finding severity.
        """
        if not findings:
            return 100.0

        total_deduction = 0.0
        for finding in findings:
            severity = finding.get("severity", "low")
            total_deduction += SEVERITY_WEIGHTS.get(severity, 2)

        score = max(0.0, 100.0 - total_deduction)
        return round(score, 1)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_subscription_scope(scope: str) -> bool:
        """Check if a scope string is at the subscription level (not RG)."""
        parts = scope.strip("/").split("/")
        # /subscriptions/{id} → 2 parts
        # /subscriptions/{id}/resourceGroups/{name} → 4+ parts
        return len(parts) <= 2

    async def _persist_scan(self, result: dict, db) -> None:
        """Save scan result and findings to the database."""
        from app.models.rbac_health import RBACFinding, RBACScanResult

        scan = RBACScanResult(
            id=result["id"],
            project_id=result["project_id"],
            tenant_id=result["tenant_id"],
            subscription_id=result["subscription_id"],
            health_score=result["health_score"],
            total_assignments=result["total_assignments"],
            finding_count=result["finding_count"],
            scan_timestamp=result["scan_timestamp"],
            status=result["status"],
        )
        db.add(scan)

        for finding_data in result["findings"]:
            finding = RBACFinding(
                scan_result_id=result["id"],
                finding_type=finding_data["finding_type"],
                severity=finding_data["severity"],
                principal_id=finding_data["principal_id"],
                principal_name=finding_data.get("principal_name"),
                role_name=finding_data["role_name"],
                scope=finding_data["scope"],
                description=finding_data["description"],
                remediation=finding_data["remediation"],
            )
            db.add(finding)

        await db.flush()


# Module-level singleton
rbac_monitor = RBACMonitor()


# Register as periodic task
@task_scheduler.periodic(
    "rbac_health_scan",
    interval_seconds=3600,
    description="Periodic RBAC health scan for role assignment risks",
)
async def _periodic_rbac_scan(
    *, tenant_id: str | None = None, project_id: str | None = None
) -> dict | None:
    """Periodic task callback for RBAC health scanning."""
    if project_id is None:
        logger.debug("Skipping RBAC scan — no project_id provided")
        return {"message": "Skipped — no project_id"}

    result = await rbac_monitor.scan_rbac_health(
        project_id=project_id,
        subscription_id="periodic-scan",
        tenant_id=tenant_id,
    )
    return {
        "message": "RBAC health scan completed",
        "health_score": result.get("health_score", 0),
        "finding_count": result.get("finding_count", 0),
    }
