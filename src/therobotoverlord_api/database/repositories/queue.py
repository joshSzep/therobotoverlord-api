"""Queue repositories for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.base import QueueStatus
from therobotoverlord_api.database.models.queue import PostModerationQueue
from therobotoverlord_api.database.models.queue import PostModerationQueueCreate
from therobotoverlord_api.database.models.queue import PrivateMessageQueue
from therobotoverlord_api.database.models.queue import PrivateMessageQueueCreate
from therobotoverlord_api.database.models.queue import QueueItemUpdate
from therobotoverlord_api.database.models.queue import QueueOverview
from therobotoverlord_api.database.models.queue import QueueWithContent
from therobotoverlord_api.database.models.queue import TopicCreationQueue
from therobotoverlord_api.database.models.queue import TopicCreationQueueCreate
from therobotoverlord_api.database.repositories.base import BaseRepository


class TopicCreationQueueRepository(BaseRepository[TopicCreationQueue]):
    """Repository for topic creation queue operations."""

    def __init__(self):
        super().__init__("topic_creation_queue")

    def _record_to_model(self, record: Record) -> TopicCreationQueue:
        """Convert database record to TopicCreationQueue model."""
        return TopicCreationQueue.model_validate(record)

    async def create(self, queue_data: TopicCreationQueueCreate) -> TopicCreationQueue:
        """Create a new topic creation queue item."""
        data = queue_data.model_dump(exclude_unset=True)
        data["created_at"] = datetime.now(UTC)
        return await self.create_from_dict(data)

    async def update(
        self, pk: UUID, queue_data: QueueItemUpdate
    ) -> TopicCreationQueue | None:
        """Update a topic creation queue item."""
        data = queue_data.model_dump(exclude_unset=True, exclude_none=True)
        return await self.update_from_dict(pk, data)

    async def get_next_pending(self) -> TopicCreationQueue | None:
        """Get the next pending item in the queue."""
        query = """
            SELECT * FROM topic_creation_queue
            WHERE status = 'pending'
            ORDER BY priority_score ASC, entered_queue_at ASC
            LIMIT 1
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query)
            return self._record_to_model(record) if record else None

    async def assign_to_worker(
        self, pk: UUID, worker_id: str
    ) -> TopicCreationQueue | None:
        """Assign queue item to worker."""
        data = {
            "status": QueueStatus.PROCESSING.value,
            "worker_assigned_at": datetime.now(UTC),
            "worker_id": worker_id,
        }
        return await self.update_from_dict(pk, data)

    async def complete_processing(self, pk: UUID) -> TopicCreationQueue | None:
        """Mark queue item as completed."""
        data = {"status": QueueStatus.COMPLETED.value}
        return await self.update_from_dict(pk, data)

    async def get_queue_position(self, topic_pk: UUID) -> int | None:
        """Get position of topic in queue."""
        query = """
            SELECT position_in_queue
            FROM topic_creation_queue
            WHERE topic_pk = $1 AND status != 'completed'
        """

        async with get_db_connection() as connection:
            return await connection.fetchval(query, topic_pk)

    async def update_queue_positions(self) -> None:
        """Update position_in_queue for all pending items."""
        query = """
            UPDATE topic_creation_queue
            SET position_in_queue = queue_position.new_position
            FROM (
                SELECT
                    pk,
                    ROW_NUMBER() OVER (ORDER BY priority_score ASC, entered_queue_at ASC) as new_position
                FROM topic_creation_queue
                WHERE status = 'pending'
            ) as queue_position
            WHERE topic_creation_queue.pk = queue_position.pk
        """

        async with get_db_connection() as connection:
            await connection.execute(query)


