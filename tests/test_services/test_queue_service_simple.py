"""Simple tests for QueueService to improve coverage."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.services.queue_service import QueueService


class TestQueueServiceSimple:
    """Simple test class for QueueService."""

    @pytest.fixture
    def queue_service(self):
        """Create a QueueService instance."""
        return QueueService()

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.queue_service.get_redis_pool")
    async def test_ensure_connections(self, mock_get_redis_pool, queue_service):
        """Test ensuring connections."""
        mock_redis_pool = AsyncMock()
        mock_get_redis_pool.return_value = mock_redis_pool
        
        await queue_service._ensure_connections()
        
        assert queue_service.redis_pool == mock_redis_pool
        mock_get_redis_pool.assert_called_once()

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.queue_service.get_redis_pool")
    async def test_ensure_connections_redis_failure(self, mock_get_redis_pool, queue_service):
        """Test ensuring connections with Redis failure."""
        mock_get_redis_pool.return_value = None
        
        with pytest.raises(RuntimeError, match="Failed to establish Redis connection"):
            await queue_service._ensure_connections()

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.queue_service.QueueService._ensure_connections")
    @patch("therobotoverlord_api.services.queue_service.QueueService._get_next_queue_position")
    async def test_add_topic_to_queue_exception(self, mock_get_position, mock_ensure_conn, queue_service):
        """Test adding topic to queue with exception."""
        topic_id = uuid4()
        mock_get_position.side_effect = Exception("Database error")
        
        result = await queue_service.add_topic_to_queue(topic_id, priority=5)
        
        mock_ensure_conn.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.queue_service.QueueService._ensure_connections")
    @patch("therobotoverlord_api.services.queue_service.QueueService._get_next_queue_position")
    async def test_add_post_to_queue_exception(self, mock_get_position, mock_ensure_conn, queue_service):
        """Test adding post to queue with exception."""
        post_id = uuid4()
        topic_id = uuid4()
        mock_get_position.side_effect = Exception("Database error")
        
        result = await queue_service.add_post_to_queue(post_id, topic_id, priority=3)
        
        mock_ensure_conn.assert_called_once()
        assert result is None
