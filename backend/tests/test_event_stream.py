"""Tests for SSE event stream infrastructure."""

import asyncio
import json

import pytest

from app.schemas.events import EventStreamEvent, EventType
from app.services.event_stream import EventStreamManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def collect_messages(
    manager: EventStreamManager,
    user_id: str,
    event_types: list[str] | None = None,
    max_messages: int = 1,
    timeout: float = 2.0,
) -> list[str]:
    """Consume messages from a subscription up to *max_messages*."""
    messages: list[str] = []
    async for msg in manager.subscribe(user_id, event_types):
        messages.append(msg)
        if len(messages) >= max_messages:
            break
    return messages


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestEventSchemas:
    def test_event_type_enum_values(self):
        assert EventType.GOVERNANCE_SCORE_UPDATED == "governance_score_updated"
        assert EventType.DRIFT_DETECTED == "drift_detected"
        assert EventType.DRIFT_RESOLVED == "drift_resolved"
        assert EventType.SCAN_STARTED == "scan_started"
        assert EventType.SCAN_COMPLETED == "scan_completed"
        assert EventType.SCAN_FAILED == "scan_failed"
        assert EventType.COMPLIANCE_CHANGED == "compliance_changed"
        assert EventType.NOTIFICATION_NEW == "notification_new"
        assert EventType.COST_ALERT == "cost_alert"

    def test_event_stream_event_defaults(self):
        evt = EventStreamEvent(event_type="scan_started", data={"progress": 0})
        assert evt.event_type == "scan_started"
        assert evt.data == {"progress": 0}
        assert evt.timestamp  # auto-generated
        assert evt.project_id is None
        assert evt.tenant_id is None

    def test_event_stream_event_with_ids(self):
        evt = EventStreamEvent(
            event_type="drift_detected",
            data={"resource": "vnet-01"},
            project_id="proj-1",
            tenant_id="tenant-1",
        )
        assert evt.project_id == "proj-1"
        assert evt.tenant_id == "tenant-1"


# ---------------------------------------------------------------------------
# EventStreamManager unit tests
# ---------------------------------------------------------------------------


