"""Task scheduler for The Robot Overlord API."""

import asyncio
import logging

from datetime import UTC
from datetime import datetime
from datetime import timedelta

from arq import create_pool
from arq.connections import ArqRedis
from arq.connections import RedisSettings as ArqRedisSettings

from therobotoverlord_api.config.redis import get_redis_settings

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Scheduler for recurring background tasks."""

    def __init__(self):
        self.redis_pool: ArqRedis | None = None
        self.scheduled_tasks = []

    async def initialize(self):
        """Initialize Redis connection."""
        redis_settings = get_redis_settings()
        arq_settings = ArqRedisSettings(
            host=redis_settings.host,
            port=redis_settings.port,
            database=redis_settings.database,
            password=redis_settings.password,
            max_connections=redis_settings.max_connections,
        )
        self.redis_pool = await create_pool(arq_settings)
        logger.info("Scheduler connected to Redis")

    async def schedule_leaderboard_refresh(self):
        """Schedule leaderboard rankings refresh every 30 minutes."""
        if self.redis_pool is None:
            logger.error("Redis pool not initialized")
            return
        try:
            # Schedule immediate refresh
            await self.redis_pool.enqueue_job(
                "refresh_leaderboard_rankings",
                _queue_name="leaderboard",
            )
            logger.info("Scheduled immediate leaderboard refresh")

            # Schedule recurring refresh every 5 minutes
            await self.redis_pool.enqueue_job(
                "refresh_leaderboard_rankings",
                _defer=timedelta(minutes=5),
                _queue_name="leaderboard",
            )
            logger.info("Scheduled recurring leaderboard refresh (every 5 minutes)")

        except Exception:
            logger.exception("Failed to schedule leaderboard refresh")

    async def schedule_leaderboard_cache_cleanup(self):
        """Schedule leaderboard cache cleanup every 10 minutes."""
        if self.redis_pool is None:
            logger.error("Redis pool not initialized")
            return

        try:
            # Schedule cache cleanup every 10 minutes
            await self.redis_pool.enqueue_job(
                "cleanup_leaderboard_cache",
                _defer=timedelta(minutes=10),
                _queue_name="leaderboard",
            )
            logger.info("Scheduled leaderboard cache cleanup (every 10 minutes)")

        except Exception:
            logger.exception("Failed to schedule leaderboard cache cleanup")

    async def start_recurring_schedules(self):
        """Start all recurring task schedules."""
        await self.initialize()

        # Schedule leaderboard maintenance tasks
        await self.schedule_leaderboard_refresh()
        await self.schedule_leaderboard_cache_cleanup()

        logger.info("All recurring schedules started")

    async def cleanup(self):
        """Clean up resources."""
        if self.redis_pool:
            await self.redis_pool.close()
            await self.redis_pool.wait_closed()


async def start_scheduler():
    """Start the task scheduler."""
    scheduler = TaskScheduler()
    try:
        await scheduler.start_recurring_schedules()

        # Keep scheduler running
        while True:
            await asyncio.sleep(60)  # Check every minute

            # Re-schedule tasks that should repeat
            current_time = datetime.now(UTC)

            # Re-schedule leaderboard refresh every 30 minutes
            if current_time.minute % 30 == 0:
                await scheduler.schedule_leaderboard_refresh()

            # Re-schedule cache cleanup every 2 hours
            if current_time.hour % 2 == 0 and current_time.minute == 0:
                await scheduler.schedule_leaderboard_cache_cleanup()

    except KeyboardInterrupt:
        logger.info("Scheduler interrupted")
    finally:
        await scheduler.cleanup()


if __name__ == "__main__":
    asyncio.run(start_scheduler())
