"""
SQLAlchemy models package.
All models are imported here for easy access and Alembic discovery.
"""
from app.models.code_analysis import (
    AnalysisResult,
    CodeSubmission,
    NotificationPreference,
    SubmissionPriority,
    SubmissionStatus,
    TrafficMetric,
)
from app.models.insight import Insight, InsightSeverity, InsightType
from app.models.order import Order
from app.models.product import Product
from app.models.shop import Shop

__all__ = [
    "Shop",
    "Product",
    "Order",
    "Insight",
    "InsightType",
    "InsightSeverity",
    "CodeSubmission",
    "AnalysisResult",
    "NotificationPreference",
    "TrafficMetric",
    "SubmissionStatus",
    "SubmissionPriority",
]
