"""Application settings for The Robot Overlord API."""

import os

from pydantic import BaseModel
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from therobotoverlord_api.config.auth import AuthSettings
from therobotoverlord_api.config.database import DatabaseSettings
from therobotoverlord_api.config.redis import RedisSettings


class LLMSettings(BaseModel):
    """LLM configuration settings."""

    api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""),
        description="Anthropic API key for Claude models",
    )
    model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model name (use claude-3-5-sonnet-20241022 for Claude Sonnet 4)",
    )
    max_tokens: int = Field(
        default=1000, description="Maximum tokens for LLM responses"
    )
    temperature: float = Field(
        default=0.7, description="Temperature for LLM responses (0.0-1.0)"
    )

    # Moderation settings
    moderation_timeout: float = Field(
        default=30.0, description="Timeout for moderation requests in seconds"
    )
    max_retries: int = Field(
        default=3, description="Maximum retries for failed LLM requests"
    )

    model_config = SettingsConfigDict(env_prefix="LLM_", case_sensitive=False)


class TranslationSettings(BaseSettings):
    """Translation service configuration settings."""

    provider: str = Field(
        default="google", description="Translation provider (google, azure, deepl)"
    )
    api_key: str | None = Field(default=None, description="Translation service API key")
    project_id: str | None = Field(
        default=None, description="GCP project ID for Google Translate"
    )
    timeout: float = Field(
        default=10.0, description="Translation request timeout in seconds"
    )

    model_config = SettingsConfigDict(env_prefix="TRANSLATION_", case_sensitive=False)


class AppSettings(BaseSettings):
    """Main application settings."""

    # App info
    app_name: str = Field(
        default="The Robot Overlord API", description="Application name"
    )
    version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Auto-reload on changes")

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )

    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    auth: AuthSettings = Field(
        default_factory=lambda: AuthSettings(
            google_client_id="", google_client_secret="", jwt_secret_key=""
        )
    )
    llm: LLMSettings = Field(default_factory=LLMSettings)
    translation: TranslationSettings = Field(default_factory=TranslationSettings)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


# Global settings instance
_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """Get application settings (singleton pattern)."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = AppSettings()
    return _settings


def get_llm_settings() -> LLMSettings:
    """Get LLM settings."""
    return get_settings().llm


def get_translation_settings() -> TranslationSettings:
    """Get translation settings."""
    return get_settings().translation
