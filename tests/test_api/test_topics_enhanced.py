"""Tests for enhanced Topics API with tag filtering and related topics."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.topics import router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.topic import TopicSummary
from therobotoverlord_api.database.models.topic import TopicWithAuthor
from therobotoverlord_api.database.models.user import User


@pytest.fixture
def test_app():
    """Create test FastAPI app with topics router."""
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
def sample_topics_with_tags():
    """Sample topics with tag information."""
    return [
        TopicSummary(
            pk=uuid4(),
            title="Political Debate",
            description="A heated political discussion",
            author_username="debater1",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            post_count=15,
            tags=["politics", "debate", "controversial"],
        ),
        TopicSummary(
            pk=uuid4(),
            title="Tech Innovation",
            description="Latest in technology",
            author_username="techie",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime(2024, 1, 2, tzinfo=UTC),
            post_count=8,
            tags=["technology", "innovation", "future"],
        ),
        TopicSummary(
            pk=uuid4(),
            title="Science Breakthrough",
            description="New scientific discovery",
            author_username="scientist",
            created_by_overlord=True,
            status=TopicStatus.APPROVED,
            created_at=datetime(2024, 1, 3, tzinfo=UTC),
            post_count=22,
            tags=["science", "research", "breakthrough"],
        ),
    ]


@pytest.fixture
def sample_topic_with_tags():
    """Sample topic with author and tags."""
    return TopicWithAuthor(
        pk=uuid4(),
        title="Tagged Topic",
        description="A topic with multiple tags",
        author_pk=uuid4(),
        author_username="tagger",
        created_by_overlord=False,
        status=TopicStatus.APPROVED,
        approved_at=None,
        approved_by=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=None,
        tags=["politics", "technology", "debate"],
    )


class TestTopicsAPITagFiltering:
    """Test Topics API tag filtering functionality."""

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topics_with_tag_filter(
        self, mock_repo_class, client, test_app, sample_topics_with_tags
    ):
        """Test GET /topics/ with tag filtering."""
        # Filter for topics with 'politics' tag
        filtered_topics = [
            topic for topic in sample_topics_with_tags if "politics" in topic.tags
        ]

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_approved_topics.return_value = filtered_topics

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/topics/?tags=politics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Political Debate"
        assert "politics" in data[0]["tags"]

        # Verify repository was called with tag filter
        mock_repo.get_approved_topics.assert_called_once_with(
            limit=50, offset=0, tag_names=["politics"]
        )

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topics_with_multiple_tag_filter(
        self, mock_repo_class, client, test_app, sample_topics_with_tags
    ):
        """Test GET /topics/ with multiple tag filtering."""
        # Filter for topics with either 'technology' or 'science' tags
        filtered_topics = [
            topic
            for topic in sample_topics_with_tags
            if any(tag in topic.tags for tag in ["technology", "science"])
        ]

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_approved_topics.return_value = filtered_topics

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/topics/?tags=technology&tags=science")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

        # Verify repository was called with multiple tags
        mock_repo.get_approved_topics.assert_called_once_with(
            limit=50, offset=0, tag_names=["technology", "science"]
        )

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topics_no_tag_filter(
        self, mock_repo_class, client, test_app, sample_topics_with_tags
    ):
        """Test GET /topics/ without tag filter returns all topics."""
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_approved_topics.return_value = sample_topics_with_tags

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/topics/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3

        # Verify repository was called without tag filter
        mock_repo.get_approved_topics.assert_called_once_with(
            limit=50, offset=0, tag_names=None
        )

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topics_empty_tag_filter(self, mock_repo_class, client, test_app):
        """Test GET /topics/ with empty tag filter."""
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_approved_topics.return_value = []

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/topics/?tags=nonexistent")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topics_with_pagination_and_tags(
        self, mock_repo_class, client, test_app, sample_topics_with_tags
    ):
        """Test GET /topics/ with both pagination and tag filtering."""
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_approved_topics.return_value = sample_topics_with_tags[:1]

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/topics/?limit=1&offset=0&tags=politics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1

        # Verify repository was called with correct parameters
        mock_repo.get_approved_topics.assert_called_once_with(
            limit=1, offset=0, tag_names=["politics"]
        )

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_topic_by_id_includes_tags(
        self, mock_repo_class, client, test_app, sample_topic_with_tags
    ):
        """Test GET /topics/{id} includes tag information."""
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_with_author.return_value = sample_topic_with_tags

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get(f"/topics/{sample_topic_with_tags.pk}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Tagged Topic"
        assert "tags" in data
        assert data["tags"] == ["politics", "technology", "debate"]

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_search_topics_includes_tag_matching(
        self, mock_repo_class, client, test_app, sample_topics_with_tags
    ):
        """Test that topic search includes tag name matching."""
        # Search should find topics with 'tech' in title, description, or tags
        tech_topics = [
            topic for topic in sample_topics_with_tags if "technology" in topic.tags
        ]

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.search_topics.return_value = tech_topics

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/topics/?search=technology")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert "technology" in data[0]["tags"]

        # Verify search was called
        mock_repo.search_topics.assert_called_once_with(
            "technology", limit=50, offset=0
        )


class TestRelatedTopicsAPI:
    """Test related topics API functionality."""

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_related_topics(
        self, mock_repo_class, client, test_app, sample_topics_with_tags
    ):
        """Test GET /topics/{id}/related endpoint."""
        topic_id = uuid4()

        # Mock related topics (topics sharing tags)
        related_topics = [
            TopicSummary(
                pk=uuid4(),
                title="Related Political Topic",
                description="Another political discussion",
                author_username="politician",
                created_by_overlord=False,
                status=TopicStatus.APPROVED,
                created_at=datetime(2024, 1, 4, tzinfo=UTC),
                post_count=12,
                tags=["politics", "government"],
            ),
            TopicSummary(
                pk=uuid4(),
                title="Debate Techniques",
                description="How to debate effectively",
                author_username="debater2",
                created_by_overlord=False,
                status=TopicStatus.APPROVED,
                created_at=datetime(2024, 1, 5, tzinfo=UTC),
                post_count=7,
                tags=["debate", "education"],
            ),
        ]

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        # Mock the topic exists and is approved
        mock_repo.get_with_author.return_value = TopicWithAuthor(
            pk=topic_id,
            title="Original Topic",
            description="Original description",
            author_pk=uuid4(),
            author_username="author",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            approved_at=None,
            approved_by=None,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=None,
            tags=["politics", "debate"],
        )

        mock_repo.get_related_topics.return_value = related_topics

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get(f"/topics/{topic_id}/related")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Related Political Topic"

        # Verify related topics query was called
        mock_repo.get_related_topics.assert_called_once_with(topic_id, limit=5)

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_related_topics_with_limit(self, mock_repo_class, client, test_app):
        """Test GET /topics/{id}/related with custom limit."""
        topic_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        # Mock approved topic
        mock_repo.get_with_author.return_value = TopicWithAuthor(
            pk=topic_id,
            title="Test Topic",
            description="Test description",
            author_pk=uuid4(),
            author_username="author",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            approved_at=None,
            approved_by=None,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=None,
            tags=["test"],
        )

        mock_repo.get_related_topics.return_value = []

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get(f"/topics/{topic_id}/related?limit=3")

        assert response.status_code == status.HTTP_200_OK

        # Verify custom limit was used
        mock_repo.get_related_topics.assert_called_once_with(topic_id, limit=3)

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_related_topics_topic_not_found(
        self, mock_repo_class, client, test_app
    ):
        """Test GET /topics/{id}/related when topic doesn't exist."""
        topic_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_with_author.return_value = None

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get(f"/topics/{topic_id}/related")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_get_related_topics_topic_not_approved(
        self, mock_repo_class, client, test_app
    ):
        """Test GET /topics/{id}/related when topic is not approved."""
        topic_id = uuid4()

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo

        # Mock pending topic
        mock_repo.get_with_author.return_value = TopicWithAuthor(
            pk=topic_id,
            title="Pending Topic",
            description="Pending description",
            author_pk=uuid4(),
            author_username="author",
            created_by_overlord=False,
            status=TopicStatus.PENDING_APPROVAL,
            approved_at=None,
            approved_by=None,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=None,
            tags=[],
        )

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get(f"/topics/{topic_id}/related")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_related_topics_invalid_limit(self, client, test_app):
        """Test GET /topics/{id}/related with invalid limit parameter."""
        topic_id = uuid4()

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        # Test limit too high
        response = client.get(f"/topics/{topic_id}/related?limit=15")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test limit too low
        response = client.get(f"/topics/{topic_id}/related?limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestTopicsAPITagIntegration:
    """Test complete integration of tags with Topics API."""

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_overlord_topics_include_tags(self, mock_repo_class, client, test_app):
        """Test that Overlord topics include tag information."""
        overlord_topics = [
            TopicSummary(
                pk=uuid4(),
                title="Overlord Decree",
                description="An important announcement",
                author_username="The Overlord",
                created_by_overlord=True,
                status=TopicStatus.APPROVED,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
                post_count=50,
                tags=["announcement", "decree", "important"],
            )
        ]

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_overlord_topics.return_value = overlord_topics

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/topics/?overlord_only=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["created_by_overlord"] is True
        assert "tags" in data[0]
        assert data[0]["tags"] == ["announcement", "decree", "important"]

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_topics_response_structure_with_tags(
        self, mock_repo_class, client, test_app, sample_topics_with_tags
    ):
        """Test that topic responses have correct structure including tags."""
        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_approved_topics.return_value = sample_topics_with_tags

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/topics/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify each topic has the expected structure
        for topic in data:
            assert "pk" in topic
            assert "title" in topic
            assert "description" in topic
            assert "author_username" in topic
            assert "created_by_overlord" in topic
            assert "status" in topic
            assert "created_at" in topic
            assert "post_count" in topic
            assert "tags" in topic
            assert isinstance(topic["tags"], list)

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_tag_filtering_with_search_combination(
        self, mock_repo_class, client, test_app
    ):
        """Test combining tag filtering with search functionality."""
        # This tests the priority: search takes precedence over tag filtering
        search_results = [
            TopicSummary(
                pk=uuid4(),
                title="Political Technology",
                description="Tech in politics",
                author_username="techpol",
                created_by_overlord=False,
                status=TopicStatus.APPROVED,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
                post_count=5,
                tags=["politics", "technology"],
            )
        ]

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.search_topics.return_value = search_results

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        # When both search and tags are provided, search takes precedence
        response = client.get("/topics/?search=technology&tags=politics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Political Technology"

        # Verify search was called, not tag filtering
        mock_repo.search_topics.assert_called_once_with(
            "technology", limit=50, offset=0
        )
        mock_repo.get_approved_topics.assert_not_called()

    @patch("therobotoverlord_api.api.topics.TopicRepository")
    def test_empty_tags_array_in_response(self, mock_repo_class, client, test_app):
        """Test that topics without tags return empty tags array."""
        untagged_topic = TopicSummary(
            pk=uuid4(),
            title="Untagged Topic",
            description="A topic without tags",
            author_username="user",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            post_count=1,
            tags=[],  # Empty tags
        )

        mock_repo = AsyncMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_approved_topics.return_value = [untagged_topic]

        # Override auth for public endpoint
        test_app.dependency_overrides[get_current_user] = lambda: None

        response = client.get("/topics/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["tags"] == []
