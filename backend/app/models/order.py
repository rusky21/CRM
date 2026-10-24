import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    BigInteger,
    Numeric,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.account import Account


class OrderStatus(str, enum.Enum):
    NEW = "NEW"                      # Новый заказ / лид
    IN_PROGRESS = "IN_PROGRESS"      # В работе
    PAID = "PAID"                    # Оплачен
    COMPLETED = "COMPLETED"          # Выполнен
    CANCELLED = "CANCELLED"          # Отменен


class Order(Base):
    """
    Represents a client deal/order created directly within a Telegram conversation thread.
    """

    __tablename__ = "orders"

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

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.00, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB", nullable=False)

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status_enum"),
        default=OrderStatus.NEW,
        nullable=False,
        index=True,
    )

    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    account: Mapped["Account"] = relationship("Account")

    __table_args__ = (
        Index("ix_orders_account_peer", "account_id", "peer_id"),
        Index("ix_orders_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Order {self.title} ({self.amount} {self.currency}) status={self.status.value}>"
