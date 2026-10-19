from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    item_id: Optional[uuid.UUID] = None
    observation_id: Optional[int] = None
    type: str # target_reached, price_drop, new_365d_low, tracking_error
    title: str
    body: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str
    read_at: Optional[datetime] = None
    created_at: datetime

class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    in_app_enabled: bool
    web_push_enabled: bool
    email_enabled: bool
    price_drop_enabled: bool
    target_reached_enabled: bool
    new_low_enabled: bool
    minimum_drop_percent: Optional[float] = None
    updated_at: datetime

class NotificationPreferenceUpdateRequest(BaseModel):
    in_app_enabled: Optional[bool] = None
    web_push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    price_drop_enabled: Optional[bool] = None
    target_reached_enabled: Optional[bool] = None
    new_low_enabled: Optional[bool] = None
    minimum_drop_percent: Optional[float] = Field(None, ge=0.0, le=100.0)

class PushSubscriptionCreateRequest(BaseModel):
    endpoint: str
    p256dh_key: str
    auth_key: str

class PushSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    endpoint: str
    created_at: datetime
    disabled_at: Optional[datetime] = None
