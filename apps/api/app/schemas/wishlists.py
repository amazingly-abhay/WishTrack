from datetime import datetime
import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class WishlistCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the wishlist")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the wishlist")

class WishlistUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class WishlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_default: bool
    item_count: int = 0
    created_at: datetime
    updated_at: datetime
