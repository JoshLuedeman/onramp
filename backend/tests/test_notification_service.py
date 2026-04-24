"""Tests for the NotificationService — adapters, rate limiting, channels."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.notification_service import (
    EmailAdapter,
    InAppAdapter,
    NotificationService,
    WebhookAdapter,
)


class TestInAppAdapter:
    """Test in-app notification adapter."""

    @pytest.mark.asyncio
    async def test_deliver_returns_stored(self):
        adapter = InAppAdapter()
        result = await adapter.deliver(
            {"notification_type": "test", "title": "Hello"}
        )
        assert result["adapter"] == "in_app"
        assert result["stored"] is True


class TestEmailAdapter:
    """Test email adapter in dev mode."""

    @pytest.mark.asyncio
    async def test_dev_mode_logs_not_sends(self):
        adapter = EmailAdapter()
        result = await adapter.deliver(
            {"email": "user@example.com", "title": "Test", "message": "Body"}
        )
        assert result["adapter"] == "email"
        assert result["mode"] == "dev_log"
        assert result["sent"] is True


class TestWebhookAdapter:
    """Test webhook adapter."""

    @pytest.mark.asyncio
    async def test_missing_url_returns_error(self):
        adapter = WebhookAdapter()
        result = await adapter.deliver({"notification_type": "test"})
        assert result["adapter"] == "webhook"
        assert result["error"] == "missing_url"
        assert result["sent"] is False

    @pytest.mark.asyncio
    async def test_successful_delivery(self):
        adapter = WebhookAdapter()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await adapter.deliver(
                {
                    "webhook_url": "https://example.com/hook",
                    "notification_type": "test",
                    "title": "Test",
                }
            )
            assert result["sent"] is True
            assert result["status_code"] == 200


class TestNotificationServiceInit:
    """Test service initialization."""

    def test_has_all_adapters(self):
        svc = NotificationService()
        assert "in_app" in svc._adapters
        assert "email" in svc._adapters
        assert "webhook" in svc._adapters

    def test_rate_tracker_empty_on_init(self):
        svc = NotificationService()
        assert len(svc._rate_tracker) == 0


class TestRateLimiting:
    """Test rate limiting logic."""

    def test_not_rate_limited_initially(self):
        svc = NotificationService()
        assert svc._is_rate_limited("user-1", "alert") is False

    def test_rate_limited_after_max_hits(self):
        svc = NotificationService()
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        key = ("user-1", "alert")
        svc._rate_tracker[key] = [now] * 10
        assert svc._is_rate_limited("user-1", "alert") is True
