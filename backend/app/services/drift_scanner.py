"""Configuration drift scanner — compares deployed Azure state against baselines.

Detects added, removed, and modified resources as well as policy violations.
In dev mode, returns mock state with controlled drift so the full scan flow
works without Azure credentials.
"""

import logging
from datetime import datetime, timezone

from app.config import settings
from app.models.base import generate_uuid
from app.services.event_stream import event_stream
from app.services.task_scheduler import task_scheduler

logger = logging.getLogger(__name__)

# ── Noise properties to ignore during comparison ─────────────────────────────

IGNORED_PROPERTIES: frozenset[str] = frozenset(
    {
        "etag",
        "provisioningState",
        "timestamp",
        "lastModifiedTime",
        "lastModifiedBy",
        "createdTime",
        "changedTime",
    }
)

# ── Security-sensitive resource types & property keywords ────────────────────

SECURITY_RESOURCE_TYPES: frozenset[str] = frozenset(
    {
        "Microsoft.Network/networkSecurityGroups",
        "Microsoft.Network/azureFirewalls",
        "Microsoft.Network/firewallPolicies",
        "Microsoft.KeyVault/vaults",
        "Microsoft.Sql/servers/firewallRules",
    }
)

SECURITY_PROPERTY_KEYWORDS: frozenset[str] = frozenset(
    {
        "securityRules",
        "encryption",
        "firewall",
        "networkAcls",
        "accessPolicies",
        "tlsVersion",
        "publicNetworkAccess",
        "httpsOnly",
        "enableRbacAuthorization",
    }
)


# ── Mock data helpers ────────────────────────────────────────────────────────

_BASE_SUB = "/subscriptions/00000000-0000-0000-0000-000000000001"


def _mock_baseline_resources() -> dict[str, dict]:
    """Return ~10 baseline resources keyed by Azure resource ID."""
    rg_app = f"{_BASE_SUB}/resourceGroups/rg-app-prod/providers"
    rg_data = f"{_BASE_SUB}/resourceGroups/rg-data-prod/providers"
    rg_net = f"{_BASE_SUB}/resourceGroups/rg-network-prod/providers"

    return {
        f"{rg_app}/Microsoft.Compute/virtualMachines/vm-web-01": {
            "resource_type": "Microsoft.Compute/virtualMachines",
            "location": "eastus2",
            "properties": {
                "vmSize": "Standard_D2s_v3",
                "osProfile": {"computerName": "vm-web-01"},
                "tags": {"env": "prod", "team": "platform"},
            },
        },
        f"{rg_app}/Microsoft.Compute/virtualMachines/vm-web-02": {
            "resource_type": "Microsoft.Compute/virtualMachines",
            "location": "eastus2",
            "properties": {
                "vmSize": "Standard_D2s_v3",
                "osProfile": {"computerName": "vm-web-02"},
                "tags": {"env": "prod", "team": "platform"},
            },
        },
        f"{rg_app}/Microsoft.Web/sites/app-api-prod": {
            "resource_type": "Microsoft.Web/sites",
            "location": "eastus2",
            "properties": {
                "httpsOnly": True,
                "siteConfig": {"minTlsVersion": "1.2"},
                "tags": {"env": "prod"},
            },
        },
        f"{rg_data}/Microsoft.Storage/storageAccounts/stproddata001": {
            "resource_type": "Microsoft.Storage/storageAccounts",
            "location": "eastus2",
            "properties": {
                "sku": "Standard_LRS",
                "encryption": {"services": {"blob": {"enabled": True}}},
                "networkAcls": {"defaultAction": "Deny"},
                "tags": {"env": "prod"},
            },
        },
        f"{rg_data}/Microsoft.Sql/servers/sql-prod-001": {
            "resource_type": "Microsoft.Sql/servers",
            "location": "eastus2",
            "properties": {
                "version": "12.0",
                "minimalTlsVersion": "1.2",
                "publicNetworkAccess": "Disabled",
                "tags": {"env": "prod"},
            },
        },
        f"{rg_net}/Microsoft.Network/networkSecurityGroups/nsg-app-prod": {
            "resource_type": "Microsoft.Network/networkSecurityGroups",
            "location": "eastus2",
            "properties": {
                "securityRules": [
                    {
                        "name": "AllowHTTPS",
                        "priority": 100,
                        "direction": "Inbound",
                        "access": "Allow",
                        "destinationPortRange": "443",
                        "sourceAddressPrefix": "Internet",
                    }
                ],
                "tags": {"env": "prod"},
            },
        },
        f"{rg_net}/Microsoft.Network/virtualNetworks/vnet-prod": {
            "resource_type": "Microsoft.Network/virtualNetworks",
            "location": "eastus2",
            "properties": {
                "addressSpace": {"addressPrefixes": ["10.0.0.0/16"]},
                "tags": {"env": "prod"},
            },
        },
        f"{rg_app}/Microsoft.KeyVault/vaults/kv-app-prod": {
            "resource_type": "Microsoft.KeyVault/vaults",
            "location": "eastus2",
            "properties": {
                "enableRbacAuthorization": True,
                "enableSoftDelete": True,
                "tags": {"env": "prod"},
            },
        },
        f"{rg_app}/Microsoft.Insights/components/ai-app-prod": {
            "resource_type": "Microsoft.Insights/components",
            "location": "eastus2",
            "properties": {
                "Application_Type": "web",
                "RetentionInDays": 90,
                "tags": {"env": "prod"},
            },
        },
        f"{rg_app}/Microsoft.ContainerRegistry/registries/crprodapp": {
            "resource_type": "Microsoft.ContainerRegistry/registries",
            "location": "eastus2",
            "properties": {
                "sku": "Standard",
                "adminUserEnabled": False,
                "tags": {"env": "prod"},
            },
        },
    }


