"""Simple tests for ContentVersionRepository to improve coverage."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.repositories.content_version import (
    ContentVersionRepository,
)


class TestContentVersionRepositorySimple:
    """Simple test class for ContentVersionRepository."""

    @pytest.fixture
    def content_version_repo(self):
        """Create a ContentVersionRepository instance."""
        return ContentVersionRepository()

    @pytest.fixture
    def mock_content_version_record(self):
        """Create a mock content version record."""
        return {
            "pk": uuid4(),
            "content_type": "post",
            "content_pk": uuid4(),
            "version_number": 1,
            "original_title": "Original Title",
            "original_content": "Original content",
            "original_description": "Original description",
            "edited_title": "Edited Title",
            "edited_content": "Edited content",
            "edited_description": "Edited description",
            "edited_by": uuid4(),
            "edit_reason": "Grammar fixes",
            "edit_type": "minor_edit",
            "change_summary": "Fixed typos",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

    def test_record_to_model(self, content_version_repo, mock_content_version_record):
        """Test converting record to model."""
        result = content_version_repo._record_to_model(mock_content_version_record)

        assert result.pk == mock_content_version_record["pk"]
        assert result.content_type == mock_content_version_record["content_type"]
        assert result.version_number == mock_content_version_record["version_number"]

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.content_version.get_db_connection"
    )
    async def test_get_latest_version(
        self, mock_get_db, content_version_repo, mock_content_version_record
    ):
        """Test getting latest version."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = mock_content_version_record

        content_pk = uuid4()
        result = await content_version_repo.get_latest_version(content_pk)

        mock_conn.fetchrow.assert_called_once()
        assert result is not None
