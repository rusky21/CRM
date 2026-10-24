import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.account import Account


class Proxy(Base):
    """Network proxy entity used to isolate MTProto client connections."""

    __tablename__ = "proxies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    protocol: Mapped[str] = mapped_column(String(20), default="socks5", nullable=False)  # socks5 or http
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="proxy")

    def to_telethon_proxy(self) -> Dict[str, Any]:
        """
        Converts the database proxy record to Telethon / python-socks compatible dict.
        """
        proxy_dict: Dict[str, Any] = {
            "proxy_type": self.protocol.lower(),
            "addr": self.host,
            "port": self.port,
            "rdns": True,
        }
        if self.username:
            proxy_dict["username"] = self.username
        if self.password:
            proxy_dict["password"] = self.password
        return proxy_dict

    def __repr__(self) -> str:
        return f"<Proxy {self.protocol}://{self.host}:{self.port} (active={self.is_active})>"
