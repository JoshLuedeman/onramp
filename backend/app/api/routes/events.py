"""SSE real-time event streaming routes."""

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.services.event_stream import event_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/stream")
async def event_stream_endpoint(
    event_types: str = Query(
        default="",
        description="Comma-separated event types to subscribe to (empty = all)",
    ),
    user: dict = Depends(get_current_user),
):
    """SSE endpoint for real-time event updates.

    Returns a ``text/event-stream`` response that emits server-sent events
    matching the requested ``event_types``.
    """
    user_id: str = user.get("sub", user.get("user_id", "anonymous"))
    types_list = [t.strip() for t in event_types.split(",") if t.strip()] if event_types else []

    return StreamingResponse(
        event_stream.subscribe(user_id, types_list),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/health")
async def event_stream_health():
    """Check SSE infrastructure health and return subscriber count."""
    return {
        "status": "active",
        "subscriber_count": event_stream.get_subscriber_count(),
    }
