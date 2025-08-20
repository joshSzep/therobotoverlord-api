"""Repository for content versioning and restoration operations."""

from datetime import datetime
from uuid import UUID

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.content_version import ContentRestoration
from therobotoverlord_api.database.models.content_version import ContentVersion
from therobotoverlord_api.database.models.content_version import ContentVersionCreate
from therobotoverlord_api.database.models.content_version import ContentVersionDiff
from therobotoverlord_api.database.models.content_version import ContentVersionSummary
from therobotoverlord_api.database.repositories.base import BaseRepository


class ContentVersionRepository(BaseRepository[ContentVersion]):
    """Repository for content version operations."""

    def __init__(self):
        super().__init__("content_versions")
        self.model_class = ContentVersion

    def _record_to_model(self, record) -> ContentVersion:
        """Convert database record to ContentVersion model."""
        return ContentVersion.model_validate(dict(record))

    async def create_version(
        self, version_data: ContentVersionCreate
    ) -> ContentVersion:
        """Create a new content version using the database function."""

        async with get_db_connection() as conn:
            # Use the database function for automatic version numbering
            result = await conn.fetchrow(
                """
                SELECT create_content_version(
                    $1::content_type_enum, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                ) as version_pk
                """,
                version_data.content_type.value,
                version_data.content_pk,
                version_data.original_title,
                version_data.original_content,
                version_data.original_description,
                version_data.edited_title,
                version_data.edited_content,
                version_data.edited_description,
                version_data.edited_by,
                version_data.edit_reason,
                version_data.edit_type,
                version_data.appeal_pk,
            )

            if not result or not result["version_pk"]:
                raise ValueError("Failed to create content version")

            # Fetch the created version
            return await self.get_by_pk(result["version_pk"])

    async def get_content_history(
        self, content_pk: UUID, limit: int = 50
    ) -> list[ContentVersionSummary]:
        """Get version history for content."""

        async with get_db_connection() as conn:
            records = await conn.fetch(
                """
                SELECT
                    pk,
                    version_number,
                    content_type,
                    content_pk,
                    edited_by,
                    edit_reason,
                    edit_type,
                    appeal_pk,
                    created_at,
                    (original_title IS DISTINCT FROM edited_title) as has_title_change,
                    (original_content IS DISTINCT FROM edited_content) as has_content_change,
                    (original_description IS DISTINCT FROM edited_description) as has_description_change
                FROM content_versions
                WHERE content_pk = $1
                ORDER BY version_number DESC
                LIMIT $2
                """,
                content_pk,
                limit,
            )

            return [
                ContentVersionSummary.model_validate(dict(record)) for record in records
            ]

    async def get_version_diff(self, version_pk: UUID) -> ContentVersionDiff | None:
        """Get diff for a specific version."""

        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                """
                SELECT
                    pk,
                    version_number,
                    content_type,
                    content_pk,
                    original_title,
                    original_content,
                    original_description,
                    edited_title,
                    edited_content,
                    edited_description,
                    edited_by,
                    edit_reason,
                    edit_type,
                    appeal_pk,
                    created_at
                FROM content_versions
                WHERE pk = $1
                """,
                version_pk,
            )

            if not record:
                return None

            # Calculate changes
            title_changed = record["original_title"] != record["edited_title"]
            content_changed = record["original_content"] != record["edited_content"]
            description_changed = (
                record["original_description"] != record["edited_description"]
            )

            # Build changes dict
            changes = {}
            if title_changed:
                changes["title"] = {
                    "from": record["original_title"],
                    "to": record["edited_title"],
                }
            if content_changed:
                changes["content"] = {
                    "from": record["original_content"],
                    "to": record["edited_content"],
                }
            if description_changed:
                changes["description"] = {
                    "from": record["original_description"],
                    "to": record["edited_description"],
                }

            # Build edit metadata
            edit_metadata = {
                "edited_by": str(record["edited_by"]) if record["edited_by"] else None,
                "edit_reason": record["edit_reason"],
                "edit_type": record["edit_type"],
                "appeal_pk": str(record["appeal_pk"]) if record["appeal_pk"] else None,
                "created_at": record["created_at"],
            }

            return ContentVersionDiff(
                version_pk=record["pk"],
                version_number=record["version_number"],
                content_type=ContentType(record["content_type"]),
                content_pk=record["content_pk"],
                title_changed=title_changed,
                content_changed=content_changed,
                description_changed=description_changed,
                changes=changes,
                edit_metadata=edit_metadata,
            )

    async def get_latest_version(self, content_pk: UUID) -> ContentVersion | None:
        """Get the latest version for content."""

        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                """
                SELECT * FROM content_versions
                WHERE content_pk = $1
                ORDER BY version_number DESC
                LIMIT 1
                """,
                content_pk,
            )

            return ContentVersion.model_validate(dict(record)) if record else None


class ContentRestorationRepository(BaseRepository[ContentRestoration]):
    """Repository for content restoration operations."""

    def __init__(self):
        super().__init__("content_restorations")
        self.model_class = ContentRestoration

    def _record_to_model(self, record) -> ContentRestoration:
        """Convert database record to ContentRestoration model."""
        return ContentRestoration.model_validate(dict(record))

    async def get_by_appeal(self, appeal_pk: UUID) -> ContentRestoration | None:
        """Get restoration record by appeal PK."""

        async with get_db_connection() as conn:
            record = await conn.fetchrow(
                f"SELECT * FROM {self.table_name} WHERE appeal_pk = $1", appeal_pk
            )

            return self.model_class.model_validate(dict(record)) if record else None

    async def get_by_content(self, content_pk: UUID) -> list[ContentRestoration]:
        """Get all restoration records for content."""

        async with get_db_connection() as conn:
            records = await conn.fetch(
                f"""
                SELECT * FROM {self.table_name}
                WHERE content_pk = $1
                ORDER BY created_at DESC
                """,
                content_pk,
            )

            return [self.model_class.model_validate(dict(record)) for record in records]

    async def get_restoration_stats(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, int]:
        """Get restoration statistics."""

        async with get_db_connection() as conn:
            where_clause = ""
            params = []

            if start_date:
                where_clause += " AND created_at >= $1"
                params.append(start_date)

            if end_date:
                param_num = len(params) + 1
                where_clause += f" AND created_at <= ${param_num}"
                params.append(end_date)

            record = await conn.fetchrow(
                f"""
                SELECT
                    COUNT(*) as total_restorations,
                    COUNT(*) FILTER (WHERE content_was_edited = true) as edited_restorations,
                    COUNT(DISTINCT restored_by) as unique_moderators,
                    COUNT(DISTINCT content_pk) as unique_content_items
                FROM {self.table_name}
                WHERE 1=1 {where_clause}
                """,
                *params,
            )

            return dict(record) if record else {}