class PostModerationQueueRepository(BaseRepository[PostModerationQueue]):
    """Repository for post moderation queue operations."""

    def __init__(self):
        super().__init__("post_moderation_queue")

    def _record_to_model(self, record: Record) -> PostModerationQueue:
        """Convert database record to PostModerationQueue model."""
        return PostModerationQueue.model_validate(record)

    async def create(
        self, queue_data: PostModerationQueueCreate
    ) -> PostModerationQueue:
        """Create a new post moderation queue item."""
        data = queue_data.model_dump(exclude_unset=True)
        data["created_at"] = datetime.now(UTC)
        return await self.create_from_dict(data)

    async def update(
        self, pk: UUID, queue_data: QueueItemUpdate
    ) -> PostModerationQueue | None:
        """Update a post moderation queue item."""
        data = queue_data.model_dump(exclude_unset=True, exclude_none=True)
        return await self.update_from_dict(pk, data)

    async def get_next_pending_by_topic(
        self, topic_pk: UUID
    ) -> PostModerationQueue | None:
        """Get the next pending item in topic-specific queue."""
        query = """
            SELECT * FROM post_moderation_queue
            WHERE topic_pk = $1 AND status = 'pending'
            ORDER BY priority_score ASC, entered_queue_at ASC
            LIMIT 1
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, topic_pk)
            return self._record_to_model(record) if record else None

    async def get_next_pending_global(self) -> PostModerationQueue | None:
        """Get the next pending item across all topics."""
        query = """
            SELECT * FROM post_moderation_queue
            WHERE status = 'pending'
            ORDER BY priority_score ASC, entered_queue_at ASC
            LIMIT 1
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query)
            return self._record_to_model(record) if record else None

    async def assign_to_worker(
        self, pk: UUID, worker_id: str
    ) -> PostModerationQueue | None:
        """Assign queue item to worker."""
        data = {
            "status": QueueStatus.PROCESSING.value,
            "worker_assigned_at": datetime.now(UTC),
            "worker_id": worker_id,
        }
        return await self.update_from_dict(pk, data)

    async def complete_processing(self, pk: UUID) -> PostModerationQueue | None:
        """Mark queue item as completed."""
        data = {"status": QueueStatus.COMPLETED.value}
        return await self.update_from_dict(pk, data)

    async def get_queue_position_by_topic(
        self, post_pk: UUID, topic_pk: UUID
    ) -> int | None:
        """Get position of post in topic-specific queue."""
        query = """
            SELECT position_in_queue
            FROM post_moderation_queue
            WHERE post_pk = $1 AND topic_pk = $2 AND status != 'completed'
        """

        async with get_db_connection() as connection:
            return await connection.fetchval(query, post_pk, topic_pk)

    async def update_queue_positions_by_topic(self, topic_pk: UUID) -> None:
        """Update position_in_queue for all pending items in a topic."""
        query = """
            UPDATE post_moderation_queue
            SET position_in_queue = queue_position.new_position
            FROM (
                SELECT
                    pk,
                    ROW_NUMBER() OVER (ORDER BY priority_score ASC, entered_queue_at ASC) as new_position
                FROM post_moderation_queue
                WHERE topic_pk = $1 AND status = 'pending'
            ) as queue_position
            WHERE post_moderation_queue.pk = queue_position.pk
        """

        async with get_db_connection() as connection:
            await connection.execute(query, topic_pk)

    async def count_by_topic(
        self, topic_pk: UUID, status: QueueStatus | None = None
    ) -> int:
        """Count queue items by topic and optional status."""
        if status:
            return await self.count(
                "topic_pk = $1 AND status = $2", [topic_pk, status.value]
            )
        return await self.count("topic_pk = $1", [topic_pk])


