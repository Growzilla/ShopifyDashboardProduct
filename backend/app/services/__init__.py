"""
Services package for business logic layer.

MVP SIMPLIFICATION: AI Code Analyzer and Notification Service commented out - not core value.
To re-enable: uncomment imports and add back to __all__.
"""
# from app.services.ai_analyzer import AICodeAnalyzer  # COMMENTED OUT FOR MVP - Code analysis feature
from app.services.insights_engine import InsightsEngine
# from app.services.notification_service import NotificationService  # COMMENTED OUT FOR MVP - Overkill notifications
from app.services.shopify_client import ShopifyAPIError, ShopifyGraphQLClient

__all__ = [
    # Core MVP services:
    "ShopifyGraphQLClient",
    "ShopifyAPIError",
    "InsightsEngine",
    # COMMENTED OUT FOR MVP:
    # "AICodeAnalyzer",
    # "NotificationService",
]
