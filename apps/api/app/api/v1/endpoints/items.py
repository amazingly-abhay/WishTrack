from datetime import datetime, timezone
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from app.db.session import get_db
from app.models.entities import User, WishlistItem, PriceObservation
from app.schemas.items import (
    ItemPreviewRequest,
    ItemPreviewResponse,
    ItemCreateRequest,
    ItemUpdateRequest,
    ItemResponse
)
from app.schemas.common import PaginatedResponse
from app.core.url_validator import validate_and_canonicalize_url
from app.services.scraper import extract_product_preview
from app.core.exceptions import WishTrackException, ItemNotFoundException
from app.api.deps import get_current_user

router = APIRouter(prefix="/items", tags=["Wishlist Items"])

SUPPORTED_HOSTS = {
    "amazon.in",
    "flipkart.com",
    "example.com",
    "shop.example"
}

@router.post("/preview", response_model=ItemPreviewResponse)
async def preview_item(
    req: ItemPreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Validate product URL, inspect support, and auto-capture metadata without persisting.
    """
    details = await extract_product_preview(req.product_url)
    retailer_host = details["retailer_host"]
    is_supported = (
        retailer_host in SUPPORTED_HOSTS
        or "flipkart.com" in retailer_host
        or "amazon." in retailer_host
    )

    return ItemPreviewResponse(
        product_url=details["product_url"],
        canonical_url=details["canonical_url"],
        retailer_host=retailer_host,
        is_supported=is_supported,
        title=details["title"],
        image_url=details["image_url"],
        price_minor=details["price_minor"],
        currency=details["currency"],
        availability=details["availability"]
    )

@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    req: ItemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new wishlist item for the authenticated user with URL deduplication.
    """
    normalized_url, canonical_url, retailer_host = validate_and_canonicalize_url(req.product_url)

    # Check if item with this canonical URL already exists for this user
    stmt = select(WishlistItem).where(
        WishlistItem.user_id == current_user.id,
        WishlistItem.canonical_url == canonical_url,
        WishlistItem.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    existing_item = result.scalar_one_or_none()

    if existing_item:
        # Return existing item per spec or update non-conflicting fields
        return await _build_item_response(existing_item, db)

    tracking_mode = "automatic" if retailer_host in SUPPORTED_HOSTS else "manual"

    # If wishlist_id was not provided, default to user's default wishlist
    target_wishlist_id = req.wishlist_id
    if not target_wishlist_id:
        from app.api.v1.endpoints.wishlists import get_or_create_default_wishlist
        default_wl = await get_or_create_default_wishlist(current_user.id, db)
        target_wishlist_id = default_wl.id

    new_item = WishlistItem(
        user_id=current_user.id,
        wishlist_id=target_wishlist_id,
        product_url=normalized_url,
        canonical_url=canonical_url,
        retailer_host=retailer_host,
        title=req.title,
        image_url=req.image_url,
        currency=req.currency or "INR",
        target_price_minor=req.target_price_minor,
        notes=req.notes,
        tags=req.tags,
        tracking_mode=tracking_mode,
        tracking_status="active",
        is_favorite=False,
        is_archived=False,
        last_checked_at=datetime.now(timezone.utc) if req.price_minor is not None else None,
        next_check_at=datetime.now(timezone.utc)
    )
    db.add(new_item)
    await db.flush()

    # Save initial price observation if a valid price was supplied
    if req.price_minor is not None:
        obs = PriceObservation(
            item_id=new_item.id,
            observed_at=datetime.now(timezone.utc),
            price_minor=req.price_minor,
            currency=new_item.currency,
            availability="in_stock",
            source=req.source,
            confidence=1.0,
            raw_price_text=str(req.price_minor / 100)
        )
        db.add(obs)

    await db.commit()
    await db.refresh(new_item)

    return await _build_item_response(new_item, db)

@router.get("", response_model=PaginatedResponse[ItemResponse])
async def list_items(
    q: Optional[str] = Query(None, description="Search query in title or retailer host"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    wishlist_id: Optional[uuid.UUID] = Query(None, description="Filter by wishlist collection ID"),
    status: Optional[str] = Query(None, description="Filter by tracking status"),
    is_archived: bool = Query(False, description="Filter archived items"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user-isolated wishlist items with filtering, search, and pagination.
    """
    base_conditions = [
        WishlistItem.user_id == current_user.id,
        WishlistItem.deleted_at.is_(None),
        WishlistItem.is_archived == is_archived
    ]

    if wishlist_id:
        # Check if the requested wishlist is the default wishlist
        from app.models.entities import Wishlist
        wl_stmt = select(Wishlist).where(Wishlist.id == wishlist_id, Wishlist.user_id == current_user.id)
        wl = (await db.execute(wl_stmt)).scalar_one_or_none()
        if wl and wl.is_default:
            # Include items with matching wishlist_id or NULL (legacy items)
            base_conditions.append(
                (WishlistItem.wishlist_id == wishlist_id) | (WishlistItem.wishlist_id.is_(None))
            )
        else:
            base_conditions.append(WishlistItem.wishlist_id == wishlist_id)

    if q:
        search_filter = f"%{q.lower()}%"
        base_conditions.append(
            (func.lower(WishlistItem.title).like(search_filter)) |
            (func.lower(WishlistItem.retailer_host).like(search_filter))
        )
    if status:
        base_conditions.append(WishlistItem.tracking_status == status)

    count_stmt = select(func.count(WishlistItem.id)).where(and_(*base_conditions))
    total_count = (await db.execute(count_stmt)).scalar() or 0

    items_stmt = (
        select(WishlistItem)
        .where(and_(*base_conditions))
        .order_by(desc(WishlistItem.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items_result = await db.execute(items_stmt)
    items = items_result.scalars().all()

    response_items = []
    for it in items:
        resp = await _build_item_response(it, db)
        response_items.append(resp)

    return PaginatedResponse[ItemResponse](
        items=response_items,
        total=total_count,
        page=page,
        limit=limit,
        has_next=(page * limit) < total_count
    )

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get wishlist item details with user isolation. Returns 404 if not found or owned by another user.
    """
    stmt = select(WishlistItem).where(
        WishlistItem.id == item_id,
        WishlistItem.user_id == current_user.id,
        WishlistItem.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise ItemNotFoundException(str(item_id))

    return await _build_item_response(item, db)

@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: uuid.UUID,
    req: ItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update target price, notes, tags, title, or tracking mode.
    """
    stmt = select(WishlistItem).where(
        WishlistItem.id == item_id,
        WishlistItem.user_id == current_user.id,
        WishlistItem.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise ItemNotFoundException(str(item_id))

    if req.title is not None:
        item.title = req.title
    if req.target_price_minor is not None:
        item.target_price_minor = req.target_price_minor
    if req.notes is not None:
        item.notes = req.notes
    if req.tags is not None:
        item.tags = req.tags
    if req.wishlist_id is not None:
        item.wishlist_id = req.wishlist_id
    if req.is_favorite is not None:
        item.is_favorite = req.is_favorite
    if req.tracking_mode is not None:
        item.tracking_mode = req.tracking_mode

    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(item)

    return await _build_item_response(item, db)

@router.delete("/{item_id}", status_code=status.HTTP_200_OK)
async def delete_or_archive_item(
    item_id: uuid.UUID,
    archive: bool = Query(True, description="If true archives the item, if false soft deletes"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Archive or soft-delete an item with owner isolation.
    """
    stmt = select(WishlistItem).where(
        WishlistItem.id == item_id,
        WishlistItem.user_id == current_user.id,
        WishlistItem.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if not item:
        raise ItemNotFoundException(str(item_id))

    if archive:
        item.is_archived = True
        item.updated_at = datetime.now(timezone.utc)
    else:
        item.deleted_at = datetime.now(timezone.utc)

    await db.commit()
    return {"status": "ok", "message": "Item archived" if archive else "Item deleted"}

async def _build_item_response(item: WishlistItem, db: AsyncSession) -> ItemResponse:
    # Query latest observations to calculate current, previous, and 365-day low
    stmt = (
        select(PriceObservation)
        .where(PriceObservation.item_id == item.id)
        .order_by(desc(PriceObservation.observed_at))
        .limit(2)
    )
    obs_res = await db.execute(stmt)
    recent_obs = obs_res.scalars().all()

    current_price = recent_obs[0].price_minor if len(recent_obs) > 0 else None
    previous_price = recent_obs[1].price_minor if len(recent_obs) > 1 else None

    # Calculate 365-day low
    low_stmt = (
        select(func.min(PriceObservation.price_minor))
        .where(PriceObservation.item_id == item.id)
    )
    lowest_365d_price = (await db.execute(low_stmt)).scalar()

    return ItemResponse(
        id=item.id,
        wishlist_id=item.wishlist_id,
        title=item.title,
        product_url=item.product_url,
        canonical_url=item.canonical_url,
        retailer_host=item.retailer_host,
        image_url=item.image_url,
        currency=item.currency,
        current_price_minor=current_price,
        previous_price_minor=previous_price,
        lowest_365d_price_minor=lowest_365d_price or current_price,
        lowest_365d_at=item.last_checked_at,
        target_price_minor=item.target_price_minor,
        tracking_mode=item.tracking_mode,
        tracking_status=item.tracking_status,
        is_favorite=item.is_favorite,
        is_archived=item.is_archived,
        tags=item.tags or [],
        notes=item.notes,
        last_checked_at=item.last_checked_at,
        next_check_at=item.next_check_at,
        created_at=item.created_at,
        updated_at=item.updated_at
    )

# --- Price History & Manual Observation Endpoints ---
from app.schemas.history import ObservationCreateRequest, ObservationResponse, HistorySummaryResponse
from datetime import timedelta

@router.post("/{item_id}/observations", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED)
async def add_manual_observation(
    item_id: uuid.UUID,
    req: ObservationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually add a price observation for an item with owner verification.
    """
    stmt = select(WishlistItem).where(
        WishlistItem.id == item_id,
        WishlistItem.user_id == current_user.id,
        WishlistItem.deleted_at.is_(None)
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise ItemNotFoundException(str(item_id))

    currency = req.currency or item.currency or "INR"
    now_utc = datetime.now(timezone.utc)

    obs = PriceObservation(
        item_id=item.id,
        observed_at=now_utc,
        price_minor=req.price_minor,
        currency=currency,
        availability=req.availability or "in_stock",
        source="manual",
        confidence=1.0,
        raw_price_text=req.raw_price_text or str(req.price_minor / 100)
    )
    db.add(obs)

    item.last_checked_at = now_utc
    item.updated_at = now_utc
    await db.commit()
    await db.refresh(obs)

    return obs

@router.get("/{item_id}/history", response_model=List[ObservationResponse])
async def get_item_history(
    item_id: uuid.UUID,
    range: str = Query("30d", pattern="^(7d|30d|90d|180d|365d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get price observations for an item over a rolling time window.
    """
    stmt = select(WishlistItem).where(
        WishlistItem.id == item_id,
        WishlistItem.user_id == current_user.id,
        WishlistItem.deleted_at.is_(None)
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise ItemNotFoundException(str(item_id))

    days_map = {"7d": 7, "30d": 30, "90d": 90, "180d": 180, "365d": 365}
    days = days_map.get(range, 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    obs_stmt = (
        select(PriceObservation)
        .where(
            PriceObservation.item_id == item.id,
            PriceObservation.observed_at >= cutoff
        )
        .order_by(PriceObservation.observed_at.asc())
    )
    result = await db.execute(obs_stmt)
    return result.scalars().all()

@router.get("/{item_id}/history/summary", response_model=HistorySummaryResponse)
async def get_item_history_summary(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get price summary, change calculations, and rolling 365-day low.
    """
    stmt = select(WishlistItem).where(
        WishlistItem.id == item_id,
        WishlistItem.user_id == current_user.id,
        WishlistItem.deleted_at.is_(None)
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise ItemNotFoundException(str(item_id))

    # All observations in 365 days
    cutoff_365 = datetime.now(timezone.utc) - timedelta(days=365)
    obs_stmt = (
        select(PriceObservation)
        .where(
            PriceObservation.item_id == item.id,
            PriceObservation.observed_at >= cutoff_365
        )
        .order_by(desc(PriceObservation.observed_at))
    )
    obs_list = (await db.execute(obs_stmt)).scalars().all()

    current_price = obs_list[0].price_minor if len(obs_list) > 0 else None
    previous_price = obs_list[1].price_minor if len(obs_list) > 1 else None

    change_amount = None
    change_percent = None
    if current_price is not None and previous_price is not None:
        change_amount = current_price - previous_price
        if previous_price > 0:
            change_percent = round(((current_price - previous_price) / previous_price) * 100, 2)

    lowest_365 = None
    lowest_365_at = None
    if obs_list:
        lowest_obs = min(obs_list, key=lambda x: x.price_minor)
        lowest_365 = lowest_obs.price_minor
        lowest_365_at = lowest_obs.observed_at

    target_reached = False
    if item.target_price_minor is not None and current_price is not None:
        target_reached = current_price <= item.target_price_minor

    return HistorySummaryResponse(
        item_id=item.id,
        currency=item.currency or "INR",
        current_price_minor=current_price,
        previous_price_minor=previous_price,
        change_amount=change_amount,
        change_percent=change_percent,
        lowest_365d_price_minor=lowest_365,
        lowest_365d_at=lowest_365_at,
        target_price_minor=item.target_price_minor,
        target_reached=target_reached,
        observation_count=len(obs_list)
    )

@router.post("/{item_id}/refresh", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_item_refresh(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enqueue an immediate price refresh check. Returns 202 Accepted per spec.
    """
    stmt = select(WishlistItem).where(
        WishlistItem.id == item_id,
        WishlistItem.user_id == current_user.id,
        WishlistItem.deleted_at.is_(None)
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise ItemNotFoundException(str(item_id))

    # Fast-forward next_check_at to now
    item.next_check_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "accepted", "message": "Price refresh scheduled", "item_id": str(item.id)}
