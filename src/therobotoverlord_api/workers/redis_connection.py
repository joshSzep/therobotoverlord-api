"""Redis connection management for Arq workers."""

import redis.asyncio as redis

from arq import create_pool
from arq.connections import RedisSettings as ArqRedisSettings

from therobotoverlord_api.config.redis import get_redis_settings


class RedisConnection:
    """Redis connection manager for Arq workers."""

    def __init__(self):
        self._pool = None
        self._redis_client = None
        self.settings = get_redis_settings()

    async def get_pool(self):
        """Get or create Redis connection pool for Arq."""
        if self._pool is None:
            arq_settings = ArqRedisSettings(
                host=self.settings.host,
                port=self.settings.port,
                database=self.settings.database,
                password=self.settings.password,
                max_connections=self.settings.max_connections,
            )
            self._pool = await create_pool(arq_settings)
        return self._pool

    async def get_redis_client(self):
        """Get or create Redis client for direct operations."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.settings.redis_url,
                max_connections=self.settings.max_connections,
                retry_on_timeout=self.settings.retry_on_timeout,
                socket_timeout=self.settings.socket_timeout,
                socket_connect_timeout=self.settings.socket_connect_timeout,
            )
        return self._redis_client

    async def close(self):
        """Close Redis connections."""
        if self._pool:
            await self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None


# Global connection instance
redis_connection = RedisConnection()


async def get_redis_pool():
    """Get Redis pool for Arq workers."""
    return await redis_connection.get_pool()


async def get_redis_client():
    """Get Redis client for direct operations."""
    return await redis_connection.get_redis_client()


async def close_redis_connections():
    """Close all Redis connections."""
    await redis_connection.close()
