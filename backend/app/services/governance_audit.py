"""Governance audit trail service — append-only event logging.

Provides structured logging of all governance-related events for
compliance, debugging, and operational visibility.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.models.base import generate_uuid

logger = logging.getLogger(__name__)


class GovernanceAuditService:
    """Singleton service for the governance audit trail."""

    # ------------------------------------------------------------------
    # Log
    # ------------------------------------------------------------------

    async def log_event(
        self,
        event_type: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor: str | None = None,
        details: dict | None = None,
        project_id: str | None = None,
        tenant_id: str | None = None,
        db: Any | None = None,
    ) -> dict:
        """Append an audit entry. Returns the created entry as a dict."""
        entry_id = generate_uuid()
        now = datetime.now(timezone.utc)

        entry_data = {
            "id": entry_id,
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "actor": actor,
            "details": details,
            "project_id": project_id,
            "tenant_id": tenant_id,
            "created_at": now,
        }

        if db is not None:
            from app.models.governance_audit import GovernanceAuditEntry

            row = GovernanceAuditEntry(
                id=entry_id,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                actor=actor,
                details=details,
                project_id=project_id,
                tenant_id=tenant_id,
            )
            db.add(row)
            await db.flush()
            await db.refresh(row)
            entry_data["created_at"] = row.created_at

        logger.info(
            "Audit event: type=%s resource=%s/%s actor=%s",
            event_type, resource_type, resource_id, actor,
        )
        return entry_data

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def query_events(
        self,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 50,
        db: Any | None = None,
    ) -> dict:
        """Query audit events with filtering and pagination.

        Returns dict with entries, total, page, page_size, has_more.
        """
        if db is not None:
            from sqlalchemy import func, select

            from app.models.governance_audit import GovernanceAuditEntry

            stmt = select(GovernanceAuditEntry).order_by(
                GovernanceAuditEntry.created_at.desc()
            )
            count_stmt = select(func.count()).select_from(GovernanceAuditEntry)

            # Apply filters
            if filters:
                if filters.get("event_type"):
                    stmt = stmt.where(
                        GovernanceAuditEntry.event_type == filters["event_type"]
                    )
                    count_stmt = count_stmt.where(
                        GovernanceAuditEntry.event_type == filters["event_type"]
                    )
                if filters.get("actor"):
                    stmt = stmt.where(
                        GovernanceAuditEntry.actor == filters["actor"]
                    )
                    count_stmt = count_stmt.where(
                        GovernanceAuditEntry.actor == filters["actor"]
                    )
                if filters.get("resource_type"):
                    stmt = stmt.where(
                        GovernanceAuditEntry.resource_type == filters["resource_type"]
                    )
                    count_stmt = count_stmt.where(
                        GovernanceAuditEntry.resource_type == filters["resource_type"]
                    )
                if filters.get("project_id"):
                    stmt = stmt.where(
                        GovernanceAuditEntry.project_id == filters["project_id"]
                    )
                    count_stmt = count_stmt.where(
                        GovernanceAuditEntry.project_id == filters["project_id"]
                    )
                if filters.get("tenant_id"):
                    stmt = stmt.where(
                        GovernanceAuditEntry.tenant_id == filters["tenant_id"]
                    )
                    count_stmt = count_stmt.where(
                        GovernanceAuditEntry.tenant_id == filters["tenant_id"]
                    )
                if filters.get("date_from"):
                    stmt = stmt.where(
                        GovernanceAuditEntry.created_at >= filters["date_from"]
                    )
                    count_stmt = count_stmt.where(
                        GovernanceAuditEntry.created_at >= filters["date_from"]
                    )
                if filters.get("date_to"):
                    stmt = stmt.where(
                        GovernanceAuditEntry.created_at <= filters["date_to"]
                    )
                    count_stmt = count_stmt.where(
                        GovernanceAuditEntry.created_at <= filters["date_to"]
                    )

            # Get total
            total_result = await db.execute(count_stmt)
            total = total_result.scalar_one()

            # Apply pagination
            offset = (page - 1) * page_size
            stmt = stmt.offset(offset).limit(page_size)

            result = await db.execute(stmt)
            rows = result.scalars().all()

            return {
                "entries": [_row_to_dict(r) for r in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": offset + page_size < total,
            }

        # Dev mode — empty
        return {
            "entries": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "has_more": False,
        }

    async def get_event(
        self,
        entry_id: str,
        db: Any | None = None,
    ) -> dict | None:
        """Get a single audit entry by ID."""
        if db is not None:
            from sqlalchemy import select

            from app.models.governance_audit import GovernanceAuditEntry

            result = await db.execute(
                select(GovernanceAuditEntry).where(
                    GovernanceAuditEntry.id == entry_id
                )
            )
            row = result.scalar_one_or_none()
            return _row_to_dict(row) if row else None

        return None

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_events(
        self,
        filters: dict | None = None,
        fmt: str = "json",
        db: Any | None = None,
    ) -> str:
        """Export filtered events as JSON or CSV string."""
        # Fetch all matching events (no pagination limit)
        all_data = await self.query_events(
            filters=filters, page=1, page_size=10000, db=db
        )
        entries = all_data["entries"]

        if fmt == "csv":
            return _entries_to_csv(entries)

        # Default to JSON
        return json.dumps(
            entries,
            default=str,
            indent=2,
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(
        self,
        project_id: str | None = None,
        tenant_id: str | None = None,
        db: Any | None = None,
    ) -> dict:
        """Get summary stats (event counts by type, recent actors)."""
        if db is not None:
            from sqlalchemy import func, select

            from app.models.governance_audit import GovernanceAuditEntry

            # Total events
            total_stmt = select(func.count()).select_from(GovernanceAuditEntry)
            if project_id:
                total_stmt = total_stmt.where(
                    GovernanceAuditEntry.project_id == project_id
                )
            if tenant_id:
                total_stmt = total_stmt.where(
                    GovernanceAuditEntry.tenant_id == tenant_id
                )
            total_result = await db.execute(total_stmt)
            total = total_result.scalar_one()

            # Events by type
            type_stmt = (
                select(
                    GovernanceAuditEntry.event_type,
                    func.count().label("count"),
                )
                .group_by(GovernanceAuditEntry.event_type)
            )
            if project_id:
                type_stmt = type_stmt.where(
                    GovernanceAuditEntry.project_id == project_id
                )
            if tenant_id:
                type_stmt = type_stmt.where(
                    GovernanceAuditEntry.tenant_id == tenant_id
                )
            type_result = await db.execute(type_stmt)
            events_by_type = {
                row.event_type: row.count for row in type_result.all()
            }

            # Recent actors (distinct, latest 10)
            actor_stmt = (
                select(GovernanceAuditEntry.actor)
                .where(GovernanceAuditEntry.actor.isnot(None))
                .distinct()
                .order_by(GovernanceAuditEntry.actor)
                .limit(10)
            )
            if project_id:
                actor_stmt = actor_stmt.where(
                    GovernanceAuditEntry.project_id == project_id
                )
            actor_result = await db.execute(actor_stmt)
            recent_actors = [row[0] for row in actor_result.all()]

            return {
                "total_events": total,
                "events_by_type": events_by_type,
                "recent_actors": recent_actors,
            }

        return {
            "total_events": 0,
            "events_by_type": {},
            "recent_actors": [],
        }


def _row_to_dict(row: Any) -> dict:
    """Convert a GovernanceAuditEntry ORM object to a dict."""
    return {
        "id": row.id,
        "event_type": row.event_type,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "actor": row.actor,
        "details": row.details,
        "project_id": row.project_id,
        "tenant_id": row.tenant_id,
        "created_at": row.created_at,
    }


def _entries_to_csv(entries: list[dict]) -> str:
    """Convert audit entries to a CSV string."""
    if not entries:
        return ""

    output = io.StringIO()
    fieldnames = [
        "id", "event_type", "resource_type", "resource_id",
        "actor", "details", "project_id", "tenant_id", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for entry in entries:
        row = {k: entry.get(k, "") for k in fieldnames}
        # Serialize details as JSON string
        if isinstance(row.get("details"), dict):
            row["details"] = json.dumps(row["details"])
        writer.writerow(row)

    return output.getvalue()


# Singleton
governance_audit_service = GovernanceAuditService()
