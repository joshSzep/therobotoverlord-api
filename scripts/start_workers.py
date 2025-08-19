#!/usr/bin/env python3
"""
Worker startup script for The Robot Overlord API.

This script starts the Arq workers for processing background tasks
including topic and post moderation queues.
"""

import asyncio
import logging
import signal
import sys

from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from arq import create_pool
from arq.connections import RedisSettings as ArqRedisSettings
from arq.worker import Worker

from therobotoverlord_api.config.redis import get_redis_settings
from therobotoverlord_api.workers.post_worker import process_post_moderation
from therobotoverlord_api.workers.topic_worker import process_topic_moderation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class WorkerManager:
    """Manages multiple Arq workers."""

    def __init__(self):
        self.workers: list[Worker] = []
        self.tasks: list[asyncio.Task] = []
        self.redis_pool = None
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Start all workers."""
        try:
            # Get Redis settings
            redis_settings = get_redis_settings()

            # Create Redis connection pool
            # Convert to arq RedisSettings format
            arq_settings = ArqRedisSettings(
                host=redis_settings.host,
                port=redis_settings.port,
                database=redis_settings.database,
                password=redis_settings.password,
                max_connections=redis_settings.max_connections,
            )
            self.redis_pool = await create_pool(arq_settings)
            logger.info("Connected to Redis")

            # Define worker configurations
            worker_configs = [
                {
                    "name": "topic_moderation_worker",
                    "functions": [process_topic_moderation],
                    "queue_name": "topic_moderation",
                },
                {
                    "name": "post_moderation_worker",
                    "functions": [process_post_moderation],
                    "queue_name": "post_moderation",
                },
            ]

            # Start workers
            for config in worker_configs:
                worker = Worker(
                    functions=config["functions"],
                    redis_pool=self.redis_pool,
                    queue_name=config["queue_name"],
                    max_jobs=5,  # Process up to 5 jobs concurrently per worker
                    job_timeout=300,  # 5 minute timeout per job
                    keep_result=3600,  # Keep results for 1 hour
                )

                # Start worker in background
                task = asyncio.create_task(self._run_worker(worker, config["name"]))
                self.workers.append(worker)
                self.tasks.append(task)
                logger.info(f"Started {config['name']} worker")

            logger.info(f"All {len(self.workers)} workers started successfully")

            # Wait for shutdown signal
            await self.shutdown_event.wait()

        except Exception as e:
            logger.exception(f"Failed to start workers: {e}")
            raise
        finally:
            await self.cleanup()

    async def _run_worker(self, worker: Worker, name: str):
        """Run a single worker with error handling."""
        try:
            await worker.async_run()
        except Exception as e:
            logger.exception(f"Worker {name} failed: {e}")
            # Signal shutdown if any worker fails
            self.shutdown_event.set()

    async def cleanup(self):
        """Clean up resources."""
        logger.info("Shutting down workers...")

        # Close workers
        for worker in self.workers:
            try:
                await worker.close()
            except Exception as e:
                logger.error(f"Error closing worker: {e}")

        # Close Redis pool
        if self.redis_pool:
            try:
                await self.redis_pool.close()
                await self.redis_pool.wait_closed()
            except Exception as e:
                logger.error(f"Error closing Redis pool: {e}")

        logger.info("Cleanup complete")

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()


async def main():
    """Main entry point."""
    manager = WorkerManager()

    # Set up signal handlers
    signal.signal(signal.SIGINT, manager.handle_shutdown)
    signal.signal(signal.SIGTERM, manager.handle_shutdown)

    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.exception(f"Worker manager failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
