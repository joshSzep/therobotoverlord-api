"""Post moderation worker for The Robot Overlord."""

import logging

from uuid import UUID

import asyncpg

from therobotoverlord_api.database.repositories.post import PostRepository
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import QueueWorkerMixin
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)


class PostModerationWorker(BaseWorker, QueueWorkerMixin):
    """Worker for processing post moderation queue."""

    async def process_post_moderation(
        self, ctx: dict, queue_id: UUID, post_id: UUID
    ) -> bool:
        """Process a post moderation task."""
        logger.info(f"Processing post moderation for post {post_id}")

        # Ensure database connection is available
        if self.db is None:  # type: ignore[has-type]
            db: asyncpg.Connection | None = ctx.get("db")
            if db and isinstance(db, asyncpg.Connection):
                self.db = db
            else:
                logger.error("Database connection not available")
                return False

        try:
            post_repo = PostRepository()

            # Get the post
            post = await post_repo.get_by_pk(post_id)
            if not post:
                logger.error(f"Post {post_id} not found")
                return False

            # For now, auto-approve all posts (placeholder for AI moderation)
            moderation_result = await self._placeholder_post_moderation(post)

            if moderation_result["approved"]:
                # Approve the post
                success = await post_repo.approve_post(
                    post_id, moderation_result.get("feedback")
                )
                if success:
                    logger.info(f"Post {post_id} approved by AI moderation")
                    return True
                logger.error(f"Failed to approve post {post_id}")
                return False
            # Reject the post
            success = await post_repo.reject_post(
                post_id,
                moderation_result.get("feedback", "Content rejected by AI moderation"),
            )
            if success:
                logger.info(f"Post {post_id} rejected by AI moderation")
                return True
            logger.error(f"Failed to reject post {post_id}")
            return False

        except Exception:
            logger.exception(f"Error moderating post {post_id}")
            return False

    async def _placeholder_post_moderation(self, post) -> dict:
        """Placeholder post moderation logic."""
        content = post.content.strip()

        # Simple rules for now:
        banned_words = ["spam", "hate", "violence", "illegal"]
        required_min_length = 10

        # Check minimum length
        if len(content) < required_min_length:
            return {
                "approved": False,
                "feedback": f"Content too short. Minimum {required_min_length} characters required.",
            }

        # Check for banned words
        content_lower = content.lower()
        for banned_word in banned_words:
            if banned_word in content_lower:
                return {
                    "approved": False,
                    "feedback": f"Content contains prohibited language: '{banned_word}'",
                }

        # Check for all caps (shouting)
        if content.isupper() and len(content) > 20:
            return {
                "approved": False,
                "feedback": "Excessive use of capital letters. Please use normal capitalization.",
            }

        # Generate positive feedback for approved posts
        feedback_options = [
            "Well-reasoned argument, citizen.",
            "Your contribution advances the discourse.",
            "Logical and relevant to the topic.",
            "Acceptable reasoning demonstrated.",
            "Your argument shows proper structure.",
        ]

        # Simple hash-based selection for consistent feedback
        feedback_index = hash(content) % len(feedback_options)

        return {"approved": True, "feedback": feedback_options[feedback_index]}


# Define worker functions
async def process_post_moderation(ctx: dict, queue_id: str, post_id: str) -> bool:
    """Worker function for post moderation."""
    try:
        worker = PostModerationWorker()
        return await worker.process_post_moderation(ctx, UUID(queue_id), UUID(post_id))
    except Exception:
        logger.exception(f"Error in post moderation worker function for post {post_id}")
        return False


# Create the worker class
PostWorker = create_worker_class(
    worker_functions=[process_post_moderation],
    functions=[process_post_moderation],
    max_jobs=10,  # More concurrent post processing
    job_timeout=60,  # 1 minute per post
)
