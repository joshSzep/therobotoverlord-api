"""Database configuration for The Robot Overlord API."""

import os

from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    # Database connection
    database_url: str = Field(
        default="",
        description="PostgreSQL database URL",
    )
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="password", description="Database password")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="therobotoverlord", description="Database name")
    ssl_mode: str = Field(default="prefer", description="SSL mode")

    # Connection pool settings
    min_pool_size: int = Field(default=5, description="Minimum connection pool size")
    max_pool_size: int = Field(default=20, description="Maximum connection pool size")
    pool_timeout: float = Field(
        default=30.0, description="Connection pool timeout in seconds"
    )

    # Query settings
    query_timeout: float = Field(default=30.0, description="Query timeout in seconds")
    command_timeout: float = Field(
        default=60.0, description="Command timeout in seconds"
    )

    # Migration settings
    migration_table: str = Field(
        default="_yoyo_migration", description="Migration tracking table name"
    )

    # SSL settings
    ssl_require: bool = Field(default=False, description="Require SSL connection")
    ssl_cert_path: str | None = Field(
        default=None, description="Path to SSL certificate"
    )
    ssl_key_path: str | None = Field(
        default=None, description="Path to SSL private key"
    )
    ssl_ca_path: str | None = Field(
        default=None, description="Path to SSL CA certificate"
    )

    class Config:
        env_prefix = "DATABASE_"
        case_sensitive = False


def get_database_settings() -> DatabaseSettings:
    """Get database settings from environment variables."""
    return DatabaseSettings()


def get_database_url() -> str:
    """Get the database URL, with environment variable override."""
    settings = get_database_settings()

    # Check for common environment variable names
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRESQL_URL")
        or f"postgresql://{settings.username}:{settings.password}@{settings.host}:{settings.port}/{settings.database}?sslmode={settings.ssl_mode}"
    )


def get_migration_database_url() -> str:
    """Get database URL for migrations (may need different format)."""
    url = get_database_url()

    # Convert postgres:// to postgresql:// if needed (some tools are picky)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url
