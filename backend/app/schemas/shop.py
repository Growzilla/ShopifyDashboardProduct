"""
Shop Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ShopBase(BaseModel):
    """Base shop schema with common fields."""

    domain: str = Field(..., min_length=1, max_length=255)


class ShopCreate(ShopBase):
    """Schema for creating a shop after OAuth."""

    access_token: str = Field(..., alias="accessToken")
    scopes: str

    model_config = ConfigDict(populate_by_name=True)


class ShopUpdate(BaseModel):
    """Schema for updating shop settings."""

    deep_mode_enabled: Optional[bool] = Field(None, alias="deepModeEnabled")
    clarity_project_id: Optional[str] = Field(None, alias="clarityProjectId")

    model_config = ConfigDict(populate_by_name=True)


class ShopResponse(ShopBase):
    """Schema for shop API responses."""

    id: UUID
    scopes: str
    deep_mode_enabled: bool = Field(alias="deepModeEnabled")
    clarity_project_id: Optional[str] = Field(None, alias="clarityProjectId")
    last_sync_at: Optional[datetime] = Field(None, alias="lastSyncAt")
    sync_status: str = Field(alias="syncStatus")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ShopSyncRequest(BaseModel):
    """Schema for triggering a shop sync."""

    full_sync: bool = Field(False, alias="fullSync")

    model_config = ConfigDict(populate_by_name=True)


class ShopSyncResponse(BaseModel):
    """Schema for sync operation response."""

    message: str
    shop_id: UUID = Field(alias="shopId")
    sync_started: bool = Field(alias="syncStarted")

    model_config = ConfigDict(populate_by_name=True)
