"""LLM client service using pydantic-ai for AI model interactions."""

from datetime import UTC
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai import RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from therobotoverlord_api.config.settings import get_settings


class ModerationResult(BaseModel):
    """Structured output for content moderation."""

    decision: str  # Violation, Warning, No Violation, Praise
    confidence: float  # 0.0 to 1.0
    reasoning: str
    feedback: str
    violations: list[str] = []
    suggestions: list[str] = []


class ChatResponse(BaseModel):
    """Structured output for chat responses."""

    message: str
    tone: str  # theatrical, disappointed, encouraging, praising
    personality_consistency: float  # 0.0 to 1.0


class LLMClient:
    """Client for interacting with LLM models using pydantic-ai."""

    def __init__(self):
        self.settings = get_settings()

        # Initialize Anthropic model with provider
        provider = AnthropicProvider(api_key=self.settings.llm.api_key)
        self.model = AnthropicModel(
            model_name=self.settings.llm.model, provider=provider
        )

        # Create moderation agent
        self.moderation_agent = Agent(
            model=self.model,
            deps_type=dict[str, Any],
            output_type=ModerationResult,
        )

        # Create chat response agent
        self.chat_agent = Agent(
            model=self.model,
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
