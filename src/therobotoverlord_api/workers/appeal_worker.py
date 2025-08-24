"""Appeal processing worker for The Robot Overlord."""

import logging

from uuid import UUID

import asyncpg

from therobotoverlord_api.database.repositories.appeal import AppealRepository
from therobotoverlord_api.services.ai_moderation_service import AIModerationService
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import QueueWorkerMixin
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)


class AppealProcessingWorker(BaseWorker, QueueWorkerMixin):
    """Worker for processing appeal review queue."""

    def __init__(self):
        super().__init__()
        self.ai_moderation = AIModerationService()

    async def process_appeal_review(
        self, ctx: dict, queue_id: UUID, appeal_id: UUID
    ) -> bool:
        """Process an appeal review task."""
        logger.info(f"Processing appeal review for appeal {appeal_id}")

        # Ensure database connection is available
        if self.db is None:  # type: ignore[has-type]
            db: asyncpg.Connection | None = ctx.get("db")
            if db and isinstance(db, asyncpg.Connection):
                self.db = db
            else:
                logger.error("Database connection not available")
                return False

        try:
            appeal_repo = AppealRepository()

            # Get the appeal
            appeal = await appeal_repo.get_by_pk(appeal_id)
            if not appeal:
                logger.error(f"Appeal {appeal_id} not found")
                return False

            # Use AI moderation service for appeal review
            review_result = await self._ai_appeal_review(appeal)

            if review_result["approved"]:
                # Approve the appeal
                success = await appeal_repo.approve_appeal(
                    appeal_id, review_result.get("feedback")
                )
                if success:
                    logger.info(f"Appeal {appeal_id} approved by AI review")
                    return True
                logger.error(f"Failed to approve appeal {appeal_id}")
                return False

            # Reject the appeal
            success = await appeal_repo.reject_appeal(
                appeal_id,
                review_result.get("feedback", "Appeal rejected by AI review"),
            )
            if success:
                logger.info(f"Appeal {appeal_id} rejected by AI review")
                return True
            logger.error(f"Failed to reject appeal {appeal_id}")
            return False

        except Exception:
            logger.exception(f"Error processing appeal {appeal_id}")
            return False

    async def _ai_appeal_review(self, appeal) -> dict:
        """AI-powered appeal review using The Robot Overlord's standards."""
        try:
            # Get appellant name if available
            appellant_name = getattr(appeal, "appellant_name", None) or getattr(
                appeal, "user_name", None
            )

            # Evaluate appeal using AI moderation service
            result = await self.ai_moderation.evaluate_appeal(
                appeal_text=appeal.appeal_text,
                original_content=getattr(appeal, "original_content", ""),
                violation_type=getattr(appeal, "violation_type", ""),
                appellant_name=appellant_name,
                language="en",  # TODO(josh): Add language detection
            )

            # Convert AI result to worker format
            approved = result.decision in ["Appeal Granted", "Partial Grant"]

            return {
                "approved": approved,
                "feedback": result.feedback,
                "reasoning": result.reasoning,
                "confidence": result.confidence,
                "decision": result.decision,
            }

        except Exception:
            logger.exception(f"Error in AI appeal review for appeal {appeal.pk}")
            # Fallback to conservative rejection with generic feedback
            return {
                "approved": False,
                "feedback": "Appeal requires manual review due to system error.",
                "reasoning": "AI moderation service unavailable",
                "confidence": 0.0,
                "decision": "System Error",
            }


# Define worker functions
async def process_appeal_review(ctx: dict, queue_id: str, appeal_id: str) -> bool:
    """Worker function for appeal review."""
    try:
        worker = AppealProcessingWorker()
        return await worker.process_appeal_review(ctx, UUID(queue_id), UUID(appeal_id))
    except Exception:
        logger.exception(
            f"Error in appeal review worker function for appeal {appeal_id}"
        )
        return False


# Create the worker class
AppealWorker = create_worker_class(
    worker_functions=[process_appeal_review],
    functions=[process_appeal_review],
    max_jobs=3,  # Limited concurrent appeal processing
    job_timeout=180,  # 3 minutes per appeal (more complex than posts)
)
