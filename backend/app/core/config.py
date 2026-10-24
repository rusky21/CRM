import binascii
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime settings and environment variables."""

    PROJECT_NAME: str = "Telegram Multi-Account CRM"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # 32-byte AES key in hex (64 hex characters)
    SECRET_ENCRYPTION_KEY: str = Field(
        ...,
        description="Hex-encoded 32-byte secret key for AES-256-GCM session encryption",
    )

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/tg_crm",
        description="PostgreSQL async connection URI",
    )

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URI",
    )

    # Optional global fallbacks for Telegram client credentials
    DEFAULT_TELEGRAM_API_ID: Optional[int] = None
    DEFAULT_TELEGRAM_API_HASH: Optional[str] = None

    # Admin Alert Bot
    ADMIN_BOT_TOKEN: Optional[str] = None
    ADMIN_CHAT_ID: Optional[int] = None

    # Telegram Mini App (TMA) Navigation Settings
    TMA_BOT_USERNAME: str = Field(
        default="StudioCrmAdminBot",
        description="Username of the admin bot hosting the Mini App",
    )
    TMA_APP_SHORT_NAME: str = Field(
        default="app",
        description="Short name of the Mini App configured in @BotFather",
    )

    # StudioCRM Integration Settings
    STUDIOCRM_SERVER_URL: str = Field(
        default="http://212.67.15.218:5000",
        description="Base URL for the existing StudioCRM ASP.NET backend",
    )
    STUDIOCRM_SQLITE_PATH: str = Field(
        default="studiocrm.db",
        description="Path to local fallback SQLite database for StudioCRM",
    )

    # Multi-Server Split Deployment CORS Configuration
    FRONTEND_ORIGIN_DOMAIN: str = Field(
        default="*",
        description="Allowed CORS origin domain from Server 1 (e.g. crm.domain.com)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("SECRET_ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        clean_v = v.strip()
        try:
            raw_bytes = binascii.unhexlify(clean_v)
            if len(raw_bytes) != 32:
                raise ValueError(
                    f"SECRET_ENCRYPTION_KEY must be exactly 32 bytes (64 hex characters), got {len(raw_bytes)} bytes."
                )
        except binascii.Error as exc:
            raise ValueError("SECRET_ENCRYPTION_KEY must be valid hex-encoded string") from exc
        return clean_v


settings = Settings()
