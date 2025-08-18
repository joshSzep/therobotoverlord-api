"""Tests for authentication middleware."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status
from starlette.responses import JSONResponse

from therobotoverlord_api.auth.middleware import AuthenticatedUser
from therobotoverlord_api.auth.middleware import AuthenticationMiddleware
from therobotoverlord_api.auth.middleware import get_current_user
from therobotoverlord_api.auth.middleware import get_current_user_optional
from therobotoverlord_api.auth.models import TokenClaims
from therobotoverlord_api.database.models.base import UserRole


class TestAuthenticatedUser:
    """Test AuthenticatedUser class."""

    def test_authenticated_user_creation(self, test_user_id):
        """Test creating authenticated user."""
        user = AuthenticatedUser(
            user_id=test_user_id,
            role=UserRole.CITIZEN,
            permissions=["view_content", "create_posts"],
            session_id="test_session",
            token_version=1,
        )

        assert user.user_id == test_user_id
        assert user.role == UserRole.CITIZEN
        assert user.permissions == ["view_content", "create_posts"]
        assert user.session_id == "test_session"
        assert user.token_version == 1

    def test_has_permission(self, test_user_id):
        """Test permission checking."""
        user = AuthenticatedUser(
            user_id=test_user_id,
            role=UserRole.CITIZEN,
            permissions=["view_content", "create_posts"],
            session_id="test_session",
        )

        assert user.has_permission("view_content") is True
        assert user.has_permission("create_posts") is True
        assert user.has_permission("moderate_content") is False

    def test_has_role(self, test_user_id):
        """Test role checking."""
        citizen = AuthenticatedUser(
            user_id=test_user_id,
            role=UserRole.CITIZEN,
            permissions=[],
            session_id="test_session",
        )

        moderator = AuthenticatedUser(
            user_id=test_user_id,
            role=UserRole.MODERATOR,
            permissions=[],
            session_id="test_session",
        )

        admin = AuthenticatedUser(
            user_id=test_user_id,
            role=UserRole.ADMIN,
            permissions=[],
            session_id="test_session",
        )

        # Test role hierarchy
        assert citizen.has_role(UserRole.CITIZEN) is True
        assert citizen.has_role(UserRole.MODERATOR) is False

        assert moderator.has_role(UserRole.CITIZEN) is True
        assert moderator.has_role(UserRole.MODERATOR) is True
        assert moderator.has_role(UserRole.ADMIN) is False

        assert admin.has_role(UserRole.CITIZEN) is True
        assert admin.has_role(UserRole.MODERATOR) is True
        assert admin.has_role(UserRole.ADMIN) is True


class TestAuthenticationMiddleware:
    """Test authentication middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        with (
            patch("therobotoverlord_api.auth.middleware.JWTService") as mock_jwt_cls,
            patch(
                "therobotoverlord_api.auth.middleware.SessionService"
            ) as mock_session_cls,
            patch(
                "therobotoverlord_api.auth.middleware.UserRepository"
            ) as mock_user_cls,
        ):
            # Create mock instances
            mock_jwt_cls.return_value = MagicMock()
            mock_session_cls.return_value = MagicMock()
            mock_user_cls.return_value = MagicMock()

            return AuthenticationMiddleware(app=MagicMock())

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/protected"
        request.cookies = {}
        request.headers = {}
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        return MagicMock(spec=Response)

    @pytest.mark.asyncio
    async def test_public_path_bypass(self, middleware, mock_request):
        """Test that public paths bypass authentication."""
        # Test various public paths
        public_paths = [
            "/docs",
            "/openapi.json",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/callback",
            "/api/v1/auth/jwks",
            "/api/v1/queue/overview",
            "/api/v1/leaderboard",
        ]

        for path in public_paths:
            mock_request.url.path = path
            assert middleware._is_public_endpoint(path) is True

    def test_private_path_requires_auth(self, middleware):
        """Test that private paths require authentication."""
        private_paths = [
            "/api/v1/posts",
            "/api/v1/users/me",
            "/api/v1/admin/users",
        ]

        for path in private_paths:
            assert middleware._is_public_endpoint(path) is False

    @pytest.mark.asyncio
    async def test_valid_token_authentication(
        self, middleware, mock_request, mock_response, valid_access_token, test_user
    ):
        """Test authentication with valid token."""
        # Set valid token in cookies
        mock_request.cookies = {"__Secure-trl_at": valid_access_token}

        # Mock JWT validation
        now = datetime.now(UTC)
        mock_claims = TokenClaims(
            sub=test_user.pk,
            role=test_user.role,
            permissions=["view_content"],
            sid="test_session",
            authz_ver=1,
            iat=int(now.timestamp()),
            exp=int((now + timedelta(hours=1)).timestamp()),
            nbf=int(now.timestamp()),
            iss="test-issuer",
            aud="test-audience",
        )
        middleware.jwt_service.decode_token_claims.return_value = mock_claims

        # Mock user lookup
        middleware.user_repository.get_by_pk.return_value = test_user

        # Mock _get_authenticated_user to return AuthenticatedUser
        expected_auth_user = AuthenticatedUser(
            user_id=test_user.pk,
            role=test_user.role,
            permissions=["view_content"],
            session_id="test_session",
        )

        with patch.object(
            middleware, "_get_authenticated_user", return_value=expected_auth_user
        ):
            # Mock call_next
            async def mock_call_next(request):
                return JSONResponse({"message": "success"})

            await middleware.dispatch(mock_request, mock_call_next)

        # Verify user context was set
        assert hasattr(mock_request.state, "user")
        assert mock_request.state.user.user_id == test_user.pk

    @pytest.mark.asyncio
    async def test_expired_token_refresh(
        self,
        middleware,
        mock_request,
        mock_response,
        expired_access_token,
        valid_refresh_token,
    ):
        """Test automatic token refresh for expired access token."""
        # Set expired access token and valid refresh token
        mock_request.cookies = {
            "__Secure-trl_at": expired_access_token,
            "__Secure-trl_rt": valid_refresh_token,
        }

        # Mock JWT service for expired token then valid token after refresh
        now = datetime.now(UTC)
        middleware.jwt_service.decode_token_claims.side_effect = [
            None,  # Expired token
            TokenClaims(
                sub=uuid4(),
                role=UserRole.CITIZEN,
                permissions=["view_content"],
                sid="test_session",
                authz_ver=1,
                iat=int(now.timestamp()),
                exp=int((now + timedelta(hours=1)).timestamp()),
                nbf=int(now.timestamp()),
                iss="test-issuer",
                aud="test-audience",
            ),
        ]

        # Mock refresh tokens and cookie setting
        with patch.object(
            middleware,
            "_refresh_tokens",
            return_value=("new_access_token", "new_refresh_token"),
        ):
            with patch.object(middleware, "_set_auth_cookies") as mock_set_cookies:
                # Mock user repository
                middleware.user_repository.get_by_pk.return_value = MagicMock(
                    is_banned=False
                )

                # Mock _get_authenticated_user
                expected_auth_user = AuthenticatedUser(
                    user_id=uuid4(),
                    role=UserRole.CITIZEN,
                    permissions=["view_content"],
                    session_id="test_session",
                )

                with patch.object(
                    middleware,
                    "_get_authenticated_user",
                    return_value=expected_auth_user,
                ):

                    async def mock_call_next(request):
                        return JSONResponse({"message": "success"})

                    response = await middleware.dispatch(mock_request, mock_call_next)

                    # Verify refresh was attempted
                    assert response is not None
                    mock_set_cookies.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_token_unauthorized(self, middleware, mock_request):
        """Test request without authentication token."""
        mock_request.cookies = {}

        async def mock_call_next(request):
            return JSONResponse({"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 401
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_invalid_token_unauthorized(self, middleware, mock_request):
        """Test request with invalid token."""
        mock_request.cookies = {"__Secure-trl_at": "invalid.token.here"}

        # Mock JWT service to return None for invalid token
        middleware.jwt_service.decode_token_claims.return_value = None

        async def mock_call_next(request):
            return JSONResponse({"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 401
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_banned_user_unauthorized(
        self, middleware, mock_request, valid_access_token, test_token_claims
    ):
        """Test that banned users are rejected."""
        mock_request.cookies = {"__Secure-trl_at": valid_access_token}

        # Mock JWT service to return valid claims
        middleware.jwt_service.decode_token_claims.return_value = test_token_claims

        # Mock banned user
        banned_user = MagicMock()
        banned_user.is_banned = True
        middleware.user_repository.get_by_pk.return_value = banned_user

        async def mock_call_next(request):
            return JSONResponse({"message": "success"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 401
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_token_refresh_failure(
        self, middleware, mock_request, expired_access_token, valid_refresh_token
    ):
        """Test handling of token refresh failure."""
        mock_request.cookies = {
            "__Secure-trl_at": expired_access_token,
            "__Secure-trl_rt": valid_refresh_token,
        }

        # Mock JWT service to return None for expired token
        middleware.jwt_service.decode_token_claims.return_value = None

        # Mock refresh tokens to fail
        with patch.object(middleware, "_refresh_tokens", return_value=None):

            async def mock_call_next(request):
                return JSONResponse({"message": "success"})

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 401
            assert response.headers["content-type"] == "application/json"

    def test_set_auth_cookies(self, middleware, mock_response):
        """Test setting authentication cookies."""
        access_token = "test_access_token"
        refresh_token = "test_refresh_token"

        with patch(
            "therobotoverlord_api.auth.middleware.get_auth_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cookie_secure=True,
                cookie_samesite="lax",
                cookie_domain=".test.com",
                access_token_lifetime=3600,
                refresh_token_lifetime=1209600,
            )

            middleware._set_auth_cookies(mock_response, access_token, refresh_token)

            # Verify cookies were set
            assert mock_response.set_cookie.call_count == 2

    @pytest.mark.asyncio
    async def test_get_client_ip(self, middleware, mock_request):
        """Test client IP extraction."""
        # Test X-Forwarded-For header
        mock_request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.100"

        # Test X-Real-IP header
        mock_request.headers = {"x-real-ip": "192.168.1.200"}
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.200"

        # Test client host fallback
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"
        ip = middleware._get_client_ip(mock_request)
        assert ip == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_middleware_error_handling(self, middleware, mock_request):
        """Test middleware error handling."""
        mock_request.cookies = {"__Secure-trl_at": "valid_token"}

        # Mock JWT service to raise exception
        middleware.jwt_service.decode_token_claims.side_effect = Exception("JWT error")

        async def mock_call_next(request):
            return JSONResponse({"message": "success"})

        # Should raise HTTPException on JWT error
        with pytest.raises(Exception, match="JWT error"):
            await middleware.dispatch(mock_request, mock_call_next)

    @pytest.mark.asyncio
    async def test_optional_authentication_dependency(self, test_user_id):
        """Test optional authentication dependency."""

        # Mock request with authenticated user
        mock_request = MagicMock()
        mock_request.state.user = AuthenticatedUser(
            user_id=test_user_id,
            role=UserRole.CITIZEN,
            permissions=["view_content"],
            session_id="test_session",
        )

        user = await get_current_user_optional(mock_request)
        assert user is not None
        assert user.user_id == test_user_id

        # Mock request without authenticated user
        mock_request.state.user = None
        user = await get_current_user_optional(mock_request)
        assert user is None

    @pytest.mark.asyncio
    async def test_required_authentication_dependency(self, test_user_id):
        """Test required authentication dependency."""

        # Mock request with authenticated user
        mock_request = MagicMock()
        mock_request.state.user = AuthenticatedUser(
            user_id=test_user_id,
            role=UserRole.CITIZEN,
            permissions=["view_content"],
            session_id="test_session",
        )

        user = await get_current_user(mock_request)
        assert user is not None
        assert user.user_id == test_user_id

        # Mock request without authenticated user
        mock_request.state.user = None
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        exception = exc_info.value
        assert isinstance(exception, HTTPException)
        assert exception.status_code == status.HTTP_403_FORBIDDEN
