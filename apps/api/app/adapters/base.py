from datetime import datetime, timezone
from typing import Protocol, Optional, Set
from pydantic import BaseModel, Field

class ProductSnapshot(BaseModel):
    canonical_url: str
    title: str
    image_url: Optional[str] = None
    price_minor: int = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    availability: str = Field("in_stock", description="in_stock, out_of_stock, unknown")
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "adapter"
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    adapter_name: str
    adapter_version: str = "1.0.0"
    raw_price_text: Optional[str] = None

class RetailerAdapter(Protocol):
    adapter_name: str
    supported_hosts: Set[str]

    async def fetch_product(self, url: str) -> ProductSnapshot:
        """Fetch through an allowed method and return normalized ProductSnapshot."""
        ...
