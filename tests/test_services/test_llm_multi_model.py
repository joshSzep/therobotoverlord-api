"""Integration tests for multi-provider LLM configuration."""

from therobotoverlord_api.config.settings import LLMSettings


class TestLLMMultiProviderConfiguration:
    """Test multi-model configuration for different agents."""

    def test_agent_config_retrieval(self):
        """Test that agent configurations are retrieved correctly from settings."""
        # Create mock LLM settings with specific agent configurations
        llm_settings = LLMSettings(
            provider="anthropic",
            api_key="test-key",
            model="claude-3-haiku-20240307",
            max_tokens=1500,
            temperature=0.5,
            anthropic_api_key="test-anthropic-key",
            moderation_provider="anthropic",
            moderation_model="claude-3-sonnet-20240229",
            moderation_max_tokens=500,
            moderation_temperature=0.1,
            tos_provider="anthropic",
            tos_model="claude-3-opus-20240229",
            tos_max_tokens=1000,
            tos_temperature=0.0,
            chat_provider="anthropic",
            chat_model="claude-3-haiku-20240307",
            chat_max_tokens=2000,
            chat_temperature=0.7,
        )

        # Test moderation agent config
        moderation_config = llm_settings.get_agent_config("moderation")
        assert moderation_config.provider == "anthropic"
        assert moderation_config.model == "claude-3-sonnet-20240229"
        assert moderation_config.max_tokens == 500
        assert moderation_config.temperature == 0.1
        assert moderation_config.api_key == "test-anthropic-key"

        # Test ToS agent config
        tos_config = llm_settings.get_agent_config("tos")
        assert tos_config.provider == "anthropic"
        assert tos_config.model == "claude-3-opus-20240229"
        assert tos_config.max_tokens == 1000
        assert tos_config.temperature == 0.0
        assert tos_config.api_key == "test-anthropic-key"

        # Test chat agent config
        chat_config = llm_settings.get_agent_config("chat")
        assert chat_config.provider == "anthropic"
        assert chat_config.model == "claude-3-haiku-20240307"
        assert chat_config.max_tokens == 2000
        assert chat_config.temperature == 0.7
        assert chat_config.api_key == "test-anthropic-key"

    def test_fallback_to_default_config(self):
        """Test that agents fall back to default config when specific config is not provided."""
        # Create mock LLM settings with only moderation-specific config
        llm_settings = LLMSettings(
            provider="anthropic",
            api_key="test-key",
            model="claude-3-haiku-20240307",
            max_tokens=1500,
            temperature=0.5,
            anthropic_api_key="test-anthropic-key",
            moderation_provider="anthropic",
            moderation_model="claude-3-sonnet-20240229",
            # Other agent configs not set, should fall back to defaults
        )

        # Test moderation agent config (should use specific config)
        moderation_config = llm_settings.get_agent_config("moderation")
        assert moderation_config.provider == "anthropic"
        assert moderation_config.model == "claude-3-sonnet-20240229"
        assert moderation_config.max_tokens == 2048  # Falls back to moderation default
        assert moderation_config.temperature == 0.8  # Falls back to moderation default
        assert moderation_config.api_key == "test-anthropic-key"

        # Test ToS agent config (should use all defaults)
        tos_config = llm_settings.get_agent_config("tos")
        assert tos_config.provider == "anthropic"  # Falls back to default
        assert tos_config.model == "claude-3-haiku-20240307"  # Falls back to default
        assert tos_config.max_tokens == 1500  # Falls back to default
        assert tos_config.temperature == 0.5  # Falls back to default
        assert tos_config.api_key == "test-anthropic-key"

        # Test chat agent config (should use all defaults)
        chat_config = llm_settings.get_agent_config("chat")
        assert chat_config.provider == "anthropic"  # Falls back to default
        assert chat_config.model == "claude-3-haiku-20240307"  # Falls back to default
        assert chat_config.max_tokens == 1500  # Falls back to default
        assert chat_config.temperature == 0.5  # Falls back to default
        assert chat_config.api_key == "test-anthropic-key"

    def test_get_llm_client_function_exists(self):
        """Test that the get_llm_client function exists and is callable."""
        from therobotoverlord_api.services.llm_client import get_llm_client

        # Verify the function exists and is callable
        assert callable(get_llm_client)
