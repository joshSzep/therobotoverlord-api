"""Flag repository for content reporting and moderation operations."""

from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.flag import Flag
from therobotoverlord_api.database.models.flag import FlagStatus
from therobotoverlord_api.database.repositories.base import BaseRepository


class FlagRepository(BaseRepository[Flag]):
    """Repository for flag database operations."""

    def __init__(self) -> None:
        """Initialize the flag repository."""
        super().__init__("flags")

    def _record_to_model(self, record: Record) -> Flag:
        """Convert database record to Flag model."""
        return Flag.model_validate(record)

    async def get_flags_for_review(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: str | None = None,
    ) -> list[Flag]:
        """Get flags for moderation review with optional status filter."""
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE ($3::text IS NULL OR status = $3)
            ORDER BY created_at ASC
            LIMIT $1 OFFSET $2
        """  # nosec B608

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, limit, offset, status_filter)
            return [self._record_to_model(row) for row in rows]

    async def get_user_flags(
        self,
        user_pk: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Flag]:
        """Get flags submitted by a specific user."""
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE flagger_pk = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """  # nosec B608

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, user_pk, limit, offset)
            return [self._record_to_model(row) for row in rows]

    async def get_content_flags(
        self,
        content_pk: UUID,
        content_type: str,
    ) -> list[Flag]:
        """Get all flags for specific content (post or topic)."""
        field = "post_pk" if content_type == "post" else "topic_pk"
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE {field} = $1
            ORDER BY created_at DESC
        """  # nosec B608

        async with get_db_connection() as conn:
            rows = await conn.fetch(query, content_pk)
            return [self._record_to_model(row) for row in rows]

    async def check_user_already_flagged(
        self,
        user_pk: UUID,
        content_pk: UUID,
        content_type: str,
    ) -> bool:
        """Check if user has already flagged specific content."""
        field = "post_pk" if content_type == "post" else "topic_pk"
        query = f"""
            SELECT EXISTS(
                SELECT 1 FROM {self.table_name}
                WHERE flagger_pk = $1 AND {field} = $2
            )
        """  # nosec B608

        async with get_db_connection() as conn:
            result = await conn.fetchval(query, user_pk, content_pk)
            return bool(result)

    async def get_user_dismissed_flags_count(
        self,
        user_pk: UUID,
        days: int = 30,
    ) -> int:
        """Get count of user's dismissed flags in the last N days."""
        query = f"""
            SELECT COUNT(*) FROM {self.table_name}
            WHERE flagger_pk = $1
            AND status = $2
            AND reviewed_at >= NOW() - INTERVAL '{days} days'
        """  # nosec B608

        async with get_db_connection() as conn:
            result = await conn.fetchval(query, user_pk, FlagStatus.DISMISSED.value)
            return int(result or 0)

    async def get_pending_flags_count(self) -> int:
        """Get total count of pending flags for admin dashboard."""
        query = f"""
            SELECT COUNT(*) FROM {self.table_name}
            WHERE status = $1
        """  # nosec B608

        async with get_db_connection() as conn:
            result = await conn.fetchval(query, FlagStatus.PENDING.value)
            return int(result or 0)
