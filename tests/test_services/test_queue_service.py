"""Tests for queue service."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from therobotoverlord_api.services.queue_service import QueueService
from therobotoverlord_api.services.queue_service import get_queue_service


@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetchval = AsyncMock()
    return conn


@pytest.fixture
def mock_redis_pool():
    """Mock Redis pool."""
    pool = AsyncMock()
    pool.enqueue_job = AsyncMock()
    return pool


@pytest.fixture
def queue_service(mock_db_connection, mock_redis_pool):
    """Queue service instance with mocked dependencies."""
    service = QueueService()
    service.db = mock_db_connection
    service.redis_pool = mock_redis_pool
    return service


class TestQueueService:
    """Test cases for QueueService."""

    @pytest.mark.asyncio
    async def test_add_topic_to_queue_success(
        self, queue_service, mock_db_connection, mock_redis_pool
    ):
        """Test successfully adding a topic to the moderation queue."""
        topic_id = uuid4()
        priority = 3
        expected_queue_id = uuid4()

        # Mock database responses
        mock_db_connection.fetchrow.side_effect = [
            {"next_position": 1},  # _get_next_queue_position
            {"pk": expected_queue_id},  # INSERT query
            {"created_by_pk": uuid4()},  # User lookup for WebSocket broadcasting
        ]
        mock_db_connection.fetchval.return_value = (
            5  # Queue size for WebSocket broadcasting
        )

        result = await queue_service.add_topic_to_queue(topic_id, priority)

        assert result == expected_queue_id
        assert mock_db_connection.fetchrow.call_count == 3
        mock_redis_pool.enqueue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_topic_to_queue_failure(self, queue_service, mock_db_connection):
        """Test handling failure when adding topic to queue."""
        topic_id = uuid4()
        priority = 3

        mock_db_connection.fetchrow.side_effect = Exception("Database error")

        result = await queue_service.add_topic_to_queue(topic_id, priority)

        assert result is None

    @pytest.mark.asyncio
    async def test_add_post_to_queue_success(
        self, queue_service, mock_db_connection, mock_redis_pool
    ):
        """Test successfully adding a post to the moderation queue."""
        post_id = uuid4()
        topic_id = uuid4()
        priority = 7
        expected_queue_id = uuid4()

        # Mock database responses
        mock_db_connection.fetchrow.side_effect = [
            {"next_position": 2},  # _get_next_queue_position
            {"pk": expected_queue_id},  # INSERT query
            {"created_by_pk": uuid4()},  # User lookup for WebSocket broadcasting
        ]
        mock_db_connection.fetchval.return_value = (
            8  # Queue size for WebSocket broadcasting
        )

        result = await queue_service.add_post_to_queue(post_id, topic_id, priority)

        assert result == expected_queue_id
        assert mock_db_connection.fetchrow.call_count == 3
        mock_redis_pool.enqueue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_post_to_queue_failure(self, queue_service, mock_db_connection):
        """Test handling failure when adding post to queue."""
        post_id = uuid4()
        topic_id = uuid4()
        priority = 7

        mock_db_connection.fetchrow.side_effect = Exception("Database error")

        result = await queue_service.add_post_to_queue(post_id, topic_id, priority)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_queue_status_success(self, queue_service, mock_db_connection):
        """Test getting queue status successfully."""
        queue_type = "topics"
        mock_response = {
            "total_items": 10,
            "pending_items": 5,
            "processing_items": 2,
            "completed_items": 3,
            "avg_processing_time": 120.5,
            "next_position": 1,
        }

        # Mock estimate wait time
        mock_db_connection.fetchrow.side_effect = [
            mock_response,  # Main query
            {"avg_time": 30.0},  # Wait time estimation query 1
            {"pending_count": 5},  # Wait time estimation query 2
        ]

        result = await queue_service.get_queue_status(queue_type)

        assert result["queue_type"] == queue_type
        assert result["total_items"] == 10
        assert result["pending_items"] == 5
        assert result["processing_items"] == 2
        assert result["completed_items"] == 3

    @pytest.mark.asyncio
    async def test_get_queue_status_invalid_type(self, queue_service):
        """Test getting queue status with invalid queue type."""
        result = await queue_service.get_queue_status("invalid")

        assert result["error"] == "Invalid queue type"

    @pytest.mark.asyncio
    async def test_get_queue_status_failure(self, queue_service, mock_db_connection):
        """Test handling failure when getting queue status."""
        queue_type = "topics"
        mock_db_connection.fetchrow.side_effect = Exception("Database error")

        result = await queue_service.get_queue_status(queue_type)

        assert result["error"] == "Failed to get queue status"

    @pytest.mark.asyncio
    async def test_get_content_position_success(
        self, queue_service, mock_db_connection
    ):
        """Test getting content queue position successfully."""
        content_type = "topics"
        content_id = uuid4()

        mock_response = {
            "queue_id": uuid4(),
            "position_in_queue": 3,
            "status": "pending",
            "entered_queue_at": datetime.now(UTC),
            "estimated_completion_at": None,
            "worker_assigned_at": None,
            "worker_id": None,
        }

        mock_db_connection.fetchrow.return_value = mock_response

        result = await queue_service.get_content_position(content_type, content_id)

        assert result is not None
        assert result["position"] == 3
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_content_position_not_found(
        self, queue_service, mock_db_connection
    ):
        """Test getting content position when content not found."""
        content_type = "topics"
        content_id = uuid4()

        mock_db_connection.fetchrow.return_value = None

        result = await queue_service.get_content_position(content_type, content_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_content_position_invalid_type(self, queue_service):
        """Test getting content position with invalid content type."""
        content_type = "invalid"
        content_id = uuid4()

        result = await queue_service.get_content_position(content_type, content_id)

        assert result is None

    def test_get_queue_table(self, queue_service):
        """Test queue table name mapping."""
        assert queue_service._get_queue_table("topics") == "topic_creation_queue"
        assert queue_service._get_queue_table("posts") == "post_moderation_queue"
        assert queue_service._get_queue_table("messages") == "private_message_queue"
        assert queue_service._get_queue_table("invalid") is None

    @pytest.mark.asyncio
    async def test_estimate_wait_time_success(self, queue_service, mock_db_connection):
        """Test wait time estimation."""
        queue_type = "topics"

        mock_db_connection.fetchrow.side_effect = [
            {"avg_time": 45.0},  # Average processing time
            {"pending_count": 3},  # Pending items count
        ]

        result = await queue_service._estimate_wait_time(queue_type)

        assert result == 135  # 3 * 45

    @pytest.mark.asyncio
    async def test_estimate_wait_time_no_data(self, queue_service, mock_db_connection):
        """Test wait time estimation with no historical data."""
        queue_type = "topics"

        mock_db_connection.fetchrow.side_effect = [
            {"avg_time": None},  # No historical data
            {"pending_count": 2},  # Pending items count
        ]

        result = await queue_service._estimate_wait_time(queue_type)

        assert result == 60  # 2 * 30 (default)


@pytest.mark.asyncio
async def test_get_queue_service():
    """Test the get_queue_service factory function."""
    service = await get_queue_service()

    assert isinstance(service, QueueService)
    assert service.db is not None  # Uses global db instance
    # Redis pool may be initialized during service creation
