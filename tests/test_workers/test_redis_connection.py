"""Tests for Redis connection management."""

from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from therobotoverlord_api.workers.redis_connection import RedisConnection
from therobotoverlord_api.workers.redis_connection import close_redis_connections
from therobotoverlord_api.workers.redis_connection import get_redis_client
from therobotoverlord_api.workers.redis_connection import get_redis_pool
from therobotoverlord_api.workers.redis_connection import redis_connection


@pytest.fixture
def mock_redis_settings():
    """Mock Redis settings."""
    with patch(
        "therobotoverlord_api.workers.redis_connection.get_redis_settings"
    ) as mock:
        mock.return_value.host = "localhost"
        mock.return_value.port = 6379
        mock.return_value.database = 0
        mock.return_value.password = None
        mock.return_value.max_connections = 10
        mock.return_value.redis_url = "redis://localhost:6379/0"
        mock.return_value.retry_on_timeout = True
        mock.return_value.socket_timeout = 5
        mock.return_value.socket_connect_timeout = 5
        yield mock


@pytest.fixture
def mock_redis_pool():
    """Mock Redis pool."""
    pool = AsyncMock()
    pool.close = AsyncMock()
    pool.wait_closed = AsyncMock()
    return pool


class TestRedisConnection:
    """Test cases for RedisConnection."""

    @pytest.mark.asyncio
    async def test_get_pool_first_time(self, mock_redis_settings):
        """Test getting pool for the first time."""
        redis_conn = RedisConnection()

        with patch(
            "therobotoverlord_api.workers.redis_connection.create_pool"
        ) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            connection = await redis_conn.get_pool()

            assert connection == mock_pool
            assert redis_conn._pool == mock_pool
            mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pool_reuse_existing(self, mock_redis_settings, mock_redis_pool):
        """Test getting pool when one already exists."""
        redis_conn = RedisConnection()
        redis_conn._pool = mock_redis_pool

        connection = await redis_conn.get_pool()

        assert connection == mock_redis_pool

    @pytest.mark.asyncio
    async def test_get_redis_client_first_time(self, mock_redis_settings):
        """Test getting Redis client for the first time."""
        redis_conn = RedisConnection()

        with patch(
            "therobotoverlord_api.workers.redis_connection.redis.from_url"
        ) as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            client = await redis_conn.get_redis_client()

            assert client == mock_client
            assert redis_conn._redis_client == mock_client
            mock_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_client_reuse_existing(self, mock_redis_settings):
        """Test getting Redis client when one already exists."""
        redis_conn = RedisConnection()
        mock_client = AsyncMock()
        redis_conn._redis_client = mock_client

        client = await redis_conn.get_redis_client()

        assert client == mock_client

    @pytest.mark.asyncio
    async def test_close_with_pool_and_client(self, mock_redis_settings):
        """Test closing connection with active pool and client."""
        redis_conn = RedisConnection()
        mock_pool = AsyncMock()
        mock_client = AsyncMock()
        redis_conn._pool = mock_pool
        redis_conn._redis_client = mock_client

        await redis_conn.close()

        mock_pool.close.assert_called_once()
        mock_pool.wait_closed.assert_called_once()
        mock_client.close.assert_called_once()
        assert redis_conn._pool is None
        assert redis_conn._redis_client is None

    @pytest.mark.asyncio
    async def test_close_without_connections(self, mock_redis_settings):
        """Test closing connection without active connections."""
        redis_conn = RedisConnection()

        # Should not raise any exception
        await redis_conn.close()

    @pytest.mark.asyncio
    async def test_global_functions(self, mock_redis_settings):
        """Test global helper functions."""
        with patch(
            "therobotoverlord_api.workers.redis_connection.redis_connection"
        ) as mock_conn:
            mock_pool = AsyncMock()
            mock_client = AsyncMock()
            mock_conn.get_pool = AsyncMock(return_value=mock_pool)
            mock_conn.get_redis_client = AsyncMock(return_value=mock_client)
            mock_conn.close = AsyncMock()

            # Test get_redis_pool
            pool = await get_redis_pool()
            assert pool == mock_pool
            mock_conn.get_pool.assert_called_once()

            # Test get_redis_client
            client = await get_redis_client()
            assert client == mock_client
            mock_conn.get_redis_client.assert_called_once()

            # Test close_redis_connections
            await close_redis_connections()
            mock_conn.close.assert_called_once()

    def test_singleton_behavior(self, mock_redis_settings):
        """Test that redis_connection is a singleton."""
        # Reset connection state for test
        redis_connection._pool = None
        redis_connection._redis_client = None

        conn1 = redis_connection
        conn2 = redis_connection

        assert conn1 is conn2
        assert conn1._pool is None
        assert conn1._redis_client is None
