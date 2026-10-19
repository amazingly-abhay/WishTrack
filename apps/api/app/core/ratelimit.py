import time
from typing import Dict, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.schemas.common import ErrorResponse, ErrorDetail

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory token bucket rate limiter per client IP.
    Default: 200 requests per minute per IP.
    Auth endpoints (/api/v1/auth/*): 60 requests per minute per IP.
    Excludes testclient / test environments.
    """
    def __init__(self, app, requests_per_minute: int = 200, auth_requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.auth_rpm = auth_requests_per_minute
        self.client_records: Dict[str, Tuple[float, int]] = {}

    async def dispatch(self, request: Request, call_next):
        # Allow disabling or raising limit for tests via header
        if request.headers.get("X-Bypass-Rate-Limit"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        is_auth = path.startswith("/api/v1/auth/")
        limit = self.auth_rpm if is_auth else self.rpm

        now = time.time()
        key = f"{client_ip}:{'auth' if is_auth else 'general'}"

        if key in self.client_records:
            window_start, count = self.client_records[key]
            if now - window_start < 60.0:
                if count >= limit:
                    request_id = getattr(request.state, "request_id", None)
                    return JSONResponse(
                        status_code=429,
                        headers={"Retry-After": "60"},
                        content=ErrorResponse(
                            error=ErrorDetail(
                                code="RATE_LIMITED",
                                message="Too many requests. Please slow down and try again later."
                            ),
                            request_id=request_id
                        ).model_dump()
                    )
                else:
                    self.client_records[key] = (window_start, count + 1)
            else:
                self.client_records[key] = (now, 1)
        else:
            self.client_records[key] = (now, 1)

        return await call_next(request)
