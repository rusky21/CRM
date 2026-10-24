import enum
import uuid
from datetime import datetime
from typing import Optional, Any, Dict, TYPE_CHECKING
from sqlalchemy import String, Integer, BigInteger, Enum, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.proxy import Proxy


class AccountStatus(str, enum.Enum):
    NEEDS_AUTH = "NEEDS_AUTH"      # Requires phone code or 2FA login
    CONNECTING = "CONNECTING"      # In process of MTProto handshake
    ACTIVE = "ACTIVE"              # Authorized, connected, listening for updates
    OFFLINE = "OFFLINE"            # Stopped intentionally
    FLOOD_WAIT = "FLOOD_WAIT"      # Rate limited by Telegram MTProto
    BANNED = "BANNED"              # Telegram revoked session or deleted account
    PAUSED = "PAUSED"              # Temporarily suspended by operator


class Account(Base):
    """Represents a managed Telegram user account session."""

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    custom_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    telegram_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, unique=True, index=True, nullable=True
    )
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    about: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Optional custom MTProto App credentials (defaults to system fallback if null)
    api_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    api_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # AES-256-GCM encrypted Telethon StringSession
    encrypted_session: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    proxy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proxies.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status_enum"),
        default=AccountStatus.NEEDS_AUTH,
        nullable=False,
    )

    # Realistic device fingerprint parameters (device_model, system_version, app_version, lang_code, system_lang_code)
    device_fingerprint: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    proxy: Mapped[Optional["Proxy"]] = relationship("Proxy", back_populates="accounts")

    def __repr__(self) -> str:
        return f"<Account {self.title} ({self.phone}) - status={self.status.value}>"
