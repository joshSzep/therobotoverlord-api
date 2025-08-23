"""Private message moderation worker for The Robot Overlord."""

import logging

from uuid import UUID

import asyncpg

from therobotoverlord_api.database.repositories.private_message import (
    PrivateMessageRepository,
)
from therobotoverlord_api.services.ai_moderation_service import AIModerationService
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import QueueWorkerMixin
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)


class PrivateMessageModerationWorker(BaseWorker, QueueWorkerMixin):
    """Worker for processing private message moderation queue."""

    def __init__(self):
        super().__init__()
        self.ai_moderation = AIModerationService()

    async def process_message_moderation(
        self, ctx: dict, queue_id: UUID, message_id: UUID
    ) -> bool:
        """Process a private message moderation task."""
        logger.info(f"Processing private message moderation for message {message_id}")

        # Ensure database connection is available
        if self.db is None:  # type: ignore[has-type]
            db: asyncpg.Connection | None = ctx.get("db")
            if db and isinstance(db, asyncpg.Connection):
                self.db = db
            else:
                logger.error("Database connection not available")
                return False

        try:
            message_repo = PrivateMessageRepository()

            # Get the message
            message = await message_repo.get_by_pk(message_id)
            if not message:
                logger.error(f"Private message {message_id} not found")
                return False

            # Use AI moderation service
            moderation_result = await self._ai_message_moderation(message)

            if moderation_result["approved"]:
                # Approve the message
                success = await message_repo.approve_message(
                    message_id, moderation_result.get("feedback")
                )
                if success:
                    logger.info(
                        f"Private message {message_id} approved by AI moderation"
                    )
                    return True
                logger.error(f"Failed to approve private message {message_id}")
                return False

            # Reject the message
            success = await message_repo.reject_message(
                message_id,
                moderation_result.get("feedback", "Message rejected by AI moderation"),
            )
            if success:
                logger.info(f"Private message {message_id} rejected by AI moderation")
                return True
            logger.error(f"Failed to reject private message {message_id}")
            return False

        except Exception:
            logger.exception(f"Error moderating private message {message_id}")
            return False

    async def _ai_message_moderation(self, message) -> dict:
        """AI-powered private message moderation using The Robot Overlord's standards."""
        try:
            # Get sender name if available
            sender_name = getattr(message, "sender_name", None) or getattr(
                message, "author", None
            )
            recipient_name = getattr(message, "recipient_name", None)

            # Evaluate message using AI moderation service
            result = await self.ai_moderation.evaluate_private_message(
                content=message.content,
                sender_name=sender_name,
                recipient_name=recipient_name,
                language="en",  # TODO(josh): Add language detection
            )

            # Convert AI result to worker format
            approved = result.decision in ["No Violation", "Praise"]

            return {
                "approved": approved,
                "feedback": result.feedback,
                "reasoning": result.reasoning,
                "confidence": result.confidence,
                "violations": result.violations,
            }

        except Exception:
            logger.exception(f"Error in AI message moderation for message {message.pk}")
            # Fallback to conservative approval with generic feedback
            return {
                "approved": True,
                "feedback": "Message approved pending manual review due to system error.",
                "reasoning": "AI moderation service unavailable",
                "confidence": 0.0,
            }


# Define worker functions
async def process_private_message_moderation(
    ctx: dict, queue_id: str, message_id: str
) -> bool:
    """Worker function for private message moderation."""
    try:
        worker = PrivateMessageModerationWorker()
        return await worker.process_message_moderation(
            ctx, UUID(queue_id), UUID(message_id)
        )
    except Exception:
        logger.exception(
            f"Error in private message moderation worker function for message {message_id}"
        )
        return False


# Create the worker class
PrivateMessageWorker = create_worker_class(
    worker_functions=[process_private_message_moderation],
    functions=[process_private_message_moderation],
    max_jobs=8,  # Moderate concurrent message processing
    job_timeout=30,  # 30 seconds per message (faster than posts)
)
