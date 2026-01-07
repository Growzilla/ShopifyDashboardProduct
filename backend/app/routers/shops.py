"""
Shop management API routes.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import get_logger
from app.core.security import encrypt_token
from app.repositories.shop import ShopRepository
from app.schemas.shop import (
    ShopCreate,
    ShopResponse,
    ShopSyncRequest,
    ShopSyncResponse,
    ShopUpdate,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/shops", tags=["shops"])


async def get_shop_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ShopRepository:
    """Dependency to get shop repository."""
    return ShopRepository(session)


@router.post("", response_model=ShopResponse, status_code=status.HTTP_201_CREATED)
async def create_shop(
    shop_data: ShopCreate,
    repo: Annotated[ShopRepository, Depends(get_shop_repository)],
) -> ShopResponse:
    """
    Register a shop after OAuth completion.

    Called by the auth-proxy after successful Shopify OAuth.
    Encrypts and stores the access token securely.
    """
    encrypted_token = encrypt_token(shop_data.access_token)

    shop, created = await repo.create_or_update(
        domain=shop_data.domain,
        access_token_encrypted=encrypted_token,
        scopes=shop_data.scopes,
    )

    action = "Created" if created else "Updated"
    logger.info(f"{action} shop", domain=shop_data.domain)

    return ShopResponse.model_validate(shop)


@router.get("/{shop_domain}", response_model=ShopResponse)
async def get_shop(
    shop_domain: str,
    repo: Annotated[ShopRepository, Depends(get_shop_repository)],
) -> ShopResponse:
    """Get shop details by domain."""
    shop = await repo.get_by_domain(shop_domain)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found",
        )
    return ShopResponse.model_validate(shop)


@router.patch("/{shop_domain}", response_model=ShopResponse)
async def update_shop(
    shop_domain: str,
    shop_update: ShopUpdate,
    repo: Annotated[ShopRepository, Depends(get_shop_repository)],
) -> ShopResponse:
    """Update shop settings."""
    shop = await repo.get_by_domain(shop_domain)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found",
        )

    update_data = shop_update.model_dump(exclude_unset=True, by_alias=False)
    shop = await repo.update(shop, update_data)

    logger.info("Updated shop settings", domain=shop_domain)
    return ShopResponse.model_validate(shop)


@router.delete("/{shop_domain}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shop(
    shop_domain: str,
    repo: Annotated[ShopRepository, Depends(get_shop_repository)],
) -> None:
    """
    Delete shop and all associated data.

    Called on app uninstall. Implements GDPR data deletion.
    """
    shop = await repo.get_by_domain(shop_domain)
    if shop:
        await repo.delete(shop)
        logger.info("Deleted shop and data", domain=shop_domain)


@router.post("/{shop_id}/sync", response_model=ShopSyncResponse)
async def trigger_sync(
    shop_id: UUID,
    sync_request: ShopSyncRequest,
    background_tasks: BackgroundTasks,
    repo: Annotated[ShopRepository, Depends(get_shop_repository)],
) -> ShopSyncResponse:
    """Trigger a data sync for a shop."""
    shop = await repo.get_by_id(shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found",
        )

    # Mark as syncing
    await repo.update_sync_status(shop, "syncing")

    # Queue background sync
    from app.services.data_sync import sync_shop_data

    background_tasks.add_task(
        sync_shop_data,
        shop_id=shop_id,
        full_sync=sync_request.full_sync,
    )

    logger.info("Sync triggered", shop_id=str(shop_id))

    return ShopSyncResponse(
        message="Sync started",
        shop_id=shop_id,
        sync_started=True,
    )
