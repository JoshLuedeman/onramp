"""Drift remediation service — accept, revert, or suppress drift findings.

Generates remediation recommendations and tracks audit history.
In dev mode returns mock remediation results without Azure calls.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import generate_uuid
from app.models.drift import DriftEvent
from app.models.drift_remediation import DriftRemediation
from app.schemas.drift_remediation import (
    BatchRemediationResponse,
    RemediationAuditEntry,
    RemediationAuditLog,
    RemediationResponse,
)

logger = logging.getLogger(__name__)


class DriftRemediator:
    """Generates and applies remediation actions for drift findings."""

    # ── Single finding remediation ───────────────────────────────────────

    async def remediate_finding(
        self,
        finding_id: str,
        action: str,
        actor: str,
        justification: str | None = None,
        expiration_days: int | None = None,
        db: AsyncSession | None = None,
    ) -> RemediationResponse:
        """Remediate a single drift finding.

        Args:
            finding_id: ID of the DriftEvent to remediate.
            action: One of "accept", "revert", "suppress".
            actor: Username of the person performing the action.
            justification: Optional reason for the action.
            expiration_days: For suppress, optional expiry (30/60/90 or None).
            db: Database session (None in dev mode).

        Returns:
            RemediationResponse with the action result.
        """
        now = datetime.now(timezone.utc)
        remediation_id = generate_uuid()

        # Build result details based on action type
        result_details = await self._build_result_details(
            finding_id, action, expiration_days, db
        )

        # Persist if DB available
        if db is not None:
            remediation = DriftRemediation(
                id=remediation_id,
                finding_id=finding_id,
                action=action,
                status="completed",
                actor=actor,
                justification=justification,
                expiration_days=expiration_days,
                result_details=result_details,
            )
            db.add(remediation)

            # Update the drift event resolution
            await self._resolve_drift_event(db, finding_id, action, now)

            await db.flush()

            logger.info(
                "Remediation %s applied: %s on finding %s by %s",
                remediation_id,
                action,
                finding_id,
                actor,
            )

        return RemediationResponse(
            id=remediation_id,
            finding_id=finding_id,
            action=action,
            status="completed",
            result_details=result_details,
            created_at=now,
        )

    # ── Batch remediation ────────────────────────────────────────────────

    async def remediate_batch(
        self,
        finding_ids: list[str],
        action: str,
        actor: str,
        justification: str | None = None,
        expiration_days: int | None = None,
        db: AsyncSession | None = None,
    ) -> BatchRemediationResponse:
        """Remediate multiple drift findings with the same action."""
        results: list[RemediationResponse] = []
        succeeded = 0
        failed = 0

        for finding_id in finding_ids:
            try:
                result = await self.remediate_finding(
                    finding_id=finding_id,
                    action=action,
                    actor=actor,
                    justification=justification,
                    expiration_days=expiration_days,
                    db=db,
                )
                results.append(result)
                succeeded += 1
            except Exception:
                logger.exception("Failed to remediate finding %s", finding_id)
                now = datetime.now(timezone.utc)
                results.append(
                    RemediationResponse(
                        id=generate_uuid(),
                        finding_id=finding_id,
                        action=action,
                        status="failed",
                        result_details={"error": f"Remediation failed for {finding_id}"},
                        created_at=now,
                    )
                )
                failed += 1

        return BatchRemediationResponse(
            results=results,
            total=len(finding_ids),
            succeeded=succeeded,
            failed=failed,
        )

    # ── Lookup ───────────────────────────────────────────────────────────

    async def get_remediation(
        self,
        remediation_id: str,
        db: AsyncSession | None = None,
    ) -> RemediationResponse | None:
        """Retrieve a remediation by ID."""
        if db is None:
            return None

        result = await db.execute(
            select(DriftRemediation).where(DriftRemediation.id == remediation_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        return RemediationResponse(
            id=row.id,
            finding_id=row.finding_id,
            action=row.action,
            status=row.status,
            result_details=row.result_details or {},
            created_at=row.created_at,
        )

    # ── Audit history ────────────────────────────────────────────────────

    async def get_remediation_history(
        self,
        db: AsyncSession | None = None,
    ) -> RemediationAuditLog:
        """Return the full remediation audit log."""
        if db is None:
            return RemediationAuditLog(entries=[], total=0)

        result = await db.execute(
            select(DriftRemediation).order_by(DriftRemediation.created_at.desc())
        )
        rows = result.scalars().all()

        entries = [
            RemediationAuditEntry(
                id=row.id,
                actor=row.actor,
                action=row.action,
                finding_id=row.finding_id,
                justification=row.justification,
                timestamp=row.created_at,
            )
            for row in rows
        ]

        return RemediationAuditLog(entries=entries, total=len(entries))

    # ── Private helpers ──────────────────────────────────────────────────

    async def _build_result_details(
        self,
        finding_id: str,
        action: str,
        expiration_days: int | None,
        db: AsyncSession | None,
    ) -> dict:
        """Generate action-specific result details."""
        if action == "accept":
            return self._accept_details(finding_id)
        elif action == "revert":
            return self._revert_details(finding_id)
        elif action == "suppress":
            return self._suppress_details(finding_id, expiration_days)
        return {}

    def _accept_details(self, finding_id: str) -> dict:
        """Accept drift: generate updated IaC reflecting actual state."""
        return {
            "action": "accept",
            "description": "Drift accepted — baseline will be updated to reflect actual state.",
            "iac_update": {
                "type": "bicep_parameter_override",
                "finding_id": finding_id,
                "recommendation": "Update the Bicep parameter file to match the current deployed value.",
            },
        }

    def _revert_details(self, finding_id: str) -> dict:
        """Revert drift: generate a redeployment plan to restore desired state."""
        return {
            "action": "revert",
            "description": "Revert to desired state — a redeployment will restore the baseline configuration.",
            "redeployment_plan": {
                "finding_id": finding_id,
                "steps": [
                    "Validate current Bicep templates match baseline.",
                    "Run incremental deployment targeting drifted resource.",
                    "Verify post-deployment state matches expected baseline.",
                ],
                "estimated_impact": "low",
            },
        }

    def _suppress_details(self, finding_id: str, expiration_days: int | None) -> dict:
        """Suppress drift: mark as intentional deviation."""
        now = datetime.now(timezone.utc)
        expires_at = None
        if expiration_days is not None:
            expires_at = (now + timedelta(days=expiration_days)).isoformat()

        return {
            "action": "suppress",
            "description": "Drift suppressed — marked as intentional deviation.",
            "suppression": {
                "finding_id": finding_id,
                "expiration_days": expiration_days,
                "expires_at": expires_at,
                "permanent": expiration_days is None,
            },
        }

    async def _resolve_drift_event(
        self,
        db: AsyncSession,
        finding_id: str,
        action: str,
        resolved_at: datetime,
    ) -> None:
        """Mark the drift event as resolved."""
        result = await db.execute(
            select(DriftEvent).where(DriftEvent.id == finding_id)
        )
        event = result.scalar_one_or_none()
        if event is not None:
            event.resolved_at = resolved_at
            event.resolution_type = action


# ── Singleton ────────────────────────────────────────────────────────────────

drift_remediator = DriftRemediator()
