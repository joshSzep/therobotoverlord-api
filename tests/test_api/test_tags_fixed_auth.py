"""Fixed tests for tags API endpoints using proper authentication mocking pattern."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.tags import admin_dependency
from therobotoverlord_api.api.tags import moderator_dependency
from therobotoverlord_api.api.tags import router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.tag import Tag
from therobotoverlord_api.database.models.tag import TagWithTopicCount
from therobotoverlord_api.database.models.user import User


@pytest.fixture
def test_app():
    """Create test FastAPI app with tags router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    return User(
        pk=uuid4(),
        email="test@example.com",
        google_id="google123",
        username="testuser",
        role=UserRole.CITIZEN,
        loyalty_score=50,
        is_banned=False,
        is_sanctioned=False,
        email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def mock_admin():
    """Mock admin user for testing."""
    return User(
        pk=uuid4(),
        email="admin@example.com",
        google_id="google456",
        username="admin",
        role=UserRole.ADMIN,
        loyalty_score=100,
        is_banned=False,
        is_sanctioned=False,
        email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def mock_moderator():
    """Mock moderator user for testing."""
    return User(
        pk=uuid4(),
        email="mod@example.com",
        google_id="google789",
        username="moderator",
        role=UserRole.MODERATOR,
        loyalty_score=75,
        is_banned=False,
        is_sanctioned=False,
        email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def sample_tag():
    """Sample tag for testing."""
    return Tag(
        pk=uuid4(),
        name="politics",
        description="Political discussions",
        color="#FF0000",
        created_at=datetime.now(UTC),
        updated_at=None,
    )


class TestTagsAPI:
    """Test class for tags API endpoints."""

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tags(self, mock_get_service, client, test_app, sample_tag):
        """Test GET /tags/."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_all_tags.return_value = [sample_tag]

        test_app.dependency_overrides[get_current_user] = (
            lambda: None
        )  # Public endpoint

        response = client.get("/tags/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "politics"

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tags_with_counts(self, mock_get_service, client, test_app):
        """Test GET /tags/ with topic counts."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        tag_with_count = TagWithTopicCount(
            pk=uuid4(),
            name="politics",
            description="Political discussions",
            color="#FF0000",
            topic_count=5,
            created_at=datetime.now(UTC),
        )
        mock_service.get_tags_with_topic_count.return_value = [tag_with_count]

        test_app.dependency_overrides[get_current_user] = (
            lambda: None
        )  # Public endpoint

        response = client.get("/tags/?with_counts=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["topic_count"] == 5

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_search_tags(self, mock_get_service, client, test_app, sample_tag):
        """Test GET /tags/ with search parameter."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.search_tags.return_value = [sample_tag]

        test_app.dependency_overrides[get_current_user] = (
            lambda: None
        )  # Public endpoint

        response = client.get("/tags/?search=politics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "politics"

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_popular_tags(self, mock_get_service, client, test_app):
        """Test GET /tags/popular."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Mock data that matches TagWithTopicCount schema
        mock_data = [
            {
                "pk": str(uuid4()),
                "name": "politics",
                "description": "Political discussions",
                "color": "#FF0000",
                "topic_count": 10,
                "created_at": "2024-01-01T00:00:00Z",
            }
        ]
        mock_service.get_popular_tags.return_value = mock_data

        test_app.dependency_overrides[get_current_user] = (
            lambda: None
        )  # Public endpoint

        response = client.get("/tags/popular")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["topic_count"] == 10

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tag_by_id(self, mock_get_service, client, test_app, sample_tag):
        """Test GET /tags/{tag_id}."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_tag_by_pk.return_value = sample_tag

        test_app.dependency_overrides[get_current_user] = (
            lambda: None
        )  # Public endpoint

        tag_id = uuid4()
        response = client.get(f"/tags/{tag_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "politics"

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tag_by_id_not_found(self, mock_get_service, client, test_app):
        """Test GET /tags/{tag_id} when tag not found."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_tag_by_pk.return_value = None

        test_app.dependency_overrides[get_current_user] = (
            lambda: None
        )  # Public endpoint

        tag_id = uuid4()
        response = client.get(f"/tags/{tag_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_create_tag_admin(
        self, mock_get_service, client, test_app, mock_admin, sample_tag
    ):
        """Test POST /tags/ as admin."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.create_tag.return_value = sample_tag

        # Override the admin dependency to return admin user
        test_app.dependency_overrides[admin_dependency] = lambda: mock_admin

        tag_data = {
            "name": "politics",
            "description": "Political discussions",
            "color": "#FF0000",
        }
        response = client.post("/tags/", json=tag_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "politics"

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_assign_tag_to_topic_moderator(
        self, mock_get_service, client, test_app, mock_moderator
    ):
        """Test POST /tags/topics/{topic_id}/tags/{tag_id} as moderator (should fail - admin only)."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Override the moderator dependency to return moderator user
        test_app.dependency_overrides[moderator_dependency] = lambda: mock_moderator

        topic_id = uuid4()
        tag_id = uuid4()
        response = client.post(f"/tags/topics/{topic_id}/tags/{tag_id}")

        # Should fail because tag assignment now requires admin role
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_assign_tag_to_topic_admin(
        self, mock_get_service, client, test_app, mock_admin
    ):
        """Test POST /tags/topics/{topic_id}/tags/{tag_id} as admin (should succeed)."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        topic_tag_mock = {
            "pk": str(uuid4()),
            "topic_pk": str(uuid4()),
            "tag_pk": str(uuid4()),
            "assigned_by_pk": str(mock_admin.pk),
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_service.assign_tag_to_topic.return_value = topic_tag_mock

        # Override the admin dependency to return admin user
        test_app.dependency_overrides[admin_dependency] = lambda: mock_admin

        topic_id = uuid4()
        tag_id = uuid4()
        response = client.post(f"/tags/topics/{topic_id}/tags/{tag_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "pk" in data

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tag_stats_moderator(
        self, mock_get_service, client, test_app, mock_moderator
    ):
        """Test GET /tags/stats as moderator."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_tag_usage_stats.return_value = {
            "total_tags": 50,
            "total_assignments": 200,
        }

        # Override the moderator dependency to return moderator user
        test_app.dependency_overrides[moderator_dependency] = lambda: mock_moderator

        response = client.get("/tags/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_tags"] == 50
        assert data["total_assignments"] == 200

    def test_create_tag_unauthorized(self, client, test_app):
        """Test POST /tags/ without authentication."""
        tag_data = {
            "name": "politics",
            "description": "Political discussions",
            "color": "#FF0000",
        }
        response = client.post("/tags/", json=tag_data)

        # Should fail without authentication
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
