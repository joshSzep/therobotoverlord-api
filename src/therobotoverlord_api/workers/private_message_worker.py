"""Private message moderation worker for The Robot Overlord."""

import logging

from uuid import UUID

import asyncpg

from therobotoverlord_api.database.repositories.private_message import (
    PrivateMessageRepository,
)
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import QueueWorkerMixin
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)


class PrivateMessageModerationWorker(BaseWorker, QueueWorkerMixin):
    """Worker for processing private message moderation queue."""

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

            # For now, use placeholder moderation (will be replaced with AI)
            moderation_result = await self._placeholder_message_moderation(message)

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

    async def _placeholder_message_moderation(self, message) -> dict:
        """Placeholder private message moderation logic."""
        content = message.content.strip()

        # Private messages have more lenient rules than public posts
        # Focus on serious violations: harassment, threats, doxxing
        serious_violations = [
            "kill yourself",
            "kys",
            "doxx",
            "dox",
            "home address",
            "phone number",
            "real name",
            "workplace",
            "threat",
            "violence",
        ]

        harassment_patterns = [
            "stupid",
            "idiot",
            "moron",
            "retard",
            "loser",
            "pathetic",
            "worthless",
            "waste of space",
            "kill",
            "die",
            "hurt",
        ]

        required_min_length = 1  # Very permissive for private messages

        # Check minimum length
        if len(content) < required_min_length:
            return {
                "approved": False,
                "feedback": "Empty messages are not permitted.",
            }

        # Check for serious violations
        content_lower = content.lower()
        for violation in serious_violations:
            if violation in content_lower:
                return {
                    "approved": False,
                    "feedback": "Private message contains serious policy violation. This behavior is unacceptable even in private discourse.",
                }

        # Check for harassment patterns (more lenient - need multiple indicators)
        harassment_count = sum(
            1 for pattern in harassment_patterns if pattern in content_lower
        )
        if harassment_count >= 3:  # Multiple harassment indicators
            return {
                "approved": False,
                "feedback": "Private discourse allows disagreement, but this crosses into harassment territory. Tone it down, citizen.",
            }

        # Check for excessive caps (less strict than public posts)
        if content.isupper() and len(content) > 50:
            return {
                "approved": False,
                "feedback": "Even in private, excessive shouting is unnecessary. Use your indoor voice.",
            }

        # Generate contextual feedback for approved messages
        feedback_options = [
            None,  # Most private messages get no feedback
            None,
            None,
            "Private discourse noted.",
            "Acceptable private communication.",
        ]

        # Simple hash-based selection for consistent feedback
        feedback_index = hash(content) % len(feedback_options)

        return {"approved": True, "feedback": feedback_options[feedback_index]}


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
