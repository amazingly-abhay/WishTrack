from datetime import datetime, timezone
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from app.db.session import get_db
from app.models.entities import User, Notification, NotificationPreference, PushSubscription
from app.schemas.notifications import (
    NotificationResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    PushSubscriptionCreateRequest,
    PushSubscriptionResponse,
)
from app.schemas.common import PaginatedResponse
from app.core.exceptions import WishTrackException
from app.api.deps import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get in-app notification inbox strictly scoped to current user.
    """
    conditions = [Notification.user_id == current_user.id]
    if unread_only:
        conditions.append(Notification.read_at.is_(None))

    count_stmt = select(func.count(Notification.id)).where(and_(*conditions))
    total_count = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Notification)
        .where(and_(*conditions))
        .order_by(desc(Notification.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(stmt)
    notifications = result.scalars().all()

    return PaginatedResponse[NotificationResponse](
        items=notifications,
        total=total_count,
        page=page,
        limit=limit,
        has_next=(page * limit) < total_count
    )

@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark an individual notification as read with owner verification.
    """
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    )
    notif = (await db.execute(stmt)).scalar_one_or_none()
    if not notif:
        raise WishTrackException(code="NOTIFICATION_NOT_FOUND", message="Notification not found", status_code=404)

    notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)
    return notif

@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all unread notifications as read for current user.
    """
    now_utc = datetime.now(timezone.utc)
    stmt = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.read_at.is_(None)
    )
    notifs = (await db.execute(stmt)).scalars().all()
    for n in notifs:
        n.read_at = now_utc
    await db.commit()
    return {"status": "ok", "updated_count": len(notifs)}

@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve user notification preferences.
    """
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
    prefs = (await db.execute(stmt)).scalar_one_or_none()
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs

@router.patch("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
    req: NotificationPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update notification channels and alert triggers (price drops, new lows, targets).
    """
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
    prefs = (await db.execute(stmt)).scalar_one_or_none()
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)

    if req.in_app_enabled is not None:
        prefs.in_app_enabled = req.in_app_enabled
    if req.web_push_enabled is not None:
        prefs.web_push_enabled = req.web_push_enabled
    if req.email_enabled is not None:
        prefs.email_enabled = req.email_enabled
    if req.price_drop_enabled is not None:
        prefs.price_drop_enabled = req.price_drop_enabled
    if req.target_reached_enabled is not None:
        prefs.target_reached_enabled = req.target_reached_enabled
    if req.new_low_enabled is not None:
        prefs.new_low_enabled = req.new_low_enabled
    if req.minimum_drop_percent is not None:
        prefs.minimum_drop_percent = req.minimum_drop_percent

    prefs.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(prefs)
    return prefs

@router.post("/push-subscriptions", response_model=PushSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def register_push_subscription(
    req: PushSubscriptionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register Web Push endpoint and crypto keys for PWA notifications.
    """
    stmt = select(PushSubscription).where(PushSubscription.endpoint == req.endpoint)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.user_id = current_user.id
        existing.p256dh_key = req.p256dh_key
        existing.auth_key = req.auth_key
        existing.disabled_at = None
        await db.commit()
        await db.refresh(existing)
        return existing

    sub = PushSubscription(
        user_id=current_user.id,
        endpoint=req.endpoint,
        p256dh_key=req.p256dh_key,
        auth_key=req.auth_key
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub
