"""Notification API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.db.session import get_db
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferenceCreate,
    NotificationPreferenceResponse,
    NotificationResponse,
    NotificationSeverity,
    NotificationStatus,
    TestNotificationRequest,
    UnreadCountResponse,
)
from app.services.notification_service import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# List notifications
# ---------------------------------------------------------------------------


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    notification_type: str | None = Query(None, description="Filter by notification type"),
    severity: NotificationSeverity | None = Query(None, description="Filter by severity"),
    status: NotificationStatus | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Results per page"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user."""
    if db is None:
        return NotificationListResponse(notifications=[], total=0, page=page, page_size=page_size)

    from app.models.notification import Notification

    user_id = user.get("sub", user.get("id", "dev-user-id"))

    query = select(Notification).where(Notification.user_id == user_id)

    if notification_type:
        query = query.where(Notification.notification_type == notification_type)
    if severity:
        query = query.where(Notification.severity == severity.value)
    if status:
        query = query.where(Notification.status == status.value)

    # Total count (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginated results
    query = query.order_by(Notification.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Unread count
# ---------------------------------------------------------------------------


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unread notification count for the current user."""
    if db is None:
        return UnreadCountResponse(unread_count=0)

    user_id = user.get("sub", user.get("id", "dev-user-id"))
    count = await notification_service.get_unread_count(db, user_id)
    return UnreadCountResponse(unread_count=count)


# ---------------------------------------------------------------------------
# Mark as read
# ---------------------------------------------------------------------------


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    if db is None:
        return {"success": False, "detail": "Database not configured"}

    user_id = user.get("sub", user.get("id", "dev-user-id"))
    success = await notification_service.mark_read(db, notification_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True, "notification_id": notification_id}


# ---------------------------------------------------------------------------
# Mark all as read
# ---------------------------------------------------------------------------


@router.post("/mark-all-read")
async def mark_all_read(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    if db is None:
        return {"success": True, "count": 0}

    from sqlalchemy import update

    from app.models.notification import Notification

    user_id = user.get("sub", user.get("id", "dev-user-id"))
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.status != "read")
        .values(status="read", read_at=now)
    )
    await db.flush()
    return {"success": True, "count": result.rowcount}


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


@router.get("/preferences", response_model=list[NotificationPreferenceResponse])
async def get_preferences(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's notification preferences."""
    if db is None:
        return []

    from app.models.notification import NotificationPreference

    user_id = user.get("sub", user.get("id", "dev-user-id"))
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    prefs = result.scalars().all()
    return [NotificationPreferenceResponse.model_validate(p) for p in prefs]


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preference(
    pref: NotificationPreferenceCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a notification preference for the current user."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    from app.models.base import generate_uuid
    from app.models.notification import NotificationPreference

    user_id = user.get("sub", user.get("id", "dev-user-id"))
    tenant_id = user.get("tid", user.get("tenant_id"))

    # Upsert: find existing or create
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == pref.notification_type,
            NotificationPreference.channel == pref.channel.value,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.enabled = pref.enabled
        existing.config = pref.config
        existing.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return NotificationPreferenceResponse.model_validate(existing)

    new_pref = NotificationPreference(
        id=generate_uuid(),
        user_id=user_id,
        tenant_id=tenant_id,
        notification_type=pref.notification_type,
        channel=pref.channel.value,
        enabled=pref.enabled,
        config=pref.config,
    )
    db.add(new_pref)
    await db.flush()
    return NotificationPreferenceResponse.model_validate(new_pref)


# ---------------------------------------------------------------------------
# Test notification (dev mode only)
# ---------------------------------------------------------------------------


@router.post("/test")
async def send_test_notification(
    body: TestNotificationRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test notification (development mode only)."""
    if not settings.is_dev_mode:
        raise HTTPException(status_code=403, detail="Test notifications are only available in dev mode")

    if db is None:
        return {
            "status": "logged",
            "message": "Test notification logged (no database)",
            "title": body.title,
        }

    user_id = user.get("sub", user.get("id", "dev-user-id"))
    results = await notification_service.send(
        db,
        notification_type="test",
        title=body.title,
        message=body.message,
        severity=body.severity.value,
        channel=body.channel.value,
        user_ids=[user_id],
    )
    return {"status": "sent", "results": results}
