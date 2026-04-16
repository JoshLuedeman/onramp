"""Enterprise audit logging service — append-only event store."""

import csv
import io
import json
import logging
from datetime import datetime

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise_audit import EnterpriseAuditEvent

logger = logging.getLogger(__name__)

# HTTP method → CRUD action mapping
_METHOD_ACTION: dict[str, str] = {
    "POST": "create",
    "GET": "read",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


class AuditService:
    """Singleton service for enterprise audit event management."""

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def log_event(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        actor_id: str | None = None,
        tenant_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str = "create",
        details: dict | None = None,
        request: Request | None = None,
    ) -> EnterpriseAuditEvent:
        """Append a new audit event."""
        ip_address: str | None = None
        user_agent: str | None = None
        if request is not None:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                ip_address = forwarded.split(",")[0].strip()
            elif request.client:
                ip_address = request.client.host
            user_agent = request.headers.get("user-agent")

        event = EnterpriseAuditEvent(
            event_type=event_type,
            actor_id=actor_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(event)
        await db.flush()
        logger.info(
            "Audit event: type=%s action=%s actor=%s resource=%s/%s",
            event_type, action, actor_id, resource_type, resource_id,
        )
        return event

    # ------------------------------------------------------------------
    # Read / Query
    # ------------------------------------------------------------------

    async def query_events(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Query audit events with optional filters + pagination."""
        stmt = select(EnterpriseAuditEvent)
        count_stmt = select(func.count(EnterpriseAuditEvent.id))

        if tenant_id is not None:
            stmt = stmt.where(
                EnterpriseAuditEvent.tenant_id == tenant_id,
            )
            count_stmt = count_stmt.where(
                EnterpriseAuditEvent.tenant_id == tenant_id,
            )
        if actor_id is not None:
            stmt = stmt.where(
                EnterpriseAuditEvent.actor_id == actor_id,
            )
            count_stmt = count_stmt.where(
                EnterpriseAuditEvent.actor_id == actor_id,
            )
        if resource_type is not None:
            stmt = stmt.where(
                EnterpriseAuditEvent.resource_type == resource_type,
            )
            count_stmt = count_stmt.where(
                EnterpriseAuditEvent.resource_type == resource_type,
            )
        if action is not None:
            stmt = stmt.where(
                EnterpriseAuditEvent.action == action,
            )
            count_stmt = count_stmt.where(
                EnterpriseAuditEvent.action == action,
            )
        if start_date is not None:
            stmt = stmt.where(
                EnterpriseAuditEvent.timestamp >= start_date,
            )
            count_stmt = count_stmt.where(
                EnterpriseAuditEvent.timestamp >= start_date,
            )
        if end_date is not None:
            stmt = stmt.where(
                EnterpriseAuditEvent.timestamp <= end_date,
            )
            count_stmt = count_stmt.where(
                EnterpriseAuditEvent.timestamp <= end_date,
            )

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.order_by(
            EnterpriseAuditEvent.timestamp.desc(),
        ).offset(offset).limit(page_size)

        result = await db.execute(stmt)
        events = list(result.scalars().all())

        return {
            "events": [self._event_to_dict(e) for e in events],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_events(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
        fmt: str = "json",
        actor_id: str | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> str:
        """Export filtered events as JSON or CSV string."""
        # Re-use query_events with a large page to grab everything
        data = await self.query_events(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            resource_type=resource_type,
            action=action,
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=10000,
        )
        events = data["events"]

        if fmt == "csv":
            return self._events_to_csv(events)
        return json.dumps(events, default=str)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _event_to_dict(event: EnterpriseAuditEvent) -> dict:
        return {
            "id": event.id,
            "event_type": event.event_type,
            "actor_id": event.actor_id,
            "tenant_id": event.tenant_id,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "action": event.action,
            "details": event.details,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "timestamp": (
                event.timestamp.isoformat() if event.timestamp else None
            ),
        }

    @staticmethod
    def _events_to_csv(events: list[dict]) -> str:
        if not events:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=events[0].keys())
        writer.writeheader()
        for row in events:
            writer.writerow(row)
        return buf.getvalue()

    @staticmethod
    def action_from_method(method: str) -> str:
        """Map an HTTP method to a CRUD action string."""
        return _METHOD_ACTION.get(method.upper(), "read")


# Module-level singleton
audit_service = AuditService()
