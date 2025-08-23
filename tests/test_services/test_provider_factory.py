"""Tests for the ProviderFactory service."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from therobotoverlord_api.config.settings import AgentModelConfig
from therobotoverlord_api.services.provider_factory import ProviderFactory


class TestProviderFactory:
    """Test the ProviderFactory service."""

    def test_supported_providers(self):
        """Test that all expected providers are supported."""
        expected_providers = {
            "anthropic",
            "openai",
            "google",
            "groq",
            "bedrock",
            "cohere",
        }

        mock_settings = MagicMock()
        factory = ProviderFactory(mock_settings)
        assert set(factory.get_supported_providers()) == expected_providers

    @patch("therobotoverlord_api.services.provider_factory.AnthropicProvider")
    @patch("therobotoverlord_api.services.provider_factory.AnthropicModel")
    def test_create_anthropic_provider_and_model(self, mock_model, mock_provider):
        """Test creating Anthropic provider and model."""
        config = AgentModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.7,
            api_key="test-anthropic-key",
        )

        mock_provider_instance = MagicMock()
        mock_model_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_model.return_value = mock_model_instance

        mock_settings = MagicMock()
        factory = ProviderFactory(mock_settings)
        model = factory.create_model(config)

        mock_provider.assert_called_once_with(api_key="test-anthropic-key")
        mock_model.assert_called_once_with(
            model_name="claude-3-5-sonnet-20241022", provider=mock_provider_instance
        )

        assert model == mock_model_instance

    @patch("therobotoverlord_api.services.provider_factory.OpenAIProvider")
    @patch("therobotoverlord_api.services.provider_factory.OpenAIModel")
    def test_create_openai_provider_and_model(self, mock_model, mock_provider):
        """Test creating OpenAI provider and model."""
        config = AgentModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            max_tokens=1000,
            temperature=0.7,
            api_key="test-openai-key",
        )

        mock_provider_instance = MagicMock()
        mock_model_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_model.return_value = mock_model_instance

        mock_settings = MagicMock()
        factory = ProviderFactory(mock_settings)
        model = factory.create_model(config)

        mock_provider.assert_called_once_with(api_key="test-openai-key")
        mock_model.assert_called_once_with(
            model_name="gpt-4o-mini", provider=mock_provider_instance
        )

        assert model == mock_model_instance

    @patch("therobotoverlord_api.services.provider_factory.GoogleProvider")
    @patch("therobotoverlord_api.services.provider_factory.GoogleModel")
    def test_create_google_provider_and_model(self, mock_model, mock_provider):
        """Test creating Google provider and model."""
        config = AgentModelConfig(
            provider="google",
            model="gemini-1.5-flash",
            max_tokens=1000,
            temperature=0.7,
            api_key="test-google-key",
        )

        mock_provider_instance = MagicMock()
        mock_model_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_model.return_value = mock_model_instance

        mock_settings = MagicMock()
        mock_settings.google_project_id = None
        mock_settings.google_api_key = None
        factory = ProviderFactory(mock_settings)
        model = factory.create_model(config)

        mock_provider.assert_called_once_with(api_key="test-google-key")
        mock_model.assert_called_once_with(
            model_name="gemini-1.5-flash", provider=mock_provider_instance
        )

        assert model == mock_model_instance

    def test_validate_provider_config_valid_anthropic(self):
        """Test validation of valid Anthropic config."""
        config = AgentModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.7,
            api_key="test-key",
        )

        mock_settings = MagicMock()
        factory = ProviderFactory(mock_settings)
        assert factory.validate_provider_config(config) is True

    def test_validate_provider_config_missing_api_key(self):
        """Test validation fails when API key is missing."""
        config = AgentModelConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.7,
            api_key="",
        )

        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = None
        factory = ProviderFactory(mock_settings)
        assert factory.validate_provider_config(config) is False

    def test_validate_provider_config_unsupported_provider(self):
        """Test validation fails for unsupported provider."""
        config = AgentModelConfig(
            provider="unsupported",
            model="some-model",
            max_tokens=1000,
            temperature=0.7,
            api_key="test-key",
        )

        mock_settings = MagicMock()
        factory = ProviderFactory(mock_settings)
        assert factory.validate_provider_config(config) is False

    def test_create_provider_and_model_unsupported_provider(self):
        """Test that creating unsupported provider raises ValueError."""
        config = AgentModelConfig(
            provider="unsupported",
            model="some-model",
            max_tokens=1000,
            temperature=0.7,
            api_key="test-key",
        )

        mock_settings = MagicMock()
        factory = ProviderFactory(mock_settings)
        with pytest.raises(ValueError, match="Unsupported provider: unsupported"):
            factory.create_model(config)

    def test_create_model_unsupported_provider(self):
        """Test that creating unsupported provider raises ValueError."""
        config = AgentModelConfig(
            provider="unsupported",
            model="some-model",
            max_tokens=1000,
            temperature=0.5,
            api_key="test-key",
        )

        mock_settings = MagicMock()
        factory = ProviderFactory(mock_settings)
        with pytest.raises(ValueError, match="Unsupported provider: unsupported"):
            factory.create_model(config)

    @patch("therobotoverlord_api.services.provider_factory.GroqProvider")
    @patch("therobotoverlord_api.services.provider_factory.GroqModel")
    def test_create_groq_provider_and_model(self, mock_model, mock_provider):
        """Test creating Groq provider and model."""
        config = AgentModelConfig(
            provider="groq",
            model="llama-3.1-70b-versatile",
            max_tokens=1000,
            temperature=0.7,
            api_key="test-groq-key",
        )

        mock_provider_instance = MagicMock()
        mock_model_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_model.return_value = mock_model_instance

        mock_settings = MagicMock()
        factory = ProviderFactory(mock_settings)
        model = factory.create_model(config)

        mock_provider.assert_called_once_with(api_key="test-groq-key")
        mock_model.assert_called_once_with(
            model_name="llama-3.1-70b-versatile", provider=mock_provider_instance
        )

        assert model == mock_model_instance

    @patch("therobotoverlord_api.services.provider_factory.BedrockProvider")
    @patch("therobotoverlord_api.services.provider_factory.BedrockConverseModel")
    def test_create_bedrock_provider_and_model(self, mock_model, mock_provider):
        """Test creating Bedrock provider and model."""
        config = AgentModelConfig(
            provider="bedrock",
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            max_tokens=1000,
            temperature=0.7,
            api_key="test-api-key",
        )

        mock_provider_instance = MagicMock()
        mock_model_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_model.return_value = mock_model_instance

        mock_settings = MagicMock()
        mock_settings.bedrock_access_key = "test-access-key"
        mock_settings.bedrock_secret_key = "test-secret-key"
        mock_settings.bedrock_region = "us-east-1"
        factory = ProviderFactory(mock_settings)
        model = factory.create_model(config)

        mock_provider.assert_called_once_with(
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
            region_name="us-east-1",
        )
        mock_model.assert_called_once_with(
            model_name="anthropic.claude-3-sonnet-20240229-v1:0",
            provider=mock_provider_instance,
        )

        assert model == mock_model_instance

    @patch("pydantic_ai.providers.cohere.CohereProvider")
    @patch("pydantic_ai.models.cohere.CohereModel")
    def test_create_cohere_provider_and_model(self, mock_model, mock_provider):
        """Test creating Cohere provider and model."""
        config = AgentModelConfig(
            provider="cohere",
            model="command-r-plus",
            max_tokens=1000,
            temperature=0.7,
            api_key="test-cohere-key",
        )

        mock_provider_instance = MagicMock()
        mock_model_instance = MagicMock()
        mock_provider.return_value = mock_provider_instance
        mock_model.return_value = mock_model_instance

        mock_settings = MagicMock()
        mock_settings.cohere_api_key = None
        factory = ProviderFactory(mock_settings)
        model = factory.create_model(config)

        mock_provider.assert_called_once_with(api_key="test-cohere-key")
        mock_model.assert_called_once_with(
            model_name="command-r-plus", provider=mock_provider_instance
        )

        assert model == mock_model_instance
