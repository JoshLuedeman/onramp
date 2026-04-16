"""Tests for notification delivery infrastructure.

Covers:
- Send notification creates record and dispatches
- In-app notifications stored and queryable
- Webhook adapter makes HTTP POST (mock httpx)
- Email adapter logs in dev mode
- Rate limiting prevents notification storms
- Mark read / unread count
- Preference CRUD
- Route-level tests (sync TestClient)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app

client = TestClient(app)


# ===================================================================
# Model import tests
# ===================================================================


class TestModels:
    def test_notification_model_importable(self):
        from app.models.notification import Notification

        assert Notification.__tablename__ == "notifications"

    def test_notification_preference_model_importable(self):
        from app.models.notification import NotificationPreference

        assert NotificationPreference.__tablename__ == "notification_preferences"

    def test_models_registered_in_init(self):
        from app.models import Notification, NotificationPreference

        assert Notification.__tablename__ == "notifications"
        assert NotificationPreference.__tablename__ == "notification_preferences"

    def test_models_in_metadata(self):
        from app.models import Base

        table_names = set(Base.metadata.tables.keys())
        assert "notifications" in table_names
        assert "notification_preferences" in table_names


# ===================================================================
# Schema tests
# ===================================================================


class TestSchemas:
    def test_severity_enum(self):
        from app.schemas.notification import NotificationSeverity

        assert NotificationSeverity.CRITICAL == "critical"
        assert NotificationSeverity.HIGH == "high"
        assert NotificationSeverity.MEDIUM == "medium"
        assert NotificationSeverity.LOW == "low"
        assert NotificationSeverity.INFO == "info"

    def test_channel_enum(self):
        from app.schemas.notification import NotificationChannel

        assert NotificationChannel.IN_APP == "in_app"
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.WEBHOOK == "webhook"

    def test_status_enum(self):
        from app.schemas.notification import NotificationStatus

        assert NotificationStatus.PENDING == "pending"
        assert NotificationStatus.SENT == "sent"
        assert NotificationStatus.DELIVERED == "delivered"
        assert NotificationStatus.FAILED == "failed"
        assert NotificationStatus.READ == "read"

    def test_notification_response_from_dict(self):
        from app.schemas.notification import NotificationResponse

        now = datetime.now(timezone.utc)
        resp = NotificationResponse(
            id="test-id",
            notification_type="drift_detected",
            title="Drift Found",
            message="Something drifted",
            severity="critical",
            channel="in_app",
            status="pending",
            created_at=now,
        )
        assert resp.id == "test-id"
        assert resp.severity.value == "critical"

    def test_notification_list_response(self):
        from app.schemas.notification import NotificationListResponse

        resp = NotificationListResponse(notifications=[], total=0, page=1, page_size=50)
        assert resp.total == 0
        assert resp.notifications == []

    def test_preference_create(self):
        from app.schemas.notification import NotificationPreferenceCreate

        pref = NotificationPreferenceCreate(
            notification_type="drift_detected",
            channel="email",
            enabled=True,
        )
        assert pref.notification_type == "drift_detected"
        assert pref.channel.value == "email"

    def test_unread_count_response(self):
        from app.schemas.notification import UnreadCountResponse

        resp = UnreadCountResponse(unread_count=5)
        assert resp.unread_count == 5

    def test_test_notification_request_defaults(self):
        from app.schemas.notification import TestNotificationRequest

        req = TestNotificationRequest()
        assert req.title == "Test Notification"
        assert req.severity.value == "info"
        assert req.channel.value == "in_app"


# ===================================================================
# Service / adapter unit tests
# ===================================================================


class TestInAppAdapter:
    @pytest.mark.asyncio
    async def test_deliver_returns_stored(self):
        from app.services.notification_service import InAppAdapter

        adapter = InAppAdapter()
        result = await adapter.deliver({
            "notification_type": "test",
            "title": "Hello",
        })
        assert result["adapter"] == "in_app"
        assert result["stored"] is True


class TestEmailAdapter:
    @pytest.mark.asyncio
    async def test_dev_mode_logs_instead_of_sending(self):
        from app.services.notification_service import EmailAdapter

        adapter = EmailAdapter()
        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            result = await adapter.deliver({
                "email": "user@example.com",
                "title": "Test Email",
                "message": "Hello",
            })
        assert result["adapter"] == "email"
        assert result["mode"] == "dev_log"
        assert result["sent"] is True

    @pytest.mark.asyncio
    async def test_production_mode_returns_not_sent(self):
        from app.services.notification_service import EmailAdapter

        adapter = EmailAdapter()
        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.is_dev_mode = False
            result = await adapter.deliver({
                "email": "user@example.com",
                "title": "Test Email",
                "message": "Hello",
            })
        assert result["adapter"] == "email"
        assert result["mode"] == "production"
        assert result["sent"] is False


class TestWebhookAdapter:
    @pytest.mark.asyncio
    async def test_successful_webhook_delivery(self):
        from app.services.notification_service import WebhookAdapter

        adapter = WebhookAdapter()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.deliver({
                "webhook_url": "https://example.com/webhook",
                "notification_type": "test",
                "title": "Test",
                "message": "Hello",
                "severity": "info",
            })

        assert result["adapter"] == "webhook"
        assert result["sent"] is True
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_missing_url_returns_error(self):
        from app.services.notification_service import WebhookAdapter

        adapter = WebhookAdapter()
        result = await adapter.deliver({"notification_type": "test", "title": "X"})
        assert result["adapter"] == "webhook"
        assert result["sent"] is False
        assert result["error"] == "missing_url"

    @pytest.mark.asyncio
    async def test_webhook_retries_on_failure(self):
        from app.services.notification_service import WebhookAdapter

        adapter = WebhookAdapter()
        adapter.BASE_DELAY = 0  # speed up retries for testing

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.notification_service.httpx.AsyncClient", return_value=mock_client):
            result = await adapter.deliver({
                "webhook_url": "https://example.com/webhook",
                "notification_type": "test",
                "title": "Test",
                "message": "Hello",
                "severity": "info",
            })

        assert result["sent"] is False
        assert "Connection refused" in result["error"]
        # Should have retried 3 times
        assert mock_client.post.call_count == 3


class TestNotificationService:
    @pytest.mark.asyncio
    async def test_send_creates_record(self):
        """send() should create a Notification record and call the adapter."""
        from app.services.notification_service import NotificationService

        service = NotificationService()

        # Mock the db session
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        # Patch the adapter
        mock_adapter = AsyncMock()
        mock_adapter.deliver = AsyncMock(return_value={"sent": True, "adapter": "in_app"})
        service._adapters["in_app"] = mock_adapter

        results = await service.send(
            mock_db,
            notification_type="drift_detected",
            title="Drift Found",
            message="Config changed",
            severity="high",
            user_ids=["user-1"],
            channel="in_app",
        )

        assert len(results) == 1
        assert results[0]["status"] == "delivered"
        assert results[0]["user_id"] == "user-1"
        mock_db.add.assert_called_once()
        mock_adapter.deliver.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_without_user_ids(self):
        """send() with no user_ids should dispatch to a single None target."""
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.deliver = AsyncMock(return_value={"sent": True, "adapter": "in_app"})
        service._adapters["in_app"] = mock_adapter

        results = await service.send(
            mock_db,
            notification_type="test",
            title="Test",
            message="Hi",
            channel="in_app",
        )

        assert len(results) == 1
        assert results[0]["user_id"] is None

    @pytest.mark.asyncio
    async def test_send_failed_delivery(self):
        """When adapter returns sent=False, status should be 'failed'."""
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.deliver = AsyncMock(return_value={"sent": False, "error": "timeout"})
        service._adapters["in_app"] = mock_adapter

        results = await service.send(
            mock_db,
            notification_type="test",
            title="Test",
            message="Hi",
            user_ids=["user-1"],
            channel="in_app",
        )

        assert results[0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_unknown_channel_returns_error(self):
        """send_to_channel with unknown channel returns error."""
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_notification = MagicMock()
        mock_notification.notification_type = "test"
        mock_notification.title = "Test"
        mock_notification.message = "Hi"
        mock_notification.severity = "info"
        mock_notification.tenant_id = None
        mock_notification.project_id = None
        mock_notification.created_at = None
        mock_notification.delivery_metadata = None

        result = await service.send_to_channel(mock_notification, "carrier_pigeon")
        assert result["sent"] is False
        assert "unknown_channel" in result["error"]


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limiting_prevents_storms(self):
        """After 10 notifications, subsequent ones should be rate-limited."""
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.deliver = AsyncMock(return_value={"sent": True, "adapter": "in_app"})
        service._adapters["in_app"] = mock_adapter

        # Send 10 notifications (all should succeed)
        for _ in range(10):
            results = await service.send(
                mock_db,
                notification_type="drift_detected",
                title="Drift",
                message="Config drifted",
                user_ids=["user-1"],
                channel="in_app",
            )
            assert results[0]["status"] == "delivered"

        # 11th should be rate-limited
        results = await service.send(
            mock_db,
            notification_type="drift_detected",
            title="Drift again",
            message="More drift",
            user_ids=["user-1"],
            channel="in_app",
        )
        assert results[0]["status"] == "rate_limited"

    @pytest.mark.asyncio
    async def test_rate_limiting_per_type(self):
        """Rate limiting is per notification type, not global."""
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.deliver = AsyncMock(return_value={"sent": True, "adapter": "in_app"})
        service._adapters["in_app"] = mock_adapter

        # Fill up drift_detected limit
        for _ in range(10):
            await service.send(
                mock_db,
                notification_type="drift_detected",
                title="Drift",
                message="Config drifted",
                user_ids=["user-1"],
                channel="in_app",
            )

        # Different type should still work
        results = await service.send(
            mock_db,
            notification_type="compliance_violation",
            title="Violation",
            message="Compliance issue",
            user_ids=["user-1"],
            channel="in_app",
        )
        assert results[0]["status"] == "delivered"

    @pytest.mark.asyncio
    async def test_rate_limiting_per_user(self):
        """Rate limiting is per user, different users are independent."""
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.deliver = AsyncMock(return_value={"sent": True, "adapter": "in_app"})
        service._adapters["in_app"] = mock_adapter

        # Fill up user-1 limit
        for _ in range(10):
            await service.send(
                mock_db,
                notification_type="test",
                title="Test",
                message="Hi",
                user_ids=["user-1"],
                channel="in_app",
            )

        # user-2 should still work
        results = await service.send(
            mock_db,
            notification_type="test",
            title="Test",
            message="Hi",
            user_ids=["user-2"],
            channel="in_app",
        )
        assert results[0]["status"] == "delivered"

    def test_is_rate_limited_returns_false_under_limit(self):
        from app.services.notification_service import NotificationService

        service = NotificationService()
        assert service._is_rate_limited("user-1", "test") is False

    def test_record_send_and_check(self):
        from app.services.notification_service import NotificationService

        service = NotificationService()
        for _ in range(10):
            service._record_send("user-1", "test")
        assert service._is_rate_limited("user-1", "test") is True


# ===================================================================
# Route tests (sync — uses dev mode mock user, no DB)
# ===================================================================


class TestNotificationRoutes:
    def test_list_notifications_dev_mode(self):
        r = client.get("/api/notifications/")
        assert r.status_code == 200
        data = r.json()
        assert "notifications" in data
        assert data["total"] == 0

    def test_unread_count_dev_mode(self):
        r = client.get("/api/notifications/unread-count")
        assert r.status_code == 200
        data = r.json()
        assert data["unread_count"] == 0

    def test_mark_read_no_db(self):
        r = client.post("/api/notifications/some-id/read")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False

    def test_mark_all_read_no_db(self):
        r = client.post("/api/notifications/mark-all-read")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["count"] == 0

    def test_get_preferences_no_db(self):
        r = client.get("/api/notifications/preferences")
        assert r.status_code == 200
        assert r.json() == []

    def test_update_preference_no_db(self):
        r = client.put(
            "/api/notifications/preferences",
            json={
                "notification_type": "drift_detected",
                "channel": "email",
                "enabled": True,
            },
        )
        assert r.status_code == 503

    def test_send_test_notification_no_db(self):
        r = client.post(
            "/api/notifications/test",
            json={
                "title": "Test",
                "message": "Hello",
                "severity": "info",
                "channel": "in_app",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "logged"

    def test_send_test_notification_defaults(self):
        r = client.post("/api/notifications/test", json={})
        assert r.status_code == 200

    def test_list_notifications_with_filters(self):
        r = client.get(
            "/api/notifications/",
            params={
                "notification_type": "drift_detected",
                "severity": "critical",
                "status": "pending",
                "page": 1,
                "page_size": 10,
            },
        )
        assert r.status_code == 200

    def test_test_endpoint_blocked_in_production(self):
        """Test endpoint returns 403 when not in dev mode."""
        with patch("app.api.routes.notifications.settings") as mock_settings:
            mock_settings.is_dev_mode = False
            r = client.post(
                "/api/notifications/test",
                json={"title": "Test", "message": "Hello"},
            )
            assert r.status_code == 403


# ===================================================================
# Async route tests
# ===================================================================


class TestNotificationRoutesAsync:
    @pytest.mark.asyncio
    async def test_list_notifications_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/notifications/")
            assert r.status_code == 200
            data = r.json()
            assert data["notifications"] == []

    @pytest.mark.asyncio
    async def test_unread_count_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/notifications/unread-count")
            assert r.status_code == 200
            assert r.json()["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_mark_all_read_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post("/api/notifications/mark-all-read")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_preferences_empty_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/notifications/preferences")
            assert r.status_code == 200
            assert r.json() == []

    @pytest.mark.asyncio
    async def test_test_notification_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/api/notifications/test",
                json={"title": "Async Test", "message": "Hello async"},
            )
            assert r.status_code == 200


# ===================================================================
# Singleton instance
# ===================================================================


class TestSingleton:
    def test_notification_service_singleton(self):
        from app.services.notification_service import notification_service

        assert notification_service is not None
        assert hasattr(notification_service, "send")
        assert hasattr(notification_service, "mark_read")
        assert hasattr(notification_service, "get_unread_count")

    def test_adapters_registered(self):
        from app.services.notification_service import notification_service

        assert "in_app" in notification_service._adapters
        assert "email" in notification_service._adapters
        assert "webhook" in notification_service._adapters


# ===================================================================
# Service mark_read / get_unread_count with mocked DB
# ===================================================================


class TestServiceMarkRead:
    @pytest.mark.asyncio
    async def test_mark_read_success(self):
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_notification = MagicMock()
        mock_notification.id = "notif-1"
        mock_notification.user_id = "user-1"
        mock_notification.status = "delivered"
        mock_notification.read_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_notification

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        success = await service.mark_read(mock_db, "notif-1", "user-1")
        assert success is True
        assert mock_notification.status == "read"
        assert mock_notification.read_at is not None

    @pytest.mark.asyncio
    async def test_mark_read_not_found(self):
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        success = await service.mark_read(mock_db, "nonexistent", "user-1")
        assert success is False


class TestServiceGetUnreadCount:
    @pytest.mark.asyncio
    async def test_get_unread_count(self):
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await service.get_unread_count(mock_db, "user-1")
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_unread_count_zero(self):
        from app.services.notification_service import NotificationService

        service = NotificationService()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        count = await service.get_unread_count(mock_db, "user-1")
        assert count == 0
