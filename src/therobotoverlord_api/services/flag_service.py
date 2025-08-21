"""Flag service for content reporting and moderation business logic."""

import logging

from datetime import UTC
from datetime import datetime
from uuid import UUID

from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.flag import Flag
from therobotoverlord_api.database.models.flag import FlagCreate
from therobotoverlord_api.database.models.flag import FlagStatus
from therobotoverlord_api.database.models.flag import FlagUpdate
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventOutcome
from therobotoverlord_api.database.models.loyalty_score import ModerationEventType
from therobotoverlord_api.database.models.post import PostUpdate
from therobotoverlord_api.database.models.topic import TopicUpdate
from therobotoverlord_api.database.repositories.flag import FlagRepository
from therobotoverlord_api.database.repositories.post import PostRepository
from therobotoverlord_api.database.repositories.topic import TopicRepository

logger = logging.getLogger(__name__)


class FlagService:
    """Service for handling content flagging operations."""

    def __init__(
        self,
        flag_repo: FlagRepository | None = None,
        post_repo: PostRepository | None = None,
        topic_repo: TopicRepository | None = None,
        loyalty_service=None,
    ) -> None:
        """Initialize the flag service."""
        self.flag_repo = flag_repo or FlagRepository()
        self.post_repo = post_repo or PostRepository()
        self.topic_repo = topic_repo or TopicRepository()
        self.loyalty_service = loyalty_service

    async def create_flag(self, flag_data: FlagCreate, flagger_pk: UUID) -> Flag:
        """Create a new content flag with validation."""
        # Validate that exactly one content type is specified
        if not flag_data.post_pk and not flag_data.topic_pk:
            raise ValueError("Must specify either post_pk or topic_pk")

        if flag_data.post_pk and flag_data.topic_pk:
            raise ValueError("Cannot flag both post and topic in same request")

        # Validate content exists and get content author
        if flag_data.post_pk:
            post = await self.post_repo.get_by_pk(flag_data.post_pk)
            if not post:
                raise ValueError("Post not found")
            content_author_pk = post.author_pk
            content_type = "post"
            content_pk = flag_data.post_pk
        elif flag_data.topic_pk:
            topic = await self.topic_repo.get_by_pk(flag_data.topic_pk)
            if not topic:
                raise ValueError("Topic not found")
            content_author_pk = topic.author_pk
            content_type = "topic"
            content_pk = flag_data.topic_pk
        else:
            raise ValueError("Either post_pk or topic_pk must be provided")

        # Prevent self-flagging
        if content_author_pk == flagger_pk:
            raise ValueError("Cannot flag your own content")

        # Check for duplicate flags from same user
        already_flagged = await self.flag_repo.check_user_already_flagged(
            flagger_pk, content_pk, content_type
        )
        if already_flagged:
            raise ValueError("You have already flagged this content")

        # Create the flag
        flag_create_data = flag_data.model_dump()
        flag_create_data["flagger_pk"] = flagger_pk

        return await self.flag_repo.create_from_dict(flag_create_data)

    async def review_flag(
        self,
        flag_id: UUID,
        flag_update: FlagUpdate,
        reviewer_pk: UUID,
    ) -> Flag:
        """Review a flag and take appropriate moderation action."""
        flag = await self.flag_repo.get_by_pk(flag_id)
        if not flag:
            raise ValueError("Flag not found")

        if flag.status != FlagStatus.PENDING:
            raise ValueError("Flag has already been reviewed")

        # Update flag with review information
        update_data = flag_update.model_dump()
        update_data["reviewed_by_pk"] = reviewer_pk
        update_data["reviewed_at"] = datetime.now(UTC)

        updated_flag = await self.flag_repo.update(flag_id, update_data)
        if not updated_flag:
            raise ValueError("Failed to update flag")

        # Handle flag outcome
        if flag_update.status == FlagStatus.UPHELD:
            await self._handle_upheld_flag(updated_flag)
        elif flag_update.status == FlagStatus.DISMISSED:
            await self._handle_dismissed_flag(updated_flag)

        return updated_flag

    async def _handle_upheld_flag(self, flag: Flag) -> None:
        """Handle when a flag is upheld - hide content and update loyalty scores."""
        content_author_pk = None
        content_type = None
        content_pk = None

        if flag.post_pk:
            # Get post author and hide the post
            post = await self.post_repo.get_by_pk(flag.post_pk)
            if post:
                content_author_pk = post.author_pk
                await self.post_repo.update(
                    flag.post_pk, PostUpdate(status=ContentStatus.REJECTED)
                )
            content_pk = flag.post_pk
            content_type = ContentType.POST
        elif flag.topic_pk:
            # Get topic author and hide the topic
            topic = await self.topic_repo.get_by_pk(flag.topic_pk)
            if topic:
                content_author_pk = topic.author_pk
                await self.topic_repo.update(
                    flag.topic_pk, TopicUpdate(status=TopicStatus.REJECTED)
                )
            content_pk = flag.topic_pk
            content_type = ContentType.TOPIC

        # Record loyalty event for content author if loyalty service is available
        if self.loyalty_service and content_author_pk and content_pk:
            try:
                reason = f"Flag upheld: {flag.review_notes or 'No additional notes'}"
                event_type = (
                    ModerationEventType.POST_MODERATION
                    if content_type == ContentType.POST
                    else ModerationEventType.TOPIC_MODERATION
                )
                await self.loyalty_service.record_moderation_event(
                    user_pk=content_author_pk,
                    content_pk=content_pk,
                    content_type=content_type,
                    event_type=event_type,
                    outcome=LoyaltyEventOutcome.REJECTED,
                    moderator_pk=flag.reviewed_by_pk,
                    reason=reason,
                )
            except Exception as e:
                # Don't fail flag processing if loyalty service fails
                logger.exception(
                    "Failed to record loyalty event for upheld flag: %s", e
                )

    async def _handle_dismissed_flag(self, flag: Flag) -> None:
        """Handle when a flag is dismissed - check for frivolous flagging patterns."""
        # Check for frivolous flagging pattern
        dismissed_count = await self.flag_repo.get_user_dismissed_flags_count(
            flag.flagger_pk, days=30
        )

        # If user has 3+ dismissed flags in 30 days, this indicates frivolous flagging
        # This would integrate with sanctions system when implemented
        if dismissed_count >= 3:
            # TODO(josh): Integrate with sanctions system to apply warning or restriction
            # For now, we just track the pattern
            pass

    async def get_user_flag_stats(self, user_pk: UUID) -> dict[str, int]:
        """Get flag statistics for a user."""
        user_flags = await self.flag_repo.get_user_flags(user_pk, limit=1000)

        stats = {
            "total_flags": len(user_flags),
            "pending": sum(1 for f in user_flags if f.status == FlagStatus.PENDING),
            "upheld": sum(1 for f in user_flags if f.status == FlagStatus.UPHELD),
            "dismissed": sum(1 for f in user_flags if f.status == FlagStatus.DISMISSED),
        }

        return stats

    async def get_content_flag_summary(
        self,
        content_pk: UUID,
        content_type: str,
    ) -> dict[str, int]:
        """Get flag summary for specific content."""
        flags = await self.flag_repo.get_content_flags(content_pk, content_type)

        summary = {
            "total_flags": len(flags),
            "pending": sum(1 for f in flags if f.status == FlagStatus.PENDING),
            "upheld": sum(1 for f in flags if f.status == FlagStatus.UPHELD),
            "dismissed": sum(1 for f in flags if f.status == FlagStatus.DISMISSED),
        }

        return summary


async def get_flag_service() -> FlagService:
    """Dependency injection for flag service."""
    from therobotoverlord_api.database.repositories.flag import FlagRepository
    from therobotoverlord_api.database.repositories.post import PostRepository
    from therobotoverlord_api.database.repositories.topic import TopicRepository

    return FlagService(
        flag_repo=FlagRepository(),
        post_repo=PostRepository(),
        topic_repo=TopicRepository(),
    )
