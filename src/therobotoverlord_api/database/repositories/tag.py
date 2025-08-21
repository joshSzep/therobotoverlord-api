"""Tag repository for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.tag import Tag
from therobotoverlord_api.database.models.tag import TagCreate
from therobotoverlord_api.database.models.tag import TagUpdate
from therobotoverlord_api.database.models.tag import TagWithTopicCount
from therobotoverlord_api.database.models.tag import TopicTag
from therobotoverlord_api.database.models.tag import TopicTagCreate
from therobotoverlord_api.database.models.tag import TopicTagWithDetails
from therobotoverlord_api.database.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """Repository for tag operations."""

    def __init__(self):
        super().__init__("tags")

    def _record_to_model(self, record: Record) -> Tag:
        """Convert database record to Tag model."""
        return Tag.model_validate(record)

    async def create(self, tag_data: TagCreate) -> Tag:
        """Create a new tag."""
        data = tag_data.model_dump(exclude_unset=True)
        data["created_at"] = datetime.now(UTC)
        return await self.create_from_dict(data)

    async def update(self, pk: UUID, tag_data: TagUpdate) -> Tag | None:
        """Update a tag."""
        data = tag_data.model_dump(exclude_unset=True, exclude_none=True)
        return await self.update_from_dict(pk, data)

    async def get_by_name(self, name: str) -> Tag | None:
        """Get tag by name."""
        query = "SELECT * FROM tags WHERE name = $1"

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, name)
            return self._record_to_model(record) if record else None

    async def search_tags(
        self, search_term: str, limit: int = 50, offset: int = 0
    ) -> list[Tag]:
        """Search tags by name."""
        query = """
            SELECT * FROM tags
            WHERE name ILIKE $1
            ORDER BY name ASC
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, f"%{search_term}%", limit, offset)
            return [self._record_to_model(record) for record in records]

    async def get_tags_with_topic_count(
        self, limit: int = 100, offset: int = 0
    ) -> list[TagWithTopicCount]:
        """Get tags with their topic counts."""
        query = """
            SELECT
                t.pk,
                t.name,
                t.description,
                t.created_at,
                COALESCE(COUNT(tt.topic_pk), 0) as topic_count
            FROM tags t
            LEFT JOIN topic_tags tt ON t.pk = tt.tag_pk
            GROUP BY t.pk, t.name, t.description, t.created_at
            ORDER BY topic_count DESC, t.name ASC
            LIMIT $1 OFFSET $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)
            return [TagWithTopicCount.model_validate(record) for record in records]

    async def get_popular_tags(self, limit: int = 20) -> list[TagWithTopicCount]:
        """Get most popular tags by topic count."""
        query = """
            SELECT
                t.pk,
                t.name,
                t.description,
                t.created_at,
                COUNT(tt.topic_pk) as topic_count
            FROM tags t
            INNER JOIN topic_tags tt ON t.pk = tt.tag_pk
            GROUP BY t.pk, t.name, t.description, t.created_at
            HAVING COUNT(tt.topic_pk) > 0
            ORDER BY topic_count DESC, t.name ASC
            LIMIT $1
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [TagWithTopicCount.model_validate(record) for record in records]


class TopicTagRepository(BaseRepository[TopicTag]):
    """Repository for topic tag operations."""

    def __init__(self):
        super().__init__("topic_tags")

    def _record_to_model(self, record: Record) -> TopicTag:
        """Convert database record to TopicTag model."""
        return TopicTag.model_validate(record)

    async def create(self, topic_tag_data: TopicTagCreate) -> TopicTag:
        """Create a new topic tag assignment."""
        data = topic_tag_data.model_dump(exclude_unset=True)
        data["assigned_at"] = datetime.now(UTC)
        data["created_at"] = datetime.now(UTC)
        return await self.create_from_dict(data)

    async def get_tags_for_topic(self, topic_pk: UUID) -> list[TopicTagWithDetails]:
        """Get all tags for a specific topic with details."""
        query = """
            SELECT
                tt.pk,
                tt.topic_pk,
                tt.tag_pk,
                t.name as tag_name,
                t.description as tag_description,
                tt.assigned_by_pk,
                u.username as assigned_by_username,
                tt.assigned_at,
                tt.created_at
            FROM topic_tags tt
            JOIN tags t ON tt.tag_pk = t.pk
            LEFT JOIN users u ON tt.assigned_by_pk = u.pk
            WHERE tt.topic_pk = $1
            ORDER BY tt.assigned_at DESC
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, topic_pk)
            return [TopicTagWithDetails.model_validate(record) for record in records]

    async def get_topics_by_tag(
        self, tag_pk: UUID, limit: int = 50, offset: int = 0
    ) -> list[UUID]:
        """Get topic PKs that have a specific tag."""
        query = """
            SELECT topic_pk
            FROM topic_tags
            WHERE tag_pk = $1
            ORDER BY assigned_at DESC
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, tag_pk, limit, offset)
            return [record["topic_pk"] for record in records]

    async def remove_tag_from_topic(self, topic_pk: UUID, tag_pk: UUID) -> bool:
        """Remove a tag from a topic."""
        query = "DELETE FROM topic_tags WHERE topic_pk = $1 AND tag_pk = $2"

        async with get_db_connection() as connection:
            result = await connection.execute(query, topic_pk, tag_pk)
            return result == "DELETE 1"

    async def remove_all_tags_from_topic(self, topic_pk: UUID) -> int:
        """Remove all tags from a topic. Returns count of removed tags."""
        query = "DELETE FROM topic_tags WHERE topic_pk = $1"

        async with get_db_connection() as connection:
            result = await connection.execute(query, topic_pk)
            # Parse "DELETE n" to get count
            return int(result.split()[-1]) if result.startswith("DELETE") else 0

    async def tag_exists_for_topic(self, topic_pk: UUID, tag_pk: UUID) -> bool:
        """Check if a tag is already assigned to a topic."""
        query = "SELECT EXISTS(SELECT 1 FROM topic_tags WHERE topic_pk = $1 AND tag_pk = $2)"

        async with get_db_connection() as connection:
            result = await connection.fetchval(query, topic_pk, tag_pk)
            return bool(result)

    async def count_tags_for_topic(self, topic_pk: UUID) -> int:
        """Count the number of tags assigned to a topic."""
        query = "SELECT COUNT(*) FROM topic_tags WHERE topic_pk = $1"

        async with get_db_connection() as connection:
            result = await connection.fetchval(query, topic_pk)
            return result or 0

    async def get_tag_usage_stats(self) -> dict[str, int]:
        """Get statistics about tag usage."""
        query = """
            SELECT
                COUNT(DISTINCT tag_pk) as total_tags_used,
                COUNT(*) as total_assignments,
                COUNT(DISTINCT topic_pk) as topics_with_tags
            FROM topic_tags
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query)
            return dict(record) if record else {}
