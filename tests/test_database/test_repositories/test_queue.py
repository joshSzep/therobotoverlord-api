"""Tests for queue repositories."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

import pytest

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
from therobotoverlord_api.database.repositories.queue import (
    PostModerationQueueRepository,
)
from therobotoverlord_api.database.repositories.queue import (
    PrivateMessageQueueRepository,
)
from therobotoverlord_api.database.repositories.queue import QueueOverviewRepository
from therobotoverlord_api.database.repositories.queue import (
    TopicCreationQueueRepository,
)


@pytest.mark.asyncio
class TestTopicCreationQueueRepository:
    """Test TopicCreationQueueRepository class."""

    @pytest.fixture
    async def queue_repository(self):
        """Create TopicCreationQueueRepository instance."""
        return TopicCreationQueueRepository()

    @pytest.fixture
    def sample_queue_create(self):
        """Create sample TopicCreationQueueCreate data."""
        return TopicCreationQueueCreate(
            topic_pk=uuid4(),
            priority_score=60,
        )

    async def test_create_queue_item(
        self, queue_repository, sample_queue_create, mock_db_connection
    ):
        """Test creating a queue item."""
        queue_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)

        mock_record = {
            "pk": queue_pk,
            "created_at": created_at,
            "updated_at": None,
            "topic_pk": sample_queue_create.topic_pk,
            "priority_score": sample_queue_create.priority_score,
            "status": QueueStatus.PENDING.value,
            "position_in_queue": 1,
            "assigned_worker": None,
            "entered_queue_at": entered_queue_at,
            "started_processing_at": None,
            "completed_at": None,
        }

        mock_db_connection.fetchrow.return_value = mock_record

        result = await queue_repository.create(sample_queue_create)

        assert isinstance(result, TopicCreationQueue)
        assert result.topic_pk == sample_queue_create.topic_pk
        assert result.priority_score == sample_queue_create.priority_score
        assert result.status == QueueStatus.PENDING

    async def test_get_queue_position(self, queue_repository, mock_db_connection):
        """Test getting queue position."""
        topic_pk = uuid4()
        mock_db_connection.fetchval.return_value = 3

        result = await queue_repository.get_queue_position(topic_pk)

        assert result == 3

    async def test_get_queue_position_not_found(
        self, queue_repository, mock_db_connection
    ):
        """Test getting queue position for non-existent item."""
        topic_pk = uuid4()
        mock_db_connection.fetchval.return_value = None

        result = await queue_repository.get_queue_position(topic_pk)

        assert result is None

    async def test_update_queue_positions(self, queue_repository, mock_db_connection):
        """Test updating queue positions."""
        mock_db_connection.execute.return_value = "UPDATE 5"

        await queue_repository.update_queue_positions()

        mock_db_connection.execute.assert_called_once()

    async def test_get_next_pending_item(self, queue_repository, mock_db_connection):
        """Test getting next pending item."""
        mock_record = {
            "pk": uuid4(),
            "created_at": datetime.now(UTC),
            "updated_at": None,
            "topic_pk": uuid4(),
            "priority_score": 80,
            "status": QueueStatus.PENDING.value,
            "position_in_queue": 1,
            "assigned_worker": None,
            "entered_queue_at": datetime.now(UTC),
            "started_processing_at": None,
            "completed_at": None,
        }

        mock_db_connection.fetchrow.return_value = mock_record

        result = await queue_repository.get_next_pending_item()

        assert isinstance(result, TopicCreationQueue)
        assert result.status == QueueStatus.PENDING
        assert result.position_in_queue == 1

    async def test_get_next_pending_item_empty_queue(
        self, queue_repository, mock_db_connection
    ):
        """Test getting next pending item from empty queue."""
        mock_db_connection.fetchrow.return_value = None

        result = await queue_repository.get_next_pending_item()

        assert result is None

    async def test_update_queue_item(self, queue_repository, mock_db_connection):
        """Test updating a queue item."""
        queue_pk = uuid4()
        queue_update = QueueItemUpdate(
            status=QueueStatus.PROCESSING,
            assigned_worker="worker-1",
        )

        updated_at = datetime.now(UTC)
        mock_record = {
            "pk": queue_pk,
            "created_at": datetime.now(UTC),
            "updated_at": updated_at,
            "topic_pk": uuid4(),
            "priority_score": 60,
            "status": QueueStatus.PROCESSING.value,
            "position_in_queue": 0,
            "assigned_worker": "worker-1",
            "entered_queue_at": datetime.now(UTC),
            "started_processing_at": updated_at,
            "completed_at": None,
        }

        mock_db_connection.fetchrow.return_value = mock_record

        result = await queue_repository.update(queue_pk, queue_update)

        assert result.status == QueueStatus.PROCESSING
        assert result.assigned_worker == "worker-1"


@pytest.mark.asyncio
class TestPostModerationQueueRepository:
    """Test PostModerationQueueRepository class."""

    @pytest.fixture
    async def queue_repository(self):
        """Create PostModerationQueueRepository instance."""
        return PostModerationQueueRepository()

    @pytest.fixture
    def sample_queue_create(self):
        """Create sample PostModerationQueueCreate data."""
        return PostModerationQueueCreate(
            post_pk=uuid4(),
            topic_pk=uuid4(),
            priority_score=70,
        )

    async def test_create_queue_item(
        self, queue_repository, sample_queue_create, mock_db_connection
    ):
        """Test creating a post moderation queue item."""
        queue_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)

        mock_record = {
            "pk": queue_pk,
            "created_at": created_at,
            "updated_at": None,
            "post_pk": sample_queue_create.post_pk,
            "topic_pk": sample_queue_create.topic_pk,
            "priority_score": sample_queue_create.priority_score,
            "status": QueueStatus.PENDING.value,
            "position_in_queue": 2,
            "assigned_worker": None,
            "entered_queue_at": entered_queue_at,
            "started_processing_at": None,
            "completed_at": None,
        }

        mock_db_connection.fetchrow.return_value = mock_record

        result = await queue_repository.create(sample_queue_create)

        assert isinstance(result, PostModerationQueue)
        assert result.post_pk == sample_queue_create.post_pk
        assert result.topic_pk == sample_queue_create.topic_pk

    async def test_get_queue_position_by_topic(
        self, queue_repository, mock_db_connection
    ):
        """Test getting queue position by topic."""
        post_pk = uuid4()
        topic_pk = uuid4()
        mock_db_connection.fetchval.return_value = 2

        result = await queue_repository.get_queue_position_by_topic(post_pk, topic_pk)

        assert result == 2

    async def test_update_queue_positions_by_topic(
        self, queue_repository, mock_db_connection
    ):
        """Test updating queue positions by topic."""
        topic_pk = uuid4()
        mock_db_connection.execute.return_value = "UPDATE 3"

        await queue_repository.update_queue_positions_by_topic(topic_pk)

        mock_db_connection.execute.assert_called_once()

    async def test_get_next_pending_item_by_topic(
        self, queue_repository, mock_db_connection
    ):
        """Test getting next pending item by topic."""
        topic_pk = uuid4()
        mock_record = {
            "pk": uuid4(),
            "created_at": datetime.now(UTC),
            "updated_at": None,
            "post_pk": uuid4(),
            "topic_pk": topic_pk,
            "priority_score": 75,
            "status": QueueStatus.PENDING.value,
            "position_in_queue": 1,
            "assigned_worker": None,
            "entered_queue_at": datetime.now(UTC),
            "started_processing_at": None,
            "completed_at": None,
        }

        mock_db_connection.fetchrow.return_value = mock_record

        result = await queue_repository.get_next_pending_item_by_topic(topic_pk)

        assert isinstance(result, PostModerationQueue)
        assert result.topic_pk == topic_pk


@pytest.mark.asyncio
class TestPrivateMessageQueueRepository:
    """Test PrivateMessageQueueRepository class."""

    @pytest.fixture
    async def queue_repository(self):
        """Create PrivateMessageQueueRepository instance."""
        return PrivateMessageQueueRepository()

    @pytest.fixture
    def sample_queue_create(self):
        """Create sample PrivateMessageQueueCreate data."""
        return PrivateMessageQueueCreate(
            message_pk=uuid4(),
            conversation_id="conv-123",
            priority_score=85,
        )

    async def test_create_queue_item(
        self, queue_repository, sample_queue_create, mock_db_connection
    ):
        """Test creating a private message queue item."""
        queue_pk = uuid4()
        created_at = datetime.now(UTC)
        entered_queue_at = datetime.now(UTC)

        mock_record = {
            "pk": queue_pk,
            "created_at": created_at,
            "updated_at": None,
            "message_pk": sample_queue_create.message_pk,
            "conversation_id": sample_queue_create.conversation_id,
            "priority_score": sample_queue_create.priority_score,
            "status": QueueStatus.PENDING.value,
            "position_in_queue": 1,
            "assigned_worker": None,
            "entered_queue_at": entered_queue_at,
            "started_processing_at": None,
            "completed_at": None,
        }

        mock_db_connection.fetchrow.return_value = mock_record

        result = await queue_repository.create(sample_queue_create)

        assert isinstance(result, PrivateMessageQueue)
        assert result.message_pk == sample_queue_create.message_pk
        assert result.conversation_id == sample_queue_create.conversation_id

    async def test_get_queue_position_by_conversation(
        self, queue_repository, mock_db_connection
    ):
        """Test getting queue position by conversation."""
        message_pk = uuid4()
        conversation_id = "conv-456"
        mock_db_connection.fetchval.return_value = 1

        result = await queue_repository.get_queue_position_by_conversation(
            message_pk, conversation_id
        )

        assert result == 1

    async def test_update_queue_positions_by_conversation(
        self, queue_repository, mock_db_connection
    ):
        """Test updating queue positions by conversation."""
        conversation_id = "conv-789"
        mock_db_connection.execute.return_value = "UPDATE 2"

        await queue_repository.update_queue_positions_by_conversation(conversation_id)

        mock_db_connection.execute.assert_called_once()

    async def test_get_next_pending_item_by_conversation(
        self, queue_repository, mock_db_connection
    ):
        """Test getting next pending item by conversation."""
        conversation_id = "conv-abc"
        mock_record = {
            "pk": uuid4(),
            "created_at": datetime.now(UTC),
            "updated_at": None,
            "message_pk": uuid4(),
            "conversation_id": conversation_id,
            "priority_score": 90,
            "status": QueueStatus.PENDING.value,
            "position_in_queue": 1,
            "assigned_worker": None,
            "entered_queue_at": datetime.now(UTC),
            "started_processing_at": None,
            "completed_at": None,
        }

        mock_db_connection.fetchrow.return_value = mock_record

        result = await queue_repository.get_next_pending_item_by_conversation(
            conversation_id
        )

        assert isinstance(result, PrivateMessageQueue)
        assert result.conversation_id == conversation_id


@pytest.mark.asyncio
class TestQueueOverviewRepository:
    """Test QueueOverviewRepository class."""

    @pytest.fixture
    async def overview_repository(self):
        """Create QueueOverviewRepository instance."""
        return QueueOverviewRepository()

    async def test_get_queue_status_info(self, overview_repository, mock_db_connection):
        """Test getting queue status info."""
        mock_record = {
            "queue_type": "topic_creation",
            "total_pending": 5,
            "total_processing": 2,
            "average_wait_time_minutes": 15,
            "oldest_pending_minutes": 45,
        }

        mock_db_connection.fetchrow.return_value = mock_record

        result = await overview_repository.get_queue_status_info("topic_creation")

        assert isinstance(result, QueueStatusInfo)
        assert result.queue_type == "topic_creation"
        assert result.total_pending == 5
        assert result.total_processing == 2

    async def test_get_queue_overview(self, overview_repository, mock_db_connection):
        """Test getting complete queue overview."""
        mock_records = [
            {
                "queue_type": "topic_creation",
                "total_pending": 3,
                "total_processing": 1,
                "average_wait_time_minutes": 10,
                "oldest_pending_minutes": 30,
            },
            {
                "queue_type": "post_moderation",
                "total_pending": 8,
                "total_processing": 3,
                "average_wait_time_minutes": 5,
                "oldest_pending_minutes": 20,
            },
            {
                "queue_type": "private_message",
                "total_pending": 2,
                "total_processing": 0,
                "average_wait_time_minutes": 8,
                "oldest_pending_minutes": 15,
            },
        ]

        mock_db_connection.fetch.return_value = mock_records

        result = await overview_repository.get_queue_overview()

        assert isinstance(result, QueueOverview)
        assert result.topic_creation_queue.total_pending == 3
        assert result.post_moderation_queue.total_pending == 8
        assert result.private_message_queue.total_pending == 2

    async def test_get_queue_with_content(
        self, overview_repository, mock_db_connection
    ):
        """Test getting queue items with content."""
        mock_records = [
            {
                "pk": uuid4(),
                "queue_type": "topic_creation",
                "content_pk": uuid4(),
                "content_title": "Test Topic",
                "content_preview": "A test topic for discussion...",
                "priority_score": 60,
                "status": QueueStatus.PENDING.value,
                "position_in_queue": 1,
                "entered_queue_at": datetime.now(UTC),
                "author_username": "testuser",
            },
            {
                "pk": uuid4(),
                "queue_type": "post_moderation",
                "content_pk": uuid4(),
                "content_title": "Re: Test Topic",
                "content_preview": "This is a reply...",
                "priority_score": 40,
                "status": QueueStatus.PROCESSING.value,
                "position_in_queue": 0,
                "entered_queue_at": datetime.now(UTC),
                "author_username": "replyuser",
            },
        ]

        mock_db_connection.fetch.return_value = mock_records

        result = await overview_repository.get_queue_with_content(limit=10, offset=0)

        assert len(result) == 2
        assert all(isinstance(item, QueueWithContent) for item in result)
        assert result[0].queue_type == "topic_creation"
        assert result[1].queue_type == "post_moderation"

    async def test_get_queue_with_content_by_type(
        self, overview_repository, mock_db_connection
    ):
        """Test getting queue items with content filtered by type."""
        mock_records = [
            {
                "pk": uuid4(),
                "queue_type": "topic_creation",
                "content_pk": uuid4(),
                "content_title": "Topic Only",
                "content_preview": "Only topic items...",
                "priority_score": 70,
                "status": QueueStatus.PENDING.value,
                "position_in_queue": 1,
                "entered_queue_at": datetime.now(UTC),
                "author_username": "topicuser",
            }
        ]

        mock_db_connection.fetch.return_value = mock_records

        result = await overview_repository.get_queue_with_content(
            queue_type="topic_creation", limit=10, offset=0
        )

        assert len(result) == 1
        assert result[0].queue_type == "topic_creation"

    async def test_get_empty_queue_status(
        self, overview_repository, mock_db_connection
    ):
        """Test getting status for empty queue."""
        mock_record = {
            "queue_type": "topic_creation",
            "total_pending": 0,
            "total_processing": 0,
            "average_wait_time_minutes": 0,
            "oldest_pending_minutes": 0,
        }

        mock_db_connection.fetchrow.return_value = mock_record

        result = await overview_repository.get_queue_status_info("topic_creation")

        assert result.total_pending == 0
        assert result.total_processing == 0
        assert result.average_wait_time_minutes == 0
