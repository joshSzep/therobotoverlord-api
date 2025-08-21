"""Tests for tags API endpoints with simplified authentication mocking."""

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
def sample_user():
    """Sample user for testing."""
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
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=None,
    )


@pytest.fixture
def admin_user():
    """Sample admin user for testing."""
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
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=None,
    )


@pytest.fixture
def moderator_user():
    """Sample moderator user for testing."""
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
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
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
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=None,
    )


@pytest.fixture
def sample_tag_with_count():
    """Sample tag with topic count for testing."""
    return TagWithTopicCount(
        pk=uuid4(),
        name="technology",
        description="Tech discussions",
        color="#00FF00",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        topic_count=5,
    )


class TestTagsAPI:
    """Test tags API endpoints."""

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tags(self, mock_get_service, client, test_app, sample_tag):
        """Test GET /tags/ endpoint."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_all_tags.return_value = [sample_tag]

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/tags/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "politics"

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tags_with_counts(
        self, mock_get_service, client, test_app, sample_tag_with_count
    ):
        """Test GET /tags/ with topic counts."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_tags_with_topic_count.return_value = [sample_tag_with_count]

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/tags/?with_counts=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "technology"
        assert data[0]["topic_count"] == 5

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_search_tags(self, mock_get_service, client, test_app, sample_tag):
        """Test GET /tags/ with search parameter."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.search_tags.return_value = [sample_tag]

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/tags/?search=pol")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "politics"

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_popular_tags(
        self, mock_get_service, client, test_app, sample_tag_with_count
    ):
        """Test GET /tags/popular endpoint."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_popular_tags.return_value = [sample_tag_with_count]

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/tags/popular")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "technology"
        assert data[0]["topic_count"] == 5

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tag_stats_moderator(
        self, mock_get_service, client, test_app, moderator_user
    ):
        """Test GET /tags/stats endpoint as moderator."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_tag_usage_stats.return_value = {
            "total_tags": 100,
            "used_tags": 75,
        }

        # Override auth for moderator endpoint
        test_app.dependency_overrides[moderator_dependency] = lambda: moderator_user

        response = client.get("/tags/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_tags"] == 100
        assert data["used_tags"] == 75

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tag_by_id(self, mock_get_service, client, test_app, sample_tag):
        """Test GET /tags/{tag_id} endpoint."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_tag_by_pk.return_value = sample_tag

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get(f"/tags/{sample_tag.pk}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "politics"

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_get_tag_by_id_not_found(self, mock_get_service, client, test_app):
        """Test GET /tags/{tag_id} when tag not found."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_tag_by_pk.return_value = None

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        tag_id = uuid4()
        response = client.get(f"/tags/{tag_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_create_tag_admin(
        self, mock_get_service, client, test_app, admin_user, sample_tag
    ):
        """Test POST /tags/ as admin."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.create_tag.return_value = sample_tag

        # Override auth for admin endpoint
        test_app.dependency_overrides[admin_dependency] = lambda: admin_user

        tag_data = {
            "name": "politics",
            "description": "Political discussions",
            "color": "#FF0000",
        }
        response = client.post("/tags/", json=tag_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "politics"

    def test_create_tag_unauthorized(self, client, test_app, sample_user):
        """Test POST /tags/ as regular user (should fail)."""
        from therobotoverlord_api.database.models.base import UserRole

        # Create a dependency that returns the regular user but will fail role check
        def mock_admin_dependency():
            # This will trigger the role check which should fail for a citizen
            role_hierarchy = {
                UserRole.CITIZEN: 0,
                UserRole.MODERATOR: 1,
                UserRole.ADMIN: 2,
                UserRole.SUPERADMIN: 3,
            }
            user_level = role_hierarchy.get(sample_user.role, -1)
            required_level = role_hierarchy.get(UserRole.ADMIN, 999)

            if user_level < required_level:
                from fastapi import HTTPException
                from fastapi import status

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required role: {UserRole.ADMIN.value}",
                )
            return sample_user

        # Override the admin dependency
        test_app.dependency_overrides[admin_dependency] = mock_admin_dependency

        tag_data = {
            "name": "politics",
            "description": "Political discussions",
            "color": "#FF0000",
        }
        response = client.post("/tags/", json=tag_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("therobotoverlord_api.api.tags.get_tag_service")
    def test_assign_tag_to_topic_moderator(
        self, mock_get_service, client, test_app, moderator_user
    ):
        """Test POST /tags/topics/{topic_id}/tags/{tag_id} as moderator."""
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        topic_tag_mock = {
            "pk": str(uuid4()),
            "topic_pk": str(uuid4()),
            "tag_pk": str(uuid4()),
            "assigned_by_pk": str(moderator_user.pk),
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_service.assign_tag_to_topic.return_value = topic_tag_mock

        # Override auth for moderator endpoint
        test_app.dependency_overrides[moderator_dependency] = lambda: moderator_user

        topic_id = uuid4()
        tag_id = uuid4()
        response = client.post(f"/tags/topics/{topic_id}/tags/{tag_id}")

        assert response.status_code == status.HTTP_200_OK
