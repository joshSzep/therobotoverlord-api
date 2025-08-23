"""ToS screening service for content moderation using AI."""

import logging

from therobotoverlord_api.services.llm_client import LLMClient
from therobotoverlord_api.services.llm_client import ToSScreeningResult

logger = logging.getLogger(__name__)


class ToSScreeningService:
    """Service for screening content against Terms of Service violations."""

    def __init__(self):
        self.llm_client = LLMClient()

    async def screen_content(
        self,
        content: str,
        content_type: str = "post",
        user_name: str | None = None,
        language: str = "en",
    ) -> ToSScreeningResult:
        """
        Screen content for Terms of Service violations.

        Args:
            content: The content to screen
            content_type: Type of content (post, topic, message)
            user_name: Name of the user who created the content
            language: Language of the content

        Returns:
            ToSScreeningResult with approval decision and reasoning
        """
        try:
            result = await self.llm_client.screen_content_for_tos(
                content=content,
                content_type=content_type,
                user_name=user_name,
                language=language,
            )

            # Log screening results for monitoring
            if result.approved:
                logger.info(
                    f"ToS screening APPROVED {content_type} by {user_name or 'Anonymous'} "
                    f"(confidence: {result.confidence:.2f})"
                )
            else:
                logger.warning(
                    f"ToS screening REJECTED {content_type} by {user_name or 'Anonymous'} "
                    f"for {result.violation_type}: {result.reasoning} "
                    f"(confidence: {result.confidence:.2f})"
                )

            return result

        except Exception:
            logger.exception(f"Error in ToS screening for {content_type}")
            # Fallback to approval with low confidence for system errors
            return ToSScreeningResult(
                approved=True,
                violation_type=None,
                reasoning="ToS screening service unavailable - approved pending manual review",
                confidence=0.1,
            )

    async def check_tos_violation(self, content: str) -> bool:
        """
        Legacy method for backward compatibility.

        Args:
            content: The content to check

        Returns:
            True if content violates ToS (should be rejected), False otherwise
        """
        result = await self.screen_content(content, content_type="post")
        return not result.approved


# Module-level singleton instance
_tos_screening_service: ToSScreeningService | None = None


async def get_tos_screening_service() -> ToSScreeningService:
    """Get the ToS screening service instance."""
    global _tos_screening_service  # noqa: PLW0603
    if _tos_screening_service is None:
        _tos_screening_service = ToSScreeningService()
    return _tos_screening_service
