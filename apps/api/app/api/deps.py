import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.entities import User
from app.core.security import decode_token
from app.core.exceptions import WishTrackException

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not credentials or not credentials.credentials:
        raise WishTrackException(
            code="AUTH_REQUIRED",
            message="Authentication credentials were not provided.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise WishTrackException(
            code="INVALID_TOKEN",
            message="Invalid token type.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise WishTrackException(
            code="INVALID_TOKEN",
            message="Token subject missing.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise WishTrackException(
            code="INVALID_TOKEN",
            message="Malformed user ID in token.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise WishTrackException(
            code="USER_NOT_FOUND",
            message="User associated with this token no longer exists.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    return user

async def get_current_extension_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validates either standard user access tokens or scoped extension tokens.
    """
    if not credentials or not credentials.credentials:
        raise WishTrackException(
            code="AUTH_REQUIRED",
            message="Extension authentication credentials were not provided.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    payload = decode_token(credentials.credentials)
    token_type = payload.get("type")
    if token_type not in ("access", "extension"):
        raise WishTrackException(
            code="INVALID_TOKEN",
            message="Invalid token type for extension access.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise WishTrackException(
            code="INVALID_TOKEN",
            message="Token subject missing.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise WishTrackException(
            code="INVALID_TOKEN",
            message="Malformed user ID in token.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise WishTrackException(
            code="USER_NOT_FOUND",
            message="User associated with this token no longer exists.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    return user
