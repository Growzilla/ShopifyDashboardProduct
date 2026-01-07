"""
Shop repository for data access operations.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.models.shop import Shop
from app.repositories.base import BaseRepository


class ShopRepository(BaseRepository[Shop]):
    """Repository for Shop model operations."""

    model = Shop

    async def get_by_domain(self, domain: str) -> Optional[Shop]:
        """Get a shop by its Shopify domain."""
        stmt = select(Shop).where(Shop.domain == domain)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        domain: str,
        access_token_encrypted: str,
        scopes: str,
    ) -> tuple[Shop, bool]:
        """
        Create a new shop or update existing one.
        Returns (shop, created) tuple.
        """
        existing = await self.get_by_domain(domain)

        if existing:
            existing.access_token_encrypted = access_token_encrypted
            existing.scopes = scopes
            await self.session.flush()
            await self.session.refresh(existing)
            return existing, False

        shop = Shop(
            domain=domain,
            access_token_encrypted=access_token_encrypted,
            scopes=scopes,
        )
        self.session.add(shop)
        await self.session.flush()
        await self.session.refresh(shop)
        return shop, True

    async def update_sync_status(
        self,
        shop: Shop,
        status: str,
        sync_time: Optional[datetime] = None,
    ) -> Shop:
        """Update shop sync status and timestamp."""
        shop.sync_status = status
        if sync_time:
            shop.last_sync_at = sync_time
        elif status == "completed":
            shop.last_sync_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(shop)
        return shop

    async def get_shops_needing_sync(
        self,
        hours_since_last_sync: int = 24,
    ) -> list[Shop]:
        """Get shops that haven't synced in the specified hours."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_since_last_sync)
        stmt = select(Shop).where(
            (Shop.last_sync_at.is_(None)) | (Shop.last_sync_at < cutoff)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
