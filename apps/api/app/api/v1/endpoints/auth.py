from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.entities import User, NotificationPreference
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.core.config import settings
from app.core.exceptions import WishTrackException
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email is already registered
    stmt = select(User).where(User.email == req.email.lower())
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise WishTrackException(
            code="EMAIL_ALREADY_EXISTS",
            message="An account with this email address already exists.",
            status_code=status.HTTP_409_CONFLICT
        )

    # Hash password with argon2/bcrypt
    hashed_pwd = get_password_hash(req.password)
    new_user = User(
        email=req.email.lower(),
        password_hash=hashed_pwd,
        display_name=req.display_name,
        is_active=True
    )
    db.add(new_user)
    await db.flush()

    # Initialize default notification preferences
    prefs = NotificationPreference(
        user_id=new_user.id,
        in_app_enabled=True,
        web_push_enabled=True,
        price_drop_enabled=True,
        target_reached_enabled=True,
        new_low_enabled=True
    )
    db.add(prefs)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        display_name=new_user.display_name,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )

@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise WishTrackException(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        raise WishTrackException(
            code="ACCOUNT_INACTIVE",
            message="This account is deactivated.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_TTL_MINUTES * 60
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise WishTrackException(
            code="INVALID_TOKEN",
            message="Provided token is not a valid refresh token.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise WishTrackException(
            code="INVALID_TOKEN",
            message="Token subject missing.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    user_id = uuid.UUID(user_id_str)
    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise WishTrackException(
            code="USER_NOT_FOUND",
            message="User associated with this refresh token no longer exists.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_TTL_MINUTES * 60
    )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: User = Depends(get_current_user)):
    # In stateless JWT mode, logout acknowledges successful token discard by client
    return {"status": "ok", "message": "Successfully logged out."}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