class PrivateMessageQueueRepository(BaseRepository[PrivateMessageQueue]):
    """Repository for private message queue operations."""

    def __init__(self):
        super().__init__("private_message_queue")

    def _record_to_model(self, record: Record) -> PrivateMessageQueue:
        """Convert database record to PrivateMessageQueue model."""
        return PrivateMessageQueue.model_validate(record)

    async def create(
        self, queue_data: PrivateMessageQueueCreate
    ) -> PrivateMessageQueue:
        """Create a new private message queue item."""
        data = queue_data.model_dump(exclude_unset=True)
        data["created_at"] = datetime.now(UTC)
        return await self.create_from_dict(data)

    async def update(
        self, pk: UUID, queue_data: QueueItemUpdate
    ) -> PrivateMessageQueue | None:
        """Update a private message queue item."""
        data = queue_data.model_dump(exclude_unset=True, exclude_none=True)
        return await self.update_from_dict(pk, data)

    async def get_next_pending_by_conversation(
        self, conversation_id: str
    ) -> PrivateMessageQueue | None:
        """Get the next pending item in conversation-specific queue."""
        query = """
            SELECT * FROM private_message_queue
            WHERE conversation_id = $1 AND status = 'pending'
            ORDER BY priority_score ASC, entered_queue_at ASC
            LIMIT 1
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, conversation_id)
            return self._record_to_model(record) if record else None

    async def assign_to_worker(
        self, pk: UUID, worker_id: str
    ) -> PrivateMessageQueue | None:
        """Assign queue item to worker."""
        data = {
            "status": QueueStatus.PROCESSING.value,
            "worker_assigned_at": datetime.now(UTC),
            "worker_id": worker_id,
        }
        return await self.update_from_dict(pk, data)

    async def complete_processing(self, pk: UUID) -> PrivateMessageQueue | None:
        """Mark queue item as completed."""
        data = {"status": QueueStatus.COMPLETED.value}
        return await self.update_from_dict(pk, data)

    async def get_queue_position_by_conversation(
        self, message_pk: UUID, conversation_id: str
    ) -> int | None:
        """Get position of message in conversation-specific queue."""
        query = """
            SELECT position_in_queue
            FROM private_message_queue
            WHERE message_pk = $1 AND conversation_id = $2 AND status != 'completed'
        """

        async with get_db_connection() as connection:
            return await connection.fetchval(query, message_pk, conversation_id)

    async def update_queue_positions_by_conversation(
        self, conversation_id: str
    ) -> None:
        """Update position_in_queue for all pending items in a conversation."""
        query = """
            UPDATE private_message_queue
            SET position_in_queue = queue_position.new_position
            FROM (
                SELECT
                    pk,
                    ROW_NUMBER() OVER (ORDER BY priority_score ASC, entered_queue_at ASC) as new_position
                FROM private_message_queue
                WHERE conversation_id = $1 AND status = 'pending'
            ) as queue_position
            WHERE private_message_queue.pk = queue_position.pk
        """

        async with get_db_connection() as connection:
            await connection.execute(query, conversation_id)

    async def count_by_conversation(
        self, conversation_id: str, status: QueueStatus | None = None
    ) -> int:
        """Count queue items by conversation and optional status."""
        if status:
            return await self.count(
                "conversation_id = $1 AND status = $2", [conversation_id, status.value]
            )
        return await self.count("conversation_id = $1", [conversation_id])


class QueueOverviewRepository:
    """Repository for queue overview and statistics."""

    async def get_queue_overview(self) -> QueueOverview:
        """Get overview of all queue lengths and statistics."""
        query = """
            SELECT
                (SELECT COUNT(*) FROM topic_creation_queue WHERE status = 'pending') as topic_creation_queue_length,
                (SELECT COUNT(*) FROM post_moderation_queue WHERE status = 'pending') as post_moderation_queue_length,
                (SELECT COUNT(*) FROM private_message_queue WHERE status = 'pending') as private_message_queue_length,
                NOW() as last_updated
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query)
            return QueueOverview.model_validate(record)

    async def get_queue_items_for_processing(
        self, limit: int = 10
    ) -> list[QueueWithContent]:
        """Get queue items across all queues for worker processing."""
        query = """
            SELECT
                'topic_creation' as queue_type,
                tcq.pk,
                tcq.topic_pk as content_pk,
                'topic' as content_type,
                tcq.priority_score,
                tcq.position_in_queue,
                tcq.status,
                tcq.entered_queue_at,
                tcq.worker_assigned_at,
                tcq.worker_id
            FROM topic_creation_queue tcq
            WHERE tcq.status = 'pending'

            UNION ALL

            SELECT
                'post_moderation' as queue_type,
                pmq.pk,
                pmq.post_pk as content_pk,
                'post' as content_type,
                pmq.priority_score,
                pmq.position_in_queue,
                pmq.status,
                pmq.entered_queue_at,
                pmq.worker_assigned_at,
                pmq.worker_id
            FROM post_moderation_queue pmq
            WHERE pmq.status = 'pending'

            UNION ALL

            SELECT
                'private_message' as queue_type,
                pmsgq.pk,
                pmsgq.message_pk as content_pk,
                'private_message' as content_type,
                pmsgq.priority_score,
                pmsgq.position_in_queue,
                pmsgq.status,
                pmsgq.entered_queue_at,
                pmsgq.worker_assigned_at,
                pmsgq.worker_id
            FROM private_message_queue pmsgq
            WHERE pmsgq.status = 'pending'

            ORDER BY priority_score ASC, entered_queue_at ASC
            LIMIT $1
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [QueueWithContent.model_validate(record) for record in records]
