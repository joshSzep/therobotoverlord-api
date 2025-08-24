"""Tests for User Management API endpoints."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.users import router as users_router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.badge import Badge
from therobotoverlord_api.database.models.badge import BadgeType
from therobotoverlord_api.database.models.badge import UserBadgeWithDetails
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserProfile
from therobotoverlord_api.services.user_service import get_user_service


@pytest.fixture
def test_app():
    """Create a test FastAPI app without database initialization."""
    app = FastAPI()
    app.include_router(users_router, prefix="/api/v1")
    return app


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    now = datetime.now(UTC)
    return User(
        pk=uuid4(),
        email="test@example.com",
        google_id="google123",
        username="testuser",
        role=UserRole.CITIZEN,
        loyalty_score=100,
        is_banned=False,
        is_sanctioned=False,
        email_verified=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_admin():
    """Create a sample admin user for testing."""
    now = datetime.now(UTC)
    return User(
        pk=uuid4(),
        email="admin@example.com",
        google_id="admin123",
        username="adminuser",
        role=UserRole.ADMIN,
        loyalty_score=1000,
        is_banned=False,
        is_sanctioned=False,
        email_verified=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_user_profile():
    """Create a sample user profile for testing."""
    now = datetime.now(UTC)
    return UserProfile(
        pk=uuid4(),
        username="testuser",
        loyalty_score=100,
        role=UserRole.CITIZEN,
        created_at=now,
    )


@pytest.fixture
def mock_user_service():
    """Create a mock user service."""
    return AsyncMock()


class TestGetUserProfile:
    """Test cases for GET /api/v1/users/{user_pk}/profile endpoint."""

    def test_get_user_profile_success(self, test_app, sample_user, sample_user_profile):
        """Test successful user profile retrieval."""
        # Mock the UserService
        mock_service = AsyncMock()
        mock_service.get_user_profile.return_value = sample_user_profile

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service

        # Create test client
        client = TestClient(test_app)
        response = client.get(f"/api/v1/users/{sample_user.pk}/profile")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pk"] == str(sample_user_profile.pk)
        assert data["username"] == sample_user_profile.username

    def test_get_user_profile_not_found(self, test_app, sample_user):
        """Test user profile not found."""
        # Mock the UserService to return None
        mock_service = AsyncMock()
        mock_service.get_user_profile.return_value = None

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service

        client = TestClient(test_app)
        response = client.get(f"/api/v1/users/{sample_user.pk}/profile")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetUserGraveyard:
    """Test cases for GET /api/v1/users/{user_pk}/graveyard endpoint."""

    def test_get_user_graveyard_success(self, test_app, sample_user):
        """Test successful user graveyard retrieval."""
        # Mock posts
        now = datetime.now(UTC)
        mock_posts = [
            Post(
                pk=uuid4(),
                content="Test content",
                author_pk=sample_user.pk,
                topic_pk=uuid4(),
                overlord_feedback="Test feedback",
                submitted_at=now,
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
        ]

        # Mock the UserService
        mock_service = AsyncMock()
        mock_service.get_user_graveyard.return_value = mock_posts

        # Mock current user
        def mock_current_user():
            return sample_user

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service
        test_app.dependency_overrides[get_current_user] = mock_current_user

        client = TestClient(test_app)
        response = client.get(f"/api/v1/users/{sample_user.pk}/graveyard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == "Test content"

    def test_get_user_graveyard_forbidden(self, test_app, sample_user, sample_admin):
        """Test forbidden access to another user's graveyard."""
        # Mock the UserService
        mock_service = AsyncMock()

        # Mock current user as different user
        def mock_current_user():
            return sample_admin

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service
        test_app.dependency_overrides[get_current_user] = mock_current_user

        client = TestClient(test_app)
        response = client.get(f"/api/v1/users/{sample_user.pk}/graveyard")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetUserRegistry:
    """Test cases for GET /api/v1/users/registry endpoint."""

    def test_get_user_registry_success(self, test_app, sample_user_profile):
        """Test successful user registry retrieval."""
        # Mock the UserService
        mock_service = AsyncMock()
        mock_service.get_user_registry.return_value = [sample_user_profile]

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service

        client = TestClient(test_app)
        response = client.get("/api/v1/users/registry")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == "testuser"

    def test_get_user_registry_with_filters(self, test_app, sample_user_profile):
        """Test user registry with role filter."""
        # Mock the UserService
        mock_service = AsyncMock()
        mock_service.get_user_registry.return_value = [sample_user_profile]

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service

        client = TestClient(test_app)
        response = client.get("/api/v1/users/registry?role_filter=citizen")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1


