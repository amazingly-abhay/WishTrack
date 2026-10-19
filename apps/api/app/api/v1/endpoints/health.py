from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.common import HealthResponse, ReadyResponse

router = APIRouter(tags=["Health & Status"])

@router.get("/health/live", response_model=HealthResponse, summary="Liveness Probe")
async def health_live():
    """Returns 200 OK if the FastAPI process is alive."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc)
    )

@router.get("/health/ready", response_model=ReadyResponse, summary="Readiness Probe")
async def health_ready(db: AsyncSession = Depends(get_db)):
    """Checks database connectivity to determine readiness to serve traffic."""
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # In local/testing mode, treat Redis as true or skip if not connected
    redis_ok = True

    overall_status = "ok" if (db_ok and redis_ok) else "degraded"
    status_code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content=ReadyResponse(
            status=overall_status,
            database=db_ok,
            redis=redis_ok,
            timestamp=datetime.now(timezone.utc)
        ).model_dump(mode="json")
    )
