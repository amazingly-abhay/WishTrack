from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.middleware import RequestContextMiddleware
from app.core.ratelimit import RateLimitMiddleware
from app.core.exceptions import WishTrackException, wishtrack_exception_handler
from app.api.v1.router import api_v1_router

def create_application() -> FastAPI:
    application = FastAPI(
        title="WishTrack API",
        version="0.1.0",
        description="Single source of truth API for WishTrack wishlist tracking PWA and extension.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json"
    )

    # Middleware setup (LIFO order: RateLimit runs inside RequestContext)
    application.add_middleware(RateLimitMiddleware, requests_per_minute=200, auth_requests_per_minute=40)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.WEB_ORIGIN,
            "http://localhost:5173",
            "http://localhost:3000",
        ],
        allow_origin_regex=r"https://.*\.onrender\.com",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    application.add_exception_handler(WishTrackException, wishtrack_exception_handler)

    # Include routes
    application.include_router(api_v1_router)

    return application

app = create_application()
