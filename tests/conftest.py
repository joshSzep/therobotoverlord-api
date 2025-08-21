"""Test configuration and fixtures for The Robot Overlord API tests."""

import asyncio

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio

from asyncpg import Record
from fastapi.testclient import TestClient
from httpx import ASGITransport
from httpx import AsyncClient

from therobotoverlord_api.config.database import DatabaseSettings
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserCreate
from therobotoverlord_api.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database_settings() -> DatabaseSettings:
    """Mock database settings for testing."""
    return DatabaseSettings(
        database_url="postgresql://test:test@localhost:5432/test_db",
        username="test",
        password="test",
        host="localhost",
        port=5432,
        database="test_db",
        ssl_mode="disable",
        min_pool_size=1,
        max_pool_size=5,
        pool_timeout=10.0,
        query_timeout=10.0,
        command_timeout=10.0,
    )


@pytest.fixture
def mock_connection():
    """Mock database connection for testing."""
    connection = AsyncMock()
    connection.fetchval = AsyncMock()
    connection.fetchrow = AsyncMock()
    connection.fetch = AsyncMock()
    connection.execute = AsyncMock()
    return connection


@pytest.fixture
def mock_pool():
    """Mock database connection pool for testing."""
    pool = AsyncMock()
    pool.get_size.return_value = 5
    pool.get_min_size.return_value = 1
    pool.get_max_size.return_value = 10
    pool.get_idle_size.return_value = 3
    return pool


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for testing."""
    return {
        "pk": uuid4(),
        "email": "test@example.com",
        "google_id": "google123",
        "username": "testuser",
        "role": UserRole.CITIZEN,
        "loyalty_score": 50,
        "is_banned": False,
        "is_sanctioned": False,
        "email_verified": True,
        "created_at": datetime.now(UTC),
        "updated_at": None,
    }


@pytest.fixture
def sample_user(sample_user_data) -> User:
    """Sample User model for testing."""
    return User.model_validate(sample_user_data)


@pytest.fixture
def sample_user_create() -> UserCreate:
    """Sample UserCreate model for testing."""
    return UserCreate(
        email="newuser@example.com",
        google_id="google456",
        username="newuser",
        role=UserRole.CITIZEN,
        email_verified=False,
    )


@pytest.fixture
def mock_record(sample_user_data) -> Record:
    """Mock database record for testing."""
    record = MagicMock(spec=Record)

    # Make the record behave like a dictionary
    def getitem(key):
        return sample_user_data[key]

    def get(key, default=None):
        return sample_user_data.get(key, default)

    def keys():
        return sample_user_data.keys()

    def values():
        return sample_user_data.values()

    def items():
        return sample_user_data.items()

    record.__getitem__ = getitem
    record.get = get
    record.keys = keys
    record.values = values
    record.items = items

    # Support iteration and dict() conversion
    record.__iter__ = lambda: iter(sample_user_data.keys())
    record.__len__ = lambda: len(sample_user_data)

    # Support dict() conversion by implementing the mapping protocol
    def dict_conversion():
        return sample_user_data

    # Mock the dict() behavior by patching the record to return sample_user_data when converted
    record._asdict = lambda: sample_user_data
    record.dict = lambda: sample_user_data

    return record


@pytest.fixture
def mock_records(sample_user_data) -> list[Record]:
    """Mock list of database records for testing."""
    records = []
    for i in range(3):
        record = MagicMock(spec=Record)
        data = sample_user_data.copy()
        data["pk"] = uuid4()
        data["username"] = f"testuser{i}"
        data["email"] = f"test{i}@example.com"

        def make_getitem(record_data):
            def getitem(key):
                return record_data[key]

            return getitem

        def make_get(record_data):
            def get(key, default=None):
                return record_data.get(key, default)

            return get

        def make_keys(record_data):
            def keys():
                return record_data.keys()

            return keys

        def make_values(record_data):
            def values():
                return record_data.values()

            return values

        def make_items(record_data):
            def items():
                return record_data.items()

            return items

        def make_iter(record_data):
            def iter_func():
                return iter(record_data.keys())

            return iter_func

        record.__getitem__ = make_getitem(data)
        record.get = make_get(data)
        record.keys = make_keys(data)
        record.values = make_values(data)
        record.items = make_items(data)
        record.__iter__ = make_iter(data)
        record.__len__ = lambda: len(data)

        # Support dict() conversion
        record._asdict = lambda: data
        record.dict = lambda: data

        records.append(record)

    return records


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Async FastAPI test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def get_appeal_service():
    """Mock get_appeal_service dependency."""
    return AsyncMock()


@pytest.fixture
def require_moderator():
    """Mock require_moderator dependency."""
    return MagicMock(pk=uuid4(), role=UserRole.MODERATOR)


@pytest.fixture
def citizen_user_headers():
    """Mock headers for citizen user authentication."""
    return {"Authorization": "Bearer mock_citizen_token"}


@pytest.fixture
def moderator_user_headers():
    """Mock headers for moderator user authentication."""
    return {"Authorization": "Bearer mock_moderator_token"}


@pytest.fixture
def mock_flag_service():
    """Mock flag service for testing."""
    return AsyncMock()
