from datetime import datetime, timezone, timedelta
import uuid
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.models.entities import WishlistItem, PriceObservation, Notification
from app.adapters.registry import registry
from app.core.exceptions import WishTrackException

async def process_price_check(
    item_id: uuid.UUID,
    db: AsyncSession,
    adapter_override = None
) -> Dict[str, Any]:
    """
    Core price checking execution pipeline:
    1. Loads item & resolves adapter.
    2. Fetches product snapshot safely.
    3. Persists observation append-only.
    4. Computes rolling 365-day low and price drop delta.
    5. Returns evaluation payload for alerts.
    """
    stmt = select(WishlistItem).where(WishlistItem.id == item_id, WishlistItem.deleted_at.is_(None))
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        return {"status": "error", "error": f"Item {item_id} not found"}

    adapter = adapter_override or registry.get_adapter_for_host(item.retailer_host)
    now_utc = datetime.now(timezone.utc)

    if not adapter:
        item.tracking_mode = "unsupported"
        item.tracking_status = "degraded"
        item.updated_at = now_utc
        await db.commit()
        return {"status": "unsupported", "message": f"No adapter for host {item.retailer_host}"}

    try:
        snapshot = await adapter.fetch_product(item.product_url)
    except Exception as exc:
        # Failure classification & backoff
        item.tracking_status = "degraded"
        # Back off check time by 2 hours on failure
        item.next_check_at = now_utc + timedelta(hours=2)
        item.updated_at = now_utc
        await db.commit()
        return {"status": "failed", "error": str(exc)}

    # Validate price
    if snapshot.price_minor < 0:
        return {"status": "error", "error": "Invalid negative price"}

    # Insert price observation
    obs = PriceObservation(
        item_id=item.id,
        observed_at=snapshot.observed_at,
        price_minor=snapshot.price_minor,
        currency=snapshot.currency,
        availability=snapshot.availability,
        source=snapshot.source,
        confidence=snapshot.confidence,
        raw_price_text=snapshot.raw_price_text
    )
    db.add(obs)
    await db.flush()

    # Recompute history & 365-day low
    cutoff_365 = now_utc - timedelta(days=365)
    prior_obs_stmt = (
        select(PriceObservation)
        .where(
            PriceObservation.item_id == item.id,
            PriceObservation.id != obs.id,
            PriceObservation.observed_at >= cutoff_365
        )
        .order_by(desc(PriceObservation.observed_at))
    )
    prior_obs_list = (await db.execute(prior_obs_stmt)).scalars().all()

    previous_price = prior_obs_list[0].price_minor if prior_obs_list else None
    prior_min_price = min([o.price_minor for o in prior_obs_list]) if prior_obs_list else None

    # Calculate events
    is_price_drop = False
    drop_amount = 0
    drop_percent = 0.0
    if previous_price is not None and snapshot.price_minor < previous_price:
        is_price_drop = True
        drop_amount = previous_price - snapshot.price_minor
        if previous_price > 0:
            drop_percent = round((drop_amount / previous_price) * 100, 2)

    is_new_365d_low = False
    if prior_min_price is not None:
        is_new_365d_low = snapshot.price_minor < prior_min_price
    else:
        is_new_365d_low = True # First observation is the initial 365-day low

    target_reached = False
    if item.target_price_minor is not None and snapshot.price_minor <= item.target_price_minor:
        target_reached = True

    # Update item timestamps
    item.last_checked_at = now_utc
    item.next_check_at = now_utc + timedelta(hours=12)
    item.tracking_status = "active"
    item.updated_at = now_utc

    await db.commit()
    await db.refresh(obs)

    return {
        "status": "success",
        "item_id": str(item.id),
        "observation_id": obs.id,
        "price_minor": snapshot.price_minor,
        "currency": snapshot.currency,
        "previous_price_minor": previous_price,
        "is_price_drop": is_price_drop,
        "drop_amount": drop_amount,
        "drop_percent": drop_percent,
        "is_new_365d_low": is_new_365d_low,
        "target_reached": target_reached,
    }
