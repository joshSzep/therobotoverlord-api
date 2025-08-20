"""Tests for ToS screening and dual-queue system."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi import status
from fastapi.testclient import TestClient

from therobotoverlord_api.api.posts import _check_tos_violation_placeholder
from therobotoverlord_api.api.posts import router as posts_router
from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.post import PostWithAuthor
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserRole


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
        created_at=datetime.now(UTC),
        updated_at=None,
    )


class TestTosScreeningFlow:
    """Test ToS screening and dual-queue system."""

    @patch("therobotoverlord_api.api.posts.get_queue_service")
    @patch("therobotoverlord_api.api.posts.get_loyalty_score_service")
    @patch("therobotoverlord_api.api.posts.PostRepository")
    @patch("therobotoverlord_api.api.posts._check_tos_violation_placeholder")
    def test_post_creation_with_tos_pass(
        self,
        mock_tos_check,
        mock_repo_class,
        mock_loyalty_service,
        mock_queue_service,
        client,
        mock_user,
    ):
        """Test post creation when ToS screening passes."""
        # Mock ToS check to pass
        mock_tos_check.return_value = False

        # Mock repository
        mock_repo = AsyncMock()
        topic_pk = uuid4()
        post_pk = uuid4()
        submitted_post = Post(
            pk=post_pk,
            topic_pk=topic_pk,
            author_pk=mock_user.pk,
            content="Clean content",
            status=ContentStatus.SUBMITTED,
            created_at=datetime.now(UTC),
            updated_at=None,
            submitted_at=datetime.now(UTC),
            approved_at=None,
            overlord_feedback=None,
            rejection_reason=None,
            parent_post_pk=None,
        )
        in_transit_post = Post(
            pk=post_pk,
            topic_pk=topic_pk,
            author_pk=mock_user.pk,
            content="Clean content",
            status=ContentStatus.IN_TRANSIT,
            created_at=submitted_post.created_at,
            updated_at=datetime.now(UTC),
            submitted_at=submitted_post.submitted_at,
            approved_at=None,
            overlord_feedback=None,
            rejection_reason=None,
            parent_post_pk=None,
        )

        # Configure async mocks to return proper Post objects
        mock_repo.create_from_dict = AsyncMock(return_value=submitted_post)
        mock_repo.update = AsyncMock(return_value=in_transit_post)
        mock_repo_class.return_value = mock_repo

        # Mock loyalty service
        mock_loyalty_service_instance = AsyncMock()
        mock_loyalty_service.return_value = mock_loyalty_service_instance

        # Mock queue service
        mock_queue_service_instance = AsyncMock()
        mock_queue_service_instance.add_post_to_queue.return_value = "queue_id_123"
        mock_queue_service.return_value = mock_queue_service_instance

        # Override dependency
        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        # Create post
        response = client.post(
            "/api/v1/posts/",
            json={
                "topic_pk": str(topic_pk),
                "parent_post_pk": None,
                "author_pk": str(mock_user.pk),
                "content": "Clean content",
                "submitted_at": datetime.now(UTC).isoformat(),
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        post_data = response.json()
        assert post_data["status"] == "in_transit"
        assert post_data["content"] == "Clean content"

        # Clean up
        client.app.dependency_overrides.clear()

        # Verify ToS check was called
        mock_tos_check.assert_called_once_with("Clean content")

        # Verify post was created with SUBMITTED status initially
        mock_repo.create_from_dict.assert_called_once()
        create_args = mock_repo.create_from_dict.call_args[0][0]
        assert create_args["status"] == ContentStatus.SUBMITTED

        # Verify post was updated to IN_TRANSIT after ToS pass
        mock_repo.update.assert_called_once()

    @patch("therobotoverlord_api.api.posts.PostRepository")
    @patch("therobotoverlord_api.api.posts._check_tos_violation_placeholder")
    def test_post_creation_with_tos_violation(
        self, mock_tos_check, mock_repo_class, client, mock_user
    ):
        """Test post creation when ToS screening fails."""
        # Mock ToS check to fail
        mock_tos_check.return_value = True

        # Mock repository
        mock_repo = AsyncMock()
        topic_pk = uuid4()
        post_pk = uuid4()
        submitted_post = Post(
            pk=post_pk,
            topic_pk=topic_pk,
            author_pk=mock_user.pk,
            content="Violating content",
            status=ContentStatus.SUBMITTED,
            created_at=datetime.now(UTC),
            updated_at=None,
            submitted_at=datetime.now(UTC),
            approved_at=None,
            overlord_feedback=None,
            rejection_reason=None,
            parent_post_pk=None,
        )
        tos_violation_post = Post(
            pk=post_pk,
            topic_pk=topic_pk,
            author_pk=mock_user.pk,
            content="Violating content",
            status=ContentStatus.TOS_VIOLATION,
            created_at=submitted_post.created_at,
            updated_at=datetime.now(UTC),
            submitted_at=submitted_post.submitted_at,
            approved_at=None,
            overlord_feedback=None,
            rejection_reason="Terms of Service violation detected",
            parent_post_pk=None,
        )

        # Configure async mocks to return proper Post objects
        mock_repo.create_from_dict = AsyncMock(return_value=submitted_post)
        mock_repo.update = AsyncMock(return_value=tos_violation_post)
        mock_repo_class.return_value = mock_repo

        # Override dependency
        client.app.dependency_overrides[get_current_user] = lambda: mock_user

        # Create post
        response = client.post(
            "/api/v1/posts/",
            json={
                "topic_pk": str(topic_pk),
                "parent_post_pk": None,
                "author_pk": str(mock_user.pk),
                "content": "Violating content",
                "submitted_at": datetime.now(UTC).isoformat(),
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_data = response.json()
        assert error_data["detail"]["error"] == "TOS_VIOLATION"
        assert "Terms of Service" in error_data["detail"]["message"]

        # Clean up
        client.app.dependency_overrides.clear()

        # Verify ToS check was called
        mock_tos_check.assert_called_once_with("Violating content")

        # Verify post was updated to TOS_VIOLATION status
        mock_repo.update.assert_called_once()
        update_args = mock_repo.update.call_args[0][1]
        assert update_args.status == ContentStatus.TOS_VIOLATION
        assert update_args.rejection_reason == "Terms of Service violation detected"

    @patch("therobotoverlord_api.api.posts.PostRepository")
    def test_get_submitted_posts_endpoint(self, mock_repo_class, client):
        """Test /posts/submitted endpoint."""
        # Mock repository
        mock_repo = AsyncMock()
        submitted_posts = [
            PostWithAuthor(
                pk=uuid4(),
                topic_pk=uuid4(),
                parent_post_pk=None,
                author_pk=uuid4(),
                author_username="user1",
                content="Awaiting ToS screening",
                status=ContentStatus.SUBMITTED,
                overlord_feedback=None,
                submitted_at=datetime.now(UTC),
                approved_at=None,
                rejection_reason=None,
                created_at=datetime.now(UTC),
                updated_at=None,
            )
        ]
        mock_repo.get_submitted_posts.return_value = submitted_posts
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/posts/submitted")
        assert response.status_code == status.HTTP_200_OK

        posts_data = response.json()
        assert len(posts_data) == 1
        assert posts_data[0]["status"] == "submitted"
        assert posts_data[0]["content"] == "Awaiting ToS screening"

        mock_repo.get_submitted_posts.assert_called_once_with(50, 0)

    def test_tos_violation_placeholder_function(self):
        """Test the placeholder ToS violation checker."""
        # Test that placeholder always returns False (passes)
        assert _check_tos_violation_placeholder("This is test content") is False
        assert _check_tos_violation_placeholder("Some other content") is False
        assert _check_tos_violation_placeholder("") is False


class TestContentStatusEnum:
    """Test ContentStatus enum includes new TOS_VIOLATION status."""

    def test_tos_violation_status_exists(self):
        """Test that TOS_VIOLATION status is available."""
        assert hasattr(ContentStatus, "TOS_VIOLATION")
        assert ContentStatus.TOS_VIOLATION == "tos_violation"

    def test_all_statuses_available(self):
        """Test that all expected statuses are available."""
        expected_statuses = {
            "SUBMITTED",
            "PENDING",
            "IN_TRANSIT",
            "APPROVED",
            "REJECTED",
            "TOS_VIOLATION",
        }

        actual_statuses = {status.name for status in ContentStatus}
        assert actual_statuses == expected_statuses
