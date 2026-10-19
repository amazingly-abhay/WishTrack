from datetime import datetime, timezone
import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.entities import User, WishlistItem, PriceObservation
from app.schemas.extension import (
    ExtensionPairRequest,
    ExtensionTokenResponse,
    ExtensionItemCreateRequest,
    ExtensionStatusResponse,
)
from app.schemas.items import ItemResponse
from app.api.v1.endpoints.items import _build_item_response
from app.core.url_validator import validate_and_canonicalize_url
from app.core.security import create_extension_token
from app.core.exceptions import WishTrackException
from app.adapters.registry import registry
from app.api.deps import get_current_user, get_current_extension_user

router = APIRouter(prefix="/extension", tags=["Browser Extension"])

@router.post("/pair", response_model=ExtensionTokenResponse, status_code=status.HTTP_200_OK)
async def pair_extension(
    req: ExtensionPairRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Explicit pairing flow: Authenticated web user authorizes and generates a scoped extension token.
    """
    token = create_extension_token(current_user.id)
    return ExtensionTokenResponse(
        extension_token=token,
        token_type="bearer",
        expires_in=90 * 24 * 3600,
        user_id=current_user.id
    )

@router.get("/status", response_model=ExtensionStatusResponse)
async def extension_status(
    current_user: User = Depends(get_current_extension_user)
):
    """
    Validates extension authorization and returns list of supported automated retailer hosts.
    """
    supported = list(registry._host_map.keys())
    return ExtensionStatusResponse(
        status="authenticated",
        user_id=current_user.id,
        email=current_user.email,
        supported_hosts=supported
    )

@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def extension_add_item(
    req: ExtensionItemCreateRequest,
    current_user: User = Depends(get_current_extension_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Browser extension item addition endpoint:
    - Treats all extension data as untrusted.
    - Performs full SSRF validation & URL canonicalization.
    - Deduplicates by canonical URL per user.
    - Saves initial observation if price is supplied.
    """
    normalized_url, canonical_url, retailer_host = validate_and_canonicalize_url(req.product_url)

    # Deduplication check
    stmt = select(WishlistItem).where(
        WishlistItem.user_id == current_user.id,
        WishlistItem.canonical_url == canonical_url,
        WishlistItem.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    existing_item = result.scalar_one_or_none()
    if existing_item:
        return await _build_item_response(existing_item, db)

    is_supported = registry.is_host_supported(retailer_host)
    tracking_mode = "automatic" if is_supported else "manual"
    now_utc = datetime.now(timezone.utc)

    new_item = WishlistItem(
        user_id=current_user.id,
        product_url=normalized_url,
        canonical_url=canonical_url,
        retailer_host=retailer_host,
        title=req.title,
        image_url=req.image_url,
        currency=req.currency or "INR",
        target_price_minor=req.target_price_minor,
        notes=req.notes,
        tags=["extension"],
        tracking_mode=tracking_mode,
        tracking_status="active",
        is_favorite=False,
        is_archived=False,
        last_checked_at=now_utc if req.price_minor is not None else None,
        next_check_at=now_utc
    )
    db.add(new_item)
    await db.flush()

    if req.price_minor is not None:
        obs = PriceObservation(
            item_id=new_item.id,
            observed_at=now_utc,
            price_minor=req.price_minor,
            currency=new_item.currency,
            availability="in_stock",
            source="extension",
            confidence=1.0,
            raw_price_text=str(req.price_minor / 100)
        )
        db.add(obs)

    await db.commit()
    await db.refresh(new_item)

    return await _build_item_response(new_item, db)
