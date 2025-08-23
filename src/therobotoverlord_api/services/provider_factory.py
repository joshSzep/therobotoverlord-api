"""Provider factory for creating AI model providers and models dynamically."""

import logging

from typing import Any

from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.openai import OpenAIProvider

from therobotoverlord_api.config.settings import AgentModelConfig
from therobotoverlord_api.config.settings import LLMSettings

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating AI providers and models."""

    def __init__(self, settings: LLMSettings):
        """Initialize the provider factory with settings."""
        self.settings = settings

    def create_provider(self, provider_name: str, config: AgentModelConfig) -> Any:
        """Create a provider instance based on the provider name and configuration."""
        provider_name = provider_name.lower()

        try:
            if provider_name == "anthropic":
                return AnthropicProvider(
                    api_key=config.api_key or self.settings.anthropic_api_key
                )

            if provider_name == "openai":
                return OpenAIProvider(
                    api_key=config.api_key or self.settings.openai_api_key
                )

            if provider_name == "google":
                if self.settings.google_project_id:
                    # Use Vertex AI
                    return GoogleProvider(
                        project=self.settings.google_project_id,
                        location=self.settings.google_location,  # type: ignore  # noqa: PGH003
                    )
                # Use Gemini API
                return GoogleProvider(
                    api_key=config.api_key or self.settings.google_api_key
                )

            if provider_name == "groq":
                return GroqProvider(
                    api_key=config.api_key or self.settings.groq_api_key
                )

            if provider_name == "bedrock":
                return BedrockProvider(
                    aws_access_key_id=self.settings.bedrock_access_key,
                    aws_secret_access_key=self.settings.bedrock_secret_key,
                    region_name=self.settings.bedrock_region,
                )

            if provider_name == "cohere":
                from pydantic_ai.providers.cohere import CohereProvider

                return CohereProvider(
                    api_key=config.api_key or self.settings.cohere_api_key
                )

            raise ValueError(f"Unsupported provider: {provider_name}")

        except Exception as e:
            logger.error(f"Failed to create provider {provider_name}: {e}")
            raise

    def create_model(self, config: AgentModelConfig) -> Any:
        """Create a model instance based on the configuration."""
        provider = self.create_provider(config.provider, config)
        provider_name = config.provider.lower()

        try:
            if provider_name == "anthropic":
                return AnthropicModel(model_name=config.model, provider=provider)

            if provider_name == "openai":
                return OpenAIModel(model_name=config.model, provider=provider)

            if provider_name == "google":
                return GoogleModel(model_name=config.model, provider=provider)

            if provider_name == "groq":
                return GroqModel(model_name=config.model, provider=provider)

            if provider_name == "bedrock":
                return BedrockConverseModel(model_name=config.model, provider=provider)

            if provider_name == "cohere":
                from pydantic_ai.models.cohere import CohereModel

                return CohereModel(model_name=config.model, provider=provider)

            raise ValueError(
                f"Unsupported provider for model creation: {provider_name}"
            )

        except Exception as e:
            logger.error(
                f"Failed to create model {config.model} with provider {provider_name}: {e}"
            )
            raise

    def get_supported_providers(self) -> list[str]:
        """Get list of supported provider names."""
        return [
            "anthropic",
            "openai",
            "google",
            "groq",
            "bedrock",
            "cohere",
        ]

    def validate_provider_config(self, config: AgentModelConfig) -> bool:
        """Validate that a provider configuration has required settings."""
        provider_name = config.provider.lower()

        if provider_name == "anthropic":
            return bool(config.api_key or self.settings.anthropic_api_key)

        if provider_name == "openai":
            return bool(config.api_key or self.settings.openai_api_key)

        if provider_name == "google":
            # Either API key for Gemini API or project ID for Vertex AI
            return bool(
                (config.api_key or self.settings.google_api_key)
                or self.settings.google_project_id
            )

        if provider_name == "groq":
            return bool(config.api_key or self.settings.groq_api_key)

        if provider_name == "bedrock":
            return bool(
                self.settings.bedrock_access_key and self.settings.bedrock_secret_key
            )

        if provider_name == "cohere":
            return bool(config.api_key or self.settings.cohere_api_key)

        return False
