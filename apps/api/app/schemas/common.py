from datetime import datetime
from typing import Optional, Generic, TypeVar, List, Any
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    has_next: bool

class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ReadyResponse(BaseModel):
    status: str
    database: bool
    redis: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
