"""Database connection management for The Robot Overlord API."""

import logging

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg

from asyncpg import Connection
from asyncpg import Pool

from therobotoverlord_api.config.database import get_database_settings
from therobotoverlord_api.config.database import get_database_url

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager with connection pooling."""

    def __init__(self):
        self._pool: Pool | None = None
        self._settings = get_database_settings()

    async def connect(self) -> None:
        """Initialize the database connection pool."""
        if self._pool is not None:
            logger.warning("Database pool already initialized")
            return

        database_url = get_database_url()

        try:
            self._pool = await asyncpg.create_pool(
                database_url,
                min_size=self._settings.min_pool_size,
                max_size=self._settings.max_pool_size,
                timeout=self._settings.pool_timeout,
                command_timeout=self._settings.command_timeout,
                server_settings={
                    "application_name": "therobotoverlord-api",
                    "timezone": "UTC",
                },
            )
            logger.info("Database connection pool initialized")

        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    async def disconnect(self) -> None:
        """Close the database connection pool."""
        if self._pool is None:
            logger.warning("Database pool not initialized")
            return

        try:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

        except Exception as e:
            logger.error(f"Error closing database pool: {e}")
            raise

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Connection]:
        """Get a database connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Database pool not initialized. Call connect() first.")

        async with self._pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                raise

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[Connection]:
        """Get a database connection with an active transaction."""
        async with self.get_connection() as connection:
            async with connection.transaction():
                yield connection

    async def execute(self, query: str, *args) -> str:
        """Execute a query and return the status."""
        async with self.get_connection() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """Execute a query and return all results."""
        async with self.get_connection() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        """Execute a query and return the first result."""
        async with self.get_connection() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Execute a query and return a single value."""
        async with self.get_connection() as connection:
            return await connection.fetchval(query, *args)

    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            async with self.get_connection() as connection:
                await connection.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def get_pool_stats(self) -> dict:
        """Get connection pool statistics."""
        if self._pool is None:
            return {"status": "not_initialized"}

        return {
            "status": "initialized",
            "size": self._pool.get_size(),
            "min_size": self._pool.get_min_size(),
            "max_size": self._pool.get_max_size(),
            "idle_size": self._pool.get_idle_size(),
        }


# Global database instance
db = Database()


async def init_database() -> None:
    """Initialize the global database connection."""
    await db.connect()


async def close_database() -> None:
    """Close the global database connection."""
    await db.disconnect()


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[Connection]:
    """Get a database connection from the global pool."""
    async with db.get_connection() as connection:
        yield connection


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[Connection]:
    """Get a database transaction from the global pool."""
    async with db.get_transaction() as connection:
        yield connection
