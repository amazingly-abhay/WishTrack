from datetime import datetime, timezone
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import WishlistItem, Notification, NotificationPreference

def format_money(minor: int, currency: str = "INR") -> str:
    amount = minor / 100
    if currency.upper() == "INR":
        return f"₹{amount:,.2f}"
    return f"{currency.upper()} {amount:,.2f}"

async def evaluate_and_create_alerts(
    item: WishlistItem,
    eval_result: Dict[str, Any],
    db: AsyncSession
) -> List[Notification]:
    """
    Evaluates alert rules for a price check observation:
    1. Target Reached: price <= target
    2. Price Drop: price < previous_price (respecting minimum_drop_percent preference)
    3. New 365-day low: price is new rolling minimum
    Ensures strict deduplication via deterministic dedupe_key.
    """
    user_id = item.user_id
    stmt = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    prefs = (await db.execute(stmt)).scalar_one_or_none()

    # Default preferences if none found
    in_app_enabled = prefs.in_app_enabled if prefs else True
    if not in_app_enabled:
        return []

    target_enabled = prefs.target_reached_enabled if prefs else True
    drop_enabled = prefs.price_drop_enabled if prefs else True
    new_low_enabled = prefs.new_low_enabled if prefs else True
    min_drop_pct = prefs.minimum_drop_percent if (prefs and prefs.minimum_drop_percent) else 0.0

    created_notifications: List[Notification] = []
    now_utc = datetime.now(timezone.utc)
    curr_str = format_money(eval_result["price_minor"], eval_result["currency"])

    # 1. Target Price Reached
    if target_enabled and eval_result.get("target_reached") and item.target_price_minor:
        dedupe_key = f"item:{item.id}:target:{item.target_price_minor}"
        if not await _is_deduped(user_id, dedupe_key, db):
            notif = Notification(
                user_id=user_id,
                item_id=item.id,
                observation_id=eval_result.get("observation_id"),
                type="target_reached",
                title=f"Target reached for {item.title}!",
                body=f"Price is now {curr_str}, reaching your target of {format_money(item.target_price_minor, eval_result['currency'])}.",
                payload={
                    "price_minor": eval_result["price_minor"],
                    "target_price_minor": item.target_price_minor,
                    "currency": eval_result["currency"],
                },
                dedupe_key=dedupe_key,
                created_at=now_utc
            )
            db.add(notif)
            created_notifications.append(notif)

    # 2. New 365-Day Low
    if new_low_enabled and eval_result.get("is_new_365d_low") and eval_result.get("previous_price_minor"):
        obs_id = eval_result.get("observation_id")
        dedupe_key = f"item:{item.id}:new-low:{obs_id}"
        if not await _is_deduped(user_id, dedupe_key, db):
            notif = Notification(
                user_id=user_id,
                item_id=item.id,
                observation_id=obs_id,
                type="new_365d_low",
                title=f"New 365-day low on {item.title}!",
                body=f"Price dropped to {curr_str}, the lowest observed in the last 365 days.",
                payload={
                    "price_minor": eval_result["price_minor"],
                    "currency": eval_result["currency"],
                },
                dedupe_key=dedupe_key,
                created_at=now_utc
            )
            db.add(notif)
            created_notifications.append(notif)

    # 3. Price Drop
    elif drop_enabled and eval_result.get("is_price_drop"):
        drop_pct = eval_result.get("drop_percent", 0.0)
        if drop_pct >= min_drop_pct:
            obs_id = eval_result.get("observation_id")
            dedupe_key = f"item:{item.id}:drop:{obs_id}"
            if not await _is_deduped(user_id, dedupe_key, db):
                notif = Notification(
                    user_id=user_id,
                    item_id=item.id,
                    observation_id=obs_id,
                    type="price_drop",
                    title=f"Price drop on {item.title}!",
                    body=f"Price dropped by {drop_pct}% to {curr_str} (was {format_money(eval_result['previous_price_minor'], eval_result['currency'])}).",
                    payload={
                        "price_minor": eval_result["price_minor"],
                        "previous_price_minor": eval_result["previous_price_minor"],
                        "drop_percent": drop_pct,
                        "currency": eval_result["currency"],
                    },
                    dedupe_key=dedupe_key,
                    created_at=now_utc
                )
                db.add(notif)
                created_notifications.append(notif)

    if created_notifications:
        await db.commit()

    return created_notifications

async def _is_deduped(user_id: uuid.UUID, dedupe_key: str, db: AsyncSession) -> bool:
    stmt = select(Notification.id).where(
        Notification.user_id == user_id,
        Notification.dedupe_key == dedupe_key
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None
