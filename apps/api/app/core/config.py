from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "dev-insecure-secret-key-change-in-prod"
    DATABASE_URL: str = "sqlite+aiosqlite:///./wishtrack.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    WEB_ORIGIN: str = "http://localhost:5173"
    API_ORIGIN: str = "http://localhost:8000"
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 30
    LOG_LEVEL: str = "INFO"
    PRICE_HISTORY_RETENTION_DAYS: int = 365
    DEFAULT_CHECK_INTERVAL_HOURS: int = 12

    VAPID_PUBLIC_KEY: Optional[str] = None
    VAPID_PRIVATE_KEY: Optional[str] = None
    VAPID_SUBJECT: str = "mailto:admin@example.com"
    EMAIL_PROVIDER: Optional[str] = None
    EMAIL_API_KEY: Optional[str] = None

settings = Settings()
