import enum
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    BigInteger,
    Boolean,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.dialogue import Dialogue
    from backend.app.models.account import Account


class MessageStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"      # Inbound message received from Telegram
    PENDING = "PENDING"        # Outbound message queued in CRM
    DELIVERED = "DELIVERED"    # Outbound message successfully sent to Telegram
    READ = "READ"              # Message read by peer or user


class Message(Base):
    """Represents an individual chat message in a dialogue."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dialogue_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dialogues.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    peer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    is_outgoing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    media_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    media_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, name="message_status_enum"),
        default=MessageStatus.RECEIVED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    dialogue: Mapped[Optional["Dialogue"]] = relationship("Dialogue", back_populates="messages")
    account: Mapped["Account"] = relationship("Account")

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "peer_id",
            "telegram_message_id",
            name="uq_messages_account_peer_telegram_id",
        ),
        Index("ix_messages_account_peer_created", "account_id", "peer_id", "created_at"),
    )

    def __repr__(self) -> str:
        direction = "OUT" if self.is_outgoing else "IN"
        return f"<Message {self.telegram_message_id} ({direction}) text='{self.text[:20] if self.text else ''}'>"