def _mock_current_state() -> dict[str, dict]:
    """Return current state with controlled drift applied to baseline.

    Drift introduced:
    - 1 removed: vm-web-02 deleted
    - 1 added:   new redis cache not in baseline
    - 2 modified:
        1. NSG rule changed (security-relevant → high severity)
        2. Storage account tag changed (config → low severity)
    """
    resources = _mock_baseline_resources()

    # Remove vm-web-02
    rg_app = f"{_BASE_SUB}/resourceGroups/rg-app-prod/providers"
    rg_data = f"{_BASE_SUB}/resourceGroups/rg-data-prod/providers"
    rg_net = f"{_BASE_SUB}/resourceGroups/rg-network-prod/providers"

    del resources[f"{rg_app}/Microsoft.Compute/virtualMachines/vm-web-02"]

    # Add a new Redis cache
    resources[f"{rg_data}/Microsoft.Cache/redis/redis-prod-001"] = {
        "resource_type": "Microsoft.Cache/redis",
        "location": "eastus2",
        "properties": {
            "sku": {"name": "Standard", "family": "C", "capacity": 1},
            "enableNonSslPort": False,
            "tags": {"env": "prod"},
        },
    }

    # Modify NSG — add a risky rule (security-relevant = high severity)
    nsg_key = f"{rg_net}/Microsoft.Network/networkSecurityGroups/nsg-app-prod"
    resources[nsg_key] = {
        "resource_type": "Microsoft.Network/networkSecurityGroups",
        "location": "eastus2",
        "properties": {
            "securityRules": [
                {
                    "name": "AllowHTTPS",
                    "priority": 100,
                    "direction": "Inbound",
                    "access": "Allow",
                    "destinationPortRange": "443",
                    "sourceAddressPrefix": "Internet",
                },
                {
                    "name": "AllowSSH",
                    "priority": 200,
                    "direction": "Inbound",
                    "access": "Allow",
                    "destinationPortRange": "22",
                    "sourceAddressPrefix": "*",
                },
            ],
            "tags": {"env": "prod"},
        },
    }

    # Modify storage account tag (low severity)
    st_key = f"{rg_data}/Microsoft.Storage/storageAccounts/stproddata001"
    resources[st_key]["properties"]["tags"]["env"] = "staging"

    return resources


# ── Core comparison & severity logic ─────────────────────────────────────────


