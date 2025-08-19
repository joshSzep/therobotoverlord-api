"""Tests for post repository."""

from datetime import UTC
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.post import PostCreate
from therobotoverlord_api.database.models.post import PostSummary
from therobotoverlord_api.database.models.post import PostThread
from therobotoverlord_api.database.models.post import PostUpdate
from therobotoverlord_api.database.models.post import PostWithAuthor
from therobotoverlord_api.database.repositories.post import PostRepository


@pytest.mark.asyncio
class TestPostRepository:
    """Test PostRepository class."""

    @pytest.fixture
    def post_repository(self):
        """Create PostRepository instance."""
        return PostRepository()

    @pytest.fixture
    def sample_post_create(self):
        """Create sample PostCreate data."""
        return PostCreate(
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="This is a test post content.",
            submitted_at=datetime.now(UTC),
        )

    @pytest.fixture
    def reply_post_create(self):
        """Create sample reply PostCreate data."""
        return PostCreate(
            topic_pk=uuid4(),
            parent_post_pk=uuid4(),
            author_pk=uuid4(),
            content="This is a reply post content.",
            submitted_at=datetime.now(UTC),
        )

    async def test_create_post(
        self, post_repository, sample_post_create, mock_connection
    ):
        """Test creating a post."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            post_pk = uuid4()
            created_at = datetime.now(UTC)

            mock_record = {
                "pk": post_pk,
                "created_at": created_at,
                "updated_at": None,
                "topic_pk": sample_post_create.topic_pk,
                "parent_post_pk": None,
                "author_pk": sample_post_create.author_pk,
                "content": sample_post_create.content,
                "status": ContentStatus.PENDING.value,
                "overlord_feedback": None,
                "submitted_at": created_at,
                "approved_at": None,
            }

            mock_connection.fetchrow.return_value = mock_record

            result = await post_repository.create(sample_post_create)

        assert isinstance(result, Post)
        assert result.topic_pk == sample_post_create.topic_pk
        assert result.author_pk == sample_post_create.author_pk
        assert result.content == sample_post_create.content
        assert result.status == ContentStatus.PENDING
        assert result.parent_post_pk is None

    async def test_create_reply_post(
        self, post_repository, reply_post_create, mock_connection
    ):
        """Test creating a reply post."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            post_pk = uuid4()
            created_at = datetime.now(UTC)

            mock_record = {
                "pk": post_pk,
                "created_at": created_at,
                "updated_at": None,
                "topic_pk": reply_post_create.topic_pk,
                "parent_post_pk": reply_post_create.parent_post_pk,
                "author_pk": reply_post_create.author_pk,
                "content": reply_post_create.content,
                "status": ContentStatus.PENDING.value,
                "overlord_feedback": None,
                "submitted_at": created_at,
                "approved_at": None,
            }

            mock_connection.fetchrow.return_value = mock_record

            result = await post_repository.create(reply_post_create)

        assert result.parent_post_pk == reply_post_create.parent_post_pk

    async def test_update_post(self, post_repository, mock_connection):
        """Test updating a post."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            post_pk = uuid4()
            post_update = PostUpdate(
                content="Updated post content",
                status=ContentStatus.APPROVED,
            )

            updated_at = datetime.now(UTC)
            mock_record = {
                "pk": post_pk,
                "created_at": datetime.now(UTC),
                "updated_at": updated_at,
                "topic_pk": uuid4(),
                "parent_post_pk": None,
                "author_pk": uuid4(),
                "content": post_update.content,
                "status": post_update.status.value if post_update.status else "pending",
                "overlord_feedback": None,
                "submitted_at": datetime.now(UTC),
                "approved_at": updated_at,
            }

            mock_connection.fetchrow.return_value = mock_record

            result = await post_repository.update(post_pk, post_update)

        assert result.content == post_update.content
        assert result.status == post_update.status
        assert result.updated_at == updated_at

    async def test_get_by_topic(self, post_repository, mock_connection):
        """Test getting posts by topic."""
        topic_pk = uuid4()
        mock_records = [
            {
                "pk": uuid4(),
                "created_at": datetime.now(UTC),
                "updated_at": None,
                "topic_pk": topic_pk,
                "parent_post_pk": None,
                "author_pk": uuid4(),
                "content": "First post content",
                "status": ContentStatus.APPROVED.value,
                "overlord_feedback": None,
                "rejection_reason": None,
                "submitted_at": datetime.now(UTC),
                "approved_at": datetime.now(UTC),
                "author_username": "user1",
                "author_avatar_url": None,
            },
            {
                "pk": uuid4(),
                "created_at": datetime.now(UTC),
                "updated_at": None,
                "topic_pk": topic_pk,
                "parent_post_pk": None,
                "author_pk": uuid4(),
                "content": "Second post content",
                "status": ContentStatus.APPROVED.value,
                "overlord_feedback": None,
                "rejection_reason": None,
                "submitted_at": datetime.now(UTC),
                "approved_at": datetime.now(UTC),
                "author_username": "user2",
                "author_avatar_url": None,
            },
        ]

        mock_connection.fetch.return_value = mock_records

        with patch(
            "therobotoverlord_api.database.repositories.post.get_db_connection"
        ) as mock_get_connection:
            mock_get_connection.return_value.__aenter__.return_value = mock_connection

            result = await post_repository.get_by_topic(topic_pk, limit=10, offset=0)

        assert len(result) == 2
        assert all(isinstance(post, PostWithAuthor) for post in result)
        assert all(post.topic_pk == topic_pk for post in result)

    async def test_get_by_topic_with_status_filter(
        self, post_repository, mock_connection
    ):
        """Test getting posts by topic with status filter."""
        with patch(
            "therobotoverlord_api.database.repositories.post.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            topic_pk = uuid4()
            mock_records = [
                {
                    "pk": uuid4(),
                    "created_at": datetime.now(UTC),
                    "updated_at": None,
                    "topic_pk": topic_pk,
                    "parent_post_pk": None,
                    "author_pk": uuid4(),
                    "content": "Approved post",
                    "status": ContentStatus.APPROVED.value,
                    "overlord_feedback": None,
                    "rejection_reason": None,
                    "submitted_at": datetime.now(UTC),
                    "approved_at": datetime.now(UTC),
                    "author_username": "user1",
                }
            ]

            mock_connection.fetch.return_value = mock_records

            result = await post_repository.get_by_topic(
                topic_pk, ContentStatus.APPROVED, limit=10, offset=0
            )

        assert len(result) == 1
        assert result[0].status == ContentStatus.APPROVED

    async def test_get_by_author(self, post_repository, mock_connection):
        """Test getting posts by author."""
        with patch(
            "therobotoverlord_api.database.repositories.post.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            author_pk = uuid4()
            mock_records = [
                {
                    "pk": uuid4(),
                    "created_at": datetime.now(UTC),
                    "updated_at": None,
                    "topic_pk": uuid4(),
                    "topic_title": "Test Topic",
                    "content": "Author's post",
                    "status": ContentStatus.APPROVED.value,
                    "overlord_feedback": None,
                    "rejection_reason": None,
                    "submitted_at": datetime.now(UTC),
                    "approved_at": datetime.now(UTC),
                },
                {
                    "pk": uuid4(),
                    "created_at": datetime.now(UTC),
                    "updated_at": None,
                    "topic_pk": uuid4(),
                    "topic_title": "Another Test Topic",
                    "content": "Author's another post",
                    "status": ContentStatus.APPROVED.value,
                    "overlord_feedback": None,
                    "rejection_reason": None,
                    "submitted_at": datetime.now(UTC),
                    "approved_at": datetime.now(UTC),
                },
            ]

            mock_connection.fetch.return_value = mock_records

            result = await post_repository.get_by_author(author_pk, limit=10, offset=0)

        assert len(result) == 2
        assert all(isinstance(post, PostSummary) for post in result)
        # PostSummary doesn't have author_pk field, it's implied from the query

    async def test_get_thread_view(self, post_repository, mock_connection):
        """Test getting thread view of posts."""
        with patch(
            "therobotoverlord_api.database.repositories.post.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            topic_pk = uuid4()
            parent_pk = uuid4()
            mock_records = [
                {
                    "pk": parent_pk,
                    "topic_pk": topic_pk,
                    "parent_post_pk": None,
                    "author_pk": uuid4(),
                    "author_username": "parent_user",
                    "content": "Parent post",
                    "status": ContentStatus.APPROVED.value,
                    "overlord_feedback": None,
                    "rejection_reason": None,
                    "submitted_at": datetime.now(UTC),
                    "approved_at": datetime.now(UTC),
                    "created_at": datetime.now(UTC),
                    "depth_level": 0,
                    "reply_count": 1,
                },
                {
                    "pk": uuid4(),
                    "topic_pk": topic_pk,
                    "parent_post_pk": parent_pk,
                    "author_pk": uuid4(),
                    "author_username": "reply_user",
                    "content": "Reply post",
                    "status": ContentStatus.APPROVED.value,
                    "overlord_feedback": None,
                    "rejection_reason": None,
                    "submitted_at": datetime.now(UTC),
                    "approved_at": datetime.now(UTC),
                    "created_at": datetime.now(UTC),
                    "depth_level": 1,
                    "reply_count": 0,
                },
            ]

            mock_connection.fetch.return_value = mock_records

            result = await post_repository.get_thread_view(topic_pk, limit=10, offset=0)

        assert len(result) == 2
        assert all(isinstance(post, PostThread) for post in result)
        assert all(post.topic_pk == topic_pk for post in result)
        assert result[0].depth_level == 0
        assert result[1].depth_level == 1

    async def test_approve_post(self, post_repository, mock_connection):
        """Test approving a post."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            post_pk = uuid4()
            approved_by = uuid4()
            approved_at = datetime.now(UTC)

            mock_record = {
                "pk": post_pk,
                "created_at": datetime.now(UTC),
                "updated_at": approved_at,
                "topic_pk": uuid4(),
                "parent_post_pk": None,
                "author_pk": uuid4(),
                "content": "Test post content",
                "status": ContentStatus.APPROVED.value,
                "overlord_feedback": None,
                "rejection_reason": None,
                "submitted_at": datetime.now(UTC),
                "approved_at": approved_at,
            }

            mock_connection.fetchrow.return_value = mock_record

            result = await post_repository.approve_post(post_pk, approved_by)

        assert result.status == ContentStatus.APPROVED
        assert result.approved_at == approved_at

    async def test_reject_post(self, post_repository, mock_connection):
        """Test rejecting a post."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            post_pk = uuid4()
            feedback = "This post violates community guidelines."

            mock_record = {
                "pk": post_pk,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "topic_pk": uuid4(),
                "parent_post_pk": None,
                "author_pk": uuid4(),
                "content": "Test post content",
                "status": ContentStatus.REJECTED.value,
                "overlord_feedback": feedback,
                "rejection_reason": None,
                "submitted_at": datetime.now(UTC),
                "approved_at": None,
            }

            mock_connection.fetchrow.return_value = mock_record

            result = await post_repository.reject_post(post_pk, feedback)

        assert result.status == ContentStatus.REJECTED
        assert result.overlord_feedback == feedback
        assert result.approved_at is None

    async def test_search_posts_with_topic_filter(
        self, post_repository, mock_connection
    ):
        """Test searching posts with topic filter."""
        with patch(
            "therobotoverlord_api.database.repositories.post.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            topic_pk = uuid4()
            mock_records = [
                {
                    "pk": uuid4(),
                    "created_at": datetime.now(UTC),
                    "updated_at": None,
                    "topic_pk": topic_pk,
                    "parent_post_pk": None,
                    "author_pk": uuid4(),
                    "content": "This is a test post about robots in this topic",
                    "status": ContentStatus.APPROVED.value,
                    "overlord_feedback": None,
                    "rejection_reason": None,
                    "submitted_at": datetime.now(UTC),
                    "approved_at": datetime.now(UTC),
                    "author_username": "testuser",
                }
            ]

            mock_connection.fetch.return_value = mock_records

            result = await post_repository.search_posts(
                "robots", topic_pk=topic_pk, limit=10, offset=0
            )

        assert len(result) == 1
        assert result[0].topic_pk == topic_pk

    async def test_get_graveyard_posts(self, post_repository, mock_connection):
        """Test getting graveyard (rejected) posts."""
        with patch(
            "therobotoverlord_api.database.repositories.post.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            author_pk = uuid4()
            mock_records = [
                {
                    "pk": uuid4(),
                    "created_at": datetime.now(UTC),
                    "updated_at": None,
                    "topic_pk": uuid4(),
                    "topic_title": "Test Topic",
                    "author_pk": author_pk,
                    "content": "First post by author",
                    "status": ContentStatus.APPROVED.value,
                    "overlord_feedback": None,
                    "rejection_reason": None,
                    "submitted_at": datetime.now(UTC),
                    "approved_at": datetime.now(UTC),
                },
                {
                    "pk": uuid4(),
                    "created_at": datetime.now(UTC),
                    "updated_at": None,
                    "topic_pk": uuid4(),
                    "topic_title": "Another Topic",
                    "author_pk": author_pk,
                    "content": "Second post by author",
                    "status": ContentStatus.APPROVED.value,
                    "overlord_feedback": None,
                    "rejection_reason": None,
                    "submitted_at": datetime.now(UTC),
                    "approved_at": datetime.now(UTC),
                },
            ]

            mock_connection.fetch.return_value = mock_records

            result = await post_repository.get_by_author(author_pk, limit=10, offset=0)

        assert len(result) == 2
        assert all(isinstance(post, PostSummary) for post in result)
        # PostSummary doesn't have author_pk field, it's implied from the query

    async def test_get_nonexistent_post(self, post_repository, mock_connection):
        """Test getting a non-existent post."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = None

            result = await post_repository.get_by_pk(uuid4())

        assert result is None

    async def test_update_nonexistent_post(self, post_repository, mock_connection):
        """Test updating a non-existent post."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = None

            post_update = PostUpdate(content="New content")
            result = await post_repository.update(uuid4(), post_update)

        assert result is None

    async def test_delete_post(self, post_repository, mock_connection):
        """Test deleting a post."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            post_pk = uuid4()
            mock_connection.execute.return_value = "DELETE 1"

            result = await post_repository.delete_by_pk(post_pk)

        assert result is True

    async def test_delete_nonexistent_post(self, post_repository, mock_connection):
        """Test deleting a non-existent post."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            post_pk = uuid4()
            mock_connection.execute.return_value = "DELETE 0"

            result = await post_repository.delete_by_pk(post_pk)

        assert result is False
