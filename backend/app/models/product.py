"""
Product model - represents a Shopify product.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.shop import Shop


class Product(Base):
    """Shopify product with inventory and metrics."""

    __tablename__ = "products"

    # Shopify product ID (not UUID, it's a GID)
    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        index=True,
    )

    # Product details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    handle: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    product_type: Mapped[Optional[str]] = mapped_column(String(255))
    vendor: Mapped[Optional[str]] = mapped_column(String(255))

    # Inventory
    total_inventory: Mapped[int] = mapped_column(Integer, default=0)
    inventory_tracked: Mapped[bool] = mapped_column(default=True)

    # Pricing
    price_min: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    price_max: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))

    # Collections (stored as JSON array)
    collections: Mapped[Optional[list[str]]] = mapped_column(
        JSONB,
        default=list,
    )

    # Variants data (stored as JSON)
    variants: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        default=dict,
    )

    # Images
    featured_image_url: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    shop: Mapped["Shop"] = relationship("Shop", back_populates="products")

    def __repr__(self) -> str:
        return f"<Product {self.title[:30]}>"
