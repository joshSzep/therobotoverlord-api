"""Service for managing content versions and edit history."""

from uuid import UUID

from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.content_version import ContentVersion
from therobotoverlord_api.database.models.content_version import ContentVersionCreate
from therobotoverlord_api.database.models.content_version import ContentVersionDiff
from therobotoverlord_api.database.models.content_version import ContentVersionSummary
from therobotoverlord_api.database.repositories.content_version import (
    ContentVersionRepository,
)


class ContentVersioningService:
    """Service for managing content versions and edit history."""

    def __init__(self):
        self.version_repository = ContentVersionRepository()

    async def create_version(
        self,
        content_type: ContentType,
        content_pk: UUID,
        original_content: dict[str, str | None],
        edited_content: dict[str, str | None] | None = None,
        edited_by: UUID | None = None,
        edit_reason: str | None = None,
        edit_type: str = "appeal_restoration",
        appeal_pk: UUID | None = None,
    ) -> ContentVersion:
        """Create a new content version with full audit trail."""

        version_data = ContentVersionCreate(
            content_type=content_type,
            content_pk=content_pk,
            original_title=original_content.get("title"),
            original_content=original_content["content"] or "",
            original_description=original_content.get("description"),
            edited_title=edited_content.get("title") if edited_content else None,
            edited_content=edited_content.get("content") if edited_content else None,
            edited_description=edited_content.get("description")
            if edited_content
            else None,
            edited_by=edited_by,
            edit_reason=edit_reason,
            edit_type=edit_type,
            appeal_pk=appeal_pk,
        )

        return await self.version_repository.create_version(version_data)

    async def get_content_history(
        self, content_pk: UUID, limit: int = 50
    ) -> list[ContentVersionSummary]:
        """Get complete edit history for content."""
        return await self.version_repository.get_content_history(content_pk, limit)

    async def get_version_diff(self, version_pk: UUID) -> ContentVersionDiff | None:
        """Get diff between original and edited content."""
        return await self.version_repository.get_version_diff(version_pk)

    async def get_latest_version(self, content_pk: UUID) -> ContentVersion | None:
        """Get the latest version for content."""
        return await self.version_repository.get_latest_version(content_pk)

    async def has_been_edited(self, content_pk: UUID) -> bool:
        """Check if content has any edit history."""
        history = await self.get_content_history(content_pk, limit=1)
        return len(history) > 0 and any(
            version.has_title_change
            or version.has_content_change
            or version.has_description_change
            for version in history
        )

    async def get_edit_count(self, content_pk: UUID) -> int:
        """Get total number of edits for content."""
        history = await self.get_content_history(
            content_pk, limit=1000
        )  # Reasonable limit
        return sum(
            1
            for version in history
            if version.has_title_change
            or version.has_content_change
            or version.has_description_change
        )

    async def get_version_by_appeal(
        self, content_pk: UUID, appeal_pk: UUID
    ) -> ContentVersion | None:
        """Get version created for a specific appeal."""
        version = await self.version_repository.get_by_field("content_pk", content_pk)
        if version and version.appeal_pk == appeal_pk:
            return version
        return None
