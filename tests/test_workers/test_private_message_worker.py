"""Tests for private message moderation worker."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import pytest

from therobotoverlord_api.workers.private_message_worker import (
    PrivateMessageModerationWorker,
)
from therobotoverlord_api.workers.private_message_worker import (
    process_private_message_moderation,
)


@pytest.fixture
def mock_connection():
    """Mock database connection."""
    mock = AsyncMock()
    mock.close = AsyncMock()
    mock.fetchrow = AsyncMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def sample_message_data():
    """Sample private message data for testing."""
    return {
        "pk": uuid4(),
        "sender_pk": uuid4(),
        "recipient_pk": uuid4(),
        "content": "This is a test private message for moderation",
        "created_at": datetime.now(UTC),
        "status": "pending_moderation",
        "moderated_at": None,
        "moderator_pk": None,
        "moderation_feedback": None,
    }


class TestPrivateMessageModerationWorker:
    """Test cases for PrivateMessageModerationWorker."""

    @pytest.mark.asyncio
    async def test_startup_success(self, mock_connection):
        """Test successful worker startup."""
        worker = PrivateMessageModerationWorker()

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
    async def test_process_message_moderation_success(
        self, mock_connection, sample_message_data
    ):
        """Test successful private message moderation processing."""
        worker = PrivateMessageModerationWorker()
        worker.db = mock_connection

        # Mock PrivateMessageRepository
        with patch(
            "therobotoverlord_api.workers.private_message_worker.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_message = MagicMock()
            mock_message.content = "This is good private message content"
            mock_repo.get_by_pk.return_value = mock_message
            mock_repo.approve_message.return_value = True
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            message_id = sample_message_data["pk"]

            result = await worker.process_message_moderation(ctx, queue_id, message_id)

            assert result is True
            mock_repo.get_by_pk.assert_called_once_with(message_id)
            mock_repo.approve_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_not_found(self, mock_connection):
        """Test processing when private message is not found."""
        worker = PrivateMessageModerationWorker()
        worker.db = mock_connection

        # Mock PrivateMessageRepository
        with patch(
            "therobotoverlord_api.workers.private_message_worker.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_pk.return_value = None
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            message_id = uuid4()

            result = await worker.process_message_moderation(ctx, queue_id, message_id)

            assert result is False
            mock_repo.get_by_pk.assert_called_once_with(message_id)

    @pytest.mark.asyncio
    async def test_process_message_rejection(
        self, mock_connection, sample_message_data
    ):
        """Test private message rejection processing."""
        worker = PrivateMessageModerationWorker()
        worker.db = mock_connection

        # Mock PrivateMessageRepository
        with patch(
            "therobotoverlord_api.workers.private_message_worker.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_message = MagicMock()
            mock_message.content = "kill yourself you idiot"  # Should be rejected
            mock_repo.get_by_pk.return_value = mock_message
            mock_repo.reject_message.return_value = True
            mock_repo_class.return_value = mock_repo

            # Mock AI moderation service to return rejection
            with patch.object(worker, "_ai_message_moderation") as mock_ai_mod:
                mock_ai_mod.return_value = {
                    "approved": False,
                    "feedback": "Content contains harassment",
                    "reasoning": "Threatening language detected",
                    "confidence": 0.98,
                }

                ctx = {"db": mock_connection}
                queue_id = uuid4()
                message_id = sample_message_data["pk"]

                result = await worker.process_message_moderation(
                    ctx, queue_id, message_id
                )

                assert result is True
                mock_repo.get_by_pk.assert_called_once_with(message_id)
                mock_repo.reject_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_database_error(self, mock_connection, sample_message_data):
        """Test processing with database error."""
        worker = PrivateMessageModerationWorker()
        worker.db = mock_connection

        # Mock PrivateMessageRepository
        with patch(
            "therobotoverlord_api.workers.private_message_worker.PrivateMessageRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_pk.side_effect = Exception("Database error")
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            message_id = sample_message_data["pk"]

            result = await worker.process_message_moderation(ctx, queue_id, message_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_database_connection_handling_no_db_in_context(self):
        """Test database connection handling when no db in context."""
        worker = PrivateMessageModerationWorker()

        ctx = {}  # No db connection
        queue_id = uuid4()
        message_id = uuid4()

        result = await worker.process_message_moderation(ctx, queue_id, message_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_database_connection_handling_invalid_db_type(self):
        """Test database connection handling with invalid db type."""
        worker = PrivateMessageModerationWorker()

        ctx = {"db": "not_a_connection"}  # Invalid type
        queue_id = uuid4()
        message_id = uuid4()

        result = await worker.process_message_moderation(ctx, queue_id, message_id)

        assert result is False


@pytest.mark.asyncio
async def test_process_private_message_moderation_function():
    """Test the process_private_message_moderation Arq worker function."""
    ctx = {"job_id": "test-job-123"}
    queue_id = str(uuid4())
    message_id = str(uuid4())

    with patch(
        "therobotoverlord_api.workers.private_message_worker.PrivateMessageModerationWorker"
    ) as mock_worker_class:
        mock_worker = AsyncMock()
        mock_worker.process_message_moderation = AsyncMock(return_value=True)
        mock_worker_class.return_value = mock_worker

        result = await process_private_message_moderation(ctx, queue_id, message_id)

        assert result is True
        mock_worker.process_message_moderation.assert_called_once_with(
            ctx, UUID(queue_id), UUID(message_id)
        )


@pytest.mark.asyncio
async def test_process_private_message_moderation_function_error():
    """Test the process_private_message_moderation function with error."""
    ctx = {"job_id": "test-job-123"}
    queue_id = str(uuid4())
    message_id = str(uuid4())

    with patch(
        "therobotoverlord_api.workers.private_message_worker.PrivateMessageModerationWorker"
    ) as mock_worker_class:
        mock_worker = AsyncMock()
        mock_worker.process_message_moderation = AsyncMock(
            side_effect=Exception("Worker error")
        )
        mock_worker_class.return_value = mock_worker

        result = await process_private_message_moderation(ctx, queue_id, message_id)

        assert result is False
