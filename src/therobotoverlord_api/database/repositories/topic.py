"""Topic repository for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.topic import Topic
from therobotoverlord_api.database.models.topic import TopicCreate
from therobotoverlord_api.database.models.topic import TopicSummary
from therobotoverlord_api.database.models.topic import TopicUpdate
from therobotoverlord_api.database.models.topic import TopicWithAuthor
from therobotoverlord_api.database.repositories.base import BaseRepository


class TopicRepository(BaseRepository[Topic]):
    """Repository for topic operations."""

    def __init__(self):
        super().__init__("topics")

    def _record_to_model(self, record: Record) -> Topic:
        """Convert database record to Topic model."""
        return Topic.model_validate(record)

    async def create(self, topic_data: TopicCreate) -> Topic:
        """Create a new topic."""
        data = topic_data.model_dump(exclude_unset=True)
        data["created_at"] = datetime.now(UTC)
        return await self.create_from_dict(data)

    async def update(self, pk: UUID, topic_data: TopicUpdate) -> Topic | None:
        """Update a topic."""
        data = topic_data.model_dump(exclude_unset=True, exclude_none=True)
        return await self.update_from_dict(pk, data)

    async def get_by_status(
        self, status: TopicStatus, limit: int = 100, offset: int = 0
    ) -> list[Topic]:
        """Get topics by status."""
        query = """
            SELECT * FROM topics
            WHERE status = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, status.value, limit, offset)
            return [self._record_to_model(record) for record in records]

    async def get_approved_topics(
        self, limit: int = 100, offset: int = 0
    ) -> list[TopicSummary]:
        """Get approved topics with summary information."""
        query = """
            SELECT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                u.username as author_username,
                COALESCE(p.post_count, 0) as post_count
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            WHERE t.status = 'approved'
            ORDER BY t.created_at DESC
            LIMIT $1 OFFSET $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)
            return [TopicSummary.model_validate(record) for record in records]

    async def get_with_author(self, pk: UUID) -> TopicWithAuthor | None:
        """Get topic with author information."""
        query = """
            SELECT
                t.*,
                u.username as author_username
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            WHERE t.pk = $1
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, pk)
            return TopicWithAuthor.model_validate(record) if record else None

    async def get_by_author(
        self, author_pk: UUID, limit: int = 100, offset: int = 0
    ) -> list[Topic]:
        """Get topics by author."""
        query = """
            SELECT * FROM topics
            WHERE author_pk = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, author_pk, limit, offset)
            return [self._record_to_model(record) for record in records]

    async def search_topics(
        self, search_term: str, limit: int = 100, offset: int = 0
    ) -> list[TopicSummary]:
        """Search topics by title and description."""
        query = """
            SELECT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                u.username as author_username,
                COALESCE(p.post_count, 0) as post_count
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            WHERE t.status = 'approved'
            AND (
                t.title ILIKE $1
                OR t.description ILIKE $1
            )
            ORDER BY t.created_at DESC
            LIMIT $2 OFFSET $3
        """

        search_pattern = f"%{search_term}%"

        async with get_db_connection() as connection:
            records = await connection.fetch(query, search_pattern, limit, offset)
            return [TopicSummary.model_validate(record) for record in records]

    async def approve_topic(self, pk: UUID, approved_by: UUID) -> Topic | None:
        """Approve a topic."""
        data = {
            "status": TopicStatus.APPROVED.value,
            "approved_at": datetime.now(UTC),
            "approved_by": approved_by,
        }
        return await self.update_from_dict(pk, data)

    async def reject_topic(self, pk: UUID) -> Topic | None:
        """Reject a topic."""
        data = {"status": TopicStatus.REJECTED.value}
        return await self.update_from_dict(pk, data)

    async def count_by_status(self, status: TopicStatus) -> int:
        """Count topics by status."""
        return await self.count("status = $1", [status.value])

    async def get_overlord_topics(
        self, limit: int = 100, offset: int = 0
    ) -> list[TopicSummary]:
        """Get topics created by the Overlord."""
        query = """
            SELECT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                'The Overlord' as author_username,
                COALESCE(p.post_count, 0) as post_count
            FROM topics t
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            WHERE t.created_by_overlord = true
            AND t.status = 'approved'
            ORDER BY t.created_at DESC
            LIMIT $1 OFFSET $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)
            return [TopicSummary.model_validate(record) for record in records]
