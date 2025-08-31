"""Topic repository for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from typing import Any
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
        self, limit: int = 100, offset: int = 0, tag_names: list[str] | None = None
    ) -> list[TopicSummary]:
        """Get approved topics with summary information."""
        base_query = """
            SELECT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                u.username as author_username,
                COALESCE(p.post_count, 0) as post_count,
                COALESCE(tag_names.tags, '{}') as tags
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            LEFT JOIN (
                SELECT
                    tt.topic_pk,
                    ARRAY_AGG(tg.name ORDER BY tg.name) as tags
                FROM topic_tags tt
                JOIN tags tg ON tt.tag_pk = tg.pk
                GROUP BY tt.topic_pk
            ) tag_names ON t.pk = tag_names.topic_pk
            WHERE t.status = 'approved'
        """

        params: list[Any] = []
        param_count = 0

        if tag_names:
            # Filter by tags using EXISTS subquery
            tag_filter = f"""
                AND EXISTS (
                    SELECT 1 FROM topic_tags tt2
                    JOIN tags tg2 ON tt2.tag_pk = tg2.pk
                    WHERE tt2.topic_pk = t.pk
                    AND tg2.name = ANY(${param_count + 1})
                )
            """
            base_query += tag_filter
            params.append(tag_names)
            param_count += 1

        query = (
            base_query
            + f"""
            ORDER BY t.created_at DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """
        )

        params.extend([limit, offset])

        async with get_db_connection() as connection:
            records = await connection.fetch(query, *params)
            return [TopicSummary.model_validate(record) for record in records]

    async def get_with_author(self, pk: UUID) -> TopicWithAuthor | None:
        """Get topic with author information."""
        query = """
            SELECT
                t.*,
                u.username as author_username,
                COALESCE(tag_names.tags, '{}') as tags
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT
                    tt.topic_pk,
                    ARRAY_AGG(tg.name ORDER BY tg.name) as tags
                FROM topic_tags tt
                JOIN tags tg ON tt.tag_pk = tg.pk
                GROUP BY tt.topic_pk
            ) tag_names ON t.pk = tag_names.topic_pk
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
        """Search topics by title, description, and tags."""
        query = """
            SELECT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                u.username as author_username,
                COALESCE(p.post_count, 0) as post_count,
                COALESCE(tag_names.tags, '{}') as tags
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            LEFT JOIN (
                SELECT
                    tt.topic_pk,
                    ARRAY_AGG(tg.name ORDER BY tg.name) as tags
                FROM topic_tags tt
                JOIN tags tg ON tt.tag_pk = tg.pk
                GROUP BY tt.topic_pk
            ) tag_names ON t.pk = tag_names.topic_pk
            WHERE t.status = 'approved'
            AND (
                t.title ILIKE $1
                OR t.description ILIKE $1
                OR EXISTS (
                    SELECT 1 FROM topic_tags tt2
                    JOIN tags tg2 ON tt2.tag_pk = tg2.pk
                    WHERE tt2.topic_pk = t.pk
                    AND tg2.name ILIKE $1
                )
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
            "approved_by_overlord": True,
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
                COALESCE(p.post_count, 0) as post_count,
                COALESCE(tag_names.tags, '{}') as tags
            FROM topics t
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            LEFT JOIN (
                SELECT
                    tt.topic_pk,
                    ARRAY_AGG(tg.name ORDER BY tg.name) as tags
                FROM topic_tags tt
                JOIN tags tg ON tt.tag_pk = tg.pk
                GROUP BY tt.topic_pk
            ) tag_names ON t.pk = tag_names.topic_pk
            WHERE t.created_by_overlord = true
            AND t.status = 'approved'
            ORDER BY t.created_at DESC
            LIMIT $1 OFFSET $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)
            return [TopicSummary.model_validate(record) for record in records]

    async def get_related_topics(
        self, topic_pk: UUID, limit: int = 5
    ) -> list[TopicSummary]:
        """Get topics that share tags with the given topic."""
        query = """
            SELECT DISTINCT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                u.username as author_username,
                COALESCE(p.post_count, 0) as post_count,
                COALESCE(tag_names.tags, '{}') as tags,
                COUNT(shared_tags.tag_pk) as shared_tag_count
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            LEFT JOIN (
                SELECT
                    tt.topic_pk,
                    ARRAY_AGG(tg.name ORDER BY tg.name) as tags
                FROM topic_tags tt
                JOIN tags tg ON tt.tag_pk = tg.pk
                GROUP BY tt.topic_pk
            ) tag_names ON t.pk = tag_names.topic_pk
            JOIN topic_tags shared_tags ON t.pk = shared_tags.topic_pk
            WHERE t.status = 'approved'
            AND t.pk != $1
            AND shared_tags.tag_pk IN (
                SELECT tag_pk FROM topic_tags WHERE topic_pk = $1
            )
            GROUP BY t.pk, t.title, t.description, t.created_by_overlord,
                     t.status, t.created_at, u.username, p.post_count, tag_names.tags
            ORDER BY shared_tag_count DESC, t.created_at DESC
            LIMIT $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, topic_pk, limit)
            return [TopicSummary.model_validate(record) for record in records]

    async def get_all_categories(self) -> list[str]:
        """Get all unique topic categories/tags."""
        query = """
            SELECT DISTINCT tg.name
            FROM tags tg
            JOIN topic_tags tt ON tg.pk = tt.tag_pk
            JOIN topics t ON tt.topic_pk = t.pk
            WHERE t.status = 'approved'
            ORDER BY tg.name
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query)
            return [record["name"] for record in records]

    async def get_topics_feed(
        self, limit: int = 20, offset: int = 0, tag_names: list[str] | None = None
    ) -> list[TopicSummary]:
        """Get topics feed for visitor mode."""
        # Use the same query structure as get_approved_topics which works
        base_query = """
            SELECT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                CASE WHEN t.created_by_overlord THEN 'The Overlord' ELSE u.username END as author_username,
                COALESCE(p.post_count, 0) as post_count,
                COALESCE(tag_names.tags, '{}') as tags
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            LEFT JOIN (
                SELECT
                    tt.topic_pk,
                    ARRAY_AGG(tg.name ORDER BY tg.name) as tags
                FROM topic_tags tt
                JOIN tags tg ON tt.tag_pk = tg.pk
                GROUP BY tt.topic_pk
            ) tag_names ON t.pk = tag_names.topic_pk
            WHERE t.status = 'approved'
        """

        params: list[Any] = []
        param_count = 0

        if tag_names:
            tag_filter = f"""
                AND EXISTS (
                    SELECT 1 FROM topic_tags tt2
                    JOIN tags tg2 ON tt2.tag_pk = tg2.pk
                    WHERE tt2.topic_pk = t.pk
                    AND tg2.name = ANY(${param_count + 1})
                )
            """
            base_query += tag_filter
            params.append(tag_names)
            param_count += 1

        query = (
            base_query
            + f"""
            ORDER BY t.created_at DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """
        )

        params.extend([limit, offset])

        async with get_db_connection() as connection:
            records = await connection.fetch(query, *params)
            return [TopicSummary.model_validate(record) for record in records]

    async def get_trending_topics(self, limit: int = 20) -> list[TopicSummary]:
        """Get trending topics based on recent post activity."""
        query = """
            SELECT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                CASE WHEN t.created_by_overlord THEN 'The Overlord' ELSE u.username END as author_username,
                COALESCE(p.post_count, 0) as post_count,
                COALESCE(tag_names.tags, '{}') as tags
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as recent_count
                FROM posts
                WHERE status = 'approved'
                AND created_at > NOW() - INTERVAL '7 days'
                GROUP BY topic_pk
            ) recent_posts ON t.pk = recent_posts.topic_pk
            LEFT JOIN (
                SELECT
                    tt.topic_pk,
                    ARRAY_AGG(tg.name ORDER BY tg.name) as tags
                FROM topic_tags tt
                JOIN tags tg ON tt.tag_pk = tg.pk
                GROUP BY tt.topic_pk
            ) tag_names ON t.pk = tag_names.topic_pk
            WHERE t.status = 'approved'
            ORDER BY COALESCE(recent_posts.recent_count, 0) DESC, p.post_count DESC, t.created_at DESC
            LIMIT $1
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [TopicSummary.model_validate(record) for record in records]

    async def get_popular_topics(self, limit: int = 20) -> list[TopicSummary]:
        """Get popular topics based on total post count."""
        query = """
            SELECT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                CASE WHEN t.created_by_overlord THEN 'The Overlord' ELSE u.username END as author_username,
                COALESCE(p.post_count, 0) as post_count,
                COALESCE(tag_names.tags, '{}') as tags
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            LEFT JOIN (
                SELECT
                    tt.topic_pk,
                    ARRAY_AGG(tg.name ORDER BY tg.name) as tags
                FROM topic_tags tt
                JOIN tags tg ON tt.tag_pk = tg.pk
                GROUP BY tt.topic_pk
            ) tag_names ON t.pk = tag_names.topic_pk
            WHERE t.status = 'approved'
            ORDER BY p.post_count DESC NULLS LAST, t.created_at DESC
            LIMIT $1
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [TopicSummary.model_validate(record) for record in records]

    async def get_featured_topics(self, limit: int = 10) -> list[TopicSummary]:
        """Get featured topics (Overlord topics and highly active topics)."""
        query = """
            SELECT
                t.pk,
                t.title,
                t.description,
                t.created_by_overlord,
                t.status,
                t.created_at,
                CASE WHEN t.created_by_overlord THEN 'The Overlord' ELSE u.username END as author_username,
                COALESCE(p.post_count, 0) as post_count,
                COALESCE(tag_names.tags, '{}') as tags
            FROM topics t
            LEFT JOIN users u ON t.author_pk = u.pk
            LEFT JOIN (
                SELECT topic_pk, COUNT(*) as post_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY topic_pk
            ) p ON t.pk = p.topic_pk
            LEFT JOIN (
                SELECT
                    tt.topic_pk,
                    ARRAY_AGG(tg.name ORDER BY tg.name) as tags
                FROM topic_tags tt
                JOIN tags tg ON tt.tag_pk = tg.pk
                GROUP BY tt.topic_pk
            ) tag_names ON t.pk = tag_names.topic_pk
            WHERE t.status = 'approved'
            ORDER BY
                t.created_by_overlord DESC,
                p.post_count DESC NULLS LAST,
                t.created_at DESC
            LIMIT $1
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [TopicSummary.model_validate(record) for record in records]
