"""Drift notification service — evaluates scan results against rules and dispatches alerts.

Bridges the drift scanner with the notification delivery infrastructure.
In dev mode, notifications are logged instead of sent to external channels.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import settings
from app.schemas.drift_notification import SEVERITY_ORDER

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DriftNotificationService:
    """Evaluates drift findings against notification rules and dispatches alerts."""

    # -- severity helpers ---------------------------------------------------

    @staticmethod
    def check_severity_threshold(finding_severity: str, threshold: str) -> bool:
        """Return True if the finding severity meets or exceeds the threshold.

        E.g. threshold='high' → 'critical' and 'high' pass; 'medium'/'low' do not.
        """
        finding_rank = SEVERITY_ORDER.get(finding_severity.lower(), 0)
        threshold_rank = SEVERITY_ORDER.get(threshold.lower(), 0)
        return finding_rank >= threshold_rank

    # -- content formatting -------------------------------------------------

    @staticmethod
    def format_notification_content(
        scan_result: dict,
        findings: list[dict],
        project_name: str | None = None,
    ) -> dict[str, str]:
        """Build notification title + message from scan results.

        Returns {"title": ..., "message": ...}.
        """
        project_label = project_name or scan_result.get("project_id", "Unknown")
        total = len(findings)

        # Severity breakdown
        severity_counts: dict[str, int] = {
            "critical": 0, "high": 0, "medium": 0, "low": 0,
        }
        for f in findings:
            sev = f.get("severity", "low").lower()
            if sev in severity_counts:
                severity_counts[sev] += 1

        title = f"{total} drift finding{'s' if total != 1 else ''} detected in {project_label}"

        parts = [title]

        # Severity line
        severity_parts = []
        for sev in ("critical", "high", "medium", "low"):
            count = severity_counts[sev]
            if count > 0:
                severity_parts.append(f"{count} {sev.capitalize()}")
        if severity_parts:
            parts.append("Severity: " + ", ".join(severity_parts))

        # Top findings (up to 5)
        for f in findings[:5]:
            resource_type = f.get("resource_type", "unknown")
            resource_id = f.get("resource_id", "unknown")
            drift_type = f.get("drift_type", "modified")
            sev = f.get("severity", "low")
            parts.append(f"  • [{sev.upper()}] {resource_type} ({resource_id}) — {drift_type}")

        if total > 5:
            parts.append(f"  ... and {total - 5} more")

        parts.append(f"View details: /governance/drift/scan-results/{scan_result.get('id', '')}")

        message = "\n".join(parts)
        return {"title": title, "message": message}

    # -- main processing ----------------------------------------------------

    async def process_scan_results(
        self,
        db: AsyncSession | None,
        scan_result: dict,
        findings: list[dict],
        project_name: str | None = None,
    ) -> dict:
        """Evaluate findings against all matching rules and dispatch notifications.

        Returns a summary dict compatible with DriftNotificationSummary.
        """
        from app.schemas.drift_notification import DriftNotificationSummary

        scan_id = scan_result.get("id", "unknown")
        project_id = scan_result.get("project_id", "")

        summary = DriftNotificationSummary(
            scan_id=scan_id,
            total_findings=len(findings),
        )

        if not findings:
            logger.info("No drift findings for scan %s — skipping notifications", scan_id)
            return summary.model_dump()

        # Load matching rules
        rules = await self._load_rules(db, project_id)
        summary.rules_evaluated = len(rules)

        if not rules:
            logger.info("No notification rules for project %s", project_id)
            return summary.model_dump()

        for rule in rules:
            if not rule.get("enabled", True):
                continue

            threshold = rule.get("severity_threshold", "high")
            channels = rule.get("channels", ["in_app"])
            recipients = rule.get("recipients", [])

            # Filter findings by threshold
            matching_findings = [
                f for f in findings
                if self.check_severity_threshold(f.get("severity", "low"), threshold)
            ]

            if not matching_findings:
                continue

            summary.notified_findings = max(
                summary.notified_findings, len(matching_findings)
            )

            # Build content
            content = self.format_notification_content(
                scan_result, matching_findings, project_name
            )

            # Count by severity for this batch
            for f in matching_findings:
                sev = f.get("severity", "low").lower()
                summary.by_severity[sev] = summary.by_severity.get(sev, 0) + 1

            # Dispatch to each channel
            for channel in channels:
                try:
                    await self._send_via_channel(
                        db=db,
                        channel=channel,
                        content=content,
                        scan_result=scan_result,
                        recipients=recipients,
                        rule=rule,
                    )
                    summary.notifications_sent += 1
                    summary.by_channel[channel] = summary.by_channel.get(channel, 0) + 1
                except Exception as exc:
                    error_msg = f"Failed to send via {channel}: {exc}"
                    logger.error(error_msg)
                    summary.errors.append(error_msg)

        return summary.model_dump()

    # -- private helpers ----------------------------------------------------

    async def _load_rules(self, db: AsyncSession | None, project_id: str) -> list[dict]:
        """Load enabled notification rules for a project."""
        if db is None:
            logger.debug("No DB session — returning empty rules")
            return []

        try:
            from sqlalchemy import select

            from app.models.drift_notification_rule import DriftNotificationRule

            result = await db.execute(
                select(DriftNotificationRule).where(
                    DriftNotificationRule.project_id == project_id,
                    DriftNotificationRule.enabled.is_(True),
                )
            )
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "project_id": r.project_id,
                    "tenant_id": r.tenant_id,
                    "severity_threshold": r.severity_threshold,
                    "channels": r.channels or ["in_app"],
                    "recipients": r.recipients or [],
                    "enabled": r.enabled,
                }
                for r in rows
            ]
        except Exception as exc:
            logger.warning("Could not load notification rules: %s", exc)
            return []

    async def _send_via_channel(
        self,
        *,
        db: AsyncSession | None,
        channel: str,
        content: dict[str, str],
        scan_result: dict,
        recipients: list[str],
        rule: dict,
    ) -> None:
        """Send a notification through the specified channel."""
        from app.services.notification_service import notification_service

        tenant_id = scan_result.get("tenant_id") or rule.get("tenant_id")
        project_id = scan_result.get("project_id")

        # Determine the highest severity in the scan for the notification record
        severity = "info"
        for sev in ("critical", "high", "medium", "low"):
            if sev in content.get("message", "").lower():
                severity = sev
                break

        if settings.is_dev_mode and db is None:
            logger.info(
                "DEV DRIFT NOTIFICATION [%s] — %s: %s",
                channel, content["title"], content["message"][:200],
            )
            return

        if db is None:
            logger.info("No DB — drift notification logged only: %s", content["title"])
            return

        await notification_service.send(
            db,
            notification_type="drift_detected",
            title=content["title"],
            message=content["message"],
            severity=severity,
            tenant_id=tenant_id,
            project_id=project_id,
            channel=channel,
            user_ids=None,
        )


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
drift_notification_service = DriftNotificationService()
