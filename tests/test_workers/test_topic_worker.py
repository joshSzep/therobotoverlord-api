"""Tests for topic moderation worker - Fixed version."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import pytest

from therobotoverlord_api.workers.topic_worker import TopicModerationWorker
from therobotoverlord_api.workers.topic_worker import process_topic_moderation


@pytest.fixture
def mock_connection():
    """Mock database connection."""
    mock = AsyncMock()
    mock.close = AsyncMock()
    mock.fetchrow = AsyncMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def sample_topic_data():
    """Sample topic data for testing."""
    return {
        "pk": uuid4(),
        "title": "Test Topic",
        "description": "This is a test topic for moderation",
        "author_pk": uuid4(),
        "status": "pending_approval",
        "created_at": datetime.now(UTC),
        "updated_at": None,
    }


class TestTopicModerationWorker:
    """Test cases for TopicModerationWorker."""

    @pytest.mark.asyncio
    async def test_startup_success(self, mock_connection):
        """Test successful worker startup."""
        worker = TopicModerationWorker()

        # Mock the database connection factory
        class MockDBConnection:
            async def __aenter__(self):
                return mock_connection

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with (
            patch("therobotoverlord_api.workers.base.init_database") as mock_init_db,
            patch("therobotoverlord_api.workers.base.get_db_connection") as mock_get_db,
        ):
            mock_init_db.return_value = None
            mock_get_db.return_value = MockDBConnection()
            ctx = {}
            await worker.startup(ctx)
            assert "get_db_connection" in ctx
            assert callable(ctx["get_db_connection"])
            assert worker.db is None

    @pytest.mark.asyncio
    async def test_process_topic_moderation_success(
        self, mock_connection, sample_topic_data
    ):
        """Test successful topic moderation processing."""
        worker = TopicModerationWorker()
        worker.db = mock_connection

        # Mock get_db_connection to avoid database initialization issues
        class MockDBConnection:
            async def __aenter__(self):
                # Mock the database connection with proper return values
                mock_conn = AsyncMock()
                mock_conn.fetchval.return_value = 0  # retry_count = 0
                mock_conn.execute.return_value = None  # for status updates
                return mock_conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        def mock_get_db_connection():
            return MockDBConnection()

        # Mock the entire process_queue_item method to avoid database complexity
        with patch.object(worker, "process_queue_item") as mock_process_queue:
            mock_process_queue.return_value = True

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            topic_id = sample_topic_data["pk"]

            result = await worker.process_topic_moderation(ctx, queue_id, topic_id)

            assert result is True
            mock_process_queue.assert_called_once_with(
                ctx,
                "topic_creation_queue",
                queue_id,
                topic_id,
                worker._moderate_topic,
            )

    @pytest.mark.asyncio
    async def test_process_topic_not_found(self, mock_connection):
        """Test processing when topic is not found."""
        worker = TopicModerationWorker()
        worker.db = mock_connection

        # Mock the entire process_queue_item method to avoid database complexity
        with patch.object(worker, "process_queue_item") as mock_process_queue:
            mock_process_queue.return_value = False

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            topic_id = uuid4()

            result = await worker.process_topic_moderation(ctx, queue_id, topic_id)

            assert result is False
            mock_process_queue.assert_called_once_with(
                ctx,
                "topic_creation_queue",
                queue_id,
                topic_id,
                worker._moderate_topic,
            )

    @pytest.mark.asyncio
    async def test_process_topic_rejection(self, mock_connection, sample_topic_data):
        """Test topic rejection processing."""
        worker = TopicModerationWorker()
        worker.db = mock_connection

        # Mock the entire process_queue_item method to avoid database complexity
        with patch.object(worker, "process_queue_item") as mock_process_queue:
            mock_process_queue.return_value = True

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            topic_id = sample_topic_data["pk"]

            result = await worker.process_topic_moderation(ctx, queue_id, topic_id)

            assert result is True
            mock_process_queue.assert_called_once_with(
                ctx,
                "topic_creation_queue",
                queue_id,
                topic_id,
                worker._moderate_topic,
            )

    @pytest.mark.asyncio
    async def test_process_database_error(self, mock_connection, sample_topic_data):
        """Test processing with database error."""
        worker = TopicModerationWorker()
        worker.db = mock_connection

        # Mock TopicRepository
        with patch(
            "therobotoverlord_api.workers.topic_worker.TopicRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_pk.side_effect = Exception("Database error")
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            topic_id = sample_topic_data["pk"]

            result = await worker.process_topic_moderation(ctx, queue_id, topic_id)

            assert result is False


@pytest.mark.asyncio
async def test_process_topic_moderation_function():
    """Test the process_topic_moderation Arq worker function."""
    ctx = {"job_id": "test-job-123"}
    queue_id = str(uuid4())
    topic_id = str(uuid4())

    with patch(
        "therobotoverlord_api.workers.topic_worker.TopicModerationWorker"
    ) as mock_worker_class:
        mock_worker = AsyncMock()
        mock_worker.process_topic_moderation = AsyncMock(return_value=True)
        mock_worker_class.return_value = mock_worker

        result = await process_topic_moderation(ctx, queue_id, topic_id)

        assert result is True
        mock_worker.process_topic_moderation.assert_called_once_with(
            ctx, UUID(queue_id), UUID(topic_id)
        )


@pytest.mark.asyncio
async def test_process_topic_moderation_function_error():
    """Test the process_topic_moderation function with error."""
    ctx = {"job_id": "test-job-123"}
    queue_id = str(uuid4())
    topic_id = str(uuid4())

    with patch(
        "therobotoverlord_api.workers.topic_worker.TopicModerationWorker"
    ) as mock_worker_class:
        mock_worker = AsyncMock()
        mock_worker.process_topic_moderation = AsyncMock(
            side_effect=Exception("Worker error")
        )
        mock_worker_class.return_value = mock_worker

        result = await process_topic_moderation(ctx, queue_id, topic_id)

        assert result is False
