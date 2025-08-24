"""Topic moderation worker for The Robot Overlord."""

import logging

from uuid import UUID

from therobotoverlord_api.database.repositories.topic import TopicRepository
from therobotoverlord_api.services.ai_moderation_service import AIModerationService
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import QueueWorkerMixin
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)

# System UUID for AI moderation approvals
AI_SYSTEM_UUID = UUID("00000000-0000-0000-0000-000000000001")


class TopicModerationWorker(BaseWorker, QueueWorkerMixin):
    """Worker for processing topic creation queue."""

    def __init__(self):
        super().__init__()
        self.ai_moderation = AIModerationService()

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

            # Use AI moderation service
            success = await self._ai_topic_moderation(topic)

            if success:
                # Approve the topic with AI system as the approver
                approved_topic = await topic_repo.approve_topic(
                    topic_id,
                    AI_SYSTEM_UUID,  # Use AI system UUID for AI approvals
                )
                if approved_topic:
                    logger.info(f"Topic {topic_id} approved by AI moderation")
                    return True
                logger.error(f"Failed to approve topic {topic_id}")
                return False
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

    async def _ai_topic_moderation(self, topic) -> bool:
        """AI-powered topic moderation using The Robot Overlord's standards."""
        try:
            # Get user name if available
            user_name = getattr(topic, "user_name", None) or getattr(
                topic, "author", None
            )

            # Evaluate topic using AI moderation service
            result = await self.ai_moderation.evaluate_topic(
                title=topic.title,
                description=topic.description,
                user_name=user_name,
                language="en",  # TODO(josh): Add language detection
            )

            # Convert AI result to worker format
            approved = result.decision in ["No Violation", "Praise"]

            if not approved:
                logger.info(
                    f"Topic {topic.pk} rejected by AI: {result.decision} - {result.reasoning}"
                )
            else:
                logger.info(
                    f"Topic {topic.pk} approved by AI: {result.decision} (confidence: {result.confidence})"
                )

            return approved

        except Exception:
            logger.exception(f"Error in AI topic moderation for topic {topic.pk}")
            # Fallback to conservative approval
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
