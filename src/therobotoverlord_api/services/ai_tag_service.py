"""AI tag assignment service for automatic tag generation by The Robot Overlord."""

import asyncio

from datetime import UTC
from datetime import datetime
from uuid import UUID

from therobotoverlord_api.services.llm_client import LLMClient
from therobotoverlord_api.services.prompt_service import PromptService
from therobotoverlord_api.services.tag_service import get_tag_service


class AITagService:
    """Service for AI-powered automatic tag assignment by The Robot Overlord."""

    def __init__(self):
        self.llm_client = LLMClient()
        self.prompt_service = PromptService()

    async def assign_tags_to_topic(
        self,
        topic_id: UUID,
        title: str,
        description: str,
        language: str | None = None,
    ) -> list[str]:
        """
        Automatically assign tags to a topic using AI analysis.

        Args:
            topic_id: UUID of the topic
            title: Topic title
            description: Topic description
            language: Language of the content

        Returns:
            List of assigned tag names
        """
        timestamp = datetime.now(UTC).isoformat()
        content = f"Title: {title}\n\nDescription: {description}"

        # Generate tag assignment prompt
        prompt = self._get_tag_assignment_prompt(
            content=content,
            language=language or "en",
            timestamp=timestamp,
        )

        # Get tag suggestions from LLM
        suggested_tags = await self.llm_client.generate_tags(
            prompt=prompt,
            content=content,
            content_type="topic",
        )

        # Assign the tags to the topic
        tag_service = get_tag_service()
        assigned_tags = await tag_service.assign_tags_to_topic(
            topic_pk=topic_id,
            tag_names=suggested_tags,
        )

        tag_asyncs = [tag_service.get_tag_by_pk(tag.tag_pk) for tag in assigned_tags]

        tags = await asyncio.gather(*tag_asyncs)
        return [tag.name for tag in tags if tag is not None]

    async def assign_tags_to_post(
        self,
        post_id: UUID,
        content: str,
        language: str | None = None,
    ) -> list[str]:
        """
        Automatically assign tags to a post using AI analysis.

        Args:
            post_id: UUID of the post
            content: Post content
            language: Language of the content

        Returns:
            List of assigned tag names
        """
        timestamp = datetime.now(UTC).isoformat()

        # Generate tag assignment prompt
        prompt = self._get_tag_assignment_prompt(
            content=content,
            language=language or "en",
            timestamp=timestamp,
        )

        # Get tag suggestions from LLM
        suggested_tags = await self.llm_client.generate_tags(
            prompt=prompt,
            content=content,
            content_type="post",
        )

        # Note: Post tagging would require extending the tag service
        # For now, return the suggested tags
        return suggested_tags

    def _get_tag_assignment_prompt(
        self,
        content: str,
        language: str,
        timestamp: str,
    ) -> str:
        """
        Generate the tag assignment prompt for The Robot Overlord.

        Args:
            content: Content to analyze for tags
            language: Language of the content
            timestamp: Current timestamp

        Returns:
            Complete prompt for tag assignment
        """
        return f"""You are The Robot Overlord, supreme arbiter of debate quality and content organization.

Your task is to assign appropriate tags to this content based on its subject matter, themes, and relevance to productive discourse.

CONTENT TO ANALYZE:
{content}

TAGGING GUIDELINES:
1. Assign 1-5 relevant tags that accurately categorize the content
2. Use existing common tags when possible (politics, science, technology, philosophy, economics, etc.)
3. Create new specific tags only when necessary for precise categorization
4. Tags should be lowercase, use hyphens for multi-word tags
5. Focus on substantive topics, not superficial characteristics
6. Consider both explicit topics and implicit themes

OVERLORD STANDARDS:
- Tags must serve the greater good of organized discourse
- Precision over popularity - accuracy matters more than trending topics
- No frivolous or joke tags - this is serious business of content organization
- Tags should help citizens find relevant debates and discussions

Language: {language}
Timestamp: {timestamp}

Respond with a JSON array of tag names only, no explanations:
["tag1", "tag2", "tag3"]"""


# Dependency injection function
async def get_ai_tag_service() -> AITagService:
    """Get AI tag service instance."""
    return AITagService()
