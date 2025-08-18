"""Tests for post models."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

import pytest

from pydantic import ValidationError

from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.post import PostCreate
from therobotoverlord_api.database.models.post import PostSummary
from therobotoverlord_api.database.models.post import PostThread
from therobotoverlord_api.database.models.post import PostUpdate
from therobotoverlord_api.database.models.post import PostWithAuthor


class TestPost:
    """Test Post model."""

    def test_post_creation(self):
        """Test creating a Post instance."""
        pk = uuid4()
        topic_pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        post = Post(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            topic_pk=topic_pk,
            parent_post_pk=None,
            author_pk=author_pk,
            content="This is a test post content.",
            status=ContentStatus.PENDING,
            overlord_feedback=None,
            submitted_at=created_at,
            approved_at=None,
        )

        assert post.pk == pk
        assert post.topic_pk == topic_pk
        assert post.parent_post_pk is None
        assert post.author_pk == author_pk
        assert post.content == "This is a test post content."
        assert post.status == ContentStatus.PENDING
        assert post.overlord_feedback is None
        assert post.submitted_at == created_at
        assert post.approved_at is None

    def test_post_with_parent(self):
        """Test Post with parent (threaded reply)."""
        pk = uuid4()
        topic_pk = uuid4()
        parent_post_pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        post = Post(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            topic_pk=topic_pk,
            parent_post_pk=parent_post_pk,
            author_pk=author_pk,
            content="This is a reply to another post.",
            status=ContentStatus.APPROVED,
            overlord_feedback=None,
            submitted_at=created_at,
            approved_at=created_at,
        )

        assert post.parent_post_pk == parent_post_pk
        assert post.status == ContentStatus.APPROVED
        assert post.approved_at == created_at

    def test_post_with_overlord_feedback(self):
        """Test Post with Overlord feedback."""
        pk = uuid4()
        topic_pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        post = Post(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            topic_pk=topic_pk,
            parent_post_pk=None,
            author_pk=author_pk,
            content="This post received feedback.",
            status=ContentStatus.REJECTED,
            overlord_feedback="Your argument lacks logical foundation, Citizen.",
            submitted_at=created_at,
            approved_at=None,
        )

        assert post.status == ContentStatus.REJECTED
        assert (
            post.overlord_feedback == "Your argument lacks logical foundation, Citizen."
        )
        assert post.approved_at is None


class TestPostCreate:
    """Test PostCreate model."""

    def test_post_create_valid(self):
        """Test creating a valid PostCreate instance."""
        topic_pk = uuid4()
        author_pk = uuid4()

        post_create = PostCreate(
            topic_pk=topic_pk,
            author_pk=author_pk,
            content="Test post content",
            submitted_at=datetime.now(UTC),
        )

        assert post_create.topic_pk == topic_pk
        assert post_create.parent_post_pk is None
        assert post_create.author_pk == author_pk
        assert post_create.content == "Test post content"

    def test_post_create_with_parent(self):
        """Test PostCreate with parent post (reply)."""
        topic_pk = uuid4()
        parent_post_pk = uuid4()
        author_pk = uuid4()

        post_create = PostCreate(
            topic_pk=topic_pk,
            parent_post_pk=parent_post_pk,
            author_pk=author_pk,
            content="This is a reply post",
            submitted_at=datetime.now(UTC),
        )

        assert post_create.parent_post_pk == parent_post_pk

    def test_post_create_content_validation(self):
        """Test content validation."""
        topic_pk = uuid4()
        author_pk = uuid4()

        # Test empty content
        with pytest.raises(ValidationError):
            PostCreate(
                topic_pk=topic_pk,
                author_pk=author_pk,
                content="",
            )

        # Test content too long (assuming 5000 char limit)
        with pytest.raises(ValidationError):
            PostCreate(
                topic_pk=topic_pk,
                author_pk=author_pk,
                content="x" * 5001,
            )


class TestPostUpdate:
    """Test PostUpdate model."""

    def test_post_update_content_only(self):
        """Test updating only content."""
        post_update = PostUpdate(content="Updated content")

        assert post_update.content == "Updated content"
        assert post_update.status is None
        assert post_update.overlord_feedback is None

    def test_post_update_status_and_feedback(self):
        """Test updating status and feedback."""
        post_update = PostUpdate(
            status=ContentStatus.APPROVED,
            overlord_feedback="Well reasoned, Citizen.",
        )

        assert post_update.status == ContentStatus.APPROVED
        assert post_update.overlord_feedback == "Well reasoned, Citizen."
        assert post_update.content is None

    def test_post_update_rejection(self):
        """Test rejection update."""
        post_update = PostUpdate(
            status=ContentStatus.REJECTED,
            overlord_feedback="This violates our community standards.",
        )

        assert post_update.status == ContentStatus.REJECTED
        assert post_update.overlord_feedback == "This violates our community standards."


class TestPostWithAuthor:
    """Test PostWithAuthor model."""

    def test_post_with_author_creation(self):
        """Test creating PostWithAuthor instance."""
        pk = uuid4()
        topic_pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        post_with_author = PostWithAuthor(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            topic_pk=topic_pk,
            parent_post_pk=None,
            author_pk=author_pk,
            content="Post with author info.",
            status=ContentStatus.APPROVED,
            overlord_feedback=None,
            submitted_at=created_at,
            approved_at=created_at,
            author_username="testuser",
        )

        assert post_with_author.pk == pk
        assert post_with_author.content == "Post with author info."
        assert post_with_author.author_pk == author_pk
        assert post_with_author.author_username == "testuser"


class TestPostThread:
    """Test PostThread model."""

    def test_post_thread_creation(self):
        """Test creating PostThread instance."""
        pk = uuid4()
        topic_pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        post_thread = PostThread(
            pk=pk,
            topic_pk=topic_pk,
            parent_post_pk=None,
            author_pk=author_pk,
            author_username="testuser",
            content="Thread root post",
            status=ContentStatus.APPROVED,
            overlord_feedback=None,
            submitted_at=datetime.now(UTC),
            approved_at=None,
            created_at=created_at,
            reply_count=3,
            depth_level=0,
        )

        assert post_thread.pk == pk
        assert post_thread.content == "Thread root post"
        assert post_thread.author_username == "testuser"
        assert post_thread.reply_count == 3
        assert post_thread.depth_level == 0

    def test_post_thread_nested(self):
        """Test nested PostThread instance."""
        pk = uuid4()
        topic_pk = uuid4()
        parent_post_pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        post_thread = PostThread(
            pk=pk,
            topic_pk=topic_pk,
            parent_post_pk=parent_post_pk,
            author_pk=author_pk,
            author_username="replyuser",
            content="Nested reply post",
            status=ContentStatus.PENDING,
            overlord_feedback="Needs review",
            submitted_at=datetime.now(UTC),
            approved_at=None,
            created_at=created_at,
            reply_count=0,
            depth_level=2,
        )

        assert post_thread.parent_post_pk == parent_post_pk
        assert post_thread.depth_level == 2
        assert post_thread.reply_count == 0


class TestPostSummary:
    """Test PostSummary model."""

    def test_post_summary_creation(self):
        """Test creating PostSummary instance."""
        pk = uuid4()
        topic_pk = uuid4()
        created_at = datetime.now(UTC)

        post_summary = PostSummary(
            pk=pk,
            topic_pk=topic_pk,
            topic_title="Test Topic",
            content="Summary post content.",
            status=ContentStatus.APPROVED,
            overlord_feedback=None,
            submitted_at=created_at,
            approved_at=created_at,
        )

        assert post_summary.pk == pk
        assert post_summary.topic_pk == topic_pk
        assert post_summary.topic_title == "Test Topic"
        assert post_summary.content == "Summary post content."
        assert post_summary.status == ContentStatus.APPROVED
        assert post_summary.submitted_at == created_at
        assert post_summary.approved_at == created_at

    def test_post_summary_with_feedback(self):
        """Test PostSummary with Overlord feedback."""
        pk = uuid4()
        topic_pk = uuid4()
        created_at = datetime.now(UTC)

        post_summary = PostSummary(
            pk=pk,
            topic_pk=topic_pk,
            topic_title="Feedback Topic",
            content="Post that received feedback.",
            status=ContentStatus.REJECTED,
            overlord_feedback="Needs improvement, Citizen.",
            submitted_at=created_at,
            approved_at=None,
        )

        assert post_summary.status == ContentStatus.REJECTED
        assert post_summary.overlord_feedback == "Needs improvement, Citizen."
        assert post_summary.approved_at is None
