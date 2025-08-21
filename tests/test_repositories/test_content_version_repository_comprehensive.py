"""Comprehensive tests for ContentVersionRepository and ContentRestorationRepository."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.content_version import ContentRestoration
from therobotoverlord_api.database.models.content_version import ContentVersion
from therobotoverlord_api.database.models.content_version import ContentVersionCreate
from therobotoverlord_api.database.models.content_version import ContentVersionDiff
from therobotoverlord_api.database.models.content_version import ContentVersionSummary
from therobotoverlord_api.database.repositories.content_version import (
    ContentRestorationRepository,
)
from therobotoverlord_api.database.repositories.content_version import (
    ContentVersionRepository,
)


class TestContentVersionRepository:
    """Test class for ContentVersionRepository."""

    @pytest.fixture
    def repository(self):
        """Create ContentVersionRepository instance."""
        return ContentVersionRepository()

    @pytest.fixture
    def mock_content_version(self):
        """Mock ContentVersion instance."""
        return ContentVersion(
            pk=uuid4(),
            version_number=1,
            content_type=ContentType.POST,
            content_pk=uuid4(),
            original_title="Original Title",
            original_content="Original content",
            original_description="Original description",
            edited_title="Edited Title",
            edited_content="Edited content",
            edited_description="Edited description",
            edited_by=uuid4(),
            edit_reason="Grammar fixes",
            edit_type="minor_edit",
            appeal_pk=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def mock_version_create(self):
        """Mock ContentVersionCreate instance."""
        return ContentVersionCreate(
            content_type=ContentType.POST,
            content_pk=uuid4(),
            original_title="Original Title",
            original_content="Original content",
            original_description="Original description",
            edited_title="Edited Title",
            edited_content="Edited content",
            edited_description="Edited description",
            edited_by=uuid4(),
            edit_reason="Grammar fixes",
            edit_type="minor_edit",
            appeal_pk=None,
        )

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_create_version_success(
        self, mock_get_connection, repository, mock_version_create, mock_content_version
    ):
        """Test creating a content version successfully."""
        version_pk = uuid4()

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {"version_pk": version_pk}
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        with patch.object(repository, "get_by_pk", return_value=mock_content_version):
            result = await repository.create_version(mock_version_create)

            mock_connection.fetchrow.assert_called_once()
            assert result == mock_content_version

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_create_version_failure(
        self, mock_get_connection, repository, mock_version_create
    ):
        """Test creating a content version with failure."""
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = {"version_pk": None}
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        with pytest.raises(ValueError, match="Failed to create content version"):
            await repository.create_version(mock_version_create)

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_content_history(self, mock_get_connection, repository):
        """Test getting content history."""
        content_pk = uuid4()
        limit = 25

        mock_records = [
            {
                "pk": uuid4(),
                "version_number": 2,
                "content_type": "post",
                "content_pk": content_pk,
                "edited_by": uuid4(),
                "edit_reason": "Grammar fixes",
                "edit_type": "minor_edit",
                "appeal_pk": None,
                "created_at": datetime.now(UTC),
                "has_title_change": True,
                "has_content_change": False,
                "has_description_change": True,
            },
            {
                "pk": uuid4(),
                "version_number": 1,
                "content_type": "post",
                "content_pk": content_pk,
                "edited_by": uuid4(),
                "edit_reason": "Initial version",
                "edit_type": "creation",
                "appeal_pk": None,
                "created_at": datetime.now(UTC),
                "has_title_change": False,
                "has_content_change": False,
                "has_description_change": False,
            },
        ]

        mock_connection = AsyncMock()
        mock_connection.fetch.return_value = mock_records
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_content_history(content_pk, limit)

        mock_connection.fetch.assert_called_once()
        assert len(result) == 2
        assert all(isinstance(item, ContentVersionSummary) for item in result)
        assert result[0].version_number == 2
        assert result[1].version_number == 1

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_version_diff_with_changes(self, mock_get_connection, repository):
        """Test getting version diff with changes."""
        version_pk = uuid4()

        mock_record = {
            "pk": version_pk,
            "version_number": 2,
            "content_type": "post",
            "content_pk": uuid4(),
            "original_title": "Original Title",
            "original_content": "Original content",
            "original_description": "Original description",
            "edited_title": "Edited Title",
            "edited_content": "Edited content",
            "edited_description": "Edited description",
            "edited_by": uuid4(),
            "edit_reason": "Grammar fixes",
            "edit_type": "minor_edit",
            "appeal_pk": None,
            "created_at": datetime.now(UTC),
        }

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = mock_record
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_version_diff(version_pk)

        assert isinstance(result, ContentVersionDiff)
        assert result.version_pk == version_pk
        assert result.title_changed is True
        assert result.content_changed is True
        assert result.description_changed is True
        assert "title" in result.changes
        assert "content" in result.changes
        assert "description" in result.changes
        assert result.changes["title"]["from"] == "Original Title"
        assert result.changes["title"]["to"] == "Edited Title"

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_version_diff_no_changes(self, mock_get_connection, repository):
        """Test getting version diff with no changes."""
        version_pk = uuid4()

        mock_record = {
            "pk": version_pk,
            "version_number": 1,
            "content_type": "post",
            "content_pk": uuid4(),
            "original_title": "Same Title",
            "original_content": "Same content",
            "original_description": "Same description",
            "edited_title": "Same Title",
            "edited_content": "Same content",
            "edited_description": "Same description",
            "edited_by": uuid4(),
            "edit_reason": "No changes",
            "edit_type": "creation",
            "appeal_pk": None,
            "created_at": datetime.now(UTC),
        }

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = mock_record
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_version_diff(version_pk)

        assert isinstance(result, ContentVersionDiff)
        assert result.title_changed is False
        assert result.content_changed is False
        assert result.description_changed is False
        assert result.changes == {}

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_version_diff_not_found(self, mock_get_connection, repository):
        """Test getting version diff for non-existent version."""
        version_pk = uuid4()

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = None
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_version_diff(version_pk)

        assert result is None

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_latest_version_found(
        self, mock_get_connection, repository, mock_content_version
    ):
        """Test getting latest version when it exists."""
        content_pk = uuid4()

        mock_record = {
            "pk": mock_content_version.pk,
            "version_number": 3,
            "content_type": "post",
            "content_pk": content_pk,
            "original_title": "Original Title",
            "original_content": "Original content",
            "original_description": "Original description",
            "edited_title": "Latest Title",
            "edited_content": "Latest content",
            "edited_description": "Latest description",
            "edited_by": uuid4(),
            "edit_reason": "Latest changes",
            "edit_type": "major_edit",
            "appeal_pk": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = mock_record
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_latest_version(content_pk)

        mock_connection.fetchrow.assert_called_once()
        assert isinstance(result, ContentVersion)
        assert result.version_number == 3

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_latest_version_not_found(self, mock_get_connection, repository):
        """Test getting latest version when none exists."""
        content_pk = uuid4()

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = None
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_latest_version(content_pk)

        assert result is None

    def test_record_to_model(self, repository):
        """Test converting database record to ContentVersion model."""
        record = {
            "pk": uuid4(),
            "version_number": 1,
            "content_type": "post",
            "content_pk": uuid4(),
            "original_title": "Original Title",
            "original_content": "Original content",
            "original_description": "Original description",
            "edited_title": "Edited Title",
            "edited_content": "Edited content",
            "edited_description": "Edited description",
            "edited_by": uuid4(),
            "edit_reason": "Grammar fixes",
            "edit_type": "minor_edit",
            "appeal_pk": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        result = repository._record_to_model(record)

        assert isinstance(result, ContentVersion)
        assert result.pk == record["pk"]
        assert result.version_number == record["version_number"]


class TestContentRestorationRepository:
    """Test class for ContentRestorationRepository."""

    @pytest.fixture
    def repository(self):
        """Create ContentRestorationRepository instance."""
        return ContentRestorationRepository()

    @pytest.fixture
    def mock_content_restoration(self):
        """Mock ContentRestoration instance."""
        return ContentRestoration(
            pk=uuid4(),
            appeal_pk=uuid4(),
            content_pk=uuid4(),
            content_type=ContentType.POST,
            content_version_pk=uuid4(),
            restored_by=uuid4(),
            original_status="rejected",
            restored_status="approved",
            content_was_edited=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_by_appeal_found(
        self, mock_get_connection, repository, mock_content_restoration
    ):
        """Test getting restoration by appeal PK when it exists."""
        appeal_pk = uuid4()

        mock_record = {
            "pk": mock_content_restoration.pk,
            "appeal_pk": appeal_pk,
            "content_pk": mock_content_restoration.content_pk,
            "content_type": "post",
            "content_version_pk": uuid4(),
            "restored_by": mock_content_restoration.restored_by,
            "original_status": "rejected",
            "restored_status": "approved",
            "content_was_edited": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = mock_record
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_by_appeal(appeal_pk)

        mock_connection.fetchrow.assert_called_once()
        assert isinstance(result, ContentRestoration)
        assert result.appeal_pk == appeal_pk

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_by_appeal_not_found(self, mock_get_connection, repository):
        """Test getting restoration by appeal PK when it doesn't exist."""
        appeal_pk = uuid4()

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = None
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_by_appeal(appeal_pk)

        assert result is None

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_by_content(self, mock_get_connection, repository):
        """Test getting all restorations for content."""
        content_pk = uuid4()

        mock_records = [
            {
                "pk": uuid4(),
                "appeal_pk": uuid4(),
                "content_pk": content_pk,
                "content_type": "post",
                "content_version_pk": uuid4(),
                "restored_by": uuid4(),
                "original_status": "rejected",
                "restored_status": "approved",
                "content_was_edited": True,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
            {
                "pk": uuid4(),
                "appeal_pk": uuid4(),
                "content_pk": content_pk,
                "content_type": "post",
                "content_version_pk": uuid4(),
                "restored_by": uuid4(),
                "original_status": "rejected",
                "restored_status": "approved",
                "content_was_edited": False,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        ]

        mock_connection = AsyncMock()
        mock_connection.fetch.return_value = mock_records
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_by_content(content_pk)

        mock_connection.fetch.assert_called_once()
        assert len(result) == 2
        assert all(isinstance(item, ContentRestoration) for item in result)
        assert all(item.content_pk == content_pk for item in result)

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_restoration_stats_no_filters(
        self, mock_get_connection, repository
    ):
        """Test getting restoration statistics without date filters."""
        mock_record = {
            "total_restorations": 100,
            "edited_restorations": 75,
            "unique_moderators": 10,
            "unique_content_items": 85,
        }

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = mock_record
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_restoration_stats()

        mock_connection.fetchrow.assert_called_once()
        assert result["total_restorations"] == 100
        assert result["edited_restorations"] == 75
        assert result["unique_moderators"] == 10
        assert result["unique_content_items"] == 85

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_restoration_stats_with_filters(
        self, mock_get_connection, repository
    ):
        """Test getting restoration statistics with date filters."""
        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 12, 31, tzinfo=UTC)

        mock_record = {
            "total_restorations": 50,
            "edited_restorations": 35,
            "unique_moderators": 5,
            "unique_content_items": 40,
        }

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = mock_record
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_restoration_stats(start_date, end_date)

        mock_connection.fetchrow.assert_called_once()
        # Verify the query was called with the date parameters
        call_args = mock_connection.fetchrow.call_args
        assert start_date in call_args[0]
        assert end_date in call_args[0]
        assert result["total_restorations"] == 50

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_restoration_stats_start_date_only(
        self, mock_get_connection, repository
    ):
        """Test getting restoration statistics with only start date."""
        start_date = datetime(2024, 6, 1, tzinfo=UTC)

        mock_record = {
            "total_restorations": 25,
            "edited_restorations": 20,
            "unique_moderators": 3,
            "unique_content_items": 22,
        }

        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = mock_record
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_restoration_stats(start_date=start_date)

        mock_connection.fetchrow.assert_called_once()
        call_args = mock_connection.fetchrow.call_args
        assert start_date in call_args[0]
        assert result["total_restorations"] == 25

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_restoration_stats_empty_result(
        self, mock_get_connection, repository
    ):
        """Test getting restoration statistics with empty result."""
        mock_connection = AsyncMock()
        mock_connection.fetchrow.return_value = None
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await repository.get_restoration_stats()

        assert result == {}

    def test_record_to_model(self, repository):
        """Test converting database record to ContentRestoration model."""
        record = {
            "pk": uuid4(),
            "appeal_pk": uuid4(),
            "content_pk": uuid4(),
            "content_type": "post",
            "content_version_pk": uuid4(),
            "restored_by": uuid4(),
            "original_status": "rejected",
            "restored_status": "approved",
            "content_was_edited": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        result = repository._record_to_model(record)

        assert isinstance(result, ContentRestoration)
        assert result.pk == record["pk"]
        assert result.appeal_pk == record["appeal_pk"]
        assert result.content_was_edited == record["content_was_edited"]
