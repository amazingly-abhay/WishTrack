from fastapi import Request
from fastapi.responses import JSONResponse
from app.schemas.common import ErrorResponse, ErrorDetail

class WishTrackException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class ItemNotFoundException(WishTrackException):
    def __init__(self, item_id: str):
        super().__init__(
            code="ITEM_NOT_FOUND",
            message=f"Item with ID '{item_id}' not found.",
            status_code=404
        )

class UnsupportedHostException(WishTrackException):
    def __init__(self, host: str):
        super().__init__(
            code="UNSUPPORTED_HOST",
            message=f"Retailer host '{host}' is not currently supported for automated tracking.",
            status_code=422
        )

class InvalidURLException(WishTrackException):
    def __init__(self, message: str = "Invalid URL supplied."):
        super().__init__(
            code="INVALID_URL",
            message=message,
            status_code=400
        )

async def wishtrack_exception_handler(request: Request, exc: WishTrackException):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details or None
            ),
            request_id=request_id
        ).model_dump()
    )
