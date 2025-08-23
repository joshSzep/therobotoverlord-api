"""Post moderation worker for The Robot Overlord."""

import logging

from uuid import UUID

import asyncpg

from therobotoverlord_api.database.repositories.post import PostRepository
from therobotoverlord_api.services.ai_moderation_service import AIModerationService
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import QueueWorkerMixin
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)


class PostModerationWorker(BaseWorker, QueueWorkerMixin):
    """Worker for processing post moderation queue."""

    def __init__(self):
        super().__init__()
        self.ai_moderation = AIModerationService()

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

            # Use AI moderation service
            moderation_result = await self._ai_post_moderation(post)

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

    async def _ai_post_moderation(self, post) -> dict:
        """AI-powered post moderation using The Robot Overlord's standards."""
        try:
            # Get user name if available
            user_name = getattr(post, "user_name", None) or getattr(
                post, "author", None
            )

            # Evaluate post using AI moderation service
            result = await self.ai_moderation.evaluate_post(
                content=post.content,
                user_name=user_name,
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
            logger.exception(f"Error in AI post moderation for post {post.pk}")
            # Fallback to conservative approval with generic feedback
            return {
                "approved": True,
                "feedback": "Post approved pending manual review due to system error.",
                "reasoning": "AI moderation service unavailable",
                "confidence": 0.0,
            }


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
