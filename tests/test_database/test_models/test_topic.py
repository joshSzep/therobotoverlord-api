"""Tests for topic models."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

import pytest

from pydantic_core import ValidationError

from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.topic import Topic
from therobotoverlord_api.database.models.topic import TopicCreate
from therobotoverlord_api.database.models.topic import TopicSummary
from therobotoverlord_api.database.models.topic import TopicUpdate
from therobotoverlord_api.database.models.topic import TopicWithAuthor


class TestTopic:
    """Test Topic model."""

    def test_topic_creation(self):
        """Test creating a Topic instance."""
        pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        topic = Topic(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            title="Test Topic",
            description="A test topic for discussion",
            author_pk=author_pk,
            status=TopicStatus.PENDING_APPROVAL,
            approved_at=None,
            approved_by=None,
            created_by_overlord=False,
        )

        assert topic.pk == pk
        assert topic.title == "Test Topic"
        assert topic.description == "A test topic for discussion"
        assert topic.author_pk == author_pk
        assert topic.status == TopicStatus.PENDING_APPROVAL
        assert topic.created_by_overlord is True
        assert topic.approved_by is None
        assert topic.created_by_overlord is False

    def test_topic_with_approval(self):
        """Test Topic with approval data."""
        pk = uuid4()
        author_pk = uuid4()
        approved_by = uuid4()
        created_at = datetime.now(UTC)
        approved_at = datetime.now(UTC)

        topic = Topic(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            title="Approved Topic",
            description="An approved topic",
            author_pk=author_pk,
            status=TopicStatus.APPROVED,
            approved_at=approved_at,
            approved_by=approved_by,
            created_by_overlord=True,
        )

        assert topic.status == TopicStatus.APPROVED
        assert topic.approved_at == approved_at
        assert topic.approved_by == approved_by

    def test_overlord_created_topic(self):
        """Test Overlord-created topic."""
        pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        topic = Topic(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            title="Overlord Topic",
            description="Created by the Overlord",
            author_pk=author_pk,
            status=TopicStatus.APPROVED,
            approved_at=created_at,
            approved_by=author_pk,
            created_by_overlord=True,
        )

        assert topic.created_by_overlord is True
        assert topic.status == TopicStatus.APPROVED


class TestTopicCreate:
    """Test TopicCreate model."""

    def test_topic_create_valid(self):
        """Test creating a valid TopicCreate instance."""
        author_pk = uuid4()

        topic_create = TopicCreate(
            title="New Topic",
            description="A new topic for discussion",
            author_pk=author_pk,
        )

        assert topic_create.title == "New Topic"
        assert topic_create.description == "A new topic for discussion"
        assert topic_create.author_pk == author_pk

    def test_topic_create_with_overlord_flag(self):
        """Test TopicCreate with overlord_created flag."""
        author_pk = uuid4()

        topic_create = TopicCreate(
            title="Overlord Topic",
            description="Created by the Overlord",
            author_pk=author_pk,
            created_by_overlord=True,
        )

        assert topic_create.created_by_overlord is True

    def test_topic_create_title_validation(self):
        """Test title validation."""
        author_pk = uuid4()

        # Test empty title
        with pytest.raises(ValidationError):
            TopicCreate(
                title="",
                description="Valid description",
                author_pk=author_pk,
            )

    def test_topic_create_description_validation(self):
        """Test description validation."""
        author_pk = uuid4()

        # Test empty description
        with pytest.raises(ValidationError):
            TopicCreate(
                title="Valid Title",
                description="",
                author_pk=author_pk,
            )


class TestTopicUpdate:
    """Test TopicUpdate model."""

    def test_topic_update_partial(self):
        """Test partial update."""
        topic_update = TopicUpdate(title="Updated Title")

        assert topic_update.title == "Updated Title"
        assert topic_update.description is None
        assert topic_update.status is None

    def test_topic_update_full(self):
        """Test full update."""
        approved_by = uuid4()

        topic_update = TopicUpdate(
            title="Updated Title",
            description="Updated description",
            status=TopicStatus.APPROVED,
            approved_by=approved_by,
        )

        assert topic_update.title == "Updated Title"
        assert topic_update.description == "Updated description"
        assert topic_update.status == TopicStatus.APPROVED
        assert topic_update.approved_by == approved_by

    def test_topic_update_status_only(self):
        """Test updating only status."""
        topic_update = TopicUpdate(status=TopicStatus.REJECTED)

        assert topic_update.status == TopicStatus.REJECTED
        assert topic_update.title is None
        assert topic_update.description is None


class TestTopicWithAuthor:
    """Test TopicWithAuthor model."""

    def test_topic_with_author_creation(self):
        """Test creating TopicWithAuthor instance."""
        pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        topic_with_author = TopicWithAuthor(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            title="Topic with Author",
            description="A topic with author info",
            author_pk=author_pk,
            status=TopicStatus.APPROVED,
            approved_at=None,
            approved_by=None,
            created_by_overlord=False,
            author_username="testuser",
        )

        assert topic_with_author.pk == pk
        assert topic_with_author.title == "Topic with Author"
        assert topic_with_author.author_pk == author_pk
        assert topic_with_author.author_username == "testuser"


class TestTopicSummary:
    """Test TopicSummary model."""

    def test_topic_summary_creation(self):
        """Test creating TopicSummary instance."""
        pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        topic_summary = TopicSummary(
            pk=pk,
            title="Test Topic",
            description="Test description",
            author_username="testuser",
            created_by_overlord=False,
            status=TopicStatus.APPROVED,
            created_at=created_at,
            post_count=5,
        )

        assert topic_summary.title == "Test Topic"
        assert topic_summary.description == "Test description"
        assert topic_summary.status == TopicStatus.APPROVED
        assert topic_summary.created_at == created_at
        assert topic_summary.post_count == 5

    def test_topic_summary_minimal(self):
        """Test TopicSummary with minimal data."""
        pk = uuid4()
        author_pk = uuid4()
        created_at = datetime.now(UTC)

        topic_summary = TopicSummary(
            pk=pk,
            title="Minimal Topic",
            description="Minimal description",
            author_username=None,
            created_by_overlord=True,
            status=TopicStatus.PENDING_APPROVAL,
            created_at=created_at,
            post_count=0,
        )

        assert topic_summary.title == "Minimal Topic"
        assert topic_summary.status == TopicStatus.PENDING_APPROVAL
        assert topic_summary.post_count == 0
