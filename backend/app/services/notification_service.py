"""Notification delivery service with pluggable channel adapters.

In development mode (no Azure credentials), the email adapter logs to
console and webhooks are attempted normally.
"""

from __future__ import annotations

import abc
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx

from app.config import settings
from app.models.base import generate_uuid

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate-limit constants
# ---------------------------------------------------------------------------
MAX_NOTIFICATIONS_PER_TYPE_PER_USER_PER_HOUR = 10


# ---------------------------------------------------------------------------
# Channel adapters (abstract base + implementations)
# ---------------------------------------------------------------------------


class ChannelAdapter(abc.ABC):
    """Abstract base class for notification delivery channels."""

    @abc.abstractmethod
    async def deliver(self, notification_data: dict) -> dict:
        """Deliver a notification.  Returns metadata dict with delivery info."""


class InAppAdapter(ChannelAdapter):
    """In-app notifications — stored in the database only."""

    async def deliver(self, notification_data: dict) -> dict:
        logger.info(
            "In-app notification stored: [%s] %s",
            notification_data.get("notification_type"),
            notification_data.get("title"),
        )
        return {"adapter": "in_app", "stored": True}


class EmailAdapter(ChannelAdapter):
    """Email notifications — logs in dev mode, SMTP/Azure in production."""

    async def deliver(self, notification_data: dict) -> dict:
        if settings.is_dev_mode:
            logger.info(
                "DEV EMAIL — To: %s | Subject: %s | Body: %s",
                notification_data.get("email", "unknown"),
                notification_data.get("title"),
                notification_data.get("message"),
            )
            return {"adapter": "email", "mode": "dev_log", "sent": True}

        # Production: integrate with SMTP / Azure Communication Services.
        # Placeholder — not implemented until Azure credentials are available.
        logger.warning("Production email delivery not yet implemented")
        return {"adapter": "email", "mode": "production", "sent": False}


class WebhookAdapter(ChannelAdapter):
    """Webhook notifications — HTTP POST with exponential-backoff retry."""

    MAX_RETRIES = 3
    BASE_DELAY = 1  # seconds

    async def deliver(self, notification_data: dict) -> dict:
        url = notification_data.get("webhook_url")
        if not url:
            logger.warning("Webhook notification missing URL — skipping")
            return {"adapter": "webhook", "error": "missing_url", "sent": False}

        payload = {
            "notification_type": notification_data.get("notification_type"),
            "title": notification_data.get("title"),
            "message": notification_data.get("message"),
            "severity": notification_data.get("severity"),
            "project_id": notification_data.get("project_id"),
            "tenant_id": notification_data.get("tenant_id"),
            "created_at": notification_data.get("created_at"),
        }

        last_error: str | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                logger.info("Webhook delivered to %s on attempt %d", url, attempt)
                return {"adapter": "webhook", "status_code": resp.status_code, "sent": True}
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Webhook attempt %d/%d to %s failed: %s",
                    attempt, self.MAX_RETRIES, url, last_error,
                )
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(self.BASE_DELAY * (2 ** (attempt - 1)))

        return {"adapter": "webhook", "error": last_error, "sent": False}


# ---------------------------------------------------------------------------
# Notification service
# ---------------------------------------------------------------------------


class NotificationService:
    """Central notification service with rate limiting and multi-channel dispatch."""

    def __init__(self) -> None:
        self._adapters: dict[str, ChannelAdapter] = {
            "in_app": InAppAdapter(),
            "email": EmailAdapter(),
            "webhook": WebhookAdapter(),
        }
        # rate-limit tracker: {(user_id, notification_type): [timestamps]}
        self._rate_tracker: dict[tuple[str, str], list[datetime]] = defaultdict(list)

    # -- public API ---------------------------------------------------------

    async def send(
        self,
        db: AsyncSession,
        *,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "info",
        tenant_id: str | None = None,
        project_id: str | None = None,
        user_ids: list[str] | None = None,
        channel: str = "in_app",
    ) -> list[dict]:
        """Create notification records and dispatch via the specified channel.

        Returns a list of result dicts (one per user).
        """
        from app.models.notification import Notification

        targets = user_ids or [None]
        results: list[dict] = []

        for uid in targets:
            # Rate-limit check
            if uid and self._is_rate_limited(uid, notification_type):
                logger.warning(
                    "Rate limit hit for user %s / type %s — skipping",
                    uid, notification_type,
                )
                results.append({"user_id": uid, "status": "rate_limited"})
                continue

            notification = Notification(
                id=generate_uuid(),
                tenant_id=tenant_id,
                project_id=project_id,
                user_id=uid,
                notification_type=notification_type,
                title=title,
                message=message,
                severity=severity,
                channel=channel,
                status="pending",
            )
            db.add(notification)
            await db.flush()

            # Dispatch
            delivery_result = await self.send_to_channel(notification, channel)

            # Update record
            now = datetime.now(timezone.utc)
            notification.delivery_metadata = delivery_result
            if delivery_result.get("sent"):
                notification.status = "delivered"
                notification.delivered_at = now
            else:
                notification.status = "failed"
            await db.flush()

            # Record for rate limiting
            if uid:
                self._record_send(uid, notification_type)

            results.append({
                "user_id": uid,
                "notification_id": notification.id,
                "status": notification.status,
                "delivery_metadata": delivery_result,
            })

        return results

    async def send_to_channel(self, notification, channel: str) -> dict:
        """Dispatch a single notification through the named channel adapter."""
        adapter = self._adapters.get(channel)
        if adapter is None:
            logger.error("Unknown channel: %s", channel)
            return {"error": f"unknown_channel: {channel}", "sent": False}

        data = {
            "notification_type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "severity": notification.severity,
            "tenant_id": notification.tenant_id,
            "project_id": notification.project_id,
            "created_at": (
                notification.created_at.isoformat()
                if notification.created_at
                else None
            ),
        }

        # Channel-specific extras from delivery_metadata
        meta = notification.delivery_metadata or {}
        data["email"] = meta.get("email")
        data["webhook_url"] = meta.get("webhook_url")

        return await adapter.deliver(data)

    async def mark_read(
        self, db: AsyncSession, notification_id: str, user_id: str
    ) -> bool:
        """Mark a single notification as read. Returns True on success."""
        from sqlalchemy import select

        from app.models.notification import Notification

        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notif = result.scalar_one_or_none()
        if notif is None:
            return False

        notif.status = "read"
        notif.read_at = datetime.now(timezone.utc)
        await db.flush()
        return True

    async def get_unread_count(self, db: AsyncSession, user_id: str) -> int:
        """Return the number of unread (non-read) notifications for a user."""
        from sqlalchemy import func, select

        from app.models.notification import Notification

        result = await db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.status != "read",
            )
        )
        return result.scalar_one()

    # -- rate limiting helpers ----------------------------------------------

    def _is_rate_limited(self, user_id: str, notification_type: str) -> bool:
        key = (user_id, notification_type)
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - 3600  # 1 hour window
        # Prune old entries
        self._rate_tracker[key] = [
            ts for ts in self._rate_tracker[key] if ts.timestamp() > cutoff
        ]
        return len(self._rate_tracker[key]) >= MAX_NOTIFICATIONS_PER_TYPE_PER_USER_PER_HOUR

    def _record_send(self, user_id: str, notification_type: str) -> None:
        key = (user_id, notification_type)
        self._rate_tracker[key].append(datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
notification_service = NotificationService()
