"""Test fixtures and utilities for authentication tests."""

import asyncio
import os

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from httpx import AsyncClient

from therobotoverlord_api.api.auth import router as auth_router
from therobotoverlord_api.auth.jwt_service import JWTService
from therobotoverlord_api.auth.middleware import AuthenticationMiddleware
from therobotoverlord_api.auth.models import GoogleUserInfo
from therobotoverlord_api.auth.models import TokenClaims
from therobotoverlord_api.auth.session_service import SessionService
from therobotoverlord_api.config.auth import AuthSettings
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserCreate
from therobotoverlord_api.database.models.user import UserUpdate


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def auth_settings():
    """Create test authentication settings."""
    return AuthSettings(
        google_client_id="test_client_id",
        google_client_secret="test_client_secret",
        google_redirect_uri="http://localhost:8000/api/v1/auth/callback",
        jwt_secret_key="test_secret_key_32_bytes_long_12345",
        jwt_algorithm="HS256",
        jwt_issuer="test-issuer",
        jwt_audience="test-audience",
        access_token_lifetime=3600,
        access_token_max_lifetime=28800,
        access_token_extension=1800,
        refresh_token_lifetime=1209600,
        cookie_domain=".test.com",
        cookie_secure=False,
        cookie_samesite="lax",
        session_cleanup_interval=3600,
    )


@pytest.fixture
def jwt_service(auth_settings):
    """Create JWT service instance."""
    with patch(
        "therobotoverlord_api.auth.jwt_service.get_auth_settings",
        return_value=auth_settings,
    ):
        return JWTService()


@pytest.fixture
def session_service():
    """Create session service instance."""
    return SessionService()


@pytest.fixture
def test_user_id():
    """Generate a test user ID."""
    return uuid4()


@pytest.fixture
def test_user(test_user_id):
    """Create a test user."""
    return User(
        pk=test_user_id,
        username="testuser",
        email="test@example.com",
        role=UserRole.CITIZEN,
        loyalty_score=100,
        is_banned=False,
        google_id="123456789",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def test_user_create():
    """Create test user creation data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "google_id": "123456789",
    }


@pytest.fixture
def google_user_info():
    """Create test Google user info."""
    return GoogleUserInfo(
        id="123456789",
        email="test@example.com",
        verified_email=True,
        name="Test User",
        given_name="Test",
        family_name="User",
        picture="https://example.com/avatar.jpg",
    )


@pytest.fixture
def test_token_claims(test_user_id):
    """Create test token claims."""
    now = datetime.now(UTC)
    return TokenClaims(
        sub=test_user_id,
        role=UserRole.CITIZEN,
        permissions=["view_content", "create_posts"],
        sid="test_session_id",
        authz_ver=1,
        iat=int(now.timestamp()),
        exp=int((now + timedelta(hours=1)).timestamp()),
        nbf=int(now.timestamp()),
        iss="test-issuer",
        aud="test-audience",
    )


@pytest.fixture
def valid_access_token(jwt_service, test_token_claims):
    """Create a valid access token."""
    claims_dict = test_token_claims.model_dump()
    return jwt_service._encode_token(claims_dict)


@pytest.fixture
def expired_access_token(jwt_service, test_token_claims):
    """Create an expired access token."""
    expired_claims = test_token_claims.model_copy()
    expired_claims.exp = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
    claims_dict = expired_claims.model_dump()
    return jwt_service._encode_token(claims_dict)


@pytest.fixture
def valid_refresh_token(jwt_service, test_token_claims):
    """Create a valid refresh token."""
    refresh_claims = test_token_claims.model_copy()
    refresh_claims.exp = int((datetime.now(UTC) + timedelta(days=14)).timestamp())
    claims_dict = refresh_claims.model_dump()
    return jwt_service._encode_token(claims_dict)


@pytest.fixture
def mock_user_repository():
    """Create a mock user repository."""

    class MockUserRepository:
        def __init__(self):
            self.users = {}

        async def get_by_pk(self, pk: UUID) -> User | None:
            return self.users.get(pk)

        async def get_by_email(self, email: str) -> User | None:
            for user in self.users.values():
                if user.email == email:
                    return user
            return None

        async def get_by_google_id(self, google_id: str) -> User | None:
            for user in self.users.values():
                if user.google_id == google_id:
                    return user
            return None

        async def get_by_username(self, username: str) -> User | None:
            for user in self.users.values():
                if user.username == username:
                    return user
            return None

        async def create(self, user_data: UserCreate) -> User:
            user = User(
                pk=uuid4(),
                username=user_data.username,
                email=user_data.email,
                role=user_data.role,
                loyalty_score=0,
                is_banned=False,
                google_id=user_data.google_id,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self.users[user.pk] = user
            return user

        async def update(self, pk: UUID, update_data: UserUpdate) -> User | None:
            user = self.users.get(pk)
            if not user:
                return None

            # Update fields
            for field, value in update_data.model_dump(exclude_unset=True).items():
                setattr(user, field, value)
            user.updated_at = datetime.now(UTC)
            return user

    return MockUserRepository()


@pytest.fixture
def app():
    """Create FastAPI test application."""
    # Set test environment variables
    os.environ.update(
        {
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
            "AUTH_GOOGLE_CLIENT_ID": "test_client_id",
            "AUTH_GOOGLE_CLIENT_SECRET": "test_client_secret",
            "AUTH_JWT_SECRET_KEY": "test_secret_key_32_bytes_long_12345",
        }
    )

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

    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware)

    # Include routers
    app.include_router(auth_router, prefix="/api/v1")

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
async def async_client(app):
    """Create async test client."""
    async with AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client(app, valid_access_token, valid_refresh_token):
    """Create authenticated test client with valid tokens."""
    async with AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Set authentication cookies
        client.cookies.set("__Secure-trl_at", valid_access_token)
        client.cookies.set("__Secure-trl_rt", valid_refresh_token)
        yield client


@pytest.fixture
def mock_google_oauth_response():
    """Create mock Google OAuth response."""
    return {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "openid email profile",
        "id_token": "mock_id_token",
    }


@pytest.fixture
def mock_session_data():
    """Create mock session data."""
    return {
        "session_id": "test_session_id",
        "user_id": uuid4(),
        "refresh_token_hash": "hashed_refresh_token",
        "ip_address": "127.0.0.1",
        "user_agent": "Test User Agent",
        "created_at": datetime.now(UTC),
        "last_used_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC) + timedelta(days=14),
    }


class MockHTTPXClient:
    """Mock httpx client for testing external API calls."""

    def __init__(self):
        self.responses = {}

    def set_response(self, url: str, response_data: dict, status_code: int = 200):
        """Set mock response for a URL."""
        self.responses[url] = {
            "json": response_data,
            "status_code": status_code,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""

    async def post(self, url: str, **kwargs):
        """Mock POST request."""
        response_data = self.responses.get(url, {"json": {}, "status_code": 404})

        class MockResponse:
            def __init__(self, json_data, status_code):
                self._json_data = json_data
                self.status_code = status_code

            def json(self):
                return self._json_data

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception(f"HTTP {self.status_code}")  # noqa: TRY002

        return MockResponse(response_data["json"], response_data["status_code"])

    async def get(self, url: str, **kwargs):
        """Mock GET request."""
        return await self.post(url, **kwargs)


@pytest.fixture
def mock_httpx_client():
    """Create mock httpx client."""
    return MockHTTPXClient()
