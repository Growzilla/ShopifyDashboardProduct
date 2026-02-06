"""
SQLAlchemy models package.
All models are imported here for easy access and Alembic discovery.

MVP SIMPLIFICATION: Code analysis models commented out - not core value proposition.
To re-enable: uncomment the code_analysis imports and add back to __all__.
"""
# COMMENTED OUT FOR MVP - Code analysis feature models:
# from app.models.code_analysis import (
#     AnalysisResult,
#     CodeSubmission,
#     NotificationPreference,
#     SubmissionPriority,
#     SubmissionStatus,
#     TrafficMetric,
# )
from app.models.insight import Insight, InsightSeverity, InsightType
from app.models.order import Order
from app.models.product import Product
from app.models.shop import Shop

__all__ = [
    # Core MVP models:
    "Shop",
    "Product",
    "Order",
    "Insight",
    "InsightType",
    "InsightSeverity",
    # COMMENTED OUT FOR MVP - Code analysis models:
    # "CodeSubmission",
    # "AnalysisResult",
    # "NotificationPreference",
    # "TrafficMetric",
    # "SubmissionStatus",
    # "SubmissionPriority",
]
