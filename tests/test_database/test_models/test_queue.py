"""Tests for queue models."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

import pytest

from pydantic import ValidationError

from therobotoverlord_api.database.models.base import QueueStatus
from therobotoverlord_api.database.models.queue import PostModerationQueue
from therobotoverlord_api.database.models.queue import PostModerationQueueCreate
from therobotoverlord_api.database.models.queue import PrivateMessageQueue
from therobotoverlord_api.database.models.queue import PrivateMessageQueueCreate
from therobotoverlord_api.database.models.queue import QueueItemUpdate
from therobotoverlord_api.database.models.queue import QueueOverview
from therobotoverlord_api.database.models.queue import QueueStatusInfo
from therobotoverlord_api.database.models.queue import QueueWithContent
from therobotoverlord_api.database.models.queue import TopicCreationQueue
from therobotoverlord_api.database.models.queue import TopicCreationQueueCreate


class TestTopicCreationQueue:
    """Test TopicCreationQueue model."""

    def test_topic_creation_queue_creation(self):
        """Test creating a TopicCreationQueue instance."""
        pk = uuid4()
        topic_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)

        queue_item = TopicCreationQueue(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            topic_pk=topic_pk,
            priority_score=50,
            status=QueueStatus.PENDING,
            position_in_queue=1,
            assigned_worker=None,
            entered_queue_at=entered_queue_at,
            started_processing_at=None,
            completed_at=None,
        )

        assert queue_item.pk == pk
        assert queue_item.topic_pk == topic_pk
        assert queue_item.priority_score == 50
        assert queue_item.status == QueueStatus.PENDING
        assert queue_item.position_in_queue == 1
        assert queue_item.assigned_worker is None
        assert queue_item.entered_queue_at == entered_queue_at
        assert queue_item.started_processing_at is None
        assert queue_item.completed_at is None

    def test_topic_creation_queue_processing(self):
        """Test TopicCreationQueue in processing state."""
        pk = uuid4()
        topic_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)
        started_processing_at = datetime.now(UTC)

        queue_item = TopicCreationQueue(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            topic_pk=topic_pk,
            priority_score=75,
            status=QueueStatus.PROCESSING,
            position_in_queue=0,
            assigned_worker="worker-1",
            entered_queue_at=entered_queue_at,
            started_processing_at=started_processing_at,
            completed_at=None,
        )

        assert queue_item.status == QueueStatus.PROCESSING
        assert queue_item.assigned_worker == "worker-1"
        assert queue_item.started_processing_at == started_processing_at
        assert queue_item.position_in_queue == 0

    def test_topic_creation_queue_completed(self):
        """Test TopicCreationQueue in completed state."""
        pk = uuid4()
        topic_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)
        started_processing_at = datetime.now(UTC)
        completed_at = datetime.now(UTC)

        queue_item = TopicCreationQueue(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            topic_pk=topic_pk,
            priority_score=100,
            status=QueueStatus.COMPLETED,
            position_in_queue=0,
            assigned_worker="worker-1",
            entered_queue_at=entered_queue_at,
            started_processing_at=started_processing_at,
            completed_at=completed_at,
        )

        assert queue_item.status == QueueStatus.COMPLETED
        assert queue_item.completed_at == completed_at


class TestTopicCreationQueueCreate:
    """Test TopicCreationQueueCreate model."""

    def test_topic_creation_queue_create_valid(self):
        """Test creating a valid TopicCreationQueueCreate instance."""
        topic_pk = uuid4()

        queue_create = TopicCreationQueueCreate(
            topic_pk=topic_pk,
            priority_score=60,
        )

        assert queue_create.topic_pk == topic_pk
        assert queue_create.priority_score == 60

    def test_topic_creation_queue_create_default_priority(self):
        """Test TopicCreationQueueCreate with default priority."""
        topic_pk = uuid4()

        queue_create = TopicCreationQueueCreate(topic_pk=topic_pk)

        assert queue_create.topic_pk == topic_pk
        assert queue_create.priority_score == 50  # Default value

    def test_topic_creation_queue_create_priority_validation(self):
        """Test priority score validation."""
        topic_pk = uuid4()

        # Test negative priority
        with pytest.raises(ValidationError):
            TopicCreationQueueCreate(
                topic_pk=topic_pk,
                priority_score=-1,
            )

        # Test priority too high
        with pytest.raises(ValidationError):
            TopicCreationQueueCreate(
                topic_pk=topic_pk,
                priority_score=101,
            )


class TestPostModerationQueue:
    """Test PostModerationQueue model."""

    def test_post_moderation_queue_creation(self):
        """Test creating a PostModerationQueue instance."""
        pk = uuid4()
        post_pk = uuid4()
        topic_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)

        queue_item = PostModerationQueue(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            post_pk=post_pk,
            topic_pk=topic_pk,
            priority_score=40,
            status=QueueStatus.PENDING,
            position_in_queue=3,
            assigned_worker=None,
            entered_queue_at=entered_queue_at,
            started_processing_at=None,
            completed_at=None,
        )

        assert queue_item.pk == pk
        assert queue_item.post_pk == post_pk
        assert queue_item.topic_pk == topic_pk
        assert queue_item.priority_score == 40
        assert queue_item.status == QueueStatus.PENDING
        assert queue_item.position_in_queue == 3


class TestPostModerationQueueCreate:
    """Test PostModerationQueueCreate model."""

    def test_post_moderation_queue_create_valid(self):
        """Test creating a valid PostModerationQueueCreate instance."""
        post_pk = uuid4()
        topic_pk = uuid4()

        queue_create = PostModerationQueueCreate(
            post_pk=post_pk,
            topic_pk=topic_pk,
            priority_score=70,
        )

        assert queue_create.post_pk == post_pk
        assert queue_create.topic_pk == topic_pk
        assert queue_create.priority_score == 70


class TestPrivateMessageQueue:
    """Test PrivateMessageQueue model."""

    def test_private_message_queue_creation(self):
        """Test creating a PrivateMessageQueue instance."""
        pk = uuid4()
        message_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)

        queue_item = PrivateMessageQueue(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            message_pk=message_pk,
            conversation_id="conv-123",
            priority_score=80,
            status=QueueStatus.PENDING,
            position_in_queue=2,
            assigned_worker=None,
            entered_queue_at=entered_queue_at,
            started_processing_at=None,
            completed_at=None,
        )

        assert queue_item.pk == pk
        assert queue_item.message_pk == message_pk
        assert queue_item.conversation_id == "conv-123"
        assert queue_item.priority_score == 80
        assert queue_item.position_in_queue == 2


class TestPrivateMessageQueueCreate:
    """Test PrivateMessageQueueCreate model."""

    def test_private_message_queue_create_valid(self):
        """Test creating a valid PrivateMessageQueueCreate instance."""
        message_pk = uuid4()

        queue_create = PrivateMessageQueueCreate(
            message_pk=message_pk,
            conversation_id="conv-456",
            priority_score=90,
        )

        assert queue_create.message_pk == message_pk
        assert queue_create.conversation_id == "conv-456"
        assert queue_create.priority_score == 90


class TestQueueItemUpdate:
    """Test QueueItemUpdate model."""

    def test_queue_item_update_status_only(self):
        """Test updating only status."""
        queue_update = QueueItemUpdate(status=QueueStatus.PROCESSING)

        assert queue_update.status == QueueStatus.PROCESSING
        assert queue_update.assigned_worker is None
        assert queue_update.priority_score is None

    def test_queue_item_update_worker_assignment(self):
        """Test worker assignment update."""
        queue_update = QueueItemUpdate(
            status=QueueStatus.PROCESSING,
            assigned_worker="worker-2",
        )

        assert queue_update.status == QueueStatus.PROCESSING
        assert queue_update.assigned_worker == "worker-2"

    def test_queue_item_update_priority_change(self):
        """Test priority score update."""
        queue_update = QueueItemUpdate(priority_score=95)

        assert queue_update.priority_score == 95
        assert queue_update.status is None
        assert queue_update.assigned_worker is None


class TestQueueStatusInfo:
    """Test QueueStatusInfo model."""

    def test_queue_status_info_creation(self):
        """Test creating QueueStatusInfo instance."""
        queue_status = QueueStatusInfo(
            queue_type="topic_creation",
            total_pending=5,
            total_processing=2,
            average_wait_time_minutes=15,
            oldest_pending_minutes=45,
        )

        assert queue_status.queue_type == "topic_creation"
        assert queue_status.total_pending == 5
        assert queue_status.total_processing == 2
        assert queue_status.average_wait_time_minutes == 15
        assert queue_status.oldest_pending_minutes == 45

    def test_queue_status_info_empty_queue(self):
        """Test QueueStatusInfo for empty queue."""
        queue_status = QueueStatusInfo(
            queue_type="post_moderation",
            total_pending=0,
            total_processing=0,
            average_wait_time_minutes=0,
            oldest_pending_minutes=0,
        )

        assert queue_status.total_pending == 0
        assert queue_status.total_processing == 0
        assert queue_status.average_wait_time_minutes == 0
        assert queue_status.oldest_pending_minutes == 0


class TestQueueOverview:
    """Test QueueOverview model."""

    def test_queue_overview_creation(self):
        """Test creating QueueOverview instance."""
        topic_status = QueueStatusInfo(
            queue_type="topic_creation",
            total_pending=3,
            total_processing=1,
            average_wait_time_minutes=10,
            oldest_pending_minutes=30,
        )

        post_status = QueueStatusInfo(
            queue_type="post_moderation",
            total_pending=8,
            total_processing=3,
            average_wait_time_minutes=5,
            oldest_pending_minutes=20,
        )

        message_status = QueueStatusInfo(
            queue_type="private_message",
            total_pending=2,
            total_processing=0,
            average_wait_time_minutes=8,
            oldest_pending_minutes=15,
        )

        overview = QueueOverview(
            topic_creation_queue=topic_status,
            post_moderation_queue=post_status,
            private_message_queue=message_status,
        )

        assert overview.topic_creation_queue == topic_status
        assert overview.post_moderation_queue == post_status
        assert overview.private_message_queue == message_status


class TestQueueWithContent:
    """Test QueueWithContent model."""

    def test_queue_with_content_topic(self):
        """Test QueueWithContent for topic."""
        pk = uuid4()
        topic_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)

        queue_with_content = QueueWithContent(
            pk=pk,
            queue_type="topic_creation",
            content_pk=topic_pk,
            content_title="Test Topic",
            content_preview="A test topic for discussion...",
            priority_score=60,
            status=QueueStatus.PENDING,
            position_in_queue=1,
            entered_queue_at=entered_queue_at,
            author_username="testuser",
        )

        assert queue_with_content.pk == pk
        assert queue_with_content.queue_type == "topic_creation"
        assert queue_with_content.content_pk == topic_pk
        assert queue_with_content.content_title == "Test Topic"
        assert queue_with_content.content_preview == "A test topic for discussion..."
        assert queue_with_content.author_username == "testuser"

    def test_queue_with_content_post(self):
        """Test QueueWithContent for post."""
        pk = uuid4()
        post_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)

        queue_with_content = QueueWithContent(
            pk=pk,
            queue_type="post_moderation",
            content_pk=post_pk,
            content_title="Re: Test Topic",
            content_preview="This is a reply to the topic...",
            priority_score=40,
            status=QueueStatus.PROCESSING,
            position_in_queue=0,
            entered_queue_at=entered_queue_at,
            author_username="replyuser",
        )

        assert queue_with_content.queue_type == "post_moderation"
        assert queue_with_content.status == QueueStatus.PROCESSING
        assert queue_with_content.position_in_queue == 0
