"""Post repository for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.post import PostCreate
from therobotoverlord_api.database.models.post import PostSummary
from therobotoverlord_api.database.models.post import PostThread
from therobotoverlord_api.database.models.post import PostUpdate
from therobotoverlord_api.database.models.post import PostWithAuthor
from therobotoverlord_api.database.repositories.base import BaseRepository


class PostRepository(BaseRepository[Post]):
    """Repository for post operations."""

    def __init__(self):
        super().__init__("posts")

    def _record_to_model(self, record: Record) -> Post:
        """Convert database record to Post model."""
        return Post.model_validate(dict(record))

    async def create(self, post_data: PostCreate) -> Post:
        """Create a new post."""
        data = post_data.model_dump(exclude_unset=True)
        data["created_at"] = datetime.now(UTC)
        return await self.create_from_dict(data)

    async def update(self, pk: UUID, post_data: PostUpdate) -> Post | None:
        """Update a post."""
        data = post_data.model_dump(exclude_unset=True, exclude_none=True)
        return await self.update_from_dict(pk, data)

    async def get_by_topic(
        self,
        topic_pk: UUID,
        status: ContentStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PostWithAuthor]:
        """Get posts by topic with author information."""
        where_clause = "p.topic_pk = $1"
        params: list[UUID | str | int] = [topic_pk]

        if status:
            where_clause += " AND p.status = $2"
            params.append(status.value)

        query = f"""
            SELECT
                p.pk,
                p.topic_pk,
                p.parent_post_pk,
                p.author_pk,
                p.content,
                p.status,
                p.overlord_feedback,
                p.submitted_at,
                p.approved_at,
                p.rejection_reason,
                p.created_at,
                p.updated_at,
                u.username as author_username
            FROM posts p
            JOIN users u ON p.author_pk = u.pk
            WHERE {where_clause}
            ORDER BY p.submitted_at ASC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """

        params.extend([limit, offset])

        async with get_db_connection() as connection:
            records = await connection.fetch(query, *params)
            return [PostWithAuthor.model_validate(dict(record)) for record in records]

    async def get_graveyard_posts(
        self, limit: int = 100, offset: int = 0
    ) -> list[PostWithAuthor]:
        """Get rejected posts (graveyard)."""
        query = """
            SELECT
                p.pk,
                p.topic_pk,
                p.parent_post_pk,
                p.author_pk,
                p.content,
                p.status,
                p.overlord_feedback,
                p.submitted_at,
                p.approved_at,
                p.rejection_reason,
                p.created_at,
                p.updated_at,
                u.username as author_username
            FROM posts p
            JOIN users u ON p.author_pk = u.pk
            WHERE p.status = 'rejected'
            ORDER BY p.submitted_at DESC
            LIMIT $1 OFFSET $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)
            return [PostWithAuthor.model_validate(dict(record)) for record in records]

    async def get_approved_by_topic(
        self, topic_pk: UUID, limit: int = 100, offset: int = 0
    ) -> list[PostWithAuthor]:
        """Get approved posts by topic."""
        return await self.get_by_topic(topic_pk, ContentStatus.APPROVED, limit, offset)

    async def get_by_author(
        self,
        author_pk: UUID,
        status: ContentStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PostSummary]:
        """Get posts by author with topic information."""
        where_clause = "p.author_pk = $1"
        params: list[UUID | str | int] = [author_pk]

        if status:
            where_clause += " AND p.status = $2"
            params.append(status.value)

        query = f"""
            SELECT
                p.pk,
                p.topic_pk,
                p.author_pk,
                p.content,
                p.status,
                p.submitted_at,
                p.rejection_reason
            FROM posts p
            WHERE {where_clause}
            ORDER BY p.submitted_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """

        params.extend([limit, offset])

        async with get_db_connection() as connection:
            records = await connection.fetch(query, *params)
            return [PostSummary.model_validate(dict(record)) for record in records]

    async def get_graveyard_by_author(
        self, author_pk: UUID, limit: int = 100, offset: int = 0
    ) -> list[PostSummary]:
        """Get rejected posts for user's graveyard."""
        return await self.get_by_author(
            author_pk, ContentStatus.REJECTED, limit, offset
        )

    async def get_graveyard_posts_by_author(
        self, author_pk: UUID, limit: int = 100, offset: int = 0
    ) -> list[PostWithAuthor]:
        """Get rejected posts by author with author information."""
        query = """
            SELECT
                p.pk,
                p.topic_pk,
                p.parent_post_pk,
                p.author_pk,
                p.content,
                p.status,
                p.overlord_feedback,
                p.submitted_at,
                p.approved_at,
                p.rejection_reason,
                p.created_at,
                p.updated_at,
                u.username as author_username
            FROM posts p
            JOIN users u ON p.author_pk = u.pk
            WHERE p.status = 'rejected' AND p.author_pk = $1
            ORDER BY p.submitted_at ASC
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, author_pk, limit, offset)
            return [PostWithAuthor.model_validate(dict(record)) for record in records]

    async def get_thread_view(
        self, topic_pk: UUID, limit: int = 100, offset: int = 0
    ) -> list[PostThread]:
        """Get posts in thread view with reply counts and depth levels."""
        query = """
            WITH RECURSIVE post_tree AS (
                -- Base case: top-level posts (no parent)
                SELECT
                    p.pk,
                    p.topic_pk,
                    p.parent_post_pk,
                    p.author_pk,
                    u.username as author_username,
                    p.content,
                    p.status,
                    p.overlord_feedback,
                    p.submitted_at,
                    p.approved_at,
                    p.created_at,
                    0 as depth_level,
                    ARRAY[p.submitted_at] as path
                FROM posts p
                JOIN users u ON p.author_pk = u.pk
                WHERE p.topic_pk = $1
                AND p.parent_post_pk IS NULL
                AND p.status = 'approved'

                UNION ALL

                -- Recursive case: replies
                SELECT
                    p.pk,
                    p.topic_pk,
                    p.parent_post_pk,
                    p.author_pk,
                    u.username as author_username,
                    p.content,
                    p.status,
                    p.overlord_feedback,
                    p.submitted_at,
                    p.approved_at,
                    p.created_at,
                    pt.depth_level + 1,
                    pt.path || p.submitted_at
                FROM posts p
                JOIN users u ON p.author_pk = u.pk
                JOIN post_tree pt ON p.parent_post_pk = pt.pk
                WHERE p.status = 'approved'
            ),
            post_reply_counts AS (
                SELECT
                    parent_post_pk,
                    COUNT(*) as reply_count
                FROM posts
                WHERE parent_post_pk IS NOT NULL
                AND status = 'approved'
                GROUP BY parent_post_pk
            )
            SELECT
                pt.pk,
                pt.topic_pk,
                pt.parent_post_pk,
                pt.author_pk,
                pt.author_username,
                pt.content,
                pt.status,
                pt.overlord_feedback,
                pt.submitted_at,
                pt.approved_at,
                pt.created_at,
                pt.depth_level,
                COALESCE(prc.reply_count, 0) as reply_count
            FROM post_tree pt
            LEFT JOIN post_reply_counts prc ON pt.pk = prc.parent_post_pk
            ORDER BY pt.path
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, topic_pk, limit, offset)
            return [PostThread.model_validate(dict(record)) for record in records]

    async def get_by_status(
        self, status: ContentStatus, limit: int = 100, offset: int = 0
    ) -> list[Post]:
        """Get posts by status."""
        query = """
            SELECT * FROM posts
            WHERE status = $1
            ORDER BY submitted_at ASC
            LIMIT $2 OFFSET $3
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, status.value, limit, offset)
            return [self._record_to_model(record) for record in records]

    async def approve_post(
        self, pk: UUID, overlord_feedback: str | None = None
    ) -> Post | None:
        """Approve a post."""
        data = {
            "status": ContentStatus.APPROVED.value,
            "approved_at": datetime.now(UTC),
        }
        if overlord_feedback:
            data["overlord_feedback"] = overlord_feedback

        return await self.update_from_dict(pk, data)

    async def reject_post(self, pk: UUID, overlord_feedback: str) -> Post | None:
        """Reject a post with feedback."""
        data = {
            "status": ContentStatus.REJECTED.value,
            "overlord_feedback": overlord_feedback,
        }
        return await self.update_from_dict(pk, data)

    async def count_by_topic_and_status(
        self, topic_pk: UUID, status: ContentStatus
    ) -> int:
        """Count posts by topic and status."""
        return await self.count(
            "topic_pk = $1 AND status = $2", [topic_pk, status.value]
        )

    async def count_approved_by_topic(self, topic_pk: UUID) -> int:
        """Count approved posts in a topic."""
        return await self.count_by_topic_and_status(topic_pk, ContentStatus.APPROVED)

    async def count_by_author_and_status(
        self, author_pk: UUID, status: ContentStatus
    ) -> int:
        """Count posts by author and status."""
        return await self.count(
            "author_pk = $1 AND status = $2", [author_pk, status.value]
        )

    async def get_recent_approved_posts(
        self, limit: int = 100, offset: int = 0
    ) -> list[PostWithAuthor]:
        """Get recent approved posts across all topics, ordered chronologically by submission."""
        query = """
            SELECT
                p.pk,
                p.topic_pk,
                p.parent_post_pk,
                p.author_pk,
                p.content,
                p.status,
                p.overlord_feedback,
                p.submitted_at,
                p.approved_at,
                p.rejection_reason,
                p.created_at,
                p.updated_at,
                u.username as author_username
            FROM posts p
            JOIN users u ON p.author_pk = u.pk
            WHERE p.status = 'approved'
            ORDER BY p.submitted_at ASC
            LIMIT $1 OFFSET $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)
            return [PostWithAuthor.model_validate(dict(record)) for record in records]

    async def search_posts(
        self,
        search_term: str,
        topic_pk: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PostWithAuthor]:
        """Search posts by content."""
        where_clause = "p.status = 'approved' AND p.content ILIKE $1"
        params: list[str | UUID | int] = [f"%{search_term}%"]

        if topic_pk:
            where_clause += " AND p.topic_pk = $2"
            params.append(topic_pk)

        query = f"""
            SELECT
                p.pk,
                p.topic_pk,
                p.parent_post_pk,
                p.author_pk,
                p.content,
                p.status,
                p.overlord_feedback,
                p.submitted_at,
                p.approved_at,
                p.rejection_reason,
                p.created_at,
                p.updated_at,
                u.username as author_username
            FROM posts p
            JOIN users u ON p.author_pk = u.pk
            WHERE {where_clause}
            ORDER BY p.submitted_at ASC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """

        params.extend([limit, offset])

        async with get_db_connection() as connection:
            records = await connection.fetch(query, *params)
            return [PostWithAuthor.model_validate(dict(record)) for record in records]

    async def get_in_transit_posts(
        self, limit: int = 100, offset: int = 0
    ) -> list[PostWithAuthor]:
        """Get posts currently in-transit through the evaluation system."""
        query = """
            SELECT
                p.pk,
                p.topic_pk,
                p.parent_post_pk,
                p.author_pk,
                p.content,
                p.status,
                p.overlord_feedback,
                p.submitted_at,
                p.approved_at,
                p.rejection_reason,
                p.created_at,
                p.updated_at,
                u.username as author_username
            FROM posts p
            JOIN users u ON p.author_pk = u.pk
            WHERE p.status = 'in_transit'
            ORDER BY p.submitted_at ASC
            LIMIT $1 OFFSET $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)
            return [PostWithAuthor.model_validate(dict(record)) for record in records]

    async def get_submitted_posts(
        self, limit: int = 50, offset: int = 0
    ) -> list[PostWithAuthor]:
        """Get posts awaiting ToS screening (SUBMITTED status)."""
        query = """
            SELECT
                p.pk,
                p.topic_pk,
                p.parent_post_pk,
                p.author_pk,
                p.content,
                p.status,
                p.overlord_feedback,
                p.rejection_reason,
                p.submitted_at,
                p.approved_at,
                p.created_at,
                p.updated_at,
                u.username as author_username
            FROM posts p
            JOIN users u ON p.author_pk = u.pk
            WHERE p.status = 'submitted'
            ORDER BY p.submitted_at ASC
            LIMIT $1 OFFSET $2
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit, offset)
            return [PostWithAuthor.model_validate(dict(record)) for record in records]

    async def get_trending_posts(self, limit: int = 20) -> list[PostWithAuthor]:
        """Get trending posts based on recent activity and engagement."""
        query = """
            SELECT
                p.pk,
                p.topic_pk,
                p.parent_post_pk,
                p.author_pk,
                p.content,
                p.status,
                p.overlord_feedback,
                p.submitted_at,
                p.approved_at,
                p.rejection_reason,
                p.created_at,
                p.updated_at,
                u.username as author_username,
                COALESCE(reply_counts.reply_count, 0) as engagement_score
            FROM posts p
            JOIN users u ON p.author_pk = u.pk
            LEFT JOIN (
                SELECT parent_post_pk, COUNT(*) as reply_count
                FROM posts
                WHERE status = 'approved'
                AND submitted_at > NOW() - INTERVAL '7 days'
                GROUP BY parent_post_pk
            ) reply_counts ON p.pk = reply_counts.parent_post_pk
            WHERE p.status = 'approved'
            AND p.submitted_at > NOW() - INTERVAL '30 days'
            ORDER BY engagement_score DESC, p.submitted_at DESC
            LIMIT $1
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [PostWithAuthor.model_validate(dict(record)) for record in records]

    async def get_popular_posts(self, limit: int = 20) -> list[PostWithAuthor]:
        """Get popular posts based on total reply count."""
        query = """
            SELECT
                p.pk,
                p.topic_pk,
                p.parent_post_pk,
                p.author_pk,
                p.content,
                p.status,
                p.overlord_feedback,
                p.submitted_at,
                p.approved_at,
                p.rejection_reason,
                p.created_at,
                p.updated_at,
                u.username as author_username,
                COALESCE(reply_counts.reply_count, 0) as total_replies
            FROM posts p
            JOIN users u ON p.author_pk = u.pk
            LEFT JOIN (
                SELECT parent_post_pk, COUNT(*) as reply_count
                FROM posts
                WHERE status = 'approved'
                GROUP BY parent_post_pk
            ) reply_counts ON p.pk = reply_counts.parent_post_pk
            WHERE p.status = 'approved'
            ORDER BY total_replies DESC, p.submitted_at DESC
            LIMIT $1
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [PostWithAuthor.model_validate(dict(record)) for record in records]
