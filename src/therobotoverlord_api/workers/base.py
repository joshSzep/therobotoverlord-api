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
        # This method should be implemented by classes that use this mixin
        # For now, we'll provide a basic implementation
        logger.warning(f"update_queue_status not implemented for {queue_table}")
        raise NotImplementedError("update_queue_status must be implemented by subclass")

    async def get_queue_item(
        self, queue_table: str, queue_id: UUID
    ) -> dict[str, Any] | None:
        """Get queue item by ID."""
        # This method should be implemented by classes that use this mixin
        # For now, we'll provide a basic implementation
        logger.warning(f"get_queue_item not implemented for {queue_table}")
        raise NotImplementedError("get_queue_item must be implemented by subclass")

    async def process_queue_item(
        self,
        ctx: dict[str, Any],
        queue_table: str,
        queue_id: UUID,
        content_id: UUID,
        processor_func: Callable[..., Any],
    ) -> bool:
        """Generic queue item processing workflow."""
        db = ctx.get("db")
        if not db:
            logger.error("Database connection not available in context")
            return False

        try:
            # Update status to processing
            await self.update_queue_status(
                queue_table, queue_id, "processing", ctx.get("worker_id")
            )

            # Process the content
            success = await processor_func(ctx, content_id)

            # Update final status
            final_status = "completed" if success else "pending"
            await self.update_queue_status(queue_table, queue_id, final_status)

            if success:
                logger.info(f"Successfully processed {queue_table} item {queue_id}")
            else:
                logger.warning(f"Failed to process {queue_table} item {queue_id}")

            return success

        except Exception as e:
            logger.exception(f"Error processing {queue_table} item {queue_id}")
            # Reset to pending for retry
            await self.update_queue_status(queue_table, queue_id, "pending")
            return False


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
