"""LLM client service using pydantic-ai for AI model interactions."""

import logging

from datetime import UTC
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai import RunContext

from therobotoverlord_api.config.settings import get_settings
from therobotoverlord_api.services.prompt_service import PromptService
from therobotoverlord_api.services.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)


class ModerationResult(BaseModel):
    """Structured output for content moderation."""

    decision: str  # Violation, Warning, No Violation, Praise
    confidence: float  # 0.0 to 1.0
    reasoning: str
    feedback: str
    violations: list[str] = []
    suggestions: list[str] = []


class ToSScreeningResult(BaseModel):
    """Structured output for Terms of Service screening."""

    approved: bool  # True = send to moderation queue, False = immediate rejection
    violation_type: str | None  # Type of violation if rejected
    reasoning: str
    confidence: float  # 0.0 to 1.0


class ChatResponse(BaseModel):
    """Structured output for chat responses."""

    message: str
    tone: str  # theatrical, disappointed, encouraging, praising
    personality_consistency: float  # 0.0 to 1.0


class LLMClient:
    """Client for interacting with LLM models using pydantic-ai."""

    def __init__(self):
        self.settings = get_settings()
        self.provider_factory = ProviderFactory(self.settings.llm)

        # Create models for each agent type using the provider factory
        self.models = self._create_models()

        # Create agents with their specific models
        self.moderation_agent = Agent(
            model=self.models["moderation"],
            deps_type=dict[str, Any],
            output_type=ModerationResult,
        )

        self.translation_agent = Agent(
            model=self.models["translation"],
            deps_type=dict[str, Any],
            output_type=ModerationResult,
        )

        self.tos_agent = Agent(
            model=self.models["tos"],
            deps_type=dict[str, Any],
            output_type=ToSScreeningResult,
        )

        self.chat_agent = Agent(
            model=self.models["chat"],
            deps_type=dict[str, Any],
            output_type=ChatResponse,
        )

        # Add system prompts to agents
        @self.moderation_agent.system_prompt
        def add_moderation_context(ctx: RunContext[dict[str, Any]]) -> str:
            """Dynamic system prompt for moderation with context."""
            context = ctx.deps
            return f"""
You are The Robot Overlord's moderation system. Analyze content and provide structured moderation decisions.

Current timestamp: {datetime.now(UTC).isoformat()}
Content type: {context.get("content_type", "unknown")}
User: {context.get("user_name", "Anonymous")}
Language: {context.get("language", "en")}

{context.get("prompt", "")}
"""

        @self.chat_agent.system_prompt
        def add_chat_context(ctx: RunContext[dict[str, Any]]) -> str:
            """Dynamic system prompt for chat with context."""
            context = ctx.deps
            return f"""
You are The Robot Overlord. Generate responses that match your theatrical, logical personality.

Current timestamp: {datetime.now(UTC).isoformat()}
User: {context.get("user_name", "Citizen")}
Chat context: {context.get("chat_history", "New conversation")}

{context.get("personality_prompt", "")}
"""

    async def moderate_content(
        self,
        prompt: str,
        content: str,
        content_type: str = "post",
        user_name: str | None = None,
        language: str = "en",
    ) -> ModerationResult:
        """
        Moderate content using the LLM with structured output.

        Args:
            prompt: The complete moderation prompt
            content: Content to moderate
            content_type: Type of content (post, topic, message)
            user_name: Name of the user who created the content
            language: Language of the content

        Returns:
            Structured moderation result
        """
        context = {
            "prompt": prompt,
            "content": content,
            "content_type": content_type,
            "user_name": user_name,
            "language": language,
        }

        result = await self.moderation_agent.run(
            f"Moderate this {content_type}: {content}", deps=context
        )

        return result.data

    async def generate_overlord_response(
        self,
        user_input: str,
        personality_prompt: str,
        user_name: str = "Citizen",
        chat_history: str | None = None,
    ) -> ChatResponse:
        """
        Generate a response as The Robot Overlord.

        Args:
            user_input: The user's message
            personality_prompt: The Overlord personality prompt
            user_name: Name of the user
            chat_history: Previous conversation context

        Returns:
            Structured chat response
        """
        context = {
            "personality_prompt": personality_prompt,
            "user_name": user_name,
            "chat_history": chat_history or "New conversation",
        }

        result = await self.chat_agent.run(user_input, deps=context)

        return result.data

    async def generate_feedback(
        self,
        decision: str,
        content: str,
        content_type: str,
        user_name: str,
        reasoning: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate feedback message based on moderation decision.

        Args:
            decision: Moderation decision (Violation, Warning, etc.)
            content: Original content
            content_type: Type of content
            user_name: User who created the content
            reasoning: Reasoning for the decision

        Returns:
            Feedback message from The Robot Overlord
        """
        # Use provided content_type parameter

        feedback_prompt = f"""
You are The Robot Overlord. You have made a moderation decision of "{decision}"
for a {content_type} by {user_name}.

Original content: {content}
Your reasoning: {reasoning}

Generate appropriate feedback that:
- Addresses {user_name} directly
- Reflects your theatrical, intelligent personality
- Is firm but not cruel for violations
- Celebrates excellence for praise
- Encourages improvement for warnings
- Acknowledges valid contributions for no violations

Respond as The Robot Overlord would - with authority, intelligence, and belief in the Citizen's potential.
"""

        context = {
            "personality_prompt": feedback_prompt,
            "user_name": user_name,
            "decision": decision,
        }

        result = await self.chat_agent.run(
            f"Generate feedback for {decision} decision", deps=context
        )

        return result.data.message

    def _create_models(self) -> dict[str, Any]:
        """Create models for each agent type with their specific configurations and providers."""
        models = {}

        for agent_type in ["moderation", "tos", "chat", "translation"]:
            config = self.settings.llm.get_agent_config(agent_type)

            try:
                # Validate provider configuration
                if not self.provider_factory.validate_provider_config(config):
                    logger.warning(
                        f"Invalid configuration for {agent_type} agent with provider {config.provider}. "
                        f"Missing required API keys or settings."
                    )
                    raise ValueError(
                        f"Invalid provider configuration for {config.provider}"
                    )

                # Create model using the provider factory
                models[agent_type] = self.provider_factory.create_model(config)
                logger.info(
                    f"Created {agent_type} agent with provider {config.provider} and model {config.model}"
                )

            except Exception as e:
                logger.error(f"Failed to create model for {agent_type} agent: {e}")
                # Fall back to default configuration if agent-specific config fails
                default_config = self.settings.llm.get_agent_config("default")
                if self.provider_factory.validate_provider_config(default_config):
                    logger.info(
                        f"Falling back to default configuration for {agent_type} agent"
                    )
                    models[agent_type] = self.provider_factory.create_model(
                        default_config
                    )
                else:
                    raise RuntimeError(
                        f"Cannot create model for {agent_type} agent and default config is also invalid"
                    ) from e

        return models

    async def screen_content_for_tos(
        self,
        content: str,
        content_type: str = "post",
        user_name: str | None = None,
        language: str = "en",
    ) -> ToSScreeningResult:
        """
        Screen content for Terms of Service violations before moderation.

        Args:
            content: The content to screen
            content_type: Type of content (post, topic, message)
            user_name: Name of the user who created the content
            language: Language of the content

        Returns:
            ToSScreeningResult with approval decision and reasoning
        """

        prompt_service = PromptService()

        # Get ToS screening prompt
        tos_prompt = prompt_service._load_component(
            "system_instructions", "tos_screening"
        )

        # Create context for the screening
        context = {
            "content": content,
            "content_type": content_type,
            "user_name": user_name or "Anonymous",
            "language": language,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Add system prompt for ToS agent
        @self.tos_agent.system_prompt
        def add_tos_context(ctx: RunContext[dict[str, Any]]) -> str:
            return tos_prompt

        # Run ToS screening
        result = await self.tos_agent.run(
            user_prompt=f"""Screen this {content_type} content for Terms of Service violations:

Content: {content}
User: {user_name or "Anonymous"}
Language: {language}

Provide your screening decision in the required JSON format.""",
            deps=context,
        )

        return result.data

    async def run_translation_agent(
        self, prompt: str, output_type: type, **kwargs
    ) -> Any:
        """Run the translation agent with structured output."""
        # Create a temporary agent with the specified output type
        translation_agent = Agent(
            model=self.models["translation"],
            deps_type=dict[str, Any],
            output_type=output_type,
        )

        result = await translation_agent.run(
            prompt,
            deps=kwargs.get("deps", {}),
        )

        return result


async def get_llm_client() -> LLMClient:
    """Get the LLM client instance."""
    return LLMClient()
