"""AI moderation service for content evaluation using LLM."""

from datetime import UTC
from datetime import datetime

from therobotoverlord_api.services.llm_client import LLMClient
from therobotoverlord_api.services.llm_client import ModerationResult
from therobotoverlord_api.services.prompt_service import PromptService


class AIModerationService:
    """Service for AI-powered content moderation using The Robot Overlord's standards."""

    def __init__(self):
        self.llm_client = LLMClient()
        self.prompt_service = PromptService()

    async def evaluate_post(
        self, content: str, user_name: str | None = None, language: str | None = None
    ) -> ModerationResult:
        """
        Evaluate a post for compliance with debate standards.

        Args:
            content: Post content to evaluate
            user_name: Name of the user who created the post
            language: Language of the content

        Returns:
            Structured moderation result with decision and feedback
        """
        timestamp = datetime.now(UTC).isoformat()

        # Generate the complete moderation prompt
        prompt = self.prompt_service.get_moderation_prompt(
            content_type="posts",
            content=content,
            user_name=user_name,
            language=language or "en",
            timestamp=timestamp,
        )

        # Get moderation decision from LLM
        result = await self.llm_client.moderate_content(
            prompt=prompt,
            content=content,
            content_type="post",
            user_name=user_name,
            language=language or "en",
        )

        return result

    async def evaluate_topic(
        self,
        title: str,
        description: str,
        user_name: str | None = None,
        language: str | None = None,
    ) -> ModerationResult:
        """
        Evaluate a topic for quality and relevance.

        Args:
            title: Topic title
            description: Topic description
            user_name: Name of the user who created the topic
            language: Language of the content

        Returns:
            Structured moderation result with decision and feedback
        """
        timestamp = datetime.now(UTC).isoformat()
        content = f"Title: {title}\n\nDescription: {description}"

        # Generate the complete moderation prompt
        prompt = self.prompt_service.get_moderation_prompt(
            content_type="topics",
            content=content,
            user_name=user_name,
            language=language or "en",
            timestamp=timestamp,
        )

        # Get moderation decision from LLM
        result = await self.llm_client.moderate_content(
            prompt=prompt,
            content=content,
            content_type="topic",
            user_name=user_name,
            language=language or "en",
        )

        return result

    async def evaluate_private_message(
        self,
        content: str,
        sender_name: str | None = None,
        recipient_name: str | None = None,
        language: str | None = None,
    ) -> ModerationResult:
        """
        Evaluate a private message for harassment and serious violations.

        Args:
            content: Message content to evaluate
            sender_name: Name of the message sender
            recipient_name: Name of the message recipient
            language: Language of the content

        Returns:
            Structured moderation result with decision and feedback
        """
        timestamp = datetime.now(UTC).isoformat()

        # Generate the complete moderation prompt
        prompt = self.prompt_service.get_moderation_prompt(
            content_type="private_messages",
            content=content,
            user_name=sender_name,
            language=language or "en",
            timestamp=timestamp,
        )

        # Get moderation decision from LLM
        result = await self.llm_client.moderate_content(
            prompt=prompt,
            content=content,
            content_type="private_message",
            user_name=sender_name,
            language=language or "en",
        )

        return result

    async def evaluate_system_chat(
        self, content: str, user_name: str | None = None, language: str | None = None
    ) -> ModerationResult:
        """
        Evaluate a system chat message.

        Args:
            content: Chat message content to evaluate
            user_name: Name of the user who sent the message
            language: Language of the content

        Returns:
            Structured moderation result with decision and feedback
        """
        timestamp = datetime.now(UTC).isoformat()

        # Generate the complete moderation prompt
        prompt = self.prompt_service.get_moderation_prompt(
            content_type="system_chats",
            content=content,
            user_name=user_name,
            language=language or "en",
            timestamp=timestamp,
        )

        # Get moderation decision from LLM
        result = await self.llm_client.moderate_content(
            prompt=prompt,
            content=content,
            content_type="system_chat",
            user_name=user_name,
            language=language or "en",
        )

        return result

    async def generate_feedback(
        self,
        content: str,
        decision: str,
        content_type: str = "post",
        user_name: str | None = None,
        reasoning: str | None = None,
    ) -> str:
        """
        Generate Robot Overlord feedback based on moderation decision.

        Args:
            content: Original content that was moderated
            decision: Moderation decision (Violation, Warning, No Violation, Praise)
            content_type: Type of content (post, topic, message)
            user_name: Name of the user who created the content
            reasoning: Reasoning for the decision

        Returns:
            Feedback message from The Robot Overlord
        """
        return await self.llm_client.generate_feedback(
            decision=decision,
            content=content,
            content_type=content_type,
            user_name=user_name or "Citizen",
            reasoning=reasoning or "Standard evaluation",
        )

    async def generate_overlord_chat_response(
        self,
        user_input: str,
        user_name: str = "Citizen",
        chat_history: str | None = None,
    ) -> str:
        """
        Generate a chat response as The Robot Overlord.

        Args:
            user_input: The user's message
            user_name: Name of the user
            chat_history: Previous conversation context

        Returns:
            Response message from The Robot Overlord
        """
        personality_prompt = self.prompt_service.get_overlord_personality_prompt()

        result = await self.llm_client.generate_overlord_response(
            user_input=user_input,
            personality_prompt=personality_prompt,
            user_name=user_name,
            chat_history=chat_history,
        )

        return result.message
