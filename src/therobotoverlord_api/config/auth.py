"""Authentication configuration for The Robot Overlord API."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    """Authentication configuration settings."""

    # Google OAuth Configuration
    google_client_id: str = Field(..., description="Google OAuth client ID")
    google_client_secret: str = Field(..., description="Google OAuth client secret")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/callback",
        description="Google OAuth redirect URI",
    )

    # JWT Configuration
    jwt_secret_key: str = Field(..., description="JWT signing secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_issuer: str = Field(default="therobotoverlord-api", description="JWT issuer")
    jwt_audience: str = Field(
        default="therobotoverlord.com", description="JWT audience"
    )

    # Token Lifetimes (in seconds)
    access_token_lifetime: int = Field(
        default=3600, description="Access token lifetime (1 hour)"
    )
    access_token_max_lifetime: int = Field(
        default=28800, description="Max access token lifetime (8 hours)"
    )
    access_token_extension: int = Field(
        default=1800, description="Token extension per activity (30 minutes)"
    )
    refresh_token_lifetime: int = Field(
        default=1209600, description="Refresh token lifetime (14 days)"
    )

    # Cookie Configuration
    cookie_domain: str = Field(
        default=".therobotoverlord.com", description="Cookie domain"
    )
    cookie_secure: bool = Field(default=True, description="Use secure cookies")
    cookie_samesite: Literal["strict", "lax", "none"] = Field(
        default="lax", description="Cookie SameSite policy"
    )

    # Session Configuration
    session_cleanup_interval: int = Field(
        default=3600, description="Session cleanup interval (1 hour)"
    )

    class Config:
        env_prefix = "AUTH_"
        case_sensitive = False


def get_auth_settings() -> AuthSettings:
    """Get authentication settings instance."""
    from therobotoverlord_api.config.settings import get_settings

    settings = get_settings()
    return AuthSettings(
        google_client_id=settings.auth.google_client_id,
        google_client_secret=settings.auth.google_client_secret,
        jwt_secret_key=settings.auth.jwt_secret_key,
    )
