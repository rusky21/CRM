import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, BigInteger, Text, DateTime, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.account import Account
    from backend.app.models.message import Message


class Dialogue(Base):
    """Represents a conversation/chat thread between a managed Account and a Telegram peer."""

    __tablename__ = "dialogues"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    peer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    peer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    peer_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    account: Mapped["Account"] = relationship("Account")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="dialogue", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("account_id", "peer_id", name="uq_dialogues_account_peer"),
        Index("ix_dialogues_account_updated", "account_id", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Dialogue {self.peer_name} (peer_id={self.peer_id}, unread={self.unread_count})>"
