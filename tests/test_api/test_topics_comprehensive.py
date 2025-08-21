"""Comprehensive unit tests for Topics API endpoints."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.topics import moderator_dependency
from therobotoverlord_api.api.topics import router as topics_router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.topic import Topic
from therobotoverlord_api.database.models.topic import TopicSummary
from therobotoverlord_api.database.models.topic import TopicWithAuthor
from therobotoverlord_api.database.models.user import User


@pytest.fixture
def test_app():
    """Create test FastAPI app without middleware."""
    app = FastAPI()
    app.include_router(topics_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app):
    """Test client for API endpoints."""
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
def mock_moderator():
    """Mock moderator user for testing."""
    return User(
        pk=uuid4(),
        email="mod@example.com",
        google_id="google456",
        username="moderator",
        role=UserRole.MODERATOR,
        loyalty_score=100,
        is_banned=False,
        is_sanctioned=False,
        email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def sample_topic():
    """Sample Topic model for testing."""
    return Topic(
        pk=uuid4(),
        title="Test Topic",
        description="This is a test topic for debate",
        author_pk=uuid4(),
        created_by_overlord=False,
        status=TopicStatus.APPROVED,
        approved_at=datetime.now(UTC),
        approved_by=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def sample_topic_with_author(sample_topic):
    """Sample TopicWithAuthor model for testing."""
    return TopicWithAuthor(
        pk=sample_topic.pk,
        title=sample_topic.title,
        description=sample_topic.description,
        author_pk=sample_topic.author_pk,
        author_username="testuser",
        created_by_overlord=sample_topic.created_by_overlord,
        status=sample_topic.status,
        approved_at=sample_topic.approved_at,
        approved_by=sample_topic.approved_by,
        created_at=sample_topic.created_at,
        updated_at=sample_topic.updated_at,
    )


@pytest.fixture
def sample_topic_summary(sample_topic):
    """Sample TopicSummary model for testing."""
    return TopicSummary(
        pk=sample_topic.pk,
        title=sample_topic.title,
        description=sample_topic.description,
        author_username="testuser",
        created_by_overlord=sample_topic.created_by_overlord,
        status=sample_topic.status,
        created_at=sample_topic.created_at,
        post_count=5,
    )


class TestGetTopics:
    """Test cases for GET /topics/ endpoint."""

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topics_success(self, mock_repo_class, client, sample_topic_summary):
        """Test successful retrieval of topics."""
        mock_repo = AsyncMock()
        mock_repo.get_approved_topics.return_value = [sample_topic_summary]
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/topics/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Topic"
        mock_repo.get_approved_topics.assert_called_once_with(
            limit=50, offset=0, tag_names=None
        )

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topics_with_search(
        self, mock_repo_class, client, sample_topic_summary
    ):
        """Test topics retrieval with search parameter."""
        mock_repo = AsyncMock()
        mock_repo.search_topics.return_value = [sample_topic_summary]
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/topics/?search=test")

        assert response.status_code == status.HTTP_200_OK
        mock_repo.search_topics.assert_called_once_with("test", limit=50, offset=0)

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topics_overlord_only(
        self, mock_repo_class, client, sample_topic_summary
    ):
        """Test topics retrieval with overlord_only filter."""
        mock_repo = AsyncMock()
        mock_repo.get_overlord_topics.return_value = [sample_topic_summary]
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/topics/?overlord_only=true")

        assert response.status_code == status.HTTP_200_OK
        mock_repo.get_overlord_topics.assert_called_once_with(limit=50, offset=0)


class TestGetTopic:
    """Test cases for GET /topics/{topic_id} endpoint."""

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topic_success(self, mock_repo_class, client, sample_topic_with_author):
        """Test successful retrieval of a specific topic."""
        mock_repo = AsyncMock()
        mock_repo.get_with_author.return_value = sample_topic_with_author
        mock_repo_class.return_value = mock_repo

        topic_id = sample_topic_with_author.pk
        response = client.get(f"/api/v1/topics/{topic_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Test Topic"
        assert data["author_username"] == "testuser"

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topic_not_found(self, mock_repo_class, client):
        """Test retrieval of non-existent topic."""
        mock_repo = AsyncMock()
        mock_repo.get_with_author.return_value = None
        mock_repo_class.return_value = mock_repo

        topic_id = uuid4()
        response = client.get(f"/api/v1/topics/{topic_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateTopic:
    """Test cases for POST /topics/ endpoint."""

    @patch("therobotoverlord_api.api.topics.get_queue_service")
    @patch("therobotoverlord_api.api.topics.get_loyalty_score_service")
    @patch("therobotoverlord_api.database.repositories.user.UserRepository")
    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_create_topic_success(
        self,
        mock_topic_repo_class,
        mock_user_repo_class,
        mock_loyalty_service,
        mock_queue_service,
        client,
        mock_user,
        sample_topic,
    ):
        """Test successful topic creation."""
        mock_user.loyalty_score = 100  # High enough loyalty score

        mock_topic_repo = AsyncMock()
        mock_topic_repo.create.return_value = sample_topic
        mock_topic_repo_class.return_value = mock_topic_repo

        mock_user_repo = AsyncMock()
        mock_user_repo.can_create_topic.return_value = True
        mock_user_repo_class.return_value = mock_user_repo

        # Mock loyalty service
        mock_loyalty_service_instance = AsyncMock()
        mock_loyalty_service_instance.get_score_thresholds.return_value = {
            "topic_creation": 50
        }
        mock_loyalty_service_instance.record_moderation_event.return_value = AsyncMock()
        mock_loyalty_service.return_value = mock_loyalty_service_instance

        # Mock queue service
        mock_queue_service_instance = AsyncMock()
        mock_queue_service_instance.add_topic_to_queue.return_value = AsyncMock()
        mock_queue_service.return_value = mock_queue_service_instance

        topic_data = {
            "title": "New Topic",
            "description": "This is a new topic for debate",
        }

        # Override the dependency
        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.post("/api/v1/topics/", json=topic_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == sample_topic.title
        mock_topic_repo.create.assert_called_once()
        # Loyalty service should be called instead of UserRepository.can_create_topic
        mock_loyalty_service_instance.get_score_thresholds.assert_called_once()

        # Clean up
        client.app.dependency_overrides.clear()

    @patch("therobotoverlord_api.api.topics.get_loyalty_score_service")
    @patch("therobotoverlord_api.database.repositories.user.UserRepository")
    def test_create_topic_insufficient_loyalty(
        self, mock_user_repo_class, mock_loyalty_service, client, mock_user
    ):
        """Test topic creation with insufficient loyalty score."""
        mock_user.loyalty_score = 5  # Below threshold

        mock_user_repo = AsyncMock()
        mock_user_repo.can_create_topic.return_value = False
        mock_user_repo.get_top_percent_loyalty_threshold.return_value = 75
        mock_user_repo_class.return_value = mock_user_repo

        # Mock loyalty service
        mock_loyalty_service_instance = AsyncMock()
        mock_loyalty_service_instance.get_score_thresholds.return_value = {
            "topic_creation": 50
        }
        mock_loyalty_service.return_value = mock_loyalty_service_instance

        topic_data = {
            "title": "New Topic",
            "description": "This is a new topic for debate",
        }

        # Override the dependency
        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.post("/api/v1/topics/", json=topic_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_detail = response.json()["detail"]
        assert "Insufficient loyalty score" in response_detail
        assert "Required: 50" in response_detail
        assert "Your score: 5" in response_detail

        # Clean up
        client.app.dependency_overrides.clear()

    def test_create_topic_unauthenticated(self, client):
        """Test topic creation without authentication."""
        topic_data = {
            "title": "New Topic",
            "description": "This is a new topic for debate",
        }

        response = client.post("/api/v1/topics/", json=topic_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestModerationEndpoints:
    """Test cases for moderation endpoints."""

    @patch("therobotoverlord_api.api.topics.get_loyalty_score_service")
    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_approve_topic_success(
        self,
        mock_repo_class,
        mock_loyalty_service,
        client,
        mock_moderator,
        sample_topic,
    ):
        """Test successful topic approval by moderator."""
        mock_repo = AsyncMock()
        mock_repo.approve_topic.return_value = sample_topic
        mock_repo_class.return_value = mock_repo

        # Mock loyalty service
        mock_loyalty_service_instance = AsyncMock()
        mock_loyalty_service.return_value = mock_loyalty_service_instance

        topic_id = sample_topic.pk

        # Override the dependency
        client.app.dependency_overrides[moderator_dependency] = lambda: mock_moderator

        response = client.patch(f"/api/v1/topics/{topic_id}/approve")

        assert response.status_code == status.HTTP_200_OK
        mock_repo.approve_topic.assert_called_once_with(topic_id, mock_moderator.pk)

        # Clean up
        client.app.dependency_overrides.clear()

    @patch("therobotoverlord_api.api.topics.get_loyalty_score_service")
    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_reject_topic_success(
        self,
        mock_repo_class,
        mock_loyalty_service,
        client,
        mock_moderator,
        sample_topic,
    ):
        """Test successful topic rejection by moderator."""
        mock_repo = AsyncMock()
        mock_repo.reject_topic.return_value = sample_topic
        mock_repo_class.return_value = mock_repo

        # Mock loyalty service
        mock_loyalty_service_instance = AsyncMock()
        mock_loyalty_service.return_value = mock_loyalty_service_instance

        topic_id = sample_topic.pk

        # Override the dependency
        client.app.dependency_overrides[moderator_dependency] = lambda: mock_moderator

        response = client.patch(f"/api/v1/topics/{topic_id}/reject")

        assert response.status_code == status.HTTP_200_OK
        mock_repo.reject_topic.assert_called_once_with(topic_id)

        # Clean up
        client.app.dependency_overrides.clear()

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_pending_topics_success(
        self, mock_repo_class, client, mock_moderator, sample_topic
    ):
        """Test successful retrieval of pending topics by moderator."""
        mock_repo = AsyncMock()
        mock_repo.get_by_status.return_value = [sample_topic]
        mock_repo_class.return_value = mock_repo

        # Override the dependency
        client.app.dependency_overrides[moderator_dependency] = lambda: mock_moderator

        response = client.get("/api/v1/topics/pending/list")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        mock_repo.get_by_status.assert_called_once_with(
            TopicStatus.PENDING_APPROVAL, limit=50, offset=0
        )

        # Clean up
        client.app.dependency_overrides.clear()

    def test_moderation_endpoints_unauthorized(self, client):
        """Test moderation endpoints without authentication."""
        topic_id = uuid4()

        # Test approve endpoint
        response = client.patch(f"/api/v1/topics/{topic_id}/approve")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test reject endpoint
        response = client.patch(f"/api/v1/topics/{topic_id}/reject")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test pending list endpoint
        response = client.get("/api/v1/topics/pending/list")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestValidation:
    """Test cases for input validation."""

    def test_invalid_limit(self, client):
        """Test topics retrieval with invalid limit parameter."""
        response = client.get("/api/v1/topics/?limit=200")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_negative_offset(self, client):
        """Test topics retrieval with negative offset parameter."""
        response = client.get("/api/v1/topics/?offset=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_uuid(self, client):
        """Test retrieval with invalid UUID format."""
        response = client.get("/api/v1/topics/invalid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestBusinessLogic:
    """Test cases for business logic validation."""

    @patch("therobotoverlord_api.api.topics.get_loyalty_score_service")
    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_moderator_bypass_loyalty_score(
        self,
        mock_repo_class,
        mock_loyalty_service,
        client,
        mock_moderator,
        sample_topic,
    ):
        """Test that moderators can create topics regardless of loyalty score."""
        mock_moderator.loyalty_score = 0  # Below threshold but should be bypassed
        mock_repo = AsyncMock()
        mock_repo.create.return_value = sample_topic
        mock_repo_class.return_value = mock_repo

        # Mock loyalty service
        mock_loyalty_service_instance = AsyncMock()
        mock_loyalty_service.return_value = mock_loyalty_service_instance

        topic_data = {
            "title": "Moderator Topic",
            "description": "Topic created by moderator",
        }

        # Override the dependency
        client.app.dependency_overrides[get_current_user] = lambda: mock_moderator

        response = client.post("/api/v1/topics/", json=topic_data)

        assert response.status_code == status.HTTP_201_CREATED
        # Note: No UserRepository should be called for non-citizens

        # Clean up
        client.app.dependency_overrides.clear()

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_non_approved_topic_hidden(
        self, mock_repo_class, client, sample_topic_with_author
    ):
        """Test that non-approved topics are hidden from public view."""
        sample_topic_with_author.status = TopicStatus.PENDING_APPROVAL
        mock_repo = AsyncMock()
        mock_repo.get_with_author.return_value = sample_topic_with_author
        mock_repo_class.return_value = mock_repo

        topic_id = sample_topic_with_author.pk
        response = client.get(f"/api/v1/topics/{topic_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Topic not found" in response.json()["detail"]
