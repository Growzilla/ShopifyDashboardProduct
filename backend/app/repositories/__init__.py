"""
Repository package for data access layer.
"""
from app.repositories.base import BaseRepository
from app.repositories.insight import InsightRepository
from app.repositories.shop import ShopRepository

__all__ = [
    "BaseRepository",
    "ShopRepository",
    "InsightRepository",
]
