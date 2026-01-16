"""
Centralized configuration management with Pydantic Settings.
All environment variables are validated and typed.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "EcomDash V2 API"
    app_version: str = "2.0.0"
    debug: bool = False
    environment: str = Field(default="development", pattern="^(development|staging|production)$")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    database_url: PostgresDsn
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_echo: bool = False

    # Redis (for caching and rate limiting)
    redis_url: Optional[RedisDsn] = None

    # Security
    secret_key: str = Field(min_length=32)
    encryption_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # CORS - stored as comma-separated string to avoid JSON parsing issues
    allowed_origins_str: str = Field(default="http://localhost:3000", alias="ALLOWED_ORIGINS")

    @property
    def allowed_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins_str.split(",") if origin.strip()]

    # Shopify (optional for initial deployment - features disabled without these)
    shopify_api_key: Optional[str] = None
    shopify_api_secret: Optional[str] = None
    shopify_scopes: str = "read_products,read_orders,read_customers,read_inventory"
    shopify_app_url: Optional[str] = None

    # OpenAI (Fallback - now optional)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"

    # DeepSeek via OpenRouter (Primary AI Provider - optional for initial deployment)
    openrouter_api_key: Optional[str] = None
    deepseek_model: str = "deepseek/deepseek-chat"
    deepseek_reasoner_model: str = "deepseek/deepseek-reasoner"
    prefer_deepseek: bool = True

    # Pattern Analysis Settings
    enable_pattern_analysis: bool = True
    pattern_analysis_max_days: int = 30
    pattern_analysis_cache_ttl: int = 3600  # 1 hour in seconds

    # Notifications
    resend_api_key: Optional[str] = None
    app_url: str = "https://ecomdash.onrender.com"

    # Observability
    sentry_dsn: Optional[str] = None
    log_level: str = "INFO"
    enable_metrics: bool = True

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60

    # Adaptive Scheduling Thresholds
    traffic_threshold: int = 1000  # requests/hour to trigger early run
    pending_threshold: int = 50  # pending submissions to trigger early run
    analysis_batch_size: int = 100  # max submissions per batch run


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
