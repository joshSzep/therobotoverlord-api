"""Queue management service for The Robot Overlord."""

import logging

from datetime import UTC
from datetime import datetime
from typing import Any
from uuid import UUID

from therobotoverlord_api.database.connection import db
from therobotoverlord_api.workers.redis_connection import get_redis_pool

logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing content moderation queues."""

    def __init__(self):
        self.db = db
        self.redis_pool = None

    async def _ensure_connections(self):
        """Ensure database and Redis connections are available."""
        if not self.db:
            self.db = db
        if not self.redis_pool:
            self.redis_pool = await get_redis_pool()

        if not self.redis_pool:
            raise RuntimeError("Failed to establish Redis connection")

    async def add_topic_to_queue(
        self, topic_id: UUID, priority: int = 0
    ) -> UUID | None:
        """Add a topic to the moderation queue."""
        await self._ensure_connections()

        try:
            # Calculate priority score (timestamp + priority offset)
            now = datetime.now(UTC)
            priority_score = int(now.timestamp() * 1000) + priority

            # Get current queue position
            position = await self._get_next_queue_position("topic_creation_queue")

            # Insert into queue
            query = """
                INSERT INTO topic_creation_queue
                (topic_pk, priority_score, priority, position_in_queue, status, entered_queue_at)
                VALUES ($1, $2, $3, $4, 'pending', $5)
                RETURNING pk
            """

            result = await self.db.fetchrow(
                query, topic_id, priority_score, priority, position, now
            )

            if result:
                queue_id = result["pk"]

                # Enqueue the job in Redis
                if self.redis_pool:
                    await self.redis_pool.enqueue_job(
                        "process_topic_moderation",
                        str(queue_id),
                        str(topic_id),
                        _job_id=f"topic_{topic_id}",
                    )
                else:
                    raise RuntimeError("Redis pool not available")

                logger.info(f"Added topic {topic_id} to queue at position {position}")
                return queue_id

            return None

        except Exception as e:
            logger.exception(f"Error adding topic {topic_id} to queue: {e}")
            return None

    async def add_post_to_queue(
        self, post_id: UUID, topic_id: UUID, priority: int = 0
    ) -> UUID | None:
        """Add a post to the moderation queue."""
        await self._ensure_connections()

        try:
            # Calculate priority score
            now = datetime.now(UTC)
            priority_score = int(now.timestamp() * 1000) + priority

            # Get current queue position
            position = await self._get_next_queue_position("post_moderation_queue")

            # Insert into queue
            query = """
                INSERT INTO post_moderation_queue
                (post_pk, topic_pk, priority_score, priority, position_in_queue, status, entered_queue_at)
                VALUES ($1, $2, $3, $4, $5, 'pending', $6)
                RETURNING pk
            """

            result = await self.db.fetchrow(
                query, post_id, topic_id, priority_score, priority, position, now
            )

            if result:
                queue_id = result["pk"]

                # Enqueue the job in Redis
                if self.redis_pool:
                    await self.redis_pool.enqueue_job(
                        "process_post_moderation",
                        str(queue_id),
                        str(post_id),
                        _job_id=f"post_{post_id}",
                    )
                else:
                    raise RuntimeError("Redis pool not available")

                logger.info(f"Added post {post_id} to queue at position {position}")
                return queue_id

            return None

        except Exception as e:
            logger.exception(f"Error adding post {post_id} to queue: {e}")
            return None

    async def get_queue_status(self, queue_type: str) -> dict[str, Any]:
        """Get status information for a specific queue."""
        await self._ensure_connections()

        queue_table = self._get_queue_table(queue_type)
        if not queue_table:
            return {"error": "Invalid queue type"}

        try:
            # Get queue statistics
            query = f"""  # nosec B608
                SELECT
                    COUNT(*) as total_items,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_items,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing_items,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_items,
                    AVG(EXTRACT(EPOCH FROM (NOW() - entered_queue_at))) FILTER (WHERE status = 'completed') as avg_processing_time,
                    MIN(position_in_queue) FILTER (WHERE status = 'pending') as next_position
                FROM {queue_table}
                WHERE entered_queue_at > NOW() - INTERVAL '24 hours'
            """

            result = await self.db.fetchrow(query)

            if result:
                return {
                    "queue_type": queue_type,
                    "total_items": result["total_items"] or 0,
                    "pending_items": result["pending_items"] or 0,
                    "processing_items": result["processing_items"] or 0,
                    "completed_items": result["completed_items"] or 0,
                    "avg_processing_time_seconds": result["avg_processing_time"] or 0,
                    "next_position": result["next_position"] or 0,
                    "estimated_wait_time": await self._estimate_wait_time(queue_type),
                }

            return {
                "queue_type": queue_type,
                "total_items": 0,
                "pending_items": 0,
                "processing_items": 0,
                "completed_items": 0,
                "avg_processing_time_seconds": 0,
                "next_position": 0,
                "estimated_wait_time": 0,
            }

        except Exception as e:
            logger.exception(f"Error getting queue status for {queue_type}: {e}")
            return {"error": "Failed to get queue status"}

    async def get_content_position(
        self, content_type: str, content_id: UUID
    ) -> dict[str, Any] | None:
        """Get the queue position for specific content."""
        await self._ensure_connections()

        queue_table = self._get_queue_table(content_type)
        if not queue_table:
            return None

        content_field = "topic_pk" if content_type == "topics" else "post_pk"

        try:
            query = f"""  # nosec B608
                SELECT
                    pk as queue_id,
                    position_in_queue,
                    status,
                    entered_queue_at,
                    estimated_completion_at,
                    worker_assigned_at,
                    worker_id
                FROM {queue_table}
                WHERE {content_field} = $1 AND status != 'completed'
                ORDER BY entered_queue_at DESC
                LIMIT 1
            """

            result = await self.db.fetchrow(query, content_id)

            if result:
                return {
                    "queue_id": result["queue_id"],
                    "position": result["position_in_queue"],
                    "status": result["status"],
                    "entered_at": result["entered_queue_at"],
                    "estimated_completion": result["estimated_completion_at"],
                    "worker_assigned_at": result["worker_assigned_at"],
                    "worker_id": result["worker_id"],
                }

            return None

        except Exception as e:
            logger.exception(
                f"Error getting position for {content_type} {content_id}: {e}"
            )
            return None

    async def _get_next_queue_position(self, queue_table: str) -> int:
        """Get the next position number in the queue."""
        query = f"""  # nosec B608
            SELECT COALESCE(MAX(position_in_queue), 0) + 1 as next_position
            FROM {queue_table}
        """

        result = await self.db.fetchrow(query)
        if result is None:
            return 1
        return result["next_position"]

    def _get_queue_table(self, queue_type: str) -> str | None:
        """Get the database table name for a queue type."""
        queue_tables = {
            "topics": "topic_creation_queue",
            "posts": "post_moderation_queue",
            "messages": "private_message_queue",
        }
        return queue_tables.get(queue_type)

    async def _estimate_wait_time(self, queue_type: str) -> int:
        """Estimate wait time in seconds for new items in the queue."""
        queue_table = self._get_queue_table(queue_type)
        if not queue_table:
            return 0

        try:
            # Calculate average processing time from recent completions
            query = f"""  # nosec B608
                SELECT AVG(EXTRACT(EPOCH FROM (updated_at - worker_assigned_at))) as avg_time
                FROM {queue_table}
                WHERE status = 'completed'
                AND worker_assigned_at IS NOT NULL
                AND updated_at > NOW() - INTERVAL '1 hour'
            """

            result = await self.db.fetchrow(query)
            avg_processing_time = (
                result["avg_time"] if result else None
            ) or 30  # Default 30 seconds

            # Count pending items
            pending_query = f"""  # nosec B608
                SELECT COUNT(*) as pending_count
                FROM {queue_table}
                WHERE status = 'pending'
            """

            pending_result = await self.db.fetchrow(pending_query)
            pending_count = (
                pending_result["pending_count"] if pending_result else None
            ) or 0

            # Estimate: pending items * average processing time
            return int(pending_count * avg_processing_time)

        except Exception as e:
            logger.exception(f"Error estimating wait time for {queue_type}: {e}")
            return 0


# Global service instance
queue_service = QueueService()


async def get_queue_service() -> QueueService:
    """Get the queue service instance."""
    return queue_service
