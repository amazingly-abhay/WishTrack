from datetime import datetime
import uuid
from typing import Optional
from pydantic import BaseModel, Field

class ExtensionPairRequest(BaseModel):
    client_name: Optional[str] = Field("Chromium Browser Extension", max_length=128)

class ExtensionTokenResponse(BaseModel):
    extension_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: uuid.UUID

class ExtensionItemCreateRequest(BaseModel):
    product_url: str
    title: str = Field(..., min_length=1, max_length=512)
    image_url: Optional[str] = None
    price_minor: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    target_price_minor: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    source: str = "extension"

class ExtensionStatusResponse(BaseModel):
    status: str = "authenticated"
    user_id: uuid.UUID
    email: str
    supported_hosts: list[str]
