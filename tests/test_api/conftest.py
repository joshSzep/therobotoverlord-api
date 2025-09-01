"""Test configuration for API coverage tests."""

from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
import pytest_asyncio

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from httpx import ASGITransport
from httpx import AsyncClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from therobotoverlord_api.api.auth import router as auth_router
from therobotoverlord_api.api.badges import router as badges_router
from therobotoverlord_api.api.leaderboard import router as leaderboard_router
from therobotoverlord_api.api.loyalty_score import router as loyalty_score_router
from therobotoverlord_api.api.queue import router as queue_router
from therobotoverlord_api.api.rbac import router as rbac_router
from therobotoverlord_api.api.tags import router as tags_router
from therobotoverlord_api.api.topics import router as topics_router
from therobotoverlord_api.api.translations import router as translations_router


@pytest.fixture
def app():
    """Create test FastAPI app without database initialization."""
    # Create app without lifespan to avoid database initialization
    app = FastAPI(
        title="The Robot Overlord API",
        description="A satirical AI-moderated debate platform",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://therobotoverlord.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handler for HTTPException
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    # Include routers with /api/v1 prefix
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(badges_router, prefix="/api/v1")
    app.include_router(leaderboard_router, prefix="/api/v1")
    app.include_router(loyalty_score_router, prefix="/api/v1")
    app.include_router(queue_router, prefix="/api/v1")
    app.include_router(rbac_router, prefix="/api/v1")
    app.include_router(tags_router, prefix="/api/v1")
    app.include_router(topics_router, prefix="/api/v1")
    app.include_router(translations_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok", "database": {"healthy": True}}

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest_asyncio.fixture
def async_client(app):
    """Create an async test client with mocked dependencies."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(scope="session", autouse=True)
def mock_redis_globally():
    """Mock Redis connections globally for all tests."""
    # Mock at the module level before any imports happen
    patches = []

    # Mock Redis client creation
    mock_redis_client = AsyncMock()
    mock_redis_client.get.return_value = None
    mock_redis_client.set.return_value = True
    mock_redis_client.delete.return_value = 1
    mock_redis_client.exists.return_value = False
    mock_redis_client.ping.return_value = True
    mock_redis_client.close.return_value = None
    mock_redis_client.hget.return_value = None
    mock_redis_client.hset.return_value = True
    mock_redis_client.hdel.return_value = 1

    # Mock Redis pool
    mock_redis_pool = AsyncMock()
    mock_redis_pool.ping.return_value = True
    mock_redis_pool.get_connection.return_value = mock_redis_client

    # Patch all Redis-related functions
    patches.extend(
        [
            patch(
                "therobotoverlord_api.workers.redis_connection.get_redis_client",
                return_value=mock_redis_client,
            ),
            patch(
                "therobotoverlord_api.workers.redis_connection.get_redis_pool",
                return_value=mock_redis_pool,
            ),
            patch("arq.connections.create_pool", return_value=mock_redis_pool),
            patch("redis.asyncio.Redis", return_value=mock_redis_client),
            patch("redis.asyncio.ConnectionPool", return_value=mock_redis_pool),
        ]
    )

    # Start all patches
    for p in patches:
        p.start()

    yield {
        "client": mock_redis_client,
        "pool": mock_redis_pool,
    }

    # Stop all patches
    for p in patches:
        p.stop()


@pytest.fixture(autouse=True)
def mock_database_connection():
    """Mock database connection to prevent connection errors."""
    with patch("therobotoverlord_api.database.connection.get_db_connection") as mock_db:
        mock_connection = AsyncMock()
        mock_connection.fetch.return_value = []
        mock_connection.fetchrow.return_value = None
        mock_connection.fetchval.return_value = None
        mock_connection.execute.return_value = None

        mock_db.return_value.__aenter__.return_value = mock_connection
        mock_db.return_value.__aexit__.return_value = None

        # Also mock the Database class methods
        with patch(
            "therobotoverlord_api.database.connection.Database.get_connection"
        ) as mock_db_conn:
            mock_db_conn.return_value.__aenter__.return_value = mock_connection
            mock_db_conn.return_value.__aexit__.return_value = None

            yield
