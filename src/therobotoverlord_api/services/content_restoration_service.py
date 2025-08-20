"""Enhanced service for restoring content with editing capability."""

from datetime import UTC
from datetime import datetime
from uuid import UUID

from therobotoverlord_api.database.models.appeal import Appeal
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.content_version import ContentRestoration
from therobotoverlord_api.database.models.content_version import (
    ContentRestorationCreate,
)
from therobotoverlord_api.database.models.content_version import RestorationResult
from therobotoverlord_api.database.models.post import PostUpdate
from therobotoverlord_api.database.models.private_message import PrivateMessageUpdate
from therobotoverlord_api.database.models.topic import TopicUpdate
from therobotoverlord_api.database.repositories.content_version import (
    ContentRestorationRepository,
)
from therobotoverlord_api.database.repositories.post import PostRepository
from therobotoverlord_api.database.repositories.private_message import (
    PrivateMessageRepository,
)
from therobotoverlord_api.database.repositories.topic import TopicRepository
from therobotoverlord_api.services.content_versioning_service import (
    ContentVersioningService,
)


class ContentNotFoundError(Exception):
    """Raised when content to be restored is not found."""


class ContentRestorationService:
    """Enhanced service for restoring content with editing capability."""

    def __init__(self):
        self.versioning_service = ContentVersioningService()
        self.restoration_repository = ContentRestorationRepository()
        self.post_repository = PostRepository()
        self.topic_repository = TopicRepository()
        self.message_repository = PrivateMessageRepository()

    async def restore_with_edits(
        self,
        content_type: ContentType,
        content_pk: UUID,
        appeal: Appeal,
        reviewer_pk: UUID,
        edited_content: dict[str, str | None] | None = None,
        edit_reason: str | None = None,
    ) -> RestorationResult:
        """Restore content with optional moderator edits."""

        try:
            # 1. Get original content
            original_content = await self._get_original_content(
                content_type, content_pk
            )
            if not original_content:
                return RestorationResult(
                    success=False,
                    content_type=content_type,
                    content_pk=content_pk,
                    error_message=f"Content {content_pk} not found",
                )

            # 2. Create content version for audit trail
            version = await self.versioning_service.create_version(
                content_type=content_type,
                content_pk=content_pk,
                original_content=original_content,
                edited_content=edited_content,
                edited_by=reviewer_pk,
                edit_reason=edit_reason,
                edit_type="appeal_restoration",
                appeal_pk=appeal.pk,
            )

            # 3. Apply content changes (use edited version if provided)
            final_content = edited_content if edited_content else original_content
            restored_content = await self._restore_content_with_data(
                content_type,
                content_pk,
                final_content,
                original_content["status"] or "unknown",
            )

            if not restored_content:
                return RestorationResult(
                    success=False,
                    content_type=content_type,
                    content_pk=content_pk,
                    version_pk=version.pk,
                    error_message="Failed to restore content",
                )

            # 4. Record restoration with version reference
            restoration = await self._record_restoration(
                appeal=appeal,
                content_type=content_type,
                content_pk=content_pk,
                content_version_pk=version.pk,
                restored_by=reviewer_pk,
                content_was_edited=bool(edited_content),
                edit_summary=edit_reason,
                original_status=original_content["status"] or "unknown",
                restored_status=ContentStatus.APPROVED.value,
            )

            return RestorationResult(
                success=True,
                content_type=content_type,
                content_pk=content_pk,
                version_pk=version.pk,
                restoration_pk=restoration.pk,
                content_edited=bool(edited_content),
                metadata={
                    "original_status": original_content["status"],
                    "restored_status": ContentStatus.APPROVED.value,
                    "edit_reason": edit_reason,
                },
            )

        except Exception as e:
            return RestorationResult(
                success=False,
                content_type=content_type,
                content_pk=content_pk,
                error_message=str(e),
            )

    async def _get_original_content(
        self, content_type: ContentType, content_pk: UUID
    ) -> dict[str, str | None] | None:
        """Get original content data for restoration."""

        if content_type == ContentType.POST:
            post = await self.post_repository.get_by_pk(content_pk)
            if not post:
                return None
            return {
                "content": post.content,
                "title": None,  # Posts don't have titles
                "description": None,
                "status": post.status.value,
            }

        if content_type == ContentType.TOPIC:
            topic = await self.topic_repository.get_by_pk(content_pk)
            if not topic:
                return None
            return {
                "title": topic.title,
                "content": topic.description,  # Topic description as content
                "description": topic.description,
                "status": topic.status.value,
            }

        if content_type == ContentType.PRIVATE_MESSAGE:
            message = await self.message_repository.get_by_pk(content_pk)
            if not message:
                return None
            return {
                "content": message.content,
                "title": None,  # Messages don't have titles
                "description": None,
                "status": message.status.value,
            }

        return None

    async def _restore_content_with_data(
        self,
        content_type: ContentType,
        content_pk: UUID,
        content_data: dict[str, str | None],
        original_status: str,
    ) -> bool:
        """Restore content using provided data."""

        try:
            if content_type == ContentType.POST:
                return await self._restore_post_with_data(content_pk, content_data)
            if content_type == ContentType.TOPIC:
                return await self._restore_topic_with_data(content_pk, content_data)
            if content_type == ContentType.PRIVATE_MESSAGE:
                return await self._restore_message_with_data(content_pk, content_data)

            return False

        except Exception:
            return False

    async def _restore_post_with_data(
        self, post_pk: UUID, content_data: dict[str, str | None]
    ) -> bool:
        """Restore post with potentially edited content."""

        update_data = PostUpdate(
            content=content_data["content"],
            status=ContentStatus.APPROVED,
            approved_at=datetime.now(UTC),
            rejection_reason=None,
        )

        restored_post = await self.post_repository.update(post_pk, update_data)
        return restored_post is not None

    async def _restore_topic_with_data(
        self, topic_pk: UUID, content_data: dict[str, str | None]
    ) -> bool:
        """Restore topic with potentially edited content."""

        update_data = TopicUpdate(
            title=content_data.get("title"),
            description=content_data.get("description"),
            status=TopicStatus.APPROVED,
            approved_at=datetime.now(UTC),
        )

        restored_topic = await self.topic_repository.update(topic_pk, update_data)
        return restored_topic is not None

    async def _restore_message_with_data(
        self, message_pk: UUID, content_data: dict[str, str | None]
    ) -> bool:
        """Restore private message with potentially edited content."""

        update_data = PrivateMessageUpdate(
            content=content_data["content"],
            status=ContentStatus.APPROVED,
        )

        restored_message = await self.message_repository.update(message_pk, update_data)
        return restored_message is not None

    async def _record_restoration(
        self,
        appeal: Appeal,
        content_type: ContentType,
        content_pk: UUID,
        content_version_pk: UUID,
        restored_by: UUID,
        *,
        content_was_edited: bool,
        edit_summary: str | None,
        original_status: str,
        restored_status: str,
    ) -> ContentRestoration:
        """Record the restoration event."""

        restoration_data = ContentRestorationCreate(
            appeal_pk=appeal.pk,
            content_type=content_type,
            content_pk=content_pk,
            content_version_pk=content_version_pk,
            restored_by=restored_by,
            restoration_reason=f"Appeal {appeal.pk} sustained",
            original_status=original_status,
            restored_status=restored_status,
            content_was_edited=content_was_edited,
            edit_summary=edit_summary,
        )

        return await self.restoration_repository.create_from_dict(
            restoration_data.model_dump()
        )

    async def get_restoration_history(
        self, content_pk: UUID
    ) -> list[ContentRestoration]:
        """Get restoration history for content."""
        return await self.restoration_repository.get_by_content(content_pk)

    async def get_restoration_by_appeal(
        self, appeal_pk: UUID
    ) -> ContentRestoration | None:
        """Get restoration record by appeal."""
        return await self.restoration_repository.get_by_appeal(appeal_pk)

    async def get_restoration_stats(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, int]:
        """Get restoration statistics."""
        return await self.restoration_repository.get_restoration_stats(
            start_date, end_date
        )
