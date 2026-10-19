from datetime import datetime, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.entities import WishlistItem

async def get_due_items_for_check(db: AsyncSession, limit: int = 50) -> List[WishlistItem]:
    """
    Selects items whose next_check_at is due and whose tracking status is active/degraded.
    """
    now_utc = datetime.now(timezone.utc)
    stmt = (
        select(WishlistItem)
        .where(
            WishlistItem.deleted_at.is_(None),
            WishlistItem.is_archived == False,
            WishlistItem.tracking_mode == "automatic",
            WishlistItem.tracking_status.in_(["active", "degraded"]),
            WishlistItem.next_check_at <= now_utc
        )
        .order_by(WishlistItem.next_check_at.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