def _deep_diff(
    expected: dict, actual: dict, path: str = ""
) -> list[dict]:
    """Recursively compare two dicts, returning a list of change records.

    Each change record: {"path": "a.b.c", "expected": ..., "actual": ...}
    Ignores keys listed in ``IGNORED_PROPERTIES``.
    """
    changes: list[dict] = []
    all_keys = set(expected.keys()) | set(actual.keys())

    for key in sorted(all_keys):
        if key in IGNORED_PROPERTIES:
            continue

        full_path = f"{path}.{key}" if path else key
        exp_val = expected.get(key)
        act_val = actual.get(key)

        if exp_val == act_val:
            continue

        if isinstance(exp_val, dict) and isinstance(act_val, dict):
            changes.extend(_deep_diff(exp_val, act_val, full_path))
        else:
            changes.append(
                {"path": full_path, "expected": exp_val, "actual": act_val}
            )

    return changes


def _classify_severity(
    resource_type: str,
    drift_type: str,
    changes: list[dict] | None = None,
) -> str:
    """Assign a severity level based on resource type and change nature.

    Rules:
    - Removed resources are always at least ``medium``; security resources → ``high``.
    - Security resource types or property keywords → ``high`` (or ``critical``
      for NSG/firewall rule changes).
    - Tag/metadata-only changes → ``low``.
    - Everything else → ``medium``.
    """
    # Added resources default to medium
    if drift_type == "added":
        if resource_type in SECURITY_RESOURCE_TYPES:
            return "high"
        return "medium"

    # Removed resources
    if drift_type == "removed":
        if resource_type in SECURITY_RESOURCE_TYPES:
            return "high"
        return "medium"

    # Modified resources — inspect changes
    if changes:
        has_security_change = False
        has_non_tag_change = False
        for change in changes:
            path_lower = change["path"].lower()
            # Check if any changed property is security-related
            if any(kw.lower() in path_lower for kw in SECURITY_PROPERTY_KEYWORDS):
                has_security_change = True
            # Check if it's not just a tag/metadata change
            if "tags" not in path_lower:
                has_non_tag_change = True

        if has_security_change:
            # NSG / firewall rule changes are critical
            if resource_type in SECURITY_RESOURCE_TYPES:
                return "critical"
            return "high"

        if not has_non_tag_change:
            return "low"

    return "medium"


# ── DriftScanner class ───────────────────────────────────────────────────────


