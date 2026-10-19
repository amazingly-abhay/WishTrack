from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, items, notifications, extension, wishlists

api_v1_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(items.router)
api_v1_router.include_router(wishlists.router)
api_v1_router.include_router(notifications.router)
api_v1_router.include_router(extension.router)
