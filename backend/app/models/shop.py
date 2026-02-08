"""
Shop model - represents a connected Shopify store.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.insight import Insight
    from app.models.order import Order
    from app.models.product import Product


class Shop(Base):
    """Shopify shop model with encrypted access token storage."""

    __tablename__ = "shops"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    domain: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    access_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    scopes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Settings
    deep_mode_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    clarity_project_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Sync tracking
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sync_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="shop",
        cascade="all, delete-orphan",
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="shop",
        cascade="all, delete-orphan",
    )
    insights: Mapped[list["Insight"]] = relationship(
        "Insight",
        back_populates="shop",
        cascade="all, delete-orphan",
    )
    # COMMENTED OUT FOR MVP - CodeSubmission model not imported
    # code_submissions: Mapped[list["CodeSubmission"]] = relationship(
    #     "CodeSubmission",
    #     back_populates="shop",
    #     cascade="all, delete-orphan",
    # )

    def __repr__(self) -> str:
        return f"<Shop {self.domain}>"
