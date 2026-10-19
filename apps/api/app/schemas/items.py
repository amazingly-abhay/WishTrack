from datetime import datetime
import uuid
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

class ItemPreviewRequest(BaseModel):
    product_url: str = Field(..., description="The URL of the product to preview")

class ItemPreviewResponse(BaseModel):
    product_url: str
    canonical_url: str
    retailer_host: str
    is_supported: bool
    title: Optional[str] = None
    image_url: Optional[str] = None
    price_minor: Optional[int] = None
    currency: Optional[str] = None
    availability: Optional[str] = "unknown"

class ItemCreateRequest(BaseModel):
    product_url: str
    canonical_url: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=512)
    image_url: Optional[str] = None
    price_minor: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    target_price_minor: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    wishlist_id: Optional[uuid.UUID] = Field(None, description="Optional custom wishlist collection ID")
    source: str = Field("manual", description="Source of item creation (manual or extension)")

class ItemUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    target_price_minor: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    wishlist_id: Optional[uuid.UUID] = None
    is_favorite: Optional[bool] = None
    tracking_mode: Optional[str] = None

class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    wishlist_id: Optional[uuid.UUID] = None
    title: str
    product_url: str
    canonical_url: str
    retailer_host: str
    image_url: Optional[str] = None
    currency: Optional[str] = None
    current_price_minor: Optional[int] = None
    previous_price_minor: Optional[int] = None
    lowest_365d_price_minor: Optional[int] = None
    lowest_365d_at: Optional[datetime] = None
    target_price_minor: Optional[int] = None
    tracking_mode: str
    tracking_status: str
    is_favorite: bool
    is_archived: bool
    tags: List[str]
    notes: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    next_check_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
