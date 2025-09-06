"""Worker health monitoring for The Robot Overlord."""

import logging

from datetime import UTC
from datetime import datetime
from typing import Any
from typing import cast

import redis.asyncio as redis

from therobotoverlord_api.config.redis import get_redis_settings
from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import create_worker_class

logger = logging.getLogger(__name__)


class WorkerHealthMonitor(BaseWorker):
    """Monitor health of worker systems and queues."""

    def __init__(self):
        super().__init__()
        self.redis_client: redis.Redis | None = None

    async def check_worker_health(self, ctx: dict) -> bool:
        """Check overall worker system health."""
        try:
            health_status: dict[str, Any] = {
                "timestamp": datetime.now(UTC).isoformat(),
                "database": await self._check_database_health(),
                "redis": await self._check_redis_health(),
                "queues": await self._check_queue_health(),
                "workers": await self._check_worker_status(),
            }

            # Log health status
            overall_healthy = all(
                [
                    health_status["database"]["healthy"],
                    health_status["redis"]["healthy"],
                    health_status["queues"]["healthy"],
                ]
            )

            if overall_healthy:
                logger.info("Worker system health check passed")
            else:
                logger.warning(f"Worker system health issues detected: {health_status}")

            # Store health metrics in Redis for monitoring
            await self._store_health_metrics(health_status)

            return overall_healthy

        except Exception:
            logger.exception("Error during worker health check")
            return False

    async def _check_database_health(self) -> dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            async with get_db_connection() as connection:
                # Simple query to test connectivity
                result = await connection.fetchval("SELECT 1")

                # Check connection pool stats
                pool_stats = await connection.get_pool().get_stats()

                return {
                    "healthy": result == 1,
                    "pool_size": pool_stats.get("size", 0),
                    "pool_used": pool_stats.get("used", 0),
                    "pool_free": pool_stats.get("free", 0),
                }
        except Exception as e:
            logger.exception("Database health check failed")
            return {
                "healthy": False,
                "error": str(e),
            }

    async def _check_redis_health(self) -> dict[str, Any]:
        """Check Redis connectivity and performance."""
        try:
            if not self.redis_client:
                redis_settings = get_redis_settings()
                self.redis_client = redis.from_url(
                    redis_settings.redis_url,
                    decode_responses=True,
                )

            # Test Redis connectivity
            pong = await self.redis_client.ping()

            # Get Redis info
            info = await self.redis_client.info()

            return {
                "healthy": pong,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "uptime": info.get("uptime_in_seconds", 0),
            }
        except Exception as e:
            logger.exception("Redis health check failed")
            return {
                "healthy": False,
                "error": str(e),
            }

    async def _check_queue_health(self) -> dict[str, Any]:
        """Check queue system health and pending items."""
        try:
            async with get_db_connection() as connection:
                # Check various queue tables for pending items
                queue_stats = {}

                queue_tables = [
                    "topic_creation_queue",
                    "post_moderation_queue",
                    "private_message_queue",
                    "appeal_review_queue",
                ]

                total_pending = 0
                for table in queue_tables:
                    try:
                        count = await connection.fetchval(
                            f"SELECT COUNT(*) FROM {table} WHERE status = 'pending'"  # nosec B608
                        )
                        queue_stats[table] = count or 0
                        total_pending += count or 0
                    except Exception:
                        # Table might not exist
                        queue_stats[table] = "unknown"

                return {
                    "healthy": total_pending < 1000,  # Alert if too many pending
                    "total_pending": total_pending,
                    "queue_details": queue_stats,
                }
        except Exception as e:
            logger.exception("Queue health check failed")
            return {
                "healthy": False,
                "error": str(e),
            }

    async def _check_worker_status(self) -> dict[str, Any]:
        """Check status of individual workers."""
        try:
            if not self.redis_client:
                return {"healthy": False, "error": "Redis not available"}

            # Get worker information from Redis/ARQ
            worker_info_raw = self.redis_client.hgetall("arq:health")
            worker_info = cast("dict[str, str]", worker_info_raw or {})

            return {
                "healthy": len(worker_info) > 0,
                "active_workers": len(worker_info),
                "worker_details": worker_info,
            }
        except Exception as e:
            logger.exception("Worker status check failed")
            return {
                "healthy": False,
                "error": str(e),
            }

    async def _store_health_metrics(self, health_status: dict[str, Any]) -> None:
        """Store health metrics in Redis for monitoring dashboard."""
        try:
            if not self.redis_client:
                return

            # Store current health status
            self.redis_client.hset(
                "worker:health:current",
                mapping={
                    "timestamp": health_status["timestamp"],
                    "overall_healthy": str(
                        health_status["database"]["healthy"]
                        and health_status["redis"]["healthy"]
                        and health_status["queues"]["healthy"]
                    ),
                    "database_healthy": str(health_status["database"]["healthy"]),
                    "redis_healthy": str(health_status["redis"]["healthy"]),
                    "queues_healthy": str(health_status["queues"]["healthy"]),
                    "total_pending": str(
                        health_status["queues"].get("total_pending", 0)
                    ),
                },
            )

            # Store in time-series for historical tracking
            timestamp_key = (
                f"worker:health:history:{datetime.now(UTC).strftime('%Y%m%d%H%M')}"
            )
            await self.redis_client.setex(
                timestamp_key,
                3600,  # Keep for 1 hour
                str(health_status),
            )

        except Exception:
            logger.exception("Failed to store health metrics")

    async def cleanup_failed_jobs(self, ctx: dict) -> bool:
        """Clean up failed or stuck jobs."""
        try:
            if not self.redis_client:
                logger.error("Redis not available for job cleanup")
                return False

            # Get failed jobs from ARQ
            failed_jobs_raw = self.redis_client.lrange("arq:failed", 0, -1)
            failed_jobs = cast("list[str]", failed_jobs_raw or [])

            if failed_jobs:
                logger.info(f"Found {len(failed_jobs)} failed jobs for cleanup")

                # Clear failed jobs (they should be retried or logged)
                self.redis_client.delete("arq:failed")

                logger.info(f"Cleaned up {len(failed_jobs)} failed jobs")

            return True

        except Exception:
            logger.exception("Error during failed job cleanup")
            return False


# Define worker functions
async def check_worker_health(ctx: dict) -> bool:
    """Worker function for health monitoring."""
    try:
        monitor = WorkerHealthMonitor()
        return await monitor.check_worker_health(ctx)
    except Exception:
        logger.exception("Error in worker health check")
        return False


async def cleanup_failed_jobs(ctx: dict) -> bool:
    """Worker function for cleaning up failed jobs."""
    try:
        monitor = WorkerHealthMonitor()
        return await monitor.cleanup_failed_jobs(ctx)
    except Exception:
        logger.exception("Error in failed job cleanup")
        return False


# Create the worker class
HealthMonitorWorker = create_worker_class(
    worker_functions=[check_worker_health, cleanup_failed_jobs],
    functions=[check_worker_health, cleanup_failed_jobs],
    max_jobs=1,  # Single health monitoring job at a time
    job_timeout=60,  # 1 minute for health checks
)
