from datetime import datetime, timezone
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update

from app.db.session import get_db
from app.models.entities import User, Wishlist, WishlistItem
from app.schemas.wishlists import WishlistCreateRequest, WishlistUpdateRequest, WishlistResponse
from app.api.v1.endpoints.auth import get_current_user
from app.core.exceptions import WishTrackException

router = APIRouter(prefix="/wishlists", tags=["Wishlists"])

async def get_or_create_default_wishlist(user_id: uuid.UUID, db: AsyncSession) -> Wishlist:
    stmt = select(Wishlist).where(Wishlist.user_id == user_id, Wishlist.is_default == True)
    result = await db.execute(stmt)
    default_wl = result.scalar_one_or_none()
    if not default_wl:
        # Check if user has any wishlist at all
        any_stmt = select(Wishlist).where(Wishlist.user_id == user_id).order_by(Wishlist.created_at.asc())
        first_wl = (await db.execute(any_stmt)).scalar_one_or_none()
        if first_wl:
            first_wl.is_default = True
            await db.commit()
            await db.refresh(first_wl)
            return first_wl
        
        default_wl = Wishlist(
            user_id=user_id,
            name="My Wishlist",
            description="Default wishlist collection",
            is_default=True
        )
        db.add(default_wl)
        await db.commit()
        await db.refresh(default_wl)
    return default_wl

@router.get("", response_model=List[WishlistResponse])
async def list_wishlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all wishlist collections owned by the current user, including item counts.
    Ensures a default wishlist exists.
    """
    await get_or_create_default_wishlist(current_user.id, db)

    # Subquery for item counts
    count_subq = (
        select(
            WishlistItem.wishlist_id,
            func.count(WishlistItem.id).label("item_count")
        )
        .where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.deleted_at.is_(None),
            WishlistItem.is_archived == False
        )
        .group_by(WishlistItem.wishlist_id)
        .subquery()
    )

    stmt = (
        select(
            Wishlist,
            func.coalesce(count_subq.c.item_count, 0).label("item_count")
        )
        .outerjoin(count_subq, Wishlist.id == count_subq.c.wishlist_id)
        .where(Wishlist.user_id == current_user.id)
        .order_by(Wishlist.is_default.desc(), Wishlist.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Also handle legacy items where wishlist_id is NULL by associating them with the default wishlist
    null_count_stmt = select(func.count(WishlistItem.id)).where(
        WishlistItem.user_id == current_user.id,
        WishlistItem.wishlist_id.is_(None),
        WishlistItem.deleted_at.is_(None),
        WishlistItem.is_archived == False
    )
    null_items_count = (await db.execute(null_count_stmt)).scalar() or 0

    responses = []
    for wl, cnt in rows:
        total_items = cnt + (null_items_count if wl.is_default else 0)
        responses.append(
            WishlistResponse(
                id=wl.id,
                name=wl.name,
                description=wl.description,
                is_default=wl.is_default,
                item_count=total_items,
                created_at=wl.created_at,
                updated_at=wl.updated_at
            )
        )
    return responses

@router.post("", response_model=WishlistResponse, status_code=status.HTTP_201_CREATED)
async def create_wishlist(
    req: WishlistCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new custom wishlist collection.
    """
    new_wl = Wishlist(
        user_id=current_user.id,
        name=req.name.strip(),
        description=req.description.strip() if req.description else None,
        is_default=False
    )
    db.add(new_wl)
    await db.commit()
    await db.refresh(new_wl)
    return WishlistResponse(
        id=new_wl.id,
        name=new_wl.name,
        description=new_wl.description,
        is_default=new_wl.is_default,
        item_count=0,
        created_at=new_wl.created_at,
        updated_at=new_wl.updated_at
    )

@router.patch("/{wishlist_id}", response_model=WishlistResponse)
async def update_wishlist(
    wishlist_id: uuid.UUID,
    req: WishlistUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update wishlist name or description.
    """
    stmt = select(Wishlist).where(Wishlist.id == wishlist_id, Wishlist.user_id == current_user.id)
    wl = (await db.execute(stmt)).scalar_one_or_none()
    if not wl:
        raise WishTrackException(code="WISHLIST_NOT_FOUND", message="Wishlist not found", status_code=404)

    if req.name is not None:
        wl.name = req.name.strip()
    if req.description is not None:
        wl.description = req.description.strip()
    wl.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(wl)

    # Count items
    cnt_stmt = select(func.count(WishlistItem.id)).where(
        WishlistItem.wishlist_id == wl.id,
        WishlistItem.deleted_at.is_(None),
        WishlistItem.is_archived == False
    )
    cnt = (await db.execute(cnt_stmt)).scalar() or 0

    return WishlistResponse(
        id=wl.id,
        name=wl.name,
        description=wl.description,
        is_default=wl.is_default,
        item_count=cnt,
        created_at=wl.created_at,
        updated_at=wl.updated_at
    )

@router.delete("/{wishlist_id}", status_code=status.HTTP_200_OK)
async def delete_wishlist(
    wishlist_id: uuid.UUID,
    delete_items: bool = Query(False, description="If true, soft deletes all items in list; if false moves them to default list"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a custom wishlist. Cannot delete default wishlist.
    """
    stmt = select(Wishlist).where(Wishlist.id == wishlist_id, Wishlist.user_id == current_user.id)
    wl = (await db.execute(stmt)).scalar_one_or_none()
    if not wl:
        raise WishTrackException(code="WISHLIST_NOT_FOUND", message="Wishlist not found", status_code=404)

    if wl.is_default:
        raise WishTrackException(code="CANNOT_DELETE_DEFAULT_LIST", message="Cannot delete the default wishlist", status_code=400)

    default_wl = await get_or_create_default_wishlist(current_user.id, db)

    if delete_items:
        # Soft delete items in this list
        upd = (
            update(WishlistItem)
            .where(WishlistItem.wishlist_id == wl.id)
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await db.execute(upd)
    else:
        # Move items to default wishlist
        upd = (
            update(WishlistItem)
            .where(WishlistItem.wishlist_id == wl.id)
            .values(wishlist_id=default_wl.id)
        )
        await db.execute(upd)

    await db.delete(wl)
    await db.commit()
    return {"status": "ok", "message": "Wishlist deleted successfully"}