class TestUpdateUserProfile:
    """Test cases for PUT /api/v1/users/{user_pk} endpoint."""

    def test_update_user_profile_success(self, test_app, sample_user):
        """Test successful user profile update."""
        # Mock the UserService
        mock_service = AsyncMock()
        updated_user = sample_user.model_copy(update={"username": "newusername"})
        mock_service.update_user.return_value = updated_user

        # Mock current user
        def mock_current_user():
            return sample_user

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service
        test_app.dependency_overrides[get_current_user] = mock_current_user

        client = TestClient(test_app)
        response = client.put(
            f"/api/v1/users/{sample_user.pk}", json={"username": "newusername"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "newusername"

    def test_update_user_profile_forbidden(self, test_app, sample_user, sample_admin):
        """Test forbidden user profile update."""
        # Mock the UserService
        mock_service = AsyncMock()

        # Mock current user as different non-admin user
        other_user = sample_admin.model_copy(update={"role": UserRole.CITIZEN})

        def mock_current_user():
            return other_user

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service
        test_app.dependency_overrides[get_current_user] = mock_current_user

        client = TestClient(test_app)
        response = client.put(
            f"/api/v1/users/{sample_user.pk}", json={"username": "newusername"}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_profile_admin_privileges(
        self, test_app, sample_user, sample_admin
    ):
        """Test admin can update any user profile."""
        # Mock the UserService
        mock_service = AsyncMock()
        updated_user = sample_user.model_copy(update={"role": UserRole.MODERATOR})
        mock_service.update_user.return_value = updated_user

        # Mock current user as admin
        def mock_current_user():
            return sample_admin

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service
        test_app.dependency_overrides[get_current_user] = mock_current_user

        client = TestClient(test_app)
        response = client.put(
            f"/api/v1/users/{sample_user.pk}", json={"role": "moderator"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role"] == "moderator"


class TestGetUserBadges:
    """Test cases for GET /api/v1/users/{user_pk}/badges endpoint."""

    def test_get_user_badges_success(self, test_app, sample_user):
        """Test successful user badges retrieval."""
        # Mock badges
        now = datetime.now(UTC)
        badge_pk = uuid4()
        mock_badges = [
            UserBadgeWithDetails(
                pk=uuid4(),
                user_pk=sample_user.pk,
                badge_pk=badge_pk,
                awarded_at=now,
                created_at=now,
                updated_at=now,
                badge=Badge(
                    pk=badge_pk,
                    name="Test Badge",
                    description="A test badge",
                    badge_type=BadgeType.POSITIVE,
                    criteria_config={"type": "test"},
                    image_url="test.png",
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                ),
                username=sample_user.username,
            )
        ]

        # Mock the UserService
        mock_service = AsyncMock()
        mock_service.get_user_badges.return_value = mock_badges

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service

        client = TestClient(test_app)
        response = client.get(f"/api/v1/users/{sample_user.pk}/badges")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_pk"] == str(sample_user.pk)


class TestGetUserActivity:
    """Test cases for GET /api/v1/users/{user_pk}/activity endpoint."""

    def test_get_user_activity_success(self, test_app, sample_user):
        """Test successful user activity retrieval."""
        # Mock activity
        now = datetime.now(UTC)
        mock_activity = {
            "posts": [
                Post(
                    pk=uuid4(),
                    content="Test content",
                    author_pk=sample_user.pk,
                    topic_pk=uuid4(),
                    overlord_feedback="Test feedback",
                    submitted_at=now,
                    approved_at=now,
                    created_at=now,
                    updated_at=now,
                )
            ],
            "topics": [],
        }

        # Mock the UserService
        mock_service = AsyncMock()
        mock_service.get_user_activity.return_value = mock_activity

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service

        client = TestClient(test_app)
        response = client.get(f"/api/v1/users/{sample_user.pk}/activity")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "posts" in data
        assert "topics" in data
        assert len(data["posts"]) == 1


class TestDeleteUserAccount:
    """Test cases for DELETE /api/v1/users/{user_pk} endpoint."""

    def test_delete_user_account_success(self, test_app, sample_user):
        """Test successful user account deletion."""
        # Mock the UserService
        mock_service = AsyncMock()
        mock_service.delete_user_account.return_value = True

        # Mock current user
        def mock_current_user():
            return sample_user

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service
        test_app.dependency_overrides[get_current_user] = mock_current_user

        client = TestClient(test_app)
        response = client.delete(f"/api/v1/users/{sample_user.pk}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "User account deleted successfully"

    def test_delete_user_account_forbidden(self, test_app, sample_user, sample_admin):
        """Test forbidden user account deletion."""
        # Mock the UserService
        mock_service = AsyncMock()

        # Mock current user as different non-admin user
        other_user = sample_admin.model_copy(update={"role": UserRole.CITIZEN})

        def mock_current_user():
            return other_user

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service
        test_app.dependency_overrides[get_current_user] = mock_current_user

        client = TestClient(test_app)
        response = client.delete(f"/api/v1/users/{sample_user.pk}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_account_admin_privileges(
        self, test_app, sample_user, sample_admin
    ):
        """Test admin can delete any user account."""
        # Mock the UserService
        mock_service = AsyncMock()
        mock_service.delete_user_account.return_value = True

        # Mock current user as admin
        def mock_current_user():
            return sample_admin

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service
        test_app.dependency_overrides[get_current_user] = mock_current_user

        client = TestClient(test_app)
        response = client.delete(f"/api/v1/users/{sample_user.pk}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "User account deleted successfully"

    def test_delete_user_account_not_found(self, test_app, sample_user):
        """Test user account deletion when user not found."""
        # Mock the UserService
        mock_service = AsyncMock()
        mock_service.delete_user_account.return_value = False

        # Mock current user
        def mock_current_user():
            return sample_user

        # Override dependencies
        test_app.dependency_overrides[get_user_service] = lambda: mock_service
        test_app.dependency_overrides[get_current_user] = mock_current_user

        client = TestClient(test_app)
        response = client.delete(f"/api/v1/users/{sample_user.pk}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
