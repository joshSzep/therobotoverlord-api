"""Rate limiting configuration for The Robot Overlord API."""

from pydantic import Field
from pydantic_settings import BaseSettings


class RateLimitingSettings(BaseSettings):
    """Rate limiting configuration settings."""

    # Authentication endpoints (per IP)
    auth_requests_per_minute: int = Field(
        default=5, description="Auth requests per minute per IP"
    )

    # Authentication endpoints (per user)
    auth_user_requests_per_minute: int = Field(
        default=3, description="Auth requests per minute per user"
    )

    # Admin endpoints (per user)
    admin_requests_per_minute: int = Field(
        default=30, description="Admin requests per minute per user"
    )

    # RBAC endpoints (per user)
    rbac_requests_per_minute: int = Field(
        default=20, description="RBAC requests per minute per user"
    )

    # Sanctions endpoints (per user)
    sanctions_requests_per_minute: int = Field(
        default=10, description="Sanctions requests per minute per user"
    )

    # Content creation endpoints (per user)
    content_requests_per_minute: int = Field(
        default=5, description="Content creation requests per minute per user"
    )

    # General API endpoints (per IP)
    general_requests_per_minute: int = Field(
        default=60, description="General requests per minute per IP"
    )

    # Redis key prefixes
    rate_limit_key_prefix: str = Field(
        default="rl:", description="Redis key prefix for rate limiting"
    )

    # Rate limiting enabled flag
    rate_limiting_enabled: bool = Field(
        default=True, description="Enable/disable rate limiting"
    )

    # Bypass rate limiting for specific IPs (comma-separated)
    rate_limit_bypass_ips: str = Field(
        default="127.0.0.1,::1", description="IPs to bypass rate limiting"
    )

    class Config:
        env_prefix = "RATE_LIMIT_"


def get_rate_limiting_settings() -> RateLimitingSettings:
    """Get rate limiting settings instance."""
    return RateLimitingSettings()
