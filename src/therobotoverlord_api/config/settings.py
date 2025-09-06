"""Application settings for The Robot Overlord API."""

import os

from pydantic import BaseModel
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from therobotoverlord_api.config.auth import AuthSettings
from therobotoverlord_api.config.database import DatabaseSettings
from therobotoverlord_api.config.redis import RedisSettings


class AgentModelConfig(BaseModel):
    """Configuration for a specific agent's model."""

    provider: str = Field(
        description="Provider to use for this agent (anthropic, openai, google, etc.)"
    )
    model: str = Field(description="Model name to use for this agent")
    max_tokens: int = Field(default=1000, description="Maximum tokens for responses")
    temperature: float = Field(default=0.7, description="Temperature (0.0-1.0)")
    api_key: str | None = Field(
        default=None, description="API key for this provider (optional)"
    )


class LLMSettings(BaseModel):
    """LLM configuration settings."""

    # Default provider and model configuration (backward compatibility)
    provider: str = Field(
        default="anthropic",
        description="Default provider (anthropic, openai, google, bedrock, groq, cohere, azure, deepseek)",
    )
    api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""),
        description="Default API key for the provider",
    )
    model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default model name",
    )
    max_tokens: int = Field(
        default=1000, description="Default maximum tokens for LLM responses"
    )
    temperature: float = Field(
        default=0.7, description="Default temperature for LLM responses (0.0-1.0)"
    )

    # Provider-specific API keys
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""),
        description="Anthropic API key for Claude models",
    )
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="OpenAI API key",
    )
    google_api_key: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""),
        description="Google API key for Gemini models",
    )
    groq_api_key: str = Field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", ""),
        description="Groq API key",
    )
    cohere_api_key: str = Field(
        default_factory=lambda: os.getenv("COHERE_API_KEY", ""),
        description="Cohere API key",
    )
    deepseek_api_key: str = Field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""),
        description="DeepSeek API key",
    )
    azure_api_key: str = Field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_API_KEY", ""),
        description="Azure OpenAI API key",
    )
    bedrock_access_key: str = Field(
        default_factory=lambda: os.getenv("AWS_ACCESS_KEY_ID", ""),
        description="AWS access key for Bedrock",
    )
    bedrock_secret_key: str = Field(
        default_factory=lambda: os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        description="AWS secret key for Bedrock",
    )
    bedrock_region: str = Field(
        default_factory=lambda: os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        description="AWS region for Bedrock",
    )

    # Azure-specific settings
    azure_endpoint: str = Field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        description="Azure OpenAI endpoint",
    )
    azure_api_version: str = Field(
        default_factory=lambda: os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        description="Azure OpenAI API version",
    )

    # Google-specific settings
    google_project_id: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", ""),
        description="Google Cloud project ID for Vertex AI",
    )
    google_location: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        description="Google Cloud location for Vertex AI",
    )

    # Agent-specific configurations
    moderation_provider: str = Field(
        default="", description="Provider for moderation agent (uses default if empty)"
    )
    moderation_model: str = Field(
        default="", description="Model for moderation agent (uses default if empty)"
    )
    moderation_max_tokens: int = Field(
        default=2048, description="Max tokens for moderation (uses default if 0)"
    )
    moderation_temperature: float = Field(
        default=0.8, description="Temperature for moderation (uses default if -1)"
    )

    tos_provider: str = Field(
        default="",
        description="Provider for ToS screening agent (uses default if empty)",
    )
    tos_model: str = Field(
        default="", description="Model for ToS screening agent (uses default if empty)"
    )
    tos_max_tokens: int = Field(
        default=0, description="Max tokens for ToS screening (uses default if 0)"
    )
    tos_temperature: float = Field(
        default=-1.0, description="Temperature for ToS screening (uses default if -1)"
    )

    chat_provider: str = Field(
        default="", description="Provider for chat agent (uses default if empty)"
    )
    chat_model: str = Field(
        default="", description="Model for chat agent (uses default if empty)"
    )
    chat_max_tokens: int = Field(
        default=0, description="Max tokens for chat (uses default if 0)"
    )
    chat_temperature: float = Field(
        default=-1.0, description="Temperature for chat (uses default if -1)"
    )

    translation_provider: str = Field(
        default="", description="Provider for translation agent (uses default if empty)"
    )
    translation_model: str = Field(
        default="", description="Model for translation agent (uses default if empty)"
    )
    translation_max_tokens: int = Field(
        default=0, description="Max tokens for translation (uses default if 0)"
    )
    translation_temperature: float = Field(
        default=-1.0, description="Temperature for translation (uses default if -1)"
    )

    # Tagging agent configuration
    tagging_provider: str = Field(
        default="", description="Provider for tagging agent (uses default if empty)"
    )
    tagging_model: str = Field(
        default="", description="Model for tagging agent (uses default if empty)"
    )
    tagging_max_tokens: int = Field(
        default=0, description="Max tokens for tagging (uses default if 0)"
    )
    tagging_temperature: float = Field(
        default=0.0, description="Temperature for tagging (uses default if 0.0)"
    )

    # General settings
    moderation_timeout: float = Field(
        default=30.0, description="Timeout for moderation requests in seconds"
    )
    max_retries: int = Field(
        default=3, description="Maximum retries for failed LLM requests"
    )

    model_config = SettingsConfigDict(env_prefix="LLM_", case_sensitive=False)

    def get_provider_api_key(self, provider: str) -> str:
        """Get API key for a specific provider."""
        provider_keys = {
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
            "google": self.google_api_key,
            "groq": self.groq_api_key,
            "cohere": self.cohere_api_key,
            "deepseek": self.deepseek_api_key,
            "azure": self.azure_api_key,
            "bedrock": self.bedrock_access_key,
        }
        return provider_keys.get(provider, self.api_key)

    def get_agent_config(self, agent_type: str) -> AgentModelConfig:
        """Get configuration for a specific agent type."""
        if agent_type == "moderation":
            provider = self.moderation_provider or self.provider
            return AgentModelConfig(
                provider=provider,
                model=self.moderation_model or self.model,
                max_tokens=self.moderation_max_tokens or self.max_tokens,
                temperature=self.moderation_temperature
                if self.moderation_temperature >= 0
                else self.temperature,
                api_key=self.get_provider_api_key(provider),
            )
        if agent_type == "tos":
            provider = self.tos_provider or self.provider
            return AgentModelConfig(
                provider=provider,
                model=self.tos_model or self.model,
                max_tokens=self.tos_max_tokens or self.max_tokens,
                temperature=self.tos_temperature
                if self.tos_temperature >= 0
                else self.temperature,
                api_key=self.get_provider_api_key(provider),
            )
        if agent_type == "chat":
            provider = self.chat_provider or self.provider
            return AgentModelConfig(
                provider=provider,
                model=self.chat_model or self.model,
                max_tokens=self.chat_max_tokens or self.max_tokens,
                temperature=self.chat_temperature
                if self.chat_temperature >= 0
                else self.temperature,
                api_key=self.get_provider_api_key(provider),
            )
        if agent_type == "translation":
            provider = self.translation_provider or self.provider
            return AgentModelConfig(
                provider=provider,
                model=self.translation_model or self.model,
                max_tokens=self.translation_max_tokens or self.max_tokens,
                temperature=self.translation_temperature
                if self.translation_temperature >= 0
                else self.temperature,
                api_key=self.get_provider_api_key(provider),
            )
        if agent_type == "tagging":
            provider = self.tagging_provider or self.provider
            return AgentModelConfig(
                provider=provider,
                model=self.tagging_model or self.model,
                max_tokens=self.tagging_max_tokens or self.max_tokens,
                temperature=self.tagging_temperature
                if self.tagging_temperature >= 0
                else self.temperature,
                api_key=self.get_provider_api_key(provider),
            )
        # Default configuration
        return AgentModelConfig(
            provider=self.provider,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            api_key=self.get_provider_api_key(self.provider),
        )


class TranslationSettings(BaseSettings):
    """Translation service configuration settings."""

    # Translation agent configuration (uses LLM for translation)
    provider: str = Field(
        default="",
        description="Provider for translation agent (uses default LLM if empty)",
    )
    model: str = Field(
        default="",
        description="Model for translation agent (uses default LLM if empty)",
    )
    max_tokens: int = Field(
        default=0, description="Max tokens for translation (uses default if 0)"
    )
    temperature: float = Field(
        default=-1.0, description="Temperature for translation (uses default if -1)"
    )
    timeout: float = Field(
        default=30.0, description="Translation request timeout in seconds"
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
