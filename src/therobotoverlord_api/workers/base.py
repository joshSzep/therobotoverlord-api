"""Base worker classes for The Robot Overlord queue system."""

import logging

from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import Any
from uuid import UUID

if TYPE_CHECKING:
    import asyncpg

from arq.connections import RedisSettings

from therobotoverlord_api.config.redis import get_redis_settings
from therobotoverlord_api.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class BaseWorker:
    """Base class for all Robot Overlord workers."""

    def __init__(self):
        self.redis_settings = self._get_arq_redis_settings()
        self.db: asyncpg.Connection | None = None

    def _get_arq_redis_settings(self) -> RedisSettings:
        """Convert Redis settings to Arq format."""
        settings = get_redis_settings()
        return RedisSettings(
            host=settings.host,
            port=settings.port,
            database=settings.database,
            password=settings.password,
            max_connections=settings.max_connections,
        )

    async def startup(self, ctx: dict[str, Any]) -> None:
        """Worker startup hook."""
        logger.info(f"Starting {self.__class__.__name__}")
        # Note: Database connection will be managed per-request
        # Store connection factory in context for workers to use
        ctx["get_db_connection"] = get_db_connection

    async def shutdown(self, ctx: dict[str, Any]) -> None:
        """Worker shutdown hook."""
        logger.info(f"Shutting down {self.__class__.__name__}")
        if self.db is not None:
            await self.db.close()

    async def update_queue_status(
        self,
        queue_table: str,
        queue_id: UUID,
        status: str,
        worker_id: str | None = None,
    ) -> None:
        """Update queue item status."""
        if not self.db:
            logger.error("Database connection not available")
            return

        update_fields = {"status": status}
        if worker_id:
            update_fields["worker_id"] = worker_id

        # Build dynamic query
        query = f"""  # nosec B608
            UPDATE {queue_table}
            SET {", ".join(f"{k} = ${i + 2}" for i, k in enumerate(update_fields.keys()))}
            WHERE pk = $1
        """

        await self.db.execute(query, queue_id, *update_fields.values())

    async def get_queue_item(
        self, queue_table: str, queue_id: UUID
    ) -> dict[str, Any] | None:
        """Get queue item by ID."""
        if self.db is None:
            logger.error("Database connection not available")
            return None

        query = f"SELECT * FROM {queue_table} WHERE pk = $1"  # nosec B608
        record = await self.db.fetchrow(query, queue_id)
        return dict(record) if record else None


class QueueWorkerMixin:
    """Mixin for queue-specific worker functionality."""

    async def update_queue_status(
        self,
        queue_table: str,
        queue_id: UUID,
        status: str,
        worker_id: str | None = None,
    ) -> None:
        """Update queue item status."""
        try:
            async with get_db_connection() as connection:
                await self._update_queue_status_with_connection(
                    connection, queue_table, queue_id, status, worker_id
                )
        except Exception:
            logger.exception(
                f"Failed to update queue status for {queue_table} item {queue_id}"
            )

    async def get_queue_item(
        self, queue_table: str, queue_id: UUID
    ) -> dict[str, Any] | None:
        """Get queue item by ID."""
        try:
            async with get_db_connection() as connection:
                query = f"SELECT * FROM {queue_table} WHERE pk = $1"  # nosec B608
                record = await connection.fetchrow(query, queue_id)
                return dict(record) if record else None
        except Exception:
            logger.exception(
                f"Failed to get queue item from {queue_table} with id {queue_id}"
            )
            return None

    async def process_queue_item(
        self,
        ctx: dict[str, Any],
        queue_table: str,
        queue_id: UUID,
        content_id: UUID,
        processor_func: Callable[..., Any],
        max_retries: int = 3,
    ) -> bool:
        """Generic queue item processing workflow with retry logic."""
        try:
            async with get_db_connection() as connection:
                # Get current retry count
                retry_count = await self._get_retry_count(
                    connection, queue_table, queue_id
                )

                if retry_count >= max_retries:
                    logger.error(
                        f"Max retries ({max_retries}) exceeded for {queue_table} item {queue_id}"
                    )
                    await self._update_queue_status_with_connection(
                        connection, queue_table, queue_id, "failed"
                    )
                    return False

                # Update status to processing
                await self._update_queue_status_with_connection(
                    connection,
                    queue_table,
                    queue_id,
                    "processing",
                    ctx.get("worker_id"),
                )

                # Process the content
                success = await processor_func(ctx, content_id)

                if success:
                    # Update final status to completed
                    await self._update_queue_status_with_connection(
                        connection, queue_table, queue_id, "completed"
                    )
                    logger.info(f"Successfully processed {queue_table} item {queue_id}")
                    return True

                # Increment retry count and reset to pending
                await self._increment_retry_count(connection, queue_table, queue_id)
                await self._update_queue_status_with_connection(
                    connection, queue_table, queue_id, "pending"
                )
                logger.warning(
                    f"Failed to process {queue_table} item {queue_id}, retry {retry_count + 1}/{max_retries}"
                )
                return False

        except Exception as e:
            logger.exception(f"Error processing {queue_table} item {queue_id}")
            try:
                async with get_db_connection() as connection:
                    await self._increment_retry_count(connection, queue_table, queue_id)
                    await self._update_queue_status_with_connection(
                        connection, queue_table, queue_id, "pending"
                    )
            except Exception:
                logger.exception(
                    f"Failed to update retry count for {queue_table} item {queue_id}"
                )
            return False

    async def _get_retry_count(
        self, connection, queue_table: str, queue_id: UUID
    ) -> int:
        """Get current retry count for a queue item."""
        query = f"SELECT COALESCE(retry_count, 0) FROM {queue_table} WHERE pk = $1"  # nosec B608
        result = await connection.fetchval(query, queue_id)
        return result or 0

    async def _increment_retry_count(
        self, connection, queue_table: str, queue_id: UUID
    ) -> None:
        """Increment retry count for a queue item."""
        query = f"UPDATE {queue_table} SET retry_count = COALESCE(retry_count, 0) + 1 WHERE pk = $1"  # nosec B608
        await connection.execute(query, queue_id)

    async def _update_queue_status_with_connection(
        self,
        connection,
        queue_table: str,
        queue_id: UUID,
        status: str,
        worker_id: str | None = None,
    ) -> None:
        """Update queue item status with provided connection."""
        update_fields = {"status": status}
        if worker_id:
            update_fields["worker_id"] = worker_id

        # Build dynamic query
        query = f"""  # nosec B608
            UPDATE {queue_table}
            SET {", ".join(f"{k} = ${i + 2}" for i, k in enumerate(update_fields.keys()))}
            WHERE pk = $1
        """

        await connection.execute(query, queue_id, *update_fields.values())


def create_worker_class(
    worker_functions: list[Callable],
    functions: list[Callable],
    max_jobs: int = 10,
    job_timeout: int = 300,
) -> type[BaseWorker]:
    """Create a worker class with the specified functions."""

    class DynamicWorker(BaseWorker):
        pass

    # Set class attributes after class definition
    DynamicWorker.functions = {f.__name__: f for f in functions}  # type: ignore[attr-defined]
    DynamicWorker.max_jobs = max_jobs  # type: ignore[attr-defined]
    DynamicWorker.job_timeout = job_timeout  # type: ignore[attr-defined]

    return DynamicWorker
