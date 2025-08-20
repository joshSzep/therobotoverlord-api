"""Translation repository for The Robot Overlord API."""

from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.translation import Translation
from therobotoverlord_api.database.repositories.base import BaseRepository


class TranslationRepository(BaseRepository[Translation]):
    """Repository for translation operations."""

    def __init__(self):
        super().__init__("translations")

    async def get_by_content(
        self, content_pk: UUID, content_type: ContentType
    ) -> Translation | None:
        """Get translation by content ID and type."""
        async with get_db_connection() as conn:
            query = """
                SELECT pk, content_pk, content_type, language_code, original_content,
                       translated_content, translation_quality_score, translation_provider,
                       translation_metadata, created_at, updated_at
                FROM translations
                WHERE content_pk = $1 AND content_type = $2
            """
            record = await conn.fetchrow(query, content_pk, content_type.value)
            return self._record_to_model(record) if record else None

    async def get_by_content_and_language(
        self, content_pk: UUID, content_type: ContentType, language_code: str
    ) -> Translation | None:
        """Get translation by content ID, type, and language."""
        async with get_db_connection() as conn:
            query = """
                SELECT pk, content_pk, content_type, language_code, original_content,
                       translated_content, translation_quality_score, translation_provider,
                       translation_metadata, created_at, updated_at
                FROM translations
                WHERE content_pk = $1 AND content_type = $2 AND language_code = $3
            """
            record = await conn.fetchrow(
                query, content_pk, content_type.value, language_code
            )
            return self._record_to_model(record) if record else None

    async def get_translations_for_content(
        self, content_pk: UUID, content_type: ContentType
    ) -> list[Translation]:
        """Get all translations for a specific content item."""
        async with get_db_connection() as conn:
            query = """
                SELECT pk, content_pk, content_type, language_code, original_content,
                       translated_content, translation_quality_score, translation_provider,
                       translation_metadata, created_at, updated_at
                FROM translations
                WHERE content_pk = $1 AND content_type = $2
                ORDER BY created_at DESC
            """
            records = await conn.fetch(query, content_pk, content_type.value)
            return [self._record_to_model(record) for record in records]

    async def get_by_language(
        self, language_code: str, limit: int = 50, offset: int = 0
    ) -> list[Translation]:
        """Get translations by language code."""
        async with get_db_connection() as conn:
            query = """
                SELECT pk, content_pk, content_type, language_code, original_content,
                       translated_content, translation_quality_score, translation_provider,
                       translation_metadata, created_at, updated_at
                FROM translations
                WHERE language_code = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            records = await conn.fetch(query, language_code, limit, offset)
            return [self._record_to_model(record) for record in records]

    async def get_poor_quality_translations(
        self, quality_threshold: float = 0.7, limit: int = 50, offset: int = 0
    ) -> list[Translation]:
        """Get translations with quality scores below threshold."""
        async with get_db_connection() as conn:
            query = """
                SELECT pk, content_pk, content_type, language_code, original_content,
                       translated_content, translation_quality_score, translation_provider,
                       translation_metadata, created_at, updated_at
                FROM translations
                WHERE translation_quality_score IS NOT NULL
                  AND translation_quality_score < $1
                ORDER BY translation_quality_score ASC, created_at DESC
                LIMIT $2 OFFSET $3
            """
            records = await conn.fetch(query, quality_threshold, limit, offset)
            return [self._record_to_model(record) for record in records]

    async def update_quality_score(
        self,
        translation_pk: UUID,
        quality_score: float,
        metadata: dict | None = None,
    ) -> Translation | None:
        """Update translation quality score and metadata."""
        async with get_db_connection() as conn:
            query = """
                UPDATE translations
                SET translation_quality_score = $2,
                    translation_metadata = COALESCE($3, translation_metadata),
                    updated_at = NOW()
                WHERE pk = $1
                RETURNING pk, content_pk, content_type, language_code, original_content,
                          translated_content, translation_quality_score, translation_provider,
                          translation_metadata, created_at, updated_at
            """
            record = await conn.fetchrow(query, translation_pk, quality_score, metadata)
            return self._record_to_model(record) if record else None

    async def delete_by_content(
        self, content_pk: UUID, content_type: ContentType
    ) -> bool:
        """Delete all translations for a content item."""
        async with get_db_connection() as conn:
            query = """
                DELETE FROM translations
                WHERE content_pk = $1 AND content_type = $2
            """
            result = await conn.execute(query, content_pk, content_type.value)
            return result != "DELETE 0"

    async def get_translation_stats(self) -> dict:
        """Get translation statistics."""
        async with get_db_connection() as conn:
            query = """
                SELECT
                    COUNT(*) as total_translations,
                    COUNT(DISTINCT language_code) as unique_languages,
                    COUNT(DISTINCT content_pk) as translated_content_items,
                    AVG(translation_quality_score) as avg_quality_score,
                    COUNT(*) FILTER (WHERE translation_quality_score < 0.7) as poor_quality_count
                FROM translations
            """
            record = await conn.fetchrow(query)
            return dict(record) if record else {}

    async def get_language_distribution(self) -> list[dict]:
        """Get distribution of translations by language."""
        async with get_db_connection() as conn:
            query = """
                SELECT
                    language_code,
                    COUNT(*) as translation_count,
                    AVG(translation_quality_score) as avg_quality_score
                FROM translations
                GROUP BY language_code
                ORDER BY translation_count DESC
            """
            records = await conn.fetch(query)
            return [dict(record) for record in records]

    def _record_to_model(self, record: Record) -> Translation:
        """Convert database record to Translation model."""
        return Translation.model_validate(dict(record))
