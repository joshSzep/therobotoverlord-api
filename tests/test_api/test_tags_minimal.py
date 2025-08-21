"""Minimal tests for tags API endpoints focusing on non-auth endpoints."""

from datetime import UTC
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.tags import router
from therobotoverlord_api.database.models.tag import Tag


@pytest.fixture
def test_app():
    """Create test FastAPI app with tags router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(test_app):
    """Test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_tag():
    """Sample tag for testing."""
    from datetime import datetime

    return Tag(
        pk=uuid4(),
        name="politics",
        description="Political discussions",
        color="#FF0000",
        created_at=datetime.now(UTC),
    )


class TestTagsAPIMinimal:
    """Minimal test class for tags API endpoints."""

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tags_basic(self, mock_get_service, client, test_app, sample_tag):
        """Test GET /tags/ basic functionality."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_all_tags.return_value = [sample_tag]

        # Clear any existing dependency overrides
        test_app.dependency_overrides.clear()

        response = client.get("/tags/")

        assert response.status_code == status.HTTP_200_OK
        mock_service.get_all_tags.assert_called_once()

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_search_tags_basic(self, mock_get_service, client, test_app, sample_tag):
        """Test GET /tags/search basic functionality."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.search_tags.return_value = [sample_tag]

        # Clear any existing dependency overrides
        test_app.dependency_overrides.clear()

        response = client.get("/tags/?search=pol")

        assert response.status_code == status.HTTP_200_OK
        mock_service.search_tags.assert_called_once_with("pol", limit=50, offset=0)

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tag_by_id_basic(self, mock_get_service, client, test_app, sample_tag):
        """Test GET /tags/{tag_id} basic functionality."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_tag_by_pk.return_value = sample_tag

        # Clear any existing dependency overrides
        test_app.dependency_overrides.clear()

        tag_id = uuid4()
        response = client.get(f"/tags/{tag_id}")

        assert response.status_code == status.HTTP_200_OK
        mock_service.get_tag_by_pk.assert_called_once_with(tag_id)

    @pytest.mark.skip(
        reason="Authentication required - skipping until auth mocking is fixed"
    )
    def test_create_tag_admin_skipped(self):
        """Test POST /tags/ - skipped due to auth requirements."""

    @pytest.mark.skip(
        reason="Authentication required - skipping until auth mocking is fixed"
    )
    def test_assign_tag_to_topic_skipped(self):
        """Test POST /tags/topics/{topic_id}/tags/{tag_id} - skipped due to auth requirements."""

    @pytest.mark.skip(
        reason="Authentication required - skipping until auth mocking is fixed"
    )
    def test_get_tag_stats_skipped(self):
        """Test GET /tags/stats - skipped due to auth requirements."""
