"""Tests for base worker classes - Fixed version."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.workers.base import BaseWorker
from therobotoverlord_api.workers.base import QueueWorkerMixin


@pytest.fixture
def mock_connection():
    """Mock database connection."""
    mock = AsyncMock()
    mock.close = AsyncMock()
    return mock


class TestBaseWorker:
    """Test cases for BaseWorker."""

    @pytest.mark.asyncio
    async def test_startup_success(self, mock_connection):
        """Test successful worker startup."""
        worker = BaseWorker()

        with patch(
            "therobotoverlord_api.workers.base.get_db_connection",
            new_callable=AsyncMock,
            return_value=mock_connection,
        ):
            ctx = {}
            await worker.startup(ctx)

            assert "get_db_connection" in ctx
            # Worker no longer stores db connection directly

    @pytest.mark.asyncio
    async def test_startup_failure(self):
        """Test worker startup failure."""
        worker = BaseWorker()

        # Startup doesn't fail anymore since it just stores the connection factory
        # The actual connection happens per-request
        ctx = {}
        await worker.startup(ctx)

        # Verify the connection factory is stored
        assert "get_db_connection" in ctx
        assert callable(ctx["get_db_connection"])

    @pytest.mark.asyncio
    async def test_shutdown_success(self, mock_connection):
        """Test successful worker shutdown."""
        worker = BaseWorker()
        worker.db = mock_connection

        ctx = {"db": mock_connection}
        await worker.shutdown(ctx)

        mock_connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_no_connection(self):
        """Test worker shutdown with no connection."""
        worker = BaseWorker()
        worker.db = None

        ctx = {}
        await worker.shutdown(ctx)
        # Should not raise exception

    def test_get_arq_redis_settings(self):
        """Test Redis settings conversion."""
        worker = BaseWorker()
        settings = worker._get_arq_redis_settings()

        assert hasattr(settings, "host")
        assert hasattr(settings, "port")
        assert hasattr(settings, "database")


class TestQueueWorkerMixin:
    """Test cases for QueueWorkerMixin."""

    @pytest.mark.asyncio
    async def test_update_queue_status(self, mock_connection):
        """Test queue status update."""

        class TestWorker(BaseWorker, QueueWorkerMixin):
            pass

        worker = TestWorker()
        worker.db = mock_connection

        queue_id = uuid4()
        await worker.update_queue_status("test_table", queue_id, "processing")

        mock_connection.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_queue_item(self, mock_connection):
        """Test getting queue item."""

        class TestWorker(BaseWorker, QueueWorkerMixin):
            pass

        worker = TestWorker()
        worker.db = mock_connection

        mock_record = {"id": "test", "status": "pending"}
        mock_connection.fetchrow.return_value = mock_record

        queue_id = uuid4()
        result = await worker.get_queue_item("test_table", queue_id)

        assert result == mock_record
        mock_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_queue_item_no_db(self):
        """Test getting queue item without database connection."""

        class TestWorker(BaseWorker, QueueWorkerMixin):
            pass

        worker = TestWorker()
        worker.db = None

        queue_id = uuid4()
        result = await worker.get_queue_item("test_table", queue_id)

        assert result is None
