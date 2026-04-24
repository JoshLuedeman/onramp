"""Tests for the scan coordinator service."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services.scan_coordinator import ScanCoordinator


@pytest.fixture()
def coordinator() -> ScanCoordinator:
    """Return a fresh ScanCoordinator for each test."""
    return ScanCoordinator()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SCAN_TYPES = ["drift", "policy", "rbac", "tagging"]
PROJECT_ID = "proj-test-123"


# ---------------------------------------------------------------------------
# start_scan
# ---------------------------------------------------------------------------


class TestStartScan:
    @pytest.mark.asyncio
    async def test_start_scan_returns_scan_id(self, coordinator: ScanCoordinator):
        """start_scan returns a dict containing a scan_id."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            result = await coordinator.start_scan("drift", PROJECT_ID)

        assert isinstance(result, dict)
        assert "scan_id" in result
        assert isinstance(result["scan_id"], str)
        assert len(result["scan_id"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scan_type", VALID_SCAN_TYPES)
    async def test_start_scan_valid_types(
        self, coordinator: ScanCoordinator, scan_type: str
    ):
        """All four valid scan types can be started."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            result = await coordinator.start_scan(scan_type, PROJECT_ID)

        assert result["scan_type"] == scan_type
        assert result["status"] == "running"
        assert result["project_id"] == PROJECT_ID

    @pytest.mark.asyncio
    async def test_start_scan_invalid_type(self, coordinator: ScanCoordinator):
        """An invalid scan type still starts (no validation in coordinator).

        The coordinator is scan-type-agnostic; it stores whatever string
        is passed.  Validation is expected at the API layer.
        """
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            result = await coordinator.start_scan("nonexistent", PROJECT_ID)

        assert result["scan_type"] == "nonexistent"
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_start_scan_progress_fields(self, coordinator: ScanCoordinator):
        """Returned progress dict contains all expected fields."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            result = await coordinator.start_scan("drift", PROJECT_ID)

        expected_keys = {
            "scan_id",
            "scan_type",
            "total_resources",
            "scanned_resources",
            "percentage",
            "status",
            "started_at",
            "updated_at",
            "project_id",
            "error_message",
        }
        assert expected_keys.issubset(result.keys())
        assert result["total_resources"] == 0
        assert result["scanned_resources"] == 0
        assert result["percentage"] == 0.0
        assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_incremental_scan(self, coordinator: ScanCoordinator):
        """start_scan with incremental=True records properly."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            result = await coordinator.start_scan(
                "drift", PROJECT_ID, incremental=True
            )

        assert result["status"] == "running"
        assert result["scan_id"] in coordinator._active_scans


# ---------------------------------------------------------------------------
# get_progress
# ---------------------------------------------------------------------------


class TestGetProgress:
    @pytest.mark.asyncio
    async def test_get_progress_running(self, coordinator: ScanCoordinator):
        """After starting a scan, get_progress returns its running state."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            started = await coordinator.start_scan("policy", PROJECT_ID)

        progress = await coordinator.get_progress(started["scan_id"])

        assert progress is not None
        assert progress["scan_id"] == started["scan_id"]
        assert progress["status"] == "running"

    @pytest.mark.asyncio
    async def test_get_progress_nonexistent(self, coordinator: ScanCoordinator):
        """get_progress returns None for an unknown scan_id."""
        result = await coordinator.get_progress("does-not-exist")
        assert result is None


# ---------------------------------------------------------------------------
# cancel_scan
# ---------------------------------------------------------------------------


class TestCancelScan:
    @pytest.mark.asyncio
    async def test_cancel_scan(self, coordinator: ScanCoordinator):
        """Cancelling an active scan marks it as cancelled."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            started = await coordinator.start_scan("rbac", PROJECT_ID)
            result = await coordinator.cancel_scan(started["scan_id"])

        assert result is not None
        assert result["status"] == "cancelled"
        assert result["scan_id"] == started["scan_id"]

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_scan(self, coordinator: ScanCoordinator):
        """Cancelling a non-existent scan returns None gracefully."""
        result = await coordinator.cancel_scan("no-such-scan")
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled(self, coordinator: ScanCoordinator):
        """Cancelling an already-cancelled scan returns it without error."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            started = await coordinator.start_scan("drift", PROJECT_ID)
            await coordinator.cancel_scan(started["scan_id"])
            result = await coordinator.cancel_scan(started["scan_id"])

        assert result is not None
        assert result["status"] == "cancelled"


# ---------------------------------------------------------------------------
# get_paginated_results
# ---------------------------------------------------------------------------


class TestGetPaginatedResults:
    @pytest.mark.asyncio
    async def test_get_paginated_results_no_db(self, coordinator: ScanCoordinator):
        """Without a DB session, returns mock paginated data."""
        result = await coordinator.get_paginated_results("drift", PROJECT_ID)

        assert isinstance(result, dict)
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "page_size" in result
        assert "has_more" in result
        assert result["page"] == 1
        assert result["page_size"] == 50
        assert result["total"] == 100
        assert result["has_more"] is True
        assert len(result["items"]) == 50

    @pytest.mark.asyncio
    async def test_get_paginated_results_page_two(self, coordinator: ScanCoordinator):
        """Page 2 returns a different slice of mock data."""
        result = await coordinator.get_paginated_results(
            "policy", PROJECT_ID, page=2, page_size=50
        )

        assert result["page"] == 2
        assert result["has_more"] is False
        assert len(result["items"]) == 50

    @pytest.mark.asyncio
    async def test_get_paginated_results_custom_page_size(
        self, coordinator: ScanCoordinator
    ):
        """Custom page_size is respected in mock mode."""
        result = await coordinator.get_paginated_results(
            "tagging", PROJECT_ID, page=1, page_size=10
        )

        assert result["page_size"] == 10
        assert len(result["items"]) == 10
        assert result["has_more"] is True

    @pytest.mark.asyncio
    async def test_get_paginated_results_item_fields(
        self, coordinator: ScanCoordinator
    ):
        """Each mock item has expected fields."""
        result = await coordinator.get_paginated_results(
            "drift", PROJECT_ID, page=1, page_size=5
        )

        for item in result["items"]:
            assert "id" in item
            assert item["scan_type"] == "drift"
            assert item["project_id"] == PROJECT_ID
            assert "resource_id" in item
            assert item["status"] in ("compliant", "non_compliant")
            assert "checked_at" in item


# ---------------------------------------------------------------------------
# Multiple concurrent scans
# ---------------------------------------------------------------------------


class TestConcurrentScans:
    @pytest.mark.asyncio
    async def test_multiple_concurrent_scans(self, coordinator: ScanCoordinator):
        """Multiple scans can be tracked simultaneously."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            scan1 = await coordinator.start_scan("drift", "proj-1")
            scan2 = await coordinator.start_scan("policy", "proj-2")
            scan3 = await coordinator.start_scan("rbac", "proj-3")

        assert len(coordinator._active_scans) == 3
        ids = {scan1["scan_id"], scan2["scan_id"], scan3["scan_id"]}
        assert len(ids) == 3  # All unique

        # Each is independently retrievable
        for scan in [scan1, scan2, scan3]:
            progress = await coordinator.get_progress(scan["scan_id"])
            assert progress is not None
            assert progress["status"] == "running"

    @pytest.mark.asyncio
    async def test_cancel_one_does_not_affect_others(
        self, coordinator: ScanCoordinator
    ):
        """Cancelling one scan leaves others running."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            scan1 = await coordinator.start_scan("drift", "proj-1")
            scan2 = await coordinator.start_scan("policy", "proj-2")

            await coordinator.cancel_scan(scan1["scan_id"])

        p1 = await coordinator.get_progress(scan1["scan_id"])
        p2 = await coordinator.get_progress(scan2["scan_id"])

        assert p1["status"] == "cancelled"
        assert p2["status"] == "running"


# ---------------------------------------------------------------------------
# Background scan simulation
# ---------------------------------------------------------------------------


class TestBackgroundScan:
    @pytest.mark.asyncio
    async def test_scan_completes_in_background(self, coordinator: ScanCoordinator):
        """A scan eventually completes with 100% progress."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            started = await coordinator.start_scan("drift", PROJECT_ID)

        # Wait for background task to finish (50 resources × 0.05s = ~2.5s)
        scan_id = started["scan_id"]
        for _ in range(100):
            await asyncio.sleep(0.05)
            progress = await coordinator.get_progress(scan_id)
            if progress and progress["status"] == "completed":
                break

        assert progress["status"] == "completed"
        assert progress["percentage"] == 100.0
        assert progress["scanned_resources"] == 50

    @pytest.mark.asyncio
    async def test_incremental_scan_fewer_resources(
        self, coordinator: ScanCoordinator
    ):
        """Incremental scans process fewer resources (15 vs 50)."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            started = await coordinator.start_scan(
                "drift", PROJECT_ID, incremental=True
            )

        scan_id = started["scan_id"]
        for _ in range(60):
            await asyncio.sleep(0.05)
            progress = await coordinator.get_progress(scan_id)
            if progress and progress["status"] == "completed":
                break

        assert progress["status"] == "completed"
        assert progress["scanned_resources"] == 15

    @pytest.mark.asyncio
    async def test_cancel_stops_background_scan(self, coordinator: ScanCoordinator):
        """Cancelling a running scan prevents it from completing."""
        with patch.object(coordinator, "_publish_event", new_callable=AsyncMock):
            started = await coordinator.start_scan("drift", PROJECT_ID)

            # Give background task a moment to start
            await asyncio.sleep(0.1)
            await coordinator.cancel_scan(started["scan_id"])

        # Wait briefly for task loop to see cancellation
        await asyncio.sleep(0.2)
        progress = await coordinator.get_progress(started["scan_id"])

        assert progress["status"] == "cancelled"
        assert progress["scanned_resources"] < 50
