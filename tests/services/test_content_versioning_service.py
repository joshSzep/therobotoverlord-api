"""Tests for ContentVersioningService."""

from unittest.mock import AsyncMock
from unittest.mock import Mock
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.content_version import ContentVersionCreate
from therobotoverlord_api.database.models.content_version import ContentVersionDiff
from therobotoverlord_api.database.models.content_version import ContentVersionSummary
from therobotoverlord_api.services.content_versioning_service import (
    ContentVersioningService,
)


class TestContentVersioningService:
    """Test cases for ContentVersioningService."""

    @pytest.fixture
    def mock_repository(self):
        """Mock content version repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository):
        """ContentVersioningService instance with mocked dependencies."""
        service = ContentVersioningService()
        service.version_repository = mock_repository
        return service

    @pytest.mark.asyncio
    async def test_create_version_success(self, service, mock_repository):
        """Test successful version creation."""
        content_pk = uuid4()
        appeal_pk = uuid4()
        editor_pk = uuid4()

        version_data = ContentVersionCreate(
            content_type=ContentType.POST,
            content_pk=content_pk,
            original_content="Original content",
            edited_title="Edited Title",
            edited_content="Edited content",
            edited_description="Edited description",
            edited_by=editor_pk,
            edit_reason="Fixed grammar issues",
            edit_type="appeal_restoration",
            appeal_pk=appeal_pk,
        )

        mock_version = Mock()
        mock_version.pk = uuid4()
        mock_version.version_number = 1
        mock_repository.create_version.return_value = mock_version

        result = await service.create_version(
            content_type=ContentType.POST,
            content_pk=content_pk,
            original_content={"content": "Original content"},
            edited_content={"title": "Edited Title", "content": "Edited content", "description": "Edited description"},
            edited_by=editor_pk,
            edit_reason="Fixed grammar issues",
            edit_type="appeal_restoration",
            appeal_pk=appeal_pk,
        )

        assert result == mock_version
        mock_repository.create_version.assert_called_once_with(version_data)

    @pytest.mark.asyncio
    async def test_get_content_history(self, service, mock_repository):
        """Test retrieving content version history."""
        content_pk = uuid4()

        mock_versions = [
            ContentVersionSummary(
                pk=uuid4(),
                version_number=1,
                content_type=ContentType.POST,
                content_pk=content_pk,
                edited_by=uuid4(),
                edit_reason="Initial version",
                edit_type="appeal_restoration",
                appeal_pk=uuid4(),
                created_at="2024-01-01T00:00:00Z",
                has_title_change=False,
                has_content_change=True,
                has_description_change=False,
            ),
            ContentVersionSummary(
                pk=uuid4(),
                version_number=2,
                content_type=ContentType.POST,
                content_pk=content_pk,
                edited_by=uuid4(),
                edit_reason="Grammar fixes",
                edit_type="appeal_restoration",
                appeal_pk=uuid4(),
                created_at="2024-01-02T00:00:00Z",
                has_title_change=True,
                has_content_change=True,
                has_description_change=False,
            ),
        ]

        mock_repository.get_content_history.return_value = mock_versions

        result = await service.get_content_history(content_pk)

        assert result == mock_versions
        mock_repository.get_content_history.assert_called_once_with(content_pk, 50)

    @pytest.mark.asyncio
    async def test_get_version_diff(self, service, mock_repository):
        """Test retrieving version diff."""
        version_pk = uuid4()
        content_pk = uuid4()
        version_number = 2

        mock_diff = ContentVersionDiff(
            version_pk=version_pk,
            version_number=version_number,
            content_type=ContentType.POST,
            content_pk=content_pk,
            title_changed=True,
            content_changed=True,
            description_changed=False,
            changes={
                "title": {"old": "Original", "new": "Edited"},
                "body": {"old": "Original content", "new": "Edited content"},
            },
            edit_metadata={
                "edit_reason": "Grammar fixes",
                "editor_name": "Moderator 1",
            },
        )

        mock_repository.get_version_diff.return_value = mock_diff

        result = await service.get_version_diff(version_pk)

        assert result == mock_diff
        mock_repository.get_version_diff.assert_called_once_with(version_pk)

    @pytest.mark.asyncio
    async def test_has_been_edited(self, service, mock_repository):
        """Test checking if content has been edited."""
        content_pk = uuid4()

        mock_version = ContentVersionSummary(
            pk=uuid4(),
            version_number=1,
            content_type=ContentType.POST,
            content_pk=content_pk,
            edited_by=uuid4(),
            edit_reason="Grammar fixes",
            edit_type="appeal_restoration",
            appeal_pk=uuid4(),
            created_at="2024-01-01T00:00:00Z",
            has_title_change=True,
            has_content_change=False,
            has_description_change=False,
        )
        mock_repository.get_content_history.return_value = [mock_version]

        result = await service.has_been_edited(content_pk)

        assert result is True
        mock_repository.get_content_history.assert_called_once_with(content_pk, 1)

    @pytest.mark.asyncio
    async def test_has_not_been_edited(self, service, mock_repository):
        """Test checking if content has not been edited."""
        content_pk = uuid4()

        mock_version = ContentVersionSummary(
            pk=uuid4(),
            version_number=1,
            content_type=ContentType.POST,
            content_pk=content_pk,
            edited_by=uuid4(),
            edit_reason="Initial version",
            edit_type="appeal_restoration",
            appeal_pk=uuid4(),
            created_at="2024-01-01T00:00:00Z",
            has_title_change=False,
            has_content_change=False,
            has_description_change=False,
        )
        mock_repository.get_content_history.return_value = [mock_version]

        result = await service.has_been_edited(content_pk)

        assert result is False
        mock_repository.get_content_history.assert_called_once_with(content_pk, 1)

    @pytest.mark.asyncio
    async def test_has_been_edited_no_versions(self, service, mock_repository):
        """Test checking if content has been edited when no versions exist."""
        content_pk = uuid4()

        mock_repository.get_content_history.return_value = []

        result = await service.has_been_edited(content_pk)

        assert result is False
        mock_repository.get_content_history.assert_called_once_with(content_pk, 1)