class TestEventStreamManager:
    @pytest.fixture(autouse=True)
    def _manager(self):
        self.manager = EventStreamManager()

    # -- Publish / subscribe -------------------------------------------------

    @pytest.mark.asyncio
    async def test_publish_subscribe_flow(self):
        """Subscriber receives a published event."""

        async def _subscriber():
            return await collect_messages(self.manager, "user-1", max_messages=1)

        task = asyncio.create_task(_subscriber())
        # Give the subscriber time to register
        await asyncio.sleep(0.05)

        delivered = await self.manager.publish(
            "scan_started", {"progress": 0}
        )
        assert delivered == 1

        messages = await asyncio.wait_for(task, timeout=2.0)
        assert len(messages) == 1
        assert messages[0].startswith("event: scan_started\n")
        payload = json.loads(messages[0].split("data: ")[1].split("\n")[0])
        assert payload["event_type"] == "scan_started"
        assert payload["data"]["progress"] == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers_receive_same_event(self):
        """All active subscribers receive a broadcast event."""

        async def _sub(uid: str):
            return await collect_messages(self.manager, uid, max_messages=1)

        t1 = asyncio.create_task(_sub("user-a"))
        t2 = asyncio.create_task(_sub("user-b"))
        await asyncio.sleep(0.05)

        delivered = await self.manager.publish("drift_detected", {"id": "d1"})
        assert delivered == 2

        m1 = await asyncio.wait_for(t1, timeout=2.0)
        m2 = await asyncio.wait_for(t2, timeout=2.0)
        assert len(m1) == 1
        assert len(m2) == 1

    # -- Event type filtering ------------------------------------------------

    @pytest.mark.asyncio
    async def test_event_type_filtering(self):
        """Subscribers only receive events matching their filter."""

        async def _sub_drift():
            return await collect_messages(
                self.manager, "user-filter", ["drift_detected"], max_messages=1
            )

        task = asyncio.create_task(_sub_drift())
        await asyncio.sleep(0.05)

        # This should NOT be delivered (wrong type)
        delivered_scan = await self.manager.publish("scan_started", {})
        assert delivered_scan == 0

        # This SHOULD be delivered
        delivered_drift = await self.manager.publish("drift_detected", {"id": "d2"})
        assert delivered_drift == 1

        messages = await asyncio.wait_for(task, timeout=2.0)
        assert len(messages) == 1
        assert "drift_detected" in messages[0]

    @pytest.mark.asyncio
    async def test_empty_event_types_receives_all(self):
        """Subscriber with empty event_types receives all events."""

        async def _sub_all():
            return await collect_messages(
                self.manager, "user-all", event_types=[], max_messages=1
            )

        task = asyncio.create_task(_sub_all())
        await asyncio.sleep(0.05)

        delivered = await self.manager.publish("cost_alert", {"amount": 42})
        assert delivered == 1

        messages = await asyncio.wait_for(task, timeout=2.0)
        assert len(messages) == 1

    # -- Subscriber cleanup --------------------------------------------------

    @pytest.mark.asyncio
    async def test_subscriber_cleanup_on_disconnect(self):
        """Subscriber is removed after the generator exits."""
        assert self.manager.get_subscriber_count() == 0

        async def _sub():
            return await collect_messages(self.manager, "user-dc", max_messages=1)

        task = asyncio.create_task(_sub())
        await asyncio.sleep(0.05)
        assert self.manager.get_subscriber_count() == 1

        # Publish to trigger the subscriber to exit
        await self.manager.publish("scan_started", {})
        await asyncio.wait_for(task, timeout=2.0)

        # After collection is done the subscriber generator exits and
        # cleanup runs
        await asyncio.sleep(0.05)
        assert self.manager.get_subscriber_count() == 0

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """disconnect_all sends sentinels and clears all subscribers."""

        collected: list[str] = []

        async def _sub():
            async for msg in self.manager.subscribe("user-da"):
                collected.append(msg)

        task = asyncio.create_task(_sub())
        await asyncio.sleep(0.05)
        assert self.manager.get_subscriber_count() == 1

        await self.manager.disconnect_all()
        await asyncio.wait_for(task, timeout=2.0)
        assert self.manager.get_subscriber_count() == 0

    # -- Heartbeat -----------------------------------------------------------

    @pytest.mark.asyncio
    async def test_heartbeat_on_timeout(self):
        """Keepalive is sent when no events arrive within the heartbeat window."""
        # Temporarily reduce heartbeat interval for test speed
        import app.services.event_stream as mod

        original = mod.HEARTBEAT_INTERVAL_SECONDS
        mod.HEARTBEAT_INTERVAL_SECONDS = 0.1  # type: ignore[assignment]

        try:
            messages: list[str] = []

            async def _sub():
                async for msg in self.manager.subscribe("user-hb"):
                    messages.append(msg)
                    if len(messages) >= 1:
                        break

            task = asyncio.create_task(_sub())
            # Don't publish anything — heartbeat should fire
            await asyncio.wait_for(task, timeout=2.0)
            assert any(":keepalive" in m for m in messages)
        finally:
            mod.HEARTBEAT_INTERVAL_SECONDS = original  # type: ignore[assignment]

    # -- Subscriber count ----------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_subscriber_count(self):
        """get_subscriber_count returns correct active connection count."""
        assert self.manager.get_subscriber_count() == 0

        async def _sub(uid: str):
            return await collect_messages(self.manager, uid, max_messages=1)

        t1 = asyncio.create_task(_sub("u1"))
        t2 = asyncio.create_task(_sub("u2"))
        await asyncio.sleep(0.05)
        assert self.manager.get_subscriber_count() == 2

        # Disconnect one
        await self.manager.publish("scan_started", {}, user_id="u1")
        await asyncio.wait_for(t1, timeout=2.0)
        await asyncio.sleep(0.05)
        assert self.manager.get_subscriber_count() == 1

        # Disconnect the other
        await self.manager.publish("scan_started", {}, user_id="u2")
        await asyncio.wait_for(t2, timeout=2.0)
        await asyncio.sleep(0.05)
        assert self.manager.get_subscriber_count() == 0

    # -- Targeted publish ----------------------------------------------------

    @pytest.mark.asyncio
    async def test_publish_to_specific_user(self):
        """Publishing with user_id only reaches that user."""

        async def _sub(uid: str):
            return await collect_messages(self.manager, uid, max_messages=1)

        t1 = asyncio.create_task(_sub("target"))
        t2 = asyncio.create_task(_sub("other"))
        await asyncio.sleep(0.05)

        delivered = await self.manager.publish(
            "notification_new", {"msg": "hi"}, user_id="target"
        )
        assert delivered == 1

        messages = await asyncio.wait_for(t1, timeout=2.0)
        assert len(messages) == 1

        # "other" didn't get anything — disconnect cleanly
        await self.manager.publish("scan_started", {}, user_id="other")
        await asyncio.wait_for(t2, timeout=2.0)


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


class TestEventRoutes:
    """Test the /api/events/ HTTP endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client with auth disabled."""
        from unittest.mock import AsyncMock, patch

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.api.routes.events import router
        from app.auth import get_current_user

        test_app = FastAPI()
        test_app.include_router(router)

        # Override auth dependency
        async def _mock_user():
            return {"sub": "test-user", "name": "Test User"}

        test_app.dependency_overrides[get_current_user] = _mock_user
        return TestClient(test_app)

    def test_stream_health_endpoint(self, client):
        resp = client.get("/api/events/stream/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "active"
        assert "subscriber_count" in body

    def test_stream_endpoint_content_type(self, client):
        """The /stream endpoint returns text/event-stream content-type."""
        from unittest.mock import patch

        # Mock subscribe to yield one message and exit so the test doesn't hang
        async def _mock_subscribe(user_id, event_types=None):
            yield "event: test\ndata: {}\n\n"

        with patch(
            "app.api.routes.events.event_stream.subscribe",
            side_effect=_mock_subscribe,
        ):
            with client.stream("GET", "/api/events/stream") as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers.get("content-type", "")