class DriftScanner:
    """Compares deployed Azure resource state against baselines.

    In production, queries Azure Resource Graph API.
    In dev mode, returns mock state with controlled drift.
    """

    async def get_current_state(
        self, project_id: str, subscription_id: str | None = None
    ) -> dict[str, dict]:
        """Fetch current Azure resource state for a project.

        In production, this would query Azure Resource Graph API.
        In dev mode, returns mock state with controlled drift.
        """
        if settings.is_dev_mode:
            logger.info(
                "Dev mode: returning mock current state for project %s",
                project_id,
            )
            return _mock_current_state()

        # Production: Azure Resource Graph query (future implementation)
        logger.warning(
            "Azure Resource Graph query not yet implemented for project %s",
            project_id,
        )
        return {}

    async def compare_resources(
        self,
        baseline_data: dict[str, dict],
        current_state: dict[str, dict],
    ) -> list[dict]:
        """Compare baseline resource snapshot against current state.

        Returns a list of drift event dicts (not yet persisted).
        Each dict contains: resource_id, resource_type, drift_type,
        severity, expected_value, actual_value.
        """
        events: list[dict] = []
        baseline_ids = set(baseline_data.keys())
        current_ids = set(current_state.keys())

        # Removed resources: in baseline but not in current state
        for rid in sorted(baseline_ids - current_ids):
            resource = baseline_data[rid]
            resource_type = resource.get("resource_type", "Unknown")
            severity = _classify_severity(resource_type, "removed")
            events.append(
                {
                    "resource_id": rid,
                    "resource_type": resource_type,
                    "drift_type": "removed",
                    "severity": severity,
                    "expected_value": resource,
                    "actual_value": None,
                }
            )

        # Added resources: in current state but not in baseline
        for rid in sorted(current_ids - baseline_ids):
            resource = current_state[rid]
            resource_type = resource.get("resource_type", "Unknown")
            severity = _classify_severity(resource_type, "added")
            events.append(
                {
                    "resource_id": rid,
                    "resource_type": resource_type,
                    "drift_type": "added",
                    "severity": severity,
                    "expected_value": None,
                    "actual_value": resource,
                }
            )

        # Modified resources: present in both, check for property differences
        for rid in sorted(baseline_ids & current_ids):
            expected = baseline_data[rid]
            actual = current_state[rid]
            resource_type = expected.get("resource_type", "Unknown")

            changes = _deep_diff(expected, actual)
            if changes:
                severity = _classify_severity(resource_type, "modified", changes)
                events.append(
                    {
                        "resource_id": rid,
                        "resource_type": resource_type,
                        "drift_type": "modified",
                        "severity": severity,
                        "expected_value": expected,
                        "actual_value": actual,
                        "changes": changes,
                    }
                )

        return events

    async def scan_project(
        self,
        project_id: str,
        tenant_id: str | None = None,
        db=None,
    ) -> dict:
        """Full drift scan for a project.

        1. Fetch active baseline (or create mock in dev mode).
        2. Fetch current Azure state.
        3. Compare and produce drift events.
        4. Persist DriftScanResult + DriftEvent records (if DB available).
        5. Publish SSE events for any drift detected.
        6. Return the scan result dict.
        """
        now = datetime.now(timezone.utc)
        scan_id = generate_uuid()

        logger.info("Starting drift scan %s for project %s", scan_id, project_id)

        # Step 1: Get the active baseline
        baseline_id, baseline_data = await self._get_active_baseline(
            project_id, db
        )

        # Step 2: Create the scan result record (status=running)
        scan_result = {
            "id": scan_id,
            "baseline_id": baseline_id,
            "project_id": project_id,
            "tenant_id": tenant_id,
            "scan_started_at": now,
            "scan_completed_at": None,
            "total_resources_scanned": 0,
            "drifted_count": 0,
            "new_count": 0,
            "removed_count": 0,
            "status": "running",
            "error_message": None,
        }

        if db is not None:
            await self._persist_scan_result(db, scan_result)

        try:
            # Step 3: Fetch current state
            current_state = await self.get_current_state(project_id)

            # Step 4: Compare
            drift_events = await self.compare_resources(baseline_data, current_state)

            # Step 5: Count results
            total_resources = len(set(baseline_data.keys()) | set(current_state.keys()))
            drifted = sum(1 for e in drift_events if e["drift_type"] == "modified")
            added = sum(1 for e in drift_events if e["drift_type"] == "added")
            removed = sum(1 for e in drift_events if e["drift_type"] == "removed")

            # Step 6: Persist events if DB available
            if db is not None:
                await self._persist_drift_events(
                    db, baseline_id, scan_id, drift_events
                )

            # Step 7: Update scan result
            completed_at = datetime.now(timezone.utc)
            scan_result.update(
                {
                    "scan_completed_at": completed_at,
                    "total_resources_scanned": total_resources,
                    "drifted_count": drifted,
                    "new_count": added,
                    "removed_count": removed,
                    "status": "completed",
                }
            )

            if db is not None:
                await self._update_scan_result(db, scan_id, scan_result)

            # Step 8: Publish SSE events for drift
            if drift_events:
                await event_stream.publish(
                    "drift_detected",
                    {
                        "scan_id": scan_id,
                        "project_id": project_id,
                        "total_drift_events": len(drift_events),
                        "drifted_count": drifted,
                        "new_count": added,
                        "removed_count": removed,
                        "severities": _severity_summary(drift_events),
                    },
                    project_id=project_id,
                    tenant_id=tenant_id,
                )

            logger.info(
                "Drift scan %s completed: %d resources scanned, %d events",
                scan_id,
                total_resources,
                len(drift_events),
            )

        except Exception as exc:
            logger.exception("Drift scan %s failed: %s", scan_id, exc)
            scan_result.update(
                {
                    "scan_completed_at": datetime.now(timezone.utc),
                    "status": "failed",
                    "error_message": str(exc),
                }
            )
            if db is not None:
                await self._update_scan_result(db, scan_id, scan_result)

        scan_result["events"] = drift_events if "drift_events" in dir() else []
        return scan_result

    # ── Private helpers ──────────────────────────────────────────────────

    async def _get_active_baseline(
        self, project_id: str, db=None
    ) -> tuple[str, dict[str, dict]]:
        """Return (baseline_id, baseline_data) for the project.

        If DB is available, query for the active baseline.
        Otherwise, return mock baseline data.
        """
        if db is not None:
            from sqlalchemy import select

            from app.models.drift import DriftBaseline

            result = await db.execute(
                select(DriftBaseline).where(
                    DriftBaseline.project_id == project_id,
                    DriftBaseline.status == "active",
                )
            )
            baseline = result.scalar_one_or_none()
            if baseline is not None:
                return baseline.id, baseline.baseline_data

        # Fallback: mock baseline
        mock_id = generate_uuid()
        return mock_id, _mock_baseline_resources()

    async def _persist_scan_result(self, db, scan_result: dict) -> None:
        """Insert a DriftScanResult row."""
        from app.models.drift import DriftScanResult

        row = DriftScanResult(
            id=scan_result["id"],
            baseline_id=scan_result["baseline_id"],
            project_id=scan_result["project_id"],
            tenant_id=scan_result["tenant_id"],
            scan_started_at=scan_result["scan_started_at"],
            status=scan_result["status"],
        )
        db.add(row)
        await db.flush()

    async def _persist_drift_events(
        self,
        db,
        baseline_id: str,
        scan_result_id: str,
        drift_events: list[dict],
    ) -> None:
        """Insert DriftEvent rows for each drift finding."""
        from app.models.drift import DriftEvent

        now = datetime.now(timezone.utc)
        for event in drift_events:
            row = DriftEvent(
                baseline_id=baseline_id,
                scan_result_id=scan_result_id,
                resource_type=event["resource_type"],
                resource_id=event["resource_id"],
                drift_type=event["drift_type"],
                expected_value=event.get("expected_value"),
                actual_value=event.get("actual_value"),
                severity=event["severity"],
                detected_at=now,
            )
            db.add(row)
        await db.flush()

    async def _update_scan_result(
        self, db, scan_id: str, scan_result: dict
    ) -> None:
        """Update a DriftScanResult row with final status."""
        from sqlalchemy import update

        from app.models.drift import DriftScanResult

        stmt = (
            update(DriftScanResult)
            .where(DriftScanResult.id == scan_id)
            .values(
                scan_completed_at=scan_result["scan_completed_at"],
                total_resources_scanned=scan_result["total_resources_scanned"],
                drifted_count=scan_result["drifted_count"],
                new_count=scan_result["new_count"],
                removed_count=scan_result["removed_count"],
                status=scan_result["status"],
                error_message=scan_result.get("error_message"),
            )
        )
        await db.execute(stmt)
        await db.flush()


def _severity_summary(events: list[dict]) -> dict[str, int]:
    """Aggregate severity counts from drift events."""
    summary: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for event in events:
        sev = event.get("severity", "medium")
        if sev in summary:
            summary[sev] += 1
    return summary


# ── Singleton & periodic task registration ───────────────────────────────────

drift_scanner = DriftScanner()


@task_scheduler.periodic(
    "drift_scan",
    interval_seconds=3600,
    description="Scan for configuration drift against baselines",
)
async def run_periodic_drift_scan(
    tenant_id: str | None = None,
    project_id: str | None = None,
    **kwargs,
) -> dict:
    """Periodic task entry point invoked by the task scheduler."""
    if project_id is None:
        logger.info("Drift scan skipped — no project_id provided")
        return {"message": "skipped", "reason": "no project_id"}

    result = await drift_scanner.scan_project(
        project_id=project_id,
        tenant_id=tenant_id,
    )
    return {
        "message": "completed",
        "scan_id": result["id"],
        "status": result["status"],
        "total_resources_scanned": result["total_resources_scanned"],
        "drifted_count": result["drifted_count"],
        "new_count": result["new_count"],
        "removed_count": result["removed_count"],
    }
