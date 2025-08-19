"""Tests for post moderation worker - Fixed version."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import pytest

from therobotoverlord_api.workers.post_worker import PostModerationWorker
from therobotoverlord_api.workers.post_worker import process_post_moderation


@pytest.fixture
def mock_connection():
    """Mock database connection."""
    mock = AsyncMock()
    mock.close = AsyncMock()
    mock.fetchrow = AsyncMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def sample_post_data():
    """Sample post data for testing."""
    return {
        "pk": uuid4(),
        "topic_pk": uuid4(),
        "author_pk": uuid4(),
        "content": "This is a test post for moderation",
        "created_at": datetime.now(UTC),
        "parent_post_pk": None,
        "status": "pending_moderation",
        "moderated_at": None,
        "moderator_pk": None,
        "moderation_feedback": None,
    }


class TestPostModerationWorker:
    """Test cases for PostModerationWorker."""

    @pytest.mark.asyncio
    async def test_startup_success(self, mock_connection):
        """Test successful worker startup."""
        worker = PostModerationWorker()

        ctx = {}
        await worker.startup(ctx)

        # Verify the connection factory is stored in context
        assert "get_db_connection" in ctx
        assert callable(ctx["get_db_connection"])
        # Worker no longer stores db connection directly during startup
        assert worker.db is None

    @pytest.mark.asyncio
    async def test_process_post_moderation_success(
        self, mock_connection, sample_post_data
    ):
        """Test successful post moderation processing."""
        worker = PostModerationWorker()
        worker.db = mock_connection

        # Mock PostRepository
        with patch(
            "therobotoverlord_api.workers.post_worker.PostRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_post = MagicMock()
            mock_post.content = "This is good content"
            mock_repo.get_by_pk.return_value = mock_post
            mock_repo.approve_post.return_value = True
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            post_id = sample_post_data["pk"]

            result = await worker.process_post_moderation(ctx, queue_id, post_id)

            assert result is True
            mock_repo.get_by_pk.assert_called_once_with(post_id)
            mock_repo.approve_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_post_not_found(self, mock_connection):
        """Test processing when post is not found."""
        worker = PostModerationWorker()
        worker.db = mock_connection

        # Mock PostRepository
        with patch(
            "therobotoverlord_api.workers.post_worker.PostRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_pk.return_value = None
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            post_id = uuid4()

            result = await worker.process_post_moderation(ctx, queue_id, post_id)

            assert result is False
            mock_repo.get_by_pk.assert_called_once_with(post_id)

    @pytest.mark.asyncio
    async def test_process_post_rejection(self, mock_connection, sample_post_data):
        """Test post rejection processing."""
        worker = PostModerationWorker()
        worker.db = mock_connection

        # Mock PostRepository
        with patch(
            "therobotoverlord_api.workers.post_worker.PostRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_post = MagicMock()
            mock_post.content = "spam spam spam"  # Should be rejected
            mock_repo.get_by_pk.return_value = mock_post
            mock_repo.reject_post.return_value = True
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            post_id = sample_post_data["pk"]

            result = await worker.process_post_moderation(ctx, queue_id, post_id)

            assert result is True
            mock_repo.get_by_pk.assert_called_once_with(post_id)
            mock_repo.reject_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_database_error(self, mock_connection, sample_post_data):
        """Test processing with database error."""
        worker = PostModerationWorker()
        worker.db = mock_connection

        # Mock PostRepository
        with patch(
            "therobotoverlord_api.workers.post_worker.PostRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_pk.side_effect = Exception("Database error")
            mock_repo_class.return_value = mock_repo

            ctx = {"db": mock_connection}
            queue_id = uuid4()
            post_id = sample_post_data["pk"]

            result = await worker.process_post_moderation(ctx, queue_id, post_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_placeholder_moderation_approval(self):
        """Test placeholder moderation logic for approval."""
        worker = PostModerationWorker()

        mock_post = MagicMock()
        mock_post.content = "This is a good post with sufficient length"

        result = await worker._placeholder_post_moderation(mock_post)

        assert isinstance(result, dict)
        assert "approved" in result
        assert result["approved"] is True
        assert "feedback" in result

    @pytest.mark.asyncio
    async def test_placeholder_moderation_rejection(self):
        """Test placeholder moderation logic for rejection."""
        worker = PostModerationWorker()

        mock_post = MagicMock()
        mock_post.content = "spam"  # Contains banned word

        result = await worker._placeholder_post_moderation(mock_post)

        assert isinstance(result, dict)
        assert "approved" in result
        assert result["approved"] is False
        assert "feedback" in result

    @pytest.mark.asyncio
    async def test_placeholder_moderation_too_short(self):
        """Test placeholder moderation logic for too short content."""
        worker = PostModerationWorker()

        mock_post = MagicMock()
        mock_post.content = "short"  # Too short

        result = await worker._placeholder_post_moderation(mock_post)

        assert isinstance(result, dict)
        assert "approved" in result
        assert result["approved"] is False
        assert "Minimum" in result["feedback"]


@pytest.mark.asyncio
async def test_process_post_moderation_function():
    """Test the process_post_moderation Arq worker function."""
    ctx = {"job_id": "test-job-123"}
    queue_id = str(uuid4())
    post_id = str(uuid4())

    with patch(
        "therobotoverlord_api.workers.post_worker.PostModerationWorker"
    ) as mock_worker_class:
        mock_worker = AsyncMock()
        mock_worker.process_post_moderation = AsyncMock(return_value=True)
        mock_worker_class.return_value = mock_worker

        result = await process_post_moderation(ctx, queue_id, post_id)

        assert result is True
        mock_worker.process_post_moderation.assert_called_once_with(
            ctx, UUID(queue_id), UUID(post_id)
        )


@pytest.mark.asyncio
async def test_process_post_moderation_function_error():
    """Test the process_post_moderation function with error."""
    ctx = {"job_id": "test-job-123"}
    queue_id = str(uuid4())
    post_id = str(uuid4())

    with patch(
        "therobotoverlord_api.workers.post_worker.PostModerationWorker"
    ) as mock_worker_class:
        mock_worker = AsyncMock()
        mock_worker.process_post_moderation = AsyncMock(
            side_effect=Exception("Worker error")
        )
        mock_worker_class.return_value = mock_worker

        result = await process_post_moderation(ctx, queue_id, post_id)

        assert result is False
