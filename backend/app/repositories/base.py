"""
Base repository with common CRUD operations.
Implements the Repository pattern for data access abstraction.
"""
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing common database operations.

    Subclasses should set the `model` class attribute to the SQLAlchemy model.
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: UUID | str) -> ModelType | None:
        """Get a single record by its primary key."""
        return await self.session.get(self.model, id)

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Get all records with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: ModelType,
        obj_in: dict[str, Any],
    ) -> ModelType:
        """Update an existing record."""
        for field, value in obj_in.items():
            if value is not None:
                setattr(db_obj, field, value)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelType) -> None:
        """Delete a record."""
        await self.session.delete(db_obj)
        await self.session.flush()

    async def count(self) -> int:
        """Count total records."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
