"""Tests for topic moderation worker - Fixed version."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
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

        ctx = {}
        await worker.startup(ctx)

        # Verify the connection factory is stored in context
        assert "get_db_connection" in ctx
        assert callable(ctx["get_db_connection"])
        # Worker no longer stores db connection directly during startup
        assert worker.db is None

    @pytest.mark.asyncio
    async def test_process_topic_moderation_success(
        self, mock_connection, sample_topic_data
    ):
        """Test successful topic moderation processing."""
        worker = TopicModerationWorker()
        worker.db = mock_connection

        # Mock TopicRepository
        with patch(
            "therobotoverlord_api.workers.topic_worker.TopicRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_topic = MagicMock()
            mock_topic.title = "Good Topic Title"
            mock_topic.description = (
                "This is a good topic description with sufficient content"
            )
            mock_repo.get_by_pk.return_value = mock_topic
            mock_repo.approve_topic.return_value = True
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            topic_id = sample_topic_data["pk"]

            result = await worker.process_topic_moderation(ctx, queue_id, topic_id)

            assert result is True
            mock_repo.get_by_pk.assert_called_once_with(topic_id)
            # approve_topic is not called in current implementation due to moderator_pk requirement
            mock_repo.approve_topic.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_topic_not_found(self, mock_connection):
        """Test processing when topic is not found."""
        worker = TopicModerationWorker()
        worker.db = mock_connection

        # Mock TopicRepository
        with patch(
            "therobotoverlord_api.workers.topic_worker.TopicRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_pk.return_value = None
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            topic_id = uuid4()

            result = await worker.process_topic_moderation(ctx, queue_id, topic_id)

            assert result is False
            mock_repo.get_by_pk.assert_called_once_with(topic_id)

    @pytest.mark.asyncio
    async def test_process_topic_rejection(self, mock_connection, sample_topic_data):
        """Test topic rejection processing."""
        worker = TopicModerationWorker()
        worker.db = mock_connection

        # Mock TopicRepository
        with patch(
            "therobotoverlord_api.workers.topic_worker.TopicRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_topic = MagicMock()
            mock_topic.title = "spam"  # Should be rejected
            mock_topic.description = "spam content"
            mock_topic.pk = sample_topic_data["pk"]
            mock_repo.get_by_pk.return_value = mock_topic
            mock_repo.reject_topic.return_value = True
            mock_repo_class.return_value = mock_repo

            # Mock AI moderation service to return rejection
            with patch.object(worker, "_ai_topic_moderation") as mock_ai_mod:
                mock_ai_mod.return_value = False  # Topic rejected

                ctx = {"db": mock_connection}
                queue_id = uuid4()
                topic_id = sample_topic_data["pk"]

                result = await worker.process_topic_moderation(ctx, queue_id, topic_id)

                assert result is True
                mock_repo.get_by_pk.assert_called_once_with(topic_id)
                mock_repo.reject_topic.assert_called_once()

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
