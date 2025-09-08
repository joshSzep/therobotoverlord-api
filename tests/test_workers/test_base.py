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

    @pytest.mark.asyncio
    async def test_startup_failure(self, mock_connection):
        """Test worker startup with database connection failure."""
        worker = BaseWorker()
        with patch("therobotoverlord_api.workers.base.init_database") as mock_init_db:
            mock_init_db.side_effect = Exception("Database connection failed")
            ctx = {}
            with pytest.raises(Exception, match="Database connection failed"):
                await worker.startup(ctx)

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
