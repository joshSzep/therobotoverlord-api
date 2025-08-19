"""ToS screening queue repository for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.base import QueueStatus
from therobotoverlord_api.database.models.queue import PostTosScreeningQueue
from therobotoverlord_api.database.models.queue import PostTosScreeningQueueCreate
from therobotoverlord_api.database.models.queue import QueueItemUpdate
from therobotoverlord_api.database.repositories.base import BaseRepository


class PostTosScreeningQueueRepository(BaseRepository[PostTosScreeningQueue]):
    """Repository for ToS screening queue operations."""

    def __init__(self):
        super().__init__("post_tos_screening_queue")

    def _record_to_model(self, record: Record) -> PostTosScreeningQueue:
        """Convert database record to PostTosScreeningQueue model."""
        return PostTosScreeningQueue.model_validate(record)

    async def create(
        self, queue_data: PostTosScreeningQueueCreate
    ) -> PostTosScreeningQueue:
        """Create a new ToS screening queue item."""
        data = queue_data.model_dump(exclude_unset=True)
        data["created_at"] = datetime.now(UTC)
        return await self.create_from_dict(data)

    async def update(
        self, pk: UUID, queue_data: QueueItemUpdate
    ) -> PostTosScreeningQueue | None:
        """Update a ToS screening queue item."""
        data = queue_data.model_dump(exclude_unset=True)
        if data:
            data["updated_at"] = datetime.now(UTC)
            return await self.update_from_dict(pk, data)
        return await self.get_by_pk(pk)

    async def get_next_pending(
        self, worker_id: str | None = None
    ) -> PostTosScreeningQueue | None:
        """Get the next pending item in the ToS screening queue."""
        query = """
            SELECT * FROM post_tos_screening_queue
            WHERE status = $1
            ORDER BY priority_score DESC, entered_queue_at ASC
            LIMIT 1
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, QueueStatus.PENDING.value)
            if record:
                queue_item = self._record_to_model(record)

                # Assign worker if provided
                if worker_id:
                    await self.update(
                        queue_item.pk,
                        QueueItemUpdate(
                            status=QueueStatus.PROCESSING,
                            worker_assigned_at=datetime.now(UTC),
                            worker_id=worker_id,
                        ),
                    )
                    queue_item.status = QueueStatus.PROCESSING
                    queue_item.worker_assigned_at = datetime.now(UTC)
                    queue_item.worker_id = worker_id

                return queue_item
            return None

    async def get_by_post_pk(self, post_pk: UUID) -> PostTosScreeningQueue | None:
        """Get ToS screening queue item by post PK."""
        query = """
            SELECT * FROM post_tos_screening_queue
            WHERE post_pk = $1
            ORDER BY created_at DESC
            LIMIT 1
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, post_pk)
            return self._record_to_model(record) if record else None

    async def get_queue_length(self) -> int:
        """Get the current length of the ToS screening queue."""
        query = """
            SELECT COUNT(*) FROM post_tos_screening_queue
            WHERE status = $1
        """

        async with get_db_connection() as connection:
            result = await connection.fetchval(query, QueueStatus.PENDING.value)
            return result or 0

    async def get_by_status(
        self, status: QueueStatus, limit: int = 100, offset: int = 0
    ) -> list[PostTosScreeningQueue]:
        """Get ToS screening queue items by status."""
        query = """
            SELECT * FROM post_tos_screening_queue
            WHERE status = $1
            ORDER BY priority_score DESC, entered_queue_at ASC
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, status.value, limit, offset)
            return [self._record_to_model(record) for record in records]

    async def complete_processing(self, pk: UUID) -> PostTosScreeningQueue | None:
        """Mark a ToS screening queue item as completed."""
        return await self.update(
            pk,
            QueueItemUpdate(
                status=QueueStatus.COMPLETED,
            ),
        )

    async def get_processing_by_worker(
        self, worker_id: str
    ) -> list[PostTosScreeningQueue]:
        """Get items currently being processed by a specific worker."""
        query = """
            SELECT * FROM post_tos_screening_queue
            WHERE status = $1 AND worker_id = $2
            ORDER BY worker_assigned_at ASC
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(
                query, QueueStatus.PROCESSING.value, worker_id
            )
            return [self._record_to_model(record) for record in records]
