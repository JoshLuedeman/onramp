"""Remediation approval workflow service.

Manages the lifecycle of approval requests — from creation through
review (approve / reject) and expiration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.models.base import generate_uuid

logger = logging.getLogger(__name__)

# Default expiration for approval requests (72 hours)
DEFAULT_EXPIRY_HOURS = 72


class ApprovalService:
    """Singleton service for remediation approval workflows."""

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_request(
        self,
        request_type: str,
        resource_id: str,
        details: dict,
        requester: str,
        project_id: str | None = None,
        tenant_id: str | None = None,
        db: Any | None = None,
    ) -> dict:
        """Create a new pending approval request."""
        now = datetime.now(timezone.utc)
        request_id = generate_uuid()
        expires_at = now + timedelta(hours=DEFAULT_EXPIRY_HOURS)

        request_data = {
            "id": request_id,
            "request_type": request_type,
            "resource_id": resource_id,
            "requested_by": requester,
            "requested_at": now,
            "status": "pending",
            "reviewer": None,
            "reviewed_at": None,
            "review_reason": None,
            "details": details,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "expires_at": expires_at,
            "created_at": now,
            "updated_at": now,
        }

        if db is not None:
            from app.models.approval import ApprovalRequest

            row = ApprovalRequest(
                id=request_id,
                request_type=request_type,
                resource_id=resource_id,
                requested_by=requester,
                requested_at=now,
                status="pending",
                details=details,
                tenant_id=tenant_id,
                project_id=project_id,
                expires_at=expires_at,
            )
            db.add(row)
            await db.flush()
            await db.refresh(row)
            request_data = _row_to_dict(row)

        # Publish SSE event
        await self._publish_event("approval_requested", {
            "request_id": request_id,
            "type": request_type,
            "resource_id": resource_id,
            "requester": requester,
        })

        logger.info(
            "Approval request created: id=%s type=%s resource=%s",
            request_id, request_type, resource_id,
        )
        return request_data

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    async def review_request(
        self,
        request_id: str,
        decision: str,
        reviewer: str,
        reason: str = "",
        db: Any | None = None,
    ) -> dict | None:
        """Approve or reject an existing approval request."""
        now = datetime.now(timezone.utc)

        if db is not None:
            from sqlalchemy import select

            from app.models.approval import ApprovalRequest

            result = await db.execute(
                select(ApprovalRequest).where(ApprovalRequest.id == request_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            if row.status != "pending":
                return _row_to_dict(row)

            row.status = decision
            row.reviewer = reviewer
            row.reviewed_at = now
            row.review_reason = reason
            await db.flush()
            await db.refresh(row)

            await self._publish_event("approval_decided", {
                "request_id": request_id,
                "decision": decision,
                "reviewer": reviewer,
            })
            return _row_to_dict(row)

        # Dev mode mock
        await self._publish_event("approval_decided", {
            "request_id": request_id,
            "decision": decision,
            "reviewer": reviewer,
        })
        return {
            "id": request_id,
            "request_type": "drift_remediation",
            "resource_id": "mock-resource",
            "requested_by": "mock-user",
            "requested_at": now,
            "status": decision,
            "reviewer": reviewer,
            "reviewed_at": now,
            "review_reason": reason,
            "details": {},
            "tenant_id": None,
            "project_id": None,
            "expires_at": None,
            "created_at": now,
            "updated_at": now,
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_pending_requests(
        self,
        project_id: str | None = None,
        tenant_id: str | None = None,
        db: Any | None = None,
    ) -> list[dict]:
        """List pending approval requests filtered by project/tenant."""
        if db is not None:
            from sqlalchemy import select

            from app.models.approval import ApprovalRequest

            stmt = (
                select(ApprovalRequest)
                .where(ApprovalRequest.status == "pending")
                .order_by(ApprovalRequest.requested_at.desc())
            )
            if project_id:
                stmt = stmt.where(ApprovalRequest.project_id == project_id)
            if tenant_id:
                stmt = stmt.where(ApprovalRequest.tenant_id == tenant_id)

            result = await db.execute(stmt)
            return [_row_to_dict(r) for r in result.scalars().all()]

        return []

    async def get_request(
        self,
        request_id: str,
        db: Any | None = None,
    ) -> dict | None:
        """Get a single approval request by ID."""
        if db is not None:
            from sqlalchemy import select

            from app.models.approval import ApprovalRequest

            result = await db.execute(
                select(ApprovalRequest).where(ApprovalRequest.id == request_id)
            )
            row = result.scalar_one_or_none()
            return _row_to_dict(row) if row else None

        return None

    async def get_requests(
        self,
        status: str | None = None,
        project_id: str | None = None,
        tenant_id: str | None = None,
        db: Any | None = None,
    ) -> list[dict]:
        """List approval requests with optional filters."""
        if db is not None:
            from sqlalchemy import select

            from app.models.approval import ApprovalRequest

            stmt = select(ApprovalRequest).order_by(
                ApprovalRequest.requested_at.desc()
            )
            if status:
                stmt = stmt.where(ApprovalRequest.status == status)
            if project_id:
                stmt = stmt.where(ApprovalRequest.project_id == project_id)
            if tenant_id:
                stmt = stmt.where(ApprovalRequest.tenant_id == tenant_id)

            result = await db.execute(stmt)
            return [_row_to_dict(r) for r in result.scalars().all()]

        return []

    async def get_pending_count(
        self,
        project_id: str | None = None,
        tenant_id: str | None = None,
        db: Any | None = None,
    ) -> int:
        """Return count of pending approval requests."""
        if db is not None:
            from sqlalchemy import func, select

            from app.models.approval import ApprovalRequest

            stmt = select(func.count()).select_from(ApprovalRequest).where(
                ApprovalRequest.status == "pending"
            )
            if project_id:
                stmt = stmt.where(ApprovalRequest.project_id == project_id)
            if tenant_id:
                stmt = stmt.where(ApprovalRequest.tenant_id == tenant_id)

            result = await db.execute(stmt)
            return result.scalar_one()

        return 0

    # ------------------------------------------------------------------
    # Expiration
    # ------------------------------------------------------------------

    async def check_expired(self, db: Any | None = None) -> int:
        """Auto-expire old requests. Returns count of expired requests."""
        now = datetime.now(timezone.utc)

        if db is not None:
            from sqlalchemy import update

            from app.models.approval import ApprovalRequest

            stmt = (
                update(ApprovalRequest)
                .where(
                    ApprovalRequest.status == "pending",
                    ApprovalRequest.expires_at <= now,
                )
                .values(status="expired", reviewed_at=now)
            )
            result = await db.execute(stmt)
            await db.flush()
            expired_count = result.rowcount
            logger.info("Expired %d approval requests", expired_count)
            return expired_count

        return 0

    # ------------------------------------------------------------------
    # SSE helper
    # ------------------------------------------------------------------

    async def _publish_event(self, event_type: str, data: dict) -> None:
        """Publish an SSE event (best-effort)."""
        try:
            from app.services.event_stream import event_stream

            await event_stream.publish(event_type, data)
        except Exception:
            logger.debug("SSE publish failed for %s", event_type)


def _row_to_dict(row: Any) -> dict:
    """Convert an ApprovalRequest ORM object to a dict."""
    return {
        "id": row.id,
        "request_type": row.request_type,
        "resource_id": row.resource_id,
        "requested_by": row.requested_by,
        "requested_at": row.requested_at,
        "status": row.status,
        "reviewer": row.reviewer,
        "reviewed_at": row.reviewed_at,
        "review_reason": row.review_reason,
        "details": row.details,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "expires_at": row.expires_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


# Singleton
approval_service = ApprovalService()
