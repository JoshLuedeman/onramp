"""Server-Sent Events (SSE) manager for real-time updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 30


@dataclass
class Subscriber:
    """Represents a single SSE subscriber connection."""

    user_id: str
    event_types: set[str]
    queue: asyncio.Queue[str | None] = field(default_factory=asyncio.Queue)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


class EventStreamManager:
    """Manages SSE subscriptions and event publication.

    Uses an ``asyncio.Queue`` per subscriber for async event delivery.
    """

    def __init__(self) -> None:
        # user_id → list of active subscribers
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Subscribe
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        user_id: str,
        event_types: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Subscribe to an SSE event stream.

        Yields SSE-formatted strings including heartbeats.  Put ``None``
        into the subscriber's queue to signal disconnection.
        """
        subscriber = Subscriber(
            user_id=user_id,
            event_types=set(event_types) if event_types else set(),
        )

        async with self._lock:
            self._subscribers[user_id].append(subscriber)

        logger.info(
            "SSE subscriber connected: user=%s types=%s",
            user_id,
            subscriber.event_types or "all",
        )

        try:
            while True:
                try:
                    # Wait for the next message *or* heartbeat timeout
                    message = await asyncio.wait_for(
                        subscriber.queue.get(),
                        timeout=HEARTBEAT_INTERVAL_SECONDS,
                    )
                    if message is None:
                        # Sentinel → disconnect
                        break
                    yield message
                except asyncio.TimeoutError:
                    # No events within the heartbeat window → send keepalive
                    yield ":keepalive\n\n"
        finally:
            await self._remove_subscriber(user_id, subscriber)

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def publish(
        self,
        event_type: str,
        data: dict,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> int:
        """Publish an event to matching subscribers.

        Returns the number of subscribers the event was delivered to.
        """
        payload = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "tenant_id": tenant_id,
        }
        sse_message = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"

        delivered = 0
        async with self._lock:
            target_subscribers: list[Subscriber] = []

            if user_id:
                # Target a specific user
                target_subscribers = list(self._subscribers.get(user_id, []))
            else:
                # Broadcast to all subscribers
                for subs in self._subscribers.values():
                    target_subscribers.extend(subs)

            for sub in target_subscribers:
                # If subscriber specified event_types, only deliver matching events
                if sub.event_types and event_type not in sub.event_types:
                    continue
                try:
                    sub.queue.put_nowait(sse_message)
                    delivered += 1
                except asyncio.QueueFull:
                    logger.warning(
                        "SSE queue full for user=%s, dropping event=%s",
                        sub.user_id,
                        event_type,
                    )

        return delivered

    # ------------------------------------------------------------------
    # Subscriber count
    # ------------------------------------------------------------------

    def get_subscriber_count(self) -> int:
        """Return the number of active subscriber connections."""
        return sum(len(subs) for subs in self._subscribers.values())

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def _remove_subscriber(
        self, user_id: str, subscriber: Subscriber
    ) -> None:
        """Remove a disconnected subscriber."""
        async with self._lock:
            subs = self._subscribers.get(user_id, [])
            try:
                subs.remove(subscriber)
            except ValueError:
                pass
            if not subs:
                self._subscribers.pop(user_id, None)

        logger.info("SSE subscriber disconnected: user=%s", user_id)

    async def disconnect_all(self) -> None:
        """Disconnect all subscribers (e.g. on shutdown)."""
        async with self._lock:
            for subs in self._subscribers.values():
                for sub in subs:
                    try:
                        sub.queue.put_nowait(None)
                    except asyncio.QueueFull:
                        pass
            self._subscribers.clear()


# Module-level singleton
event_stream = EventStreamManager()
