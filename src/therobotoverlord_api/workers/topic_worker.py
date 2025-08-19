"""Topic moderation worker for The Robot Overlord."""

import logging

from uuid import UUID

from therobotoverlord_api.database.repositories.topic import TopicRepository
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import QueueWorkerMixin
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)


class TopicModerationWorker(BaseWorker, QueueWorkerMixin):
    """Worker for processing topic creation queue."""

    async def process_topic_moderation(
        self, ctx: dict, queue_id: UUID, topic_id: UUID
    ) -> bool:
        """Process a topic through the moderation queue."""
        return await self.process_queue_item(
            ctx,
            "topic_creation_queue",
            queue_id,
            topic_id,
            self._moderate_topic,
        )

    async def _moderate_topic(self, ctx: dict, topic_id: UUID) -> bool:
        """Moderate a single topic."""
        try:
            topic_repo = TopicRepository()

            # Get the topic
            topic = await topic_repo.get_by_pk(topic_id)
            if not topic:
                logger.error(f"Topic {topic_id} not found")
                return False

            # For now, auto-approve all topics (placeholder for AI moderation)
            # TODO(josh): Replace with actual AI moderation logic - Issue #TBD
            success = await self._placeholder_topic_moderation(topic)

            if success:
                # TODO(josh): Need to handle AI approval without moderator_pk
                # For now, skip approval until repository method is updated
                logger.info(f"Topic {topic_id} would be approved by AI moderation")
                return True
            # Reject the topic
            rejected_topic = await topic_repo.reject_topic(topic_id)
            if rejected_topic:
                logger.info(f"Topic {topic_id} rejected by AI moderation")
                return True
            logger.error(f"Failed to reject topic {topic_id}")
            return False

        except Exception:
            logger.exception(f"Error moderating topic {topic_id}")
            return False

    async def _placeholder_topic_moderation(self, topic) -> bool:
        """Placeholder topic moderation logic."""
        # Simple rules for now:
        # - Reject if title is too short
        # - Reject if description is too short
        # - Reject if contains certain banned words

        banned_words = ["spam", "test123", "delete"]

        if len(topic.title.strip()) < 10:
            logger.info(f"Topic {topic.pk} rejected: title too short")
            return False

        if len(topic.description.strip()) < 20:
            logger.info(f"Topic {topic.pk} rejected: description too short")
            return False

        content_lower = f"{topic.title} {topic.description}".lower()
        for banned_word in banned_words:
            if banned_word in content_lower:
                logger.info(
                    f"Topic {topic.pk} rejected: contains banned word '{banned_word}'"
                )
                return False

        # Default to approval
        return True


# Define worker functions
async def process_topic_moderation(ctx: dict, queue_id: str, topic_id: str) -> bool:
    """Worker function for topic moderation."""
    try:
        worker = TopicModerationWorker()
        return await worker.process_topic_moderation(
            ctx, UUID(queue_id), UUID(topic_id)
        )
    except Exception:
        logger.exception(
            f"Error in topic moderation worker function for topic {topic_id}"
        )
        return False


# Create the worker class
TopicWorker = create_worker_class(
    worker_functions=[process_topic_moderation],
    functions=[process_topic_moderation],
    max_jobs=5,  # Limit concurrent topic processing
    job_timeout=120,  # 2 minutes per topic
)
