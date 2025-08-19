"""Redis configuration for The Robot Overlord."""

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    # Redis connection
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    database: int = Field(default=0, description="Redis database number")
    password: str | None = Field(default=None, description="Redis password")

    # Connection settings
    max_connections: int = Field(default=20, description="Maximum Redis connections")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    socket_timeout: float = Field(default=5.0, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(
        default=5.0, description="Socket connect timeout in seconds"
    )

    # SSL settings
    ssl_enabled: bool = Field(default=False, description="Enable SSL connection")
    ssl_cert_reqs: str = Field(
        default="required", description="SSL certificate requirements"
    )
    ssl_ca_certs: str | None = Field(
        default=None, description="Path to SSL CA certificates"
    )
    ssl_certfile: str | None = Field(
        default=None, description="Path to SSL certificate file"
    )
    ssl_keyfile: str | None = Field(default=None, description="Path to SSL key file")

    model_config = SettingsConfigDict(env_prefix="REDIS_", case_sensitive=False)


def get_redis_settings() -> RedisSettings:
    """Get Redis settings from environment variables."""
    return RedisSettings()


def get_redis_url() -> str:
    """Get the Redis URL for connections."""
    settings = get_redis_settings()
    return settings.redis_url
