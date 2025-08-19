"""Comprehensive unit tests for Posts API endpoints."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.posts import moderator_dependency
from therobotoverlord_api.api.posts import router as posts_router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.post import PostSummary
from therobotoverlord_api.database.models.post import PostThread
from therobotoverlord_api.database.models.post import PostWithAuthor
from therobotoverlord_api.database.models.user import User


@pytest.fixture
def test_app():
    """Create test FastAPI app without middleware."""
    app = FastAPI()
    app.include_router(posts_router, prefix="/api/v1")
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
def sample_post():
    """Sample Post model for testing."""
    return Post(
        pk=uuid4(),
        topic_pk=uuid4(),
        parent_post_pk=None,
        author_pk=uuid4(),
        content="This is a test post for debate",
        status=ContentStatus.APPROVED,
        overlord_feedback=None,
        submitted_at=datetime.now(UTC),
        approved_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=None,
    )


@pytest.fixture
def sample_post_with_author(sample_post):
    """Sample PostWithAuthor model for testing."""
    return PostWithAuthor(
        pk=sample_post.pk,
        topic_pk=sample_post.topic_pk,
        parent_post_pk=sample_post.parent_post_pk,
        author_pk=sample_post.author_pk,
        author_username="testuser",
        content=sample_post.content,
        status=sample_post.status,
        overlord_feedback=sample_post.overlord_feedback,
        submitted_at=sample_post.submitted_at,
        approved_at=sample_post.approved_at,
        rejection_reason=sample_post.rejection_reason,
        tos_violation=sample_post.tos_violation,
        created_at=sample_post.created_at,
        updated_at=sample_post.updated_at,
    )


@pytest.fixture
def sample_post_summary(sample_post):
    """Sample PostSummary model for testing."""
    return PostSummary(
        pk=sample_post.pk,
        topic_pk=sample_post.topic_pk,
        topic_title="Test Topic",
        content=sample_post.content,
        status=sample_post.status,
        overlord_feedback=sample_post.overlord_feedback,
        submitted_at=sample_post.submitted_at,
        approved_at=sample_post.approved_at,
        rejection_reason=sample_post.rejection_reason,
        tos_violation=sample_post.tos_violation,
    )


@pytest.fixture
def sample_post_thread(sample_post):
    """Sample PostThread model for testing."""
    return PostThread(
        pk=sample_post.pk,
        topic_pk=sample_post.topic_pk,
        parent_post_pk=sample_post.parent_post_pk,
        author_pk=sample_post.author_pk,
        author_username="testuser",
        content=sample_post.content,
        status=sample_post.status,
        overlord_feedback=sample_post.overlord_feedback,
        submitted_at=sample_post.submitted_at,
        approved_at=sample_post.approved_at,
        created_at=sample_post.created_at,
        reply_count=0,
        depth_level=0,
    )


class TestGetPosts:
    """Test cases for GET /posts/ endpoint."""

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_posts_recent_default(
        self, mock_repo_class, client, sample_post_with_author
    ):
        """Test getting recent posts (default behavior)."""
        mock_repo = AsyncMock()
        mock_repo.get_recent_approved_posts.return_value = [sample_post_with_author]
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/posts/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == "This is a test post for debate"
        mock_repo.get_recent_approved_posts.assert_called_once_with(50, 0)

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_posts_by_topic(self, mock_repo_class, client, sample_post_with_author):
        """Test getting posts filtered by topic."""
        mock_repo = AsyncMock()
        mock_repo.get_approved_by_topic.return_value = [sample_post_with_author]
        mock_repo_class.return_value = mock_repo

        topic_id = uuid4()
        response = client.get(f"/api/v1/posts/?topic_id={topic_id}")

        assert response.status_code == status.HTTP_200_OK
        mock_repo.get_approved_by_topic.assert_called_once_with(topic_id, 50, 0)

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_posts_search(self, mock_repo_class, client, sample_post_with_author):
        """Test searching posts."""
        mock_repo = AsyncMock()
        mock_repo.search_posts.return_value = [sample_post_with_author]
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/posts/?search=test")

        assert response.status_code == status.HTTP_200_OK
        mock_repo.search_posts.assert_called_once_with("test", None, 50, 0)


class TestGetPost:
    """Test cases for GET /posts/{post_id} endpoint."""

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_post_success(
        self, mock_repo_class, client, sample_post, sample_post_with_author
    ):
        """Test successful retrieval of a specific post."""
        mock_repo = AsyncMock()
        mock_repo.get_by_pk.return_value = sample_post
        mock_repo.get_by_topic.return_value = [sample_post_with_author]
        mock_repo_class.return_value = mock_repo

        response = client.get(f"/api/v1/posts/{sample_post.pk}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"] == "This is a test post for debate"
        assert data["author_username"] == "testuser"

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_post_not_found(self, mock_repo_class, client):
        """Test retrieval of non-existent post."""
        mock_repo = AsyncMock()
        mock_repo.get_by_pk.return_value = None
        mock_repo_class.return_value = mock_repo

        post_id = uuid4()
        response = client.get(f"/api/v1/posts/{post_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_post_not_approved(self, mock_repo_class, client, sample_post):
        """Test retrieval of non-approved post (should be hidden)."""
        sample_post.status = ContentStatus.PENDING
        mock_repo = AsyncMock()
        mock_repo.get_by_pk.return_value = sample_post
        mock_repo_class.return_value = mock_repo

        response = client.get(f"/api/v1/posts/{sample_post.pk}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetTopicThread:
    """Test cases for GET /posts/topic/{topic_id}/thread endpoint."""

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_topic_thread_success(
        self, mock_repo_class, client, sample_post_thread
    ):
        """Test successful retrieval of topic thread."""
        mock_repo = AsyncMock()
        mock_repo.get_thread_view.return_value = [sample_post_thread]
        mock_repo_class.return_value = mock_repo

        topic_id = uuid4()
        response = client.get(f"/api/v1/posts/topic/{topic_id}/thread")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["depth_level"] == 0
        assert data[0]["reply_count"] == 0
        mock_repo.get_thread_view.assert_called_once_with(topic_id, 50, 0)


class TestCreatePost:
    """Test cases for POST /posts/ endpoint."""

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_create_post_success(self, mock_repo_class, client, mock_user, sample_post):
        """Test successful post creation."""
        mock_repo = AsyncMock()
        mock_repo.create.return_value = sample_post
        mock_repo_class.return_value = mock_repo

        post_data = {
            "topic_pk": str(uuid4()),
            "parent_post_pk": None,
            "author_pk": str(mock_user.pk),
            "content": "This is a new post for debate",
            "submitted_at": datetime.now(UTC).isoformat(),
        }

        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.post("/api/v1/posts/", json=post_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"] == sample_post.content
        mock_repo.create.assert_called_once()

        client.app.dependency_overrides.clear()

    def test_create_post_banned_user(self, client, mock_user):
        """Test post creation with banned user."""
        mock_user.is_banned = True

        post_data = {
            "topic_pk": str(uuid4()),
            "author_pk": str(mock_user.pk),
            "content": "This should fail",
            "submitted_at": datetime.now(UTC).isoformat(),
        }

        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.post("/api/v1/posts/", json=post_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Banned users cannot create posts" in response.json()["detail"]

        client.app.dependency_overrides.clear()

    def test_create_post_sanctioned_user(self, client, mock_user):
        """Test post creation with sanctioned user."""
        mock_user.is_sanctioned = True

        post_data = {
            "topic_pk": str(uuid4()),
            "author_pk": str(mock_user.pk),
            "content": "This should fail",
            "submitted_at": datetime.now(UTC).isoformat(),
        }

        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.post("/api/v1/posts/", json=post_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Sanctioned users cannot create posts" in response.json()["detail"]

        client.app.dependency_overrides.clear()

    def test_create_post_unauthenticated(self, client):
        """Test post creation without authentication."""
        post_data = {
            "topic_pk": str(uuid4()),
            "author_pk": str(uuid4()),
            "content": "This should fail",
            "submitted_at": datetime.now(UTC).isoformat(),
        }

        response = client.post("/api/v1/posts/", json=post_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUpdatePost:
    """Test cases for PATCH /posts/{post_id} endpoint."""

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_update_post_success(self, mock_repo_class, client, mock_user, sample_post):
        """Test successful post update by author."""
        sample_post.author_pk = mock_user.pk
        updated_post = sample_post.model_copy()
        updated_post.content = "Updated content"

        mock_repo = AsyncMock()
        mock_repo.get_by_pk.return_value = sample_post
        mock_repo.update.return_value = updated_post
        mock_repo_class.return_value = mock_repo

        update_data = {"content": "Updated content"}

        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.patch(f"/api/v1/posts/{sample_post.pk}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"] == "Updated content"

        client.app.dependency_overrides.clear()

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_update_post_not_author(
        self, mock_repo_class, client, mock_user, sample_post
    ):
        """Test post update by non-author (should fail)."""
        mock_repo = AsyncMock()
        mock_repo.get_by_pk.return_value = sample_post
        mock_repo_class.return_value = mock_repo

        update_data = {"content": "Updated content"}

        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.patch(f"/api/v1/posts/{sample_post.pk}", json=update_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "You can only update your own posts" in response.json()["detail"]

        client.app.dependency_overrides.clear()


class TestDeletePost:
    """Test cases for DELETE /posts/{post_id} endpoint."""

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_delete_post_by_author(
        self, mock_repo_class, client, mock_user, sample_post
    ):
        """Test post deletion by author."""
        sample_post.author_pk = mock_user.pk
        mock_repo = AsyncMock()
        mock_repo.get_by_pk.return_value = sample_post
        mock_repo.update.return_value = sample_post
        mock_repo_class.return_value = mock_repo

        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.delete(f"/api/v1/posts/{sample_post.pk}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_repo.update.assert_called_once()

        client.app.dependency_overrides.clear()

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_delete_post_by_moderator(
        self, mock_repo_class, client, mock_moderator, sample_post
    ):
        """Test post deletion by moderator."""
        mock_repo = AsyncMock()
        mock_repo.get_by_pk.return_value = sample_post
        mock_repo.delete.return_value = True
        mock_repo_class.return_value = mock_repo

        client.app.dependency_overrides[get_current_user] = lambda: mock_moderator

        response = client.delete(f"/api/v1/posts/{sample_post.pk}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        client.app.dependency_overrides.clear()

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_delete_post_insufficient_permissions(
        self, mock_repo_class, client, mock_user, sample_post
    ):
        """Test post deletion with insufficient permissions."""
        mock_repo = AsyncMock()
        mock_repo.get_by_pk.return_value = sample_post
        mock_repo_class.return_value = mock_repo

        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.delete(f"/api/v1/posts/{sample_post.pk}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

        client.app.dependency_overrides.clear()


class TestModerationEndpoints:
    """Test cases for moderation endpoints."""

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_approve_post_success(
        self, mock_repo_class, client, mock_moderator, sample_post
    ):
        """Test successful post approval by moderator."""
        mock_repo = AsyncMock()
        mock_repo.approve_post.return_value = sample_post
        mock_repo_class.return_value = mock_repo

        client.app.dependency_overrides[moderator_dependency] = lambda: mock_moderator

        response = client.patch(f"/api/v1/posts/{sample_post.pk}/approve")

        assert response.status_code == status.HTTP_200_OK
        mock_repo.approve_post.assert_called_once_with(sample_post.pk, None)

        client.app.dependency_overrides.clear()

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_reject_post_success(
        self, mock_repo_class, client, mock_moderator, sample_post
    ):
        """Test successful post rejection by moderator."""
        mock_repo = AsyncMock()
        mock_repo.reject_post.return_value = sample_post
        mock_repo_class.return_value = mock_repo

        client.app.dependency_overrides[moderator_dependency] = lambda: mock_moderator

        response = client.patch(
            f"/api/v1/posts/{sample_post.pk}/reject?overlord_feedback=Not appropriate"
        )

        assert response.status_code == status.HTTP_200_OK
        mock_repo.reject_post.assert_called_once_with(sample_post.pk, "Not appropriate")

        client.app.dependency_overrides.clear()

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_pending_posts_success(
        self, mock_repo_class, client, mock_moderator, sample_post
    ):
        """Test successful retrieval of pending posts by moderator."""
        mock_repo = AsyncMock()
        mock_repo.get_by_status.return_value = [sample_post]
        mock_repo_class.return_value = mock_repo

        client.app.dependency_overrides[moderator_dependency] = lambda: mock_moderator

        response = client.get("/api/v1/posts/pending/list")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        mock_repo.get_by_status.assert_called_once_with(ContentStatus.PENDING, 50, 0)

        client.app.dependency_overrides.clear()

    def test_moderation_endpoints_unauthorized(self, client):
        """Test moderation endpoints without authentication."""
        post_id = uuid4()

        response = client.patch(f"/api/v1/posts/{post_id}/approve")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = client.patch(
            f"/api/v1/posts/{post_id}/reject?overlord_feedback=test"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = client.get("/api/v1/posts/pending/list")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPublicEndpoints:
    """Test cases for public endpoints."""

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_graveyard_posts(
        self, mock_repo_class, client, sample_post_with_author, mock_user
    ):
        """Test retrieval of graveyard posts."""
        mock_repo = AsyncMock()
        mock_repo.get_graveyard_posts_by_author.return_value = [sample_post_with_author]
        mock_repo_class.return_value = mock_repo

        # Override the dependency to provide authenticated user
        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.get("/api/v1/posts/graveyard")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        mock_repo.get_graveyard_posts_by_author.assert_called_once_with(
            mock_user.pk, 50, 0
        )

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_posts_by_author(self, mock_repo_class, client, sample_post_summary):
        """Test retrieval of posts by author."""
        mock_repo = AsyncMock()
        mock_repo.get_by_author.return_value = [sample_post_summary]
        mock_repo_class.return_value = mock_repo

        author_id = uuid4()
        response = client.get(f"/api/v1/posts/author/{author_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["topic_title"] == "Test Topic"
        mock_repo.get_by_author.assert_called_once_with(
            author_id, ContentStatus.APPROVED, 50, 0
        )


class TestValidation:
    """Test cases for input validation."""

    def test_invalid_limit(self, client):
        """Test posts retrieval with invalid limit parameter."""
        response = client.get("/api/v1/posts/?limit=200")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_negative_offset(self, client):
        """Test posts retrieval with negative offset parameter."""
        response = client.get("/api/v1/posts/?offset=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_uuid(self, client):
        """Test retrieval with invalid UUID format."""
        response = client.get("/api/v1/posts/invalid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_search_length(self, client):
        """Test posts search with too long search term."""
        response = client.get("/api/v1/posts/?search=" + "a" * 201)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestChronologicalOrdering:
    """Test cases for chronological ordering by submitted_at field."""

    @pytest.fixture
    def mock_posts_with_times(self):
        """Mock posts with different submission times."""
        base_time = datetime.now(UTC)
        return [
            PostWithAuthor(
                pk=UUID("11111111-1111-1111-1111-111111111111"),
                topic_pk=UUID("22222222-2222-2222-2222-222222222222"),
                parent_post_pk=None,
                author_pk=UUID("33333333-3333-3333-3333-333333333333"),
                author_username="user1",
                content="First post",
                status=ContentStatus.APPROVED,
                overlord_feedback=None,
                submitted_at=base_time,
                approved_at=base_time,
                rejection_reason=None,
                tos_violation=False,
                created_at=base_time,
                updated_at=None,
            ),
            PostWithAuthor(
                pk=UUID("44444444-4444-4444-4444-444444444444"),
                topic_pk=UUID("22222222-2222-2222-2222-222222222222"),
                parent_post_pk=None,
                author_pk=UUID("55555555-5555-5555-5555-555555555555"),
                author_username="user2",
                content="Second post",
                status=ContentStatus.APPROVED,
                overlord_feedback=None,
                submitted_at=base_time + timedelta(minutes=1),
                approved_at=base_time + timedelta(minutes=1),
                rejection_reason=None,
                tos_violation=False,
                created_at=base_time + timedelta(minutes=1),
                updated_at=None,
            ),
            PostWithAuthor(
                pk=UUID("66666666-6666-6666-6666-666666666666"),
                topic_pk=UUID("22222222-2222-2222-2222-222222222222"),
                parent_post_pk=None,
                author_pk=UUID("77777777-7777-7777-7777-777777777777"),
                author_username="user3",
                content="Third post",
                status=ContentStatus.APPROVED,
                overlord_feedback=None,
                submitted_at=base_time + timedelta(minutes=2),
                approved_at=base_time + timedelta(minutes=2),
                rejection_reason=None,
                tos_violation=False,
                created_at=base_time + timedelta(minutes=2),
                updated_at=None,
            ),
        ]

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_posts_ordered_chronologically(
        self, mock_repo_class, client, mock_posts_with_times
    ):
        """Test that posts are returned in chronological order by submitted_at."""
        mock_repo = AsyncMock()
        mock_repo.get_recent_approved_posts.return_value = mock_posts_with_times
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/posts/")
        assert response.status_code == status.HTTP_200_OK

        posts = response.json()
        assert len(posts) == 3

        # Verify chronological order by submitted_at
        assert posts[0]["content"] == "First post"
        assert posts[1]["content"] == "Second post"
        assert posts[2]["content"] == "Third post"

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_topic_posts_ordered_chronologically(
        self, mock_repo_class, client, mock_posts_with_times
    ):
        """Test that posts by topic are returned in chronological order."""
        mock_repo = AsyncMock()
        mock_repo.get_approved_by_topic.return_value = mock_posts_with_times
        mock_repo_class.return_value = mock_repo

        response = client.get(
            "/api/v1/posts/?topic_id=22222222-2222-2222-2222-222222222222"
        )
        assert response.status_code == status.HTTP_200_OK

        posts = response.json()
        assert len(posts) == 3

        # Verify chronological order by submitted_at
        assert posts[0]["content"] == "First post"
        assert posts[1]["content"] == "Second post"
        assert posts[2]["content"] == "Third post"

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_search_posts_ordered_chronologically(
        self, mock_repo_class, client, mock_posts_with_times
    ):
        """Test that search results are returned in chronological order."""
        mock_repo = AsyncMock()
        mock_repo.search_posts.return_value = mock_posts_with_times
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/posts/?search=post")
        assert response.status_code == status.HTTP_200_OK

        posts = response.json()
        assert len(posts) == 3

        # Verify chronological order by submitted_at
        assert posts[0]["content"] == "First post"
        assert posts[1]["content"] == "Second post"
        assert posts[2]["content"] == "Third post"
