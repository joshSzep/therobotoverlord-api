"""Database configuration for The Robot Overlord API."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    # Database connection
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/therobotoverlord",
        description="PostgreSQL database URL"
    )
    
    # Connection pool settings
    min_pool_size: int = Field(default=5, description="Minimum connection pool size")
    max_pool_size: int = Field(default=20, description="Maximum connection pool size")
    pool_timeout: float = Field(default=30.0, description="Connection pool timeout in seconds")
    
    # Query settings
    query_timeout: float = Field(default=30.0, description="Query timeout in seconds")
    command_timeout: float = Field(default=60.0, description="Command timeout in seconds")
    
    # Migration settings
    migration_table: str = Field(default="_yoyo_migration", description="Migration tracking table name")
    
    # SSL settings
    ssl_require: bool = Field(default=False, description="Require SSL connection")
    ssl_cert_path: Optional[str] = Field(default=None, description="Path to SSL certificate")
    ssl_key_path: Optional[str] = Field(default=None, description="Path to SSL private key")
    ssl_ca_path: Optional[str] = Field(default=None, description="Path to SSL CA certificate")
    
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
    database_url = (
        os.getenv("DATABASE_URL") or
        os.getenv("POSTGRES_URL") or
        os.getenv("POSTGRESQL_URL") or
        settings.database_url
    )
    
    return database_url


def get_migration_database_url() -> str:
    """Get database URL for migrations (may need different format)."""
    url = get_database_url()
    
    # Convert postgres:// to postgresql:// if needed (some tools are picky)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    return url
