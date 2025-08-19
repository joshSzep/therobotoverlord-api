"""Tests for ToS screening queue repository."""

from datetime import UTC
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import QueueStatus
from therobotoverlord_api.database.models.queue import PostTosScreeningQueue
from therobotoverlord_api.database.models.queue import PostTosScreeningQueueCreate
from therobotoverlord_api.database.models.queue import QueueItemUpdate
from therobotoverlord_api.database.repositories.tos_screening_queue import (
    PostTosScreeningQueueRepository,
)


@pytest.mark.asyncio
class TestPostTosScreeningQueueRepository:
    """Test PostTosScreeningQueueRepository class."""

    @pytest.fixture
    def queue_repository(self):
        """Create PostTosScreeningQueueRepository instance."""
        return PostTosScreeningQueueRepository()

    @pytest.fixture
    def sample_queue_create(self):
        """Create sample PostTosScreeningQueueCreate data."""
        return PostTosScreeningQueueCreate(
            post_pk=uuid4(),
            topic_pk=uuid4(),
            priority_score=75,
            position_in_queue=1,
            entered_queue_at=datetime.now(UTC),
        )

    @pytest.fixture
    def mock_queue_record(self):
        """Create mock queue record."""
        return {
            "pk": uuid4(),
            "created_at": datetime.now(UTC),
            "updated_at": None,
            "post_pk": uuid4(),
            "topic_pk": uuid4(),
            "priority_score": 75,
            "priority": 0,
            "position_in_queue": 1,
            "status": QueueStatus.PENDING.value,
            "entered_queue_at": datetime.now(UTC),
            "estimated_completion_at": None,
            "worker_assigned_at": None,
            "worker_id": None,
        }

    async def test_create_queue_item(
        self, queue_repository, sample_queue_create, mock_connection
    ):
        """Test creating a ToS screening queue item."""
        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            queue_pk = uuid4()
            created_at = datetime.now(UTC)

            mock_record = {
                "pk": queue_pk,
                "created_at": created_at,
                "updated_at": None,
                "post_pk": sample_queue_create.post_pk,
                "topic_pk": sample_queue_create.topic_pk,
                "priority_score": sample_queue_create.priority_score,
                "priority": 0,
                "position_in_queue": sample_queue_create.position_in_queue,
                "status": QueueStatus.PENDING.value,
                "entered_queue_at": sample_queue_create.entered_queue_at,
                "estimated_completion_at": None,
                "worker_assigned_at": None,
                "worker_id": None,
            }

            mock_connection.fetchrow.return_value = mock_record

            result = await queue_repository.create(sample_queue_create)

        assert isinstance(result, PostTosScreeningQueue)
        assert result.post_pk == sample_queue_create.post_pk
        assert result.topic_pk == sample_queue_create.topic_pk
        assert result.priority_score == sample_queue_create.priority_score
        assert result.status == QueueStatus.PENDING

    async def test_update_queue_item(self, queue_repository, mock_connection):
        """Test updating a ToS screening queue item."""
        queue_pk = uuid4()
        queue_update = QueueItemUpdate(
            status=QueueStatus.PROCESSING,
            worker_id="worker-1",
        )

        updated_at = datetime.now(UTC)
        mock_record = {
            "pk": queue_pk,
            "created_at": datetime.now(UTC),
            "updated_at": updated_at,
            "post_pk": uuid4(),
            "topic_pk": uuid4(),
            "priority_score": 75,
            "priority": 0,
            "position_in_queue": 1,
            "status": QueueStatus.PROCESSING.value,
            "entered_queue_at": datetime.now(UTC),
            "estimated_completion_at": None,
            "worker_assigned_at": updated_at,
            "worker_id": "worker-1",
        }

        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await queue_repository.update(queue_pk, queue_update)

        assert result.status == QueueStatus.PROCESSING
        assert result.worker_id == "worker-1"
        assert result.updated_at == updated_at

    async def test_update_queue_item_no_changes(
        self, queue_repository, mock_connection
    ):
        """Test updating a queue item with no changes."""
        queue_pk = uuid4()
        queue_update = QueueItemUpdate()  # Empty update

        mock_record = {
            "pk": queue_pk,
            "created_at": datetime.now(UTC),
            "updated_at": None,
            "post_pk": uuid4(),
            "topic_pk": uuid4(),
            "priority_score": 75,
            "priority": 0,
            "position_in_queue": 1,
            "status": QueueStatus.PENDING.value,
            "entered_queue_at": datetime.now(UTC),
            "estimated_completion_at": None,
            "worker_assigned_at": None,
            "worker_id": None,
        }

        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_record

            result = await queue_repository.update(queue_pk, queue_update)

        assert result.status == QueueStatus.PENDING
        assert result.worker_id is None

    async def test_get_next_pending_without_worker(
        self, queue_repository, mock_connection, mock_queue_record
    ):
        """Test getting next pending item without assigning worker."""
        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_queue_record

            result = await queue_repository.get_next_pending()

        assert isinstance(result, PostTosScreeningQueue)
        assert result.status == QueueStatus.PENDING
        assert result.worker_id is None
        mock_connection.fetchrow.assert_called_once_with(
            """
            SELECT * FROM post_tos_screening_queue
            WHERE status = $1
            ORDER BY priority_score DESC, entered_queue_at ASC
            LIMIT 1
        """,
            QueueStatus.PENDING.value,
        )

    async def test_get_next_pending_with_worker(
        self, queue_repository, mock_connection, mock_queue_record
    ):
        """Test getting next pending item and assigning worker."""
        worker_id = "worker-123"

        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_queue_record

            # Mock the update call
            with patch.object(queue_repository, "update") as mock_update:
                mock_update.return_value = None

                result = await queue_repository.get_next_pending(worker_id)

        assert isinstance(result, PostTosScreeningQueue)
        assert result.status == QueueStatus.PROCESSING
        assert result.worker_id == worker_id
        assert result.worker_assigned_at is not None

    async def test_get_next_pending_empty_queue(
        self, queue_repository, mock_connection
    ):
        """Test getting next pending item from empty queue."""
        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = None

            result = await queue_repository.get_next_pending()

        assert result is None

    async def test_get_by_post_pk(
        self, queue_repository, mock_connection, mock_queue_record
    ):
        """Test getting ToS screening queue item by post PK."""
        post_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = mock_queue_record

            result = await queue_repository.get_by_post_pk(post_pk)

        assert isinstance(result, PostTosScreeningQueue)
        mock_connection.fetchrow.assert_called_once_with(
            """
            SELECT * FROM post_tos_screening_queue
            WHERE post_pk = $1
            ORDER BY created_at DESC
            LIMIT 1
        """,
            post_pk,
        )

    async def test_get_by_post_pk_not_found(self, queue_repository, mock_connection):
        """Test getting ToS screening queue item by post PK when not found."""
        post_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = None

            result = await queue_repository.get_by_post_pk(post_pk)

        assert result is None

    async def test_get_queue_length(self, queue_repository, mock_connection):
        """Test getting the current queue length."""
        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchval.return_value = 5

            result = await queue_repository.get_queue_length()

        assert result == 5
        mock_connection.fetchval.assert_called_once_with(
            """
            SELECT COUNT(*) FROM post_tos_screening_queue
            WHERE status = $1
        """,
            QueueStatus.PENDING.value,
        )

    async def test_get_queue_length_empty(self, queue_repository, mock_connection):
        """Test getting queue length when empty."""
        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchval.return_value = None

            result = await queue_repository.get_queue_length()

        assert result == 0

    async def test_get_by_status(
        self, queue_repository, mock_connection, mock_queue_record
    ):
        """Test getting ToS screening queue items by status."""
        mock_records = [mock_queue_record, mock_queue_record.copy()]

        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.return_value = mock_records

            result = await queue_repository.get_by_status(
                QueueStatus.PENDING, limit=50, offset=10
            )

        assert len(result) == 2
        assert all(isinstance(item, PostTosScreeningQueue) for item in result)
        mock_connection.fetch.assert_called_once_with(
            """
            SELECT * FROM post_tos_screening_queue
            WHERE status = $1
            ORDER BY priority_score DESC, entered_queue_at ASC
            LIMIT $2 OFFSET $3
        """,
            QueueStatus.PENDING.value,
            50,
            10,
        )

    async def test_get_by_status_default_params(
        self, queue_repository, mock_connection, mock_queue_record
    ):
        """Test getting ToS screening queue items by status with default parameters."""
        mock_records = [mock_queue_record]

        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.return_value = mock_records

            result = await queue_repository.get_by_status(QueueStatus.PROCESSING)

        assert len(result) == 1
        mock_connection.fetch.assert_called_once_with(
            """
            SELECT * FROM post_tos_screening_queue
            WHERE status = $1
            ORDER BY priority_score DESC, entered_queue_at ASC
            LIMIT $2 OFFSET $3
        """,
            QueueStatus.PROCESSING.value,
            100,
            0,
        )

    async def test_complete_processing(self, queue_repository, mock_connection):
        """Test marking a ToS screening queue item as completed."""
        queue_pk = uuid4()
        completed_record = {
            "pk": queue_pk,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "post_pk": uuid4(),
            "topic_pk": uuid4(),
            "priority_score": 75,
            "priority": 0,
            "position_in_queue": 1,
            "status": QueueStatus.COMPLETED.value,
            "entered_queue_at": datetime.now(UTC),
            "estimated_completion_at": None,
            "worker_assigned_at": datetime.now(UTC),
            "worker_id": "worker-1",
        }

        with patch(
            "therobotoverlord_api.database.repositories.base.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetchrow.return_value = completed_record

            result = await queue_repository.complete_processing(queue_pk)

        assert result.status == QueueStatus.COMPLETED

    async def test_get_processing_by_worker(
        self, queue_repository, mock_connection, mock_queue_record
    ):
        """Test getting items currently being processed by a specific worker."""
        worker_id = "worker-123"
        processing_record = mock_queue_record.copy()
        processing_record["status"] = QueueStatus.PROCESSING.value
        processing_record["worker_id"] = worker_id
        processing_record["worker_assigned_at"] = datetime.now(UTC)

        mock_records = [processing_record, processing_record.copy()]

        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.return_value = mock_records

            result = await queue_repository.get_processing_by_worker(worker_id)

        assert len(result) == 2
        assert all(isinstance(item, PostTosScreeningQueue) for item in result)
        assert all(item.worker_id == worker_id for item in result)
        assert all(item.status == QueueStatus.PROCESSING for item in result)

        mock_connection.fetch.assert_called_once_with(
            """
            SELECT * FROM post_tos_screening_queue
            WHERE status = $1 AND worker_id = $2
            ORDER BY worker_assigned_at ASC
        """,
            QueueStatus.PROCESSING.value,
            worker_id,
        )

    async def test_get_processing_by_worker_empty(
        self, queue_repository, mock_connection
    ):
        """Test getting processing items for worker with no items."""
        worker_id = "worker-456"

        with patch(
            "therobotoverlord_api.database.repositories.tos_screening_queue.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_connection
            mock_connection.fetch.return_value = []

            result = await queue_repository.get_processing_by_worker(worker_id)

        assert len(result) == 0

    async def test_record_to_model(self, queue_repository, mock_queue_record):
        """Test converting database record to PostTosScreeningQueue model."""
        result = queue_repository._record_to_model(mock_queue_record)

        assert isinstance(result, PostTosScreeningQueue)
        assert result.pk == mock_queue_record["pk"]
        assert result.post_pk == mock_queue_record["post_pk"]
        assert result.topic_pk == mock_queue_record["topic_pk"]
        assert result.priority_score == mock_queue_record["priority_score"]
        assert result.status == QueueStatus.PENDING

    async def test_table_name(self, queue_repository):
        """Test that repository uses correct table name."""
        assert queue_repository.table_name == "post_tos_screening_queue"
