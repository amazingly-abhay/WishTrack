from datetime import datetime
import uuid
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class ObservationCreateRequest(BaseModel):
    price_minor: int = Field(..., ge=0, description="Price in minor units (e.g. paise/cents)")
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    availability: Optional[str] = Field("in_stock", description="in_stock, out_of_stock, or unknown")
    source: Optional[str] = Field("manual", description="official_api, adapter, extension, manual")
    raw_price_text: Optional[str] = None

class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: uuid.UUID
    observed_at: datetime
    price_minor: int
    currency: str
    availability: str
    source: str
    raw_price_text: Optional[str] = None
    created_at: datetime

class HistorySummaryResponse(BaseModel):
    item_id: uuid.UUID
    currency: str
    current_price_minor: Optional[int] = None
    previous_price_minor: Optional[int] = None
    change_amount: Optional[int] = None
    change_percent: Optional[float] = None
    lowest_365d_price_minor: Optional[int] = None
    lowest_365d_at: Optional[datetime] = None
    target_price_minor: Optional[int] = None
    target_reached: bool = False
    observation_count: int
