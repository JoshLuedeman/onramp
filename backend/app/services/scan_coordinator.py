"""Scan coordinator service — progress tracking, pagination, and cancellation.

Coordinates governance scans with progress reporting via SSE,
incremental scanning support, and paginated result retrieval.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.models.base import generate_uuid

logger = logging.getLogger(__name__)

# Default scan timeout (seconds)
DEFAULT_SCAN_TIMEOUT = 300


class ScanCoordinator:
    """Singleton service for coordinating governance scans."""

    def __init__(self) -> None:
        # In-memory tracking of active scans
        self._active_scans: dict[str, dict] = {}
        # Track last scan timestamp per (scan_type, project_id) for incremental
        self._last_scan_times: dict[tuple[str, str], datetime] = {}

    # ------------------------------------------------------------------
    # Start scan
    # ------------------------------------------------------------------

    async def start_scan(
        self,
        scan_type: str,
        project_id: str,
        incremental: bool = False,
        tenant_id: str | None = None,
    ) -> dict:
        """Start a scan with progress tracking.

        Returns a ScanProgress dict immediately; the scan runs in
        the background.
        """
        scan_id = generate_uuid()
        now = datetime.now(timezone.utc)

        last_scan = None
        if incremental:
            key = (scan_type, project_id)
            last_scan = self._last_scan_times.get(key)

        progress = {
            "scan_id": scan_id,
            "scan_type": scan_type,
            "total_resources": 0,
            "scanned_resources": 0,
            "percentage": 0.0,
            "status": "running",
            "started_at": now,
            "updated_at": now,
            "project_id": project_id,
            "error_message": None,
        }
        self._active_scans[scan_id] = progress

        # Publish SSE event
        await self._publish_event("scan_started", {
            "scan_id": scan_id,
            "scan_type": scan_type,
            "project_id": project_id,
            "incremental": incremental,
        })

        # Simulate progress in background
        asyncio.create_task(
            self._run_scan(scan_id, scan_type, project_id, incremental, last_scan)
        )

        logger.info(
            "Scan started: id=%s type=%s project=%s incremental=%s",
            scan_id, scan_type, project_id, incremental,
        )
        return progress

    # ------------------------------------------------------------------
    # Get progress
    # ------------------------------------------------------------------

    async def get_progress(self, scan_id: str) -> dict | None:
        """Get current progress of a scan."""
        return self._active_scans.get(scan_id)

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    async def cancel_scan(self, scan_id: str) -> dict | None:
        """Cancel a running scan."""
        progress = self._active_scans.get(scan_id)
        if progress is None:
            return None

        if progress["status"] != "running":
            return progress

        progress["status"] = "cancelled"
        progress["updated_at"] = datetime.now(timezone.utc)

        await self._publish_event("scan_cancelled", {
            "scan_id": scan_id,
            "scan_type": progress.get("scan_type", ""),
        })

        logger.info("Scan cancelled: id=%s", scan_id)
        return progress

    # ------------------------------------------------------------------
    # Paginated results
    # ------------------------------------------------------------------

    async def get_paginated_results(
        self,
        scan_type: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        db: Any | None = None,
    ) -> dict:
        """Get paginated scan results.

        In dev mode, returns mock paginated data.
        """
        if db is not None:
            # Dispatch to the appropriate model based on scan type
            return await self._query_results_from_db(
                scan_type, project_id, page, page_size, db
            )

        # Dev mode mock
        mock_items = [
            {
                "id": generate_uuid(),
                "scan_type": scan_type,
                "project_id": project_id,
                "resource_id": f"/subscriptions/mock/resourceGroups/rg/providers/mock/{i}",
                "status": "compliant" if i % 3 != 0 else "non_compliant",
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            for i in range((page - 1) * page_size, min(page * page_size, 100))
        ]
        total = 100
        return {
            "items": mock_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": page * page_size < total,
        }

    # ------------------------------------------------------------------
    # Internal: background scan simulation
    # ------------------------------------------------------------------

    async def _run_scan(
        self,
        scan_id: str,
        scan_type: str,
        project_id: str,
        incremental: bool,
        last_scan: datetime | None,
    ) -> None:
        """Simulate a scan with progress updates."""
        progress = self._active_scans.get(scan_id)
        if progress is None:
            return

        total_resources = 50 if not incremental else 15
        progress["total_resources"] = total_resources

        for i in range(1, total_resources + 1):
            # Check for cancellation
            if progress["status"] != "running":
                return

            await asyncio.sleep(0.05)  # Simulate work
            progress["scanned_resources"] = i
            progress["percentage"] = round((i / total_resources) * 100, 1)
            progress["updated_at"] = datetime.now(timezone.utc)

            # Publish progress every 10 resources
            if i % 10 == 0:
                await self._publish_event("scan_progress", {
                    "scan_id": scan_id,
                    "scanned": i,
                    "total": total_resources,
                    "percentage": progress["percentage"],
                })

        # Mark completed
        progress["status"] = "completed"
        progress["percentage"] = 100.0
        progress["updated_at"] = datetime.now(timezone.utc)

        # Record last scan time for incremental support
        self._last_scan_times[(scan_type, project_id)] = progress["updated_at"]

        await self._publish_event("scan_completed", {
            "scan_id": scan_id,
            "scan_type": scan_type,
            "project_id": project_id,
            "total_resources": total_resources,
        })

        logger.info(
            "Scan completed: id=%s type=%s resources=%d",
            scan_id, scan_type, total_resources,
        )

    # ------------------------------------------------------------------
    # Internal: query results from DB
    # ------------------------------------------------------------------

    async def _query_results_from_db(
        self,
        scan_type: str,
        project_id: str,
        page: int,
        page_size: int,
        db: Any,
    ) -> dict:
        """Query scan results from the database based on scan type."""
        from sqlalchemy import func, select

        # Map scan types to models
        model_map = _get_scan_model_map()
        model = model_map.get(scan_type)

        if model is None:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "has_more": False,
            }

        stmt = select(model).where(model.project_id == project_id)
        count_stmt = (
            select(func.count())
            .select_from(model)
            .where(model.project_id == project_id)
        )

        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(stmt)
        rows = result.scalars().all()

        items = []
        for row in rows:
            item = {"id": row.id, "project_id": project_id}
            if hasattr(row, "status"):
                item["status"] = row.status
            if hasattr(row, "created_at"):
                item["created_at"] = str(row.created_at)
            items.append(item)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + page_size < total,
        }

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


def _get_scan_model_map() -> dict:
    """Lazily import and return scan type → ORM model map."""
    try:
        from app.models.drift import DriftScanResult
        from app.models.policy_compliance import PolicyComplianceResult
        from app.models.rbac_health import RBACScanResult
        from app.models.tagging import TaggingScanResult

        return {
            "drift": DriftScanResult,
            "policy": PolicyComplianceResult,
            "rbac": RBACScanResult,
            "tagging": TaggingScanResult,
        }
    except ImportError:
        return {}


# Singleton
scan_coordinator = ScanCoordinator()
