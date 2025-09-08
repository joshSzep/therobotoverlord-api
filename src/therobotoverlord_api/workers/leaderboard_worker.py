"""Leaderboard maintenance worker for The Robot Overlord."""

import logging

from therobotoverlord_api.services.leaderboard_service import get_leaderboard_service
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)


class LeaderboardMaintenanceWorker(BaseWorker):
    """Worker for maintaining leaderboard materialized views and cache."""

    def __init__(self):
        super().__init__()

    async def refresh_leaderboard_rankings(self, ctx: dict) -> bool:
        """Refresh the leaderboard_rankings materialized view."""
        try:
            logger.info("Starting leaderboard rankings refresh")

            # Get leaderboard service
            service = await get_leaderboard_service()

            # Refresh materialized view and invalidate caches
            success = await service.refresh_leaderboard_data()

            if success:
                logger.info(
                    "Successfully refreshed leaderboard rankings materialized view"
                )
                return True

            logger.error("Failed to refresh leaderboard rankings materialized view")
            return False

        except Exception:
            logger.exception("Error refreshing leaderboard rankings")
            return False

    async def cleanup_leaderboard_cache(self, ctx: dict) -> bool:
        """Clean up stale leaderboard cache entries."""
        try:
            logger.info("Starting leaderboard cache cleanup")

            # Get leaderboard service
            service = await get_leaderboard_service()

            # Invalidate all cache entries to ensure fresh data
            await service.invalidate_all_cache()

            logger.info("Successfully cleaned up leaderboard cache")
            return True

        except Exception:
            logger.exception("Error cleaning up leaderboard cache")
            return False


# Define worker functions
async def refresh_leaderboard_rankings(ctx: dict) -> bool:
    """Worker function for refreshing leaderboard rankings."""
    try:
        worker = LeaderboardMaintenanceWorker()
        return await worker.refresh_leaderboard_rankings(ctx)
    except Exception:
        logger.exception("Error in leaderboard rankings refresh worker")
        return False


async def cleanup_leaderboard_cache(ctx: dict) -> bool:
    """Worker function for cleaning up leaderboard cache."""
    try:
        worker = LeaderboardMaintenanceWorker()
        return await worker.cleanup_leaderboard_cache(ctx)
    except Exception:
        logger.exception("Error in leaderboard cache cleanup worker")
        return False


# Create the worker class
LeaderboardWorker = create_worker_class(
    worker_functions=[
        refresh_leaderboard_rankings,
        cleanup_leaderboard_cache,
    ],
    functions=[
        refresh_leaderboard_rankings,
        cleanup_leaderboard_cache,
    ],
    max_jobs=1,  # Single job at a time to avoid conflicts
    job_timeout=300,  # 5 minutes timeout
)
