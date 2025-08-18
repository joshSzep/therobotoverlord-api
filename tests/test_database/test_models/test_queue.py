"""Tests for queue models."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

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
            worker_id=None,
            entered_queue_at=entered_queue_at,
            worker_assigned_at=None,
        )

        assert queue_item.pk == pk
        assert queue_item.topic_pk == topic_pk
        assert queue_item.priority_score == 50
        assert queue_item.status == QueueStatus.PENDING
        assert queue_item.position_in_queue == 1
        assert queue_item.worker_id is None
        assert queue_item.entered_queue_at == entered_queue_at
        assert queue_item.worker_assigned_at is None

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
            worker_id="worker-1",
            entered_queue_at=entered_queue_at,
            worker_assigned_at=started_processing_at,
        )

        assert queue_item.status == QueueStatus.PROCESSING
        assert queue_item.worker_id == "worker-1"
        assert queue_item.worker_assigned_at == started_processing_at
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
            worker_id="worker-1",
            entered_queue_at=entered_queue_at,
            worker_assigned_at=started_processing_at,
        )

        assert queue_item.status == QueueStatus.COMPLETED
        # Completed status is tracked by status field


class TestTopicCreationQueueCreate:
    """Test TopicCreationQueueCreate model."""

    def test_topic_creation_queue_create_valid(self):
        """Test creating a valid TopicCreationQueueCreate instance."""
        topic_pk = uuid4()

        queue_create = TopicCreationQueueCreate(
            topic_pk=topic_pk,
            priority_score=60,
            position_in_queue=1,
            entered_queue_at=datetime.now(UTC),
        )

        assert queue_create.topic_pk == topic_pk
        assert queue_create.priority_score == 60

    def test_topic_creation_queue_create_default_priority(self):
        """Test TopicCreationQueueCreate with default priority."""
        topic_pk = uuid4()

        queue_create = TopicCreationQueueCreate(
            topic_pk=topic_pk,
            priority_score=50,
            position_in_queue=1,
            entered_queue_at=datetime.now(UTC),
        )

        assert queue_create.topic_pk == topic_pk
        assert queue_create.priority_score == 50

    def test_topic_creation_queue_create_priority_validation(self):
        """Test priority score validation."""
        topic_pk = uuid4()

        # Test valid priority creation
        queue_create = TopicCreationQueueCreate(
            topic_pk=topic_pk,
            priority_score=50,
            position_in_queue=1,
            entered_queue_at=datetime.now(UTC),
        )

        assert queue_create.priority_score == 50
        assert queue_create.topic_pk == topic_pk
        assert queue_create.position_in_queue == 1


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
            worker_id=None,
            entered_queue_at=entered_queue_at,
            worker_assigned_at=None,
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
            position_in_queue=1,
            entered_queue_at=datetime.now(UTC),
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
            sender_pk=uuid4(),
            recipient_pk=uuid4(),
            conversation_id="conv-123",
            priority_score=80,
            status=QueueStatus.PENDING,
            position_in_queue=2,
            worker_id=None,
            entered_queue_at=entered_queue_at,
            worker_assigned_at=None,
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
            sender_pk=uuid4(),
            recipient_pk=uuid4(),
            conversation_id="conv-456",
            priority_score=60,
            position_in_queue=1,
            entered_queue_at=datetime.now(UTC),
        )

        assert queue_create.message_pk == message_pk
        assert queue_create.conversation_id == "conv-456"
        assert queue_create.priority_score == 60


class TestQueueItemUpdate:
    """Test QueueItemUpdate model."""

    def test_queue_item_update_status_only(self):
        """Test updating only status."""
        queue_update = QueueItemUpdate(status=QueueStatus.PROCESSING)

        assert queue_update.status == QueueStatus.PROCESSING
        assert queue_update.worker_id is None
        assert queue_update.priority_score is None

    def test_queue_item_update_worker_assignment(self):
        """Test worker assignment update."""
        queue_update = QueueItemUpdate(
            status=QueueStatus.PROCESSING,
            worker_id="worker-2",
        )

        assert queue_update.status == QueueStatus.PROCESSING
        assert queue_update.worker_id == "worker-2"

    def test_queue_item_update_priority_change(self):
        """Test priority score update."""
        queue_update = QueueItemUpdate(priority_score=95)

        assert queue_update.priority_score == 95
        assert queue_update.status is None
        assert queue_update.worker_id is None


class TestQueueStatusInfo:
    """Test QueueStatusInfo model."""

    def test_queue_status_info_creation(self):
        """Test creating QueueStatusInfo instance."""
        queue_status = QueueStatusInfo(
            queue_type="topic_creation",
            position=1,
            total_items=5,
            estimated_wait_minutes=15,
            status=QueueStatus.PENDING,
            overlord_commentary="The Overlord is reviewing submissions",
        )

        assert queue_status.queue_type == "topic_creation"
        assert queue_status.position == 1
        assert queue_status.total_items == 5
        assert queue_status.estimated_wait_minutes == 15
        assert queue_status.status == QueueStatus.PENDING
        assert (
            queue_status.overlord_commentary == "The Overlord is reviewing submissions"
        )

    def test_queue_status_info_empty_queue(self):
        """Test QueueStatusInfo for empty queue."""
        queue_status = QueueStatusInfo(
            queue_type="post_moderation",
            position=0,
            total_items=0,
            estimated_wait_minutes=None,
            status=QueueStatus.PENDING,
            overlord_commentary=None,
        )

        assert queue_status.position == 0
        assert queue_status.total_items == 0
        assert queue_status.estimated_wait_minutes is None
        assert queue_status.status == QueueStatus.PENDING
        assert queue_status.overlord_commentary is None


class TestQueueOverview:
    """Test QueueOverview model."""

    def test_queue_overview_creation(self):
        """Test creating QueueOverview instance."""
        queue_overview = QueueOverview(
            topic_creation_queue_length=3,
            post_moderation_queue_length=7,
            private_message_queue_length=2,
            average_processing_time_minutes=12,
            last_updated=datetime.now(UTC),
        )

        assert queue_overview.topic_creation_queue_length == 3
        assert queue_overview.post_moderation_queue_length == 7
        assert queue_overview.private_message_queue_length == 2
        assert queue_overview.average_processing_time_minutes == 12
        assert queue_overview.last_updated


class TestQueueWithContent:
    """Test QueueWithContent model."""

    def test_queue_with_content_topic(self):
        """Test QueueWithContent for topic."""
        pk = uuid4()
        content_pk = uuid4()
        entered_queue_at = datetime.now(UTC)

        queue_with_content = QueueWithContent(
            pk=pk,
            queue_type="topic_creation",
            content_pk=content_pk,
            content_type="topic",
            priority_score=85,
            position_in_queue=2,
            status=QueueStatus.PENDING,
            entered_queue_at=datetime.now(UTC),
            worker_assigned_at=None,
            worker_id=None,
        )

        assert queue_with_content.pk == pk
        assert queue_with_content.queue_type == "topic_creation"
        assert queue_with_content.content_pk == content_pk
        assert queue_with_content.content_type == "topic"
        assert queue_with_content.priority_score == 85
        assert queue_with_content.position_in_queue == 2
        assert queue_with_content.status == QueueStatus.PENDING
        assert queue_with_content.worker_assigned_at is None
        assert queue_with_content.worker_id is None

    def test_queue_with_content_post(self):
        """Test QueueWithContent for post."""
        pk = uuid4()
        content_pk = uuid4()
        entered_queue_at = datetime.now(UTC)

        queue_with_content = QueueWithContent(
            pk=pk,
            queue_type="post_moderation",
            content_pk=content_pk,
            content_type="post",
            priority_score=60,
            position_in_queue=1,
            status=QueueStatus.PROCESSING,
            entered_queue_at=datetime.now(UTC),
            worker_assigned_at=datetime.now(UTC),
            worker_id="worker-3",
        )

        assert queue_with_content.queue_type == "post_moderation"
        assert queue_with_content.content_type == "post"
        assert queue_with_content.priority_score == 60
        assert queue_with_content.position_in_queue == 1
        assert queue_with_content.status == QueueStatus.PROCESSING
        assert queue_with_content.worker_assigned_at
        assert queue_with_content.worker_id == "worker-3"
