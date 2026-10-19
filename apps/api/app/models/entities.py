import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String, Boolean, BigInteger, Integer, DateTime, Text, Numeric,
    ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID, utc_now

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    wishlists: Mapped[List["Wishlist"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    items: Mapped[List["WishlistItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    push_subscriptions: Mapped[List["PushSubscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped[Optional["NotificationPreference"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Wishlist(Base):
    __tablename__ = "wishlists"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_wishlists_user_created", "user_id", "created_at"),
    )

    user: Mapped["User"] = relationship(back_populates="wishlists")
    items: Mapped[List["WishlistItem"]] = relationship(back_populates="wishlist")


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wishlist_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("wishlists.id", ondelete="SET NULL"), nullable=True)
    product_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    retailer_host: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    target_price_minor: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tracking_mode: Mapped[str] = mapped_column(String(32), default="automatic", nullable=False) # automatic, manual, unsupported, paused
    tracking_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False) # active, degraded, failed, paused
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Constraints & Indexes
    __table_args__ = (
        UniqueConstraint("user_id", "canonical_url", name="uq_wishlist_items_user_canonical_url"),
        Index("ix_wishlist_items_user_archive_created", "user_id", "is_archived", "created_at"),
        Index("ix_wishlist_items_status_next_check", "tracking_status", "next_check_at"),
        Index("ix_wishlist_items_wishlist_id", "wishlist_id"),
    )

    user: Mapped["User"] = relationship(back_populates="items")
    wishlist: Mapped[Optional["Wishlist"]] = relationship(back_populates="items")
    observations: Mapped[List["PriceObservation"]] = relationship(back_populates="item", cascade="all, delete-orphan")


class PriceObservation(Base):
    __tablename__ = "price_observations"

    # In SQLite, INTEGER PRIMARY KEY auto-increments automatically. In PostgreSQL, BigInteger with variant works as BIGSERIAL.
    id: Mapped[int] = mapped_column(Integer().with_variant(BigInteger, "postgresql"), primary_key=True, autoincrement=True)
    item_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("wishlist_items.id", ondelete="CASCADE"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    availability: Mapped[str] = mapped_column(String(32), default="in_stock", nullable=False) # in_stock, out_of_stock, unknown
    source: Mapped[str] = mapped_column(String(32), default="adapter", nullable=False) # official_api, adapter, extension, manual
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(4, 3), nullable=True)
    raw_price_text: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_price_observations_item_observed", "item_id", "observed_at"),
    )

    item: Mapped["WishlistItem"] = relationship(back_populates="observations")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("wishlist_items.id", ondelete="SET NULL"), nullable=True)
    observation_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False) # target_reached, price_drop, new_365d_low, etc.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe_key"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    user: Mapped["User"] = relationship(back_populates="notifications")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    p256dh_key: Mapped[str] = mapped_column(Text, nullable=False)
    auth_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="push_subscriptions")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    web_push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    price_drop_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    target_reached_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    new_low_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    minimum_drop_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    quiet_hours: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user: Mapped["User"] = relationship(back_populates="preferences")
