"""Tests for authentication API endpoints."""

import asyncio

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import status
from httpx import ASGITransport
from httpx import AsyncClient

from therobotoverlord_api.database.models.base import UserRole


class TestAuthAPIEndpoints:
    """Test authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_login_endpoint(self, async_client: AsyncClient):
        """Test login endpoint returns authorization URL."""
        response = await async_client.get("/api/v1/auth/login")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "ok"
        assert "authorization_url" in data["data"]
        auth_url = data["data"]["authorization_url"]
        assert "https://accounts.google.com/o/oauth2/auth" in auth_url

    @pytest.mark.asyncio
    async def test_callback_endpoint_success(self, async_client: AsyncClient):
        """Test successful OAuth callback."""
        with patch("therobotoverlord_api.api.auth.AuthService") as mock_auth:
            mock_auth_service = AsyncMock()
            mock_auth.return_value = mock_auth_service

            # Mock complete_login method
            mock_auth_service.complete_login.return_value = (
                {
                    "user_id": str(uuid4()),
                    "username": "testuser",
                    "email": "test@example.com",
                },
                MagicMock(),  # token_pair mock
            )

            with patch("therobotoverlord_api.api.auth._set_auth_cookies"):
                response = await async_client.request(
                    "GET",
                    "/api/v1/auth/callback",
                    json={"code": "mock_code", "state": "mock_state"},
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()

                assert data["status"] == "ok"
                assert "user_id" in data["data"]
                assert "username" in data["data"]
                assert "email" in data["data"]

    @pytest.mark.asyncio
    async def test_callback_endpoint_invalid_code(self, async_client: AsyncClient):
        """Test OAuth callback with invalid code."""
        with patch("therobotoverlord_api.api.auth.AuthService") as mock_auth:
            mock_auth_service = AsyncMock()
            mock_auth.return_value = mock_auth_service

            # Mock failed complete_login
            mock_auth_service.complete_login.side_effect = ValueError("Invalid code")

            response = await async_client.request(
                "GET",
                "/api/v1/auth/callback",
                json={"code": "invalid_code", "state": "test_state"},
            )

            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ]

    @pytest.mark.asyncio
    async def test_refresh_endpoint_success(self, authenticated_client: AsyncClient):
        """Test successful token refresh."""
        # Mock the dependency injection auth
        with patch(
            "therobotoverlord_api.auth.dependencies.get_current_user"
        ) as mock_get_user:
            # Create a mock user
            mock_user = MagicMock()
            mock_user.pk = uuid4()
            mock_user.role = UserRole.CITIZEN
            mock_user.is_banned = False
            mock_get_user.return_value = mock_user

            with patch("therobotoverlord_api.api.auth.AuthService") as mock_auth:
                mock_auth_service = AsyncMock()
                mock_auth.return_value = mock_auth_service

                # Mock successful token refresh
                mock_auth_service.refresh_tokens.return_value = MagicMock()

                with patch("therobotoverlord_api.api.auth._set_auth_cookies"):
                    response = await authenticated_client.post("/api/v1/auth/refresh")

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()

                    assert data["status"] == "ok"
                    assert "message" in data["data"]

    @pytest.mark.asyncio
    async def test_refresh_endpoint_no_token(self, async_client: AsyncClient):
        """Test refresh without refresh token."""
        response = await async_client.post("/api/v1/auth/refresh")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_logout_endpoint_current_session(self, app):
        """Test logout current session."""
        from therobotoverlord_api.auth.dependencies import get_current_user
        from therobotoverlord_api.database.models.user import User

        test_user_id = uuid4()

        # Create a mock user to return from dependency
        mock_user = MagicMock(spec=User)
        mock_user.pk = test_user_id
        mock_user.id = test_user_id
        mock_user.role = UserRole.CITIZEN
        mock_user.is_banned = False

        # Override the dependency
        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            with patch("therobotoverlord_api.api.auth.AuthService") as mock_auth:
                mock_auth_service = AsyncMock()
                mock_auth.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/v1/auth/logout", json={"revoke_all_sessions": False}
                    )

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()

                    assert data["status"] == "ok"
                    assert "message" in data["data"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_logout_endpoint_all_sessions(self, app):
        """Test logout all sessions."""
        from therobotoverlord_api.auth.dependencies import get_current_user
        from therobotoverlord_api.database.models.user import User

        test_user_id = uuid4()

        # Create a mock user to return from dependency
        mock_user = MagicMock(spec=User)
        mock_user.pk = test_user_id
        mock_user.id = test_user_id
        mock_user.role = UserRole.CITIZEN
        mock_user.is_banned = False

        # Override the dependency
        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            with patch("therobotoverlord_api.api.auth.AuthService") as mock_auth:
                mock_auth_service = AsyncMock()
                mock_auth.return_value = mock_auth_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/v1/auth/logout", json={"revoke_all_sessions": True}
                    )

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()

                    assert data["status"] == "ok"
                    assert "message" in data["data"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_me_endpoint_authenticated(self, app):
        """Test /me endpoint with authenticated user."""
        from therobotoverlord_api.auth.dependencies import get_current_user
        from therobotoverlord_api.database.models.user import User

        test_user_id = uuid4()

        # Create a mock user to return from dependency
        mock_user = MagicMock(spec=User)
        mock_user.pk = test_user_id
        mock_user.id = test_user_id  # Auth service expects 'id' attribute
        mock_user.role = UserRole.CITIZEN
        mock_user.is_banned = False

        # Override the dependency
        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            auth_service_patch = (
                "therobotoverlord_api.api.auth.AuthService.get_user_info"
            )
            with patch(auth_service_patch) as mock_get_info:
                # Create a mock user object with the required attributes
                mock_user_info = MagicMock()
                mock_user_info.pk = test_user_id
                mock_user_info.username = "testuser"
                mock_user_info.email = "test@example.com"
                mock_user_info.role = "citizen"
                mock_user_info.loyalty_score = 100
                mock_user_info.created_at = "2024-01-01T00:00:00Z"
                mock_user_info.updated_at = "2024-01-01T00:00:00Z"

                mock_get_info.return_value = mock_user_info

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/v1/auth/me")

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()

                    assert data["status"] == "ok"
                    assert "user_id" in data["data"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_me_endpoint_unauthorized(self, async_client: AsyncClient):
        """Test /me endpoint without authentication."""
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_jwks_endpoint(self, async_client: AsyncClient):
        """Test JWKS endpoint."""
        jwks_patch = (
            "therobotoverlord_api.auth.jwt_service.JWTService.create_jwks_response"
        )
        with patch(jwks_patch) as mock_jwks:
            mock_jwks.return_value = {
                "keys": [{"kty": "oct", "use": "sig", "alg": "HS256", "k": "test_key"}]
            }

            response = await async_client.get("/api/v1/auth/jwks")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "keys" in data
            assert len(data["keys"]) == 1

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, async_client: AsyncClient):
        """Test concurrent API requests."""

        async def make_login_request():
            return await async_client.get("/api/v1/auth/login")

        # Make multiple concurrent login requests
        tasks = [make_login_request() for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_api_response_format_consistency(self, async_client: AsyncClient):
        """Test API response format consistency."""
        response = await async_client.get("/api/v1/auth/login")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check consistent response format
        assert isinstance(data, dict)
        assert data["status"] == "ok"
        assert "authorization_url" in data["data"]
