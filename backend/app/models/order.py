"""
Order model - represents a Shopify order.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.shop import Shop


class Order(Base):
    """Shopify order with line items and financial data."""

    __tablename__ = "orders"

    # Shopify order ID
    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        index=True,
    )

    # Order number for display
    order_number: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(50))  # e.g., "#1001"

    # Financial
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_tax: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_discounts: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Status
    financial_status: Mapped[str] = mapped_column(String(50), default="pending")
    fulfillment_status: Mapped[Optional[str]] = mapped_column(String(50))

    # Customer
    customer_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255))

    # Line items (stored as JSON)
    line_items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
    )
    line_item_count: Mapped[int] = mapped_column(Integer, default=0)

    # Discount codes applied
    discount_codes: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB,
        default=list,
    )

    # Timestamps
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    shop: Mapped["Shop"] = relationship("Shop", back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order {self.name}>"
