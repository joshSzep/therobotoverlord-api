"""Tests for WebSocket authentication and authorization."""

from datetime import UTC
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from fastapi import HTTPException
from fastapi import WebSocket
from fastapi import status

from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.websocket.auth import authenticate_websocket
from therobotoverlord_api.websocket.auth import authorize_channel_access
from therobotoverlord_api.websocket.auth import require_websocket_role


class TestWebSocketAuthentication:
    """Test WebSocket authentication functions."""

    @pytest.mark.asyncio
    async def test_authenticate_websocket_missing_token(self):
        """Test authentication fails when token is missing."""
        websocket = AsyncMock(spec=WebSocket)

        with pytest.raises(HTTPException) as exc_info:
            await authenticate_websocket(websocket, token=None)

        exc = cast("HTTPException", exc_info.value)
        assert exc.status_code == 401
        assert "Authentication token required" in str(exc.detail)
        websocket.close.assert_called_once_with(
            code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token"
        )

    @pytest.mark.asyncio
    async def test_authenticate_websocket_invalid_token(self):
        """Test authentication fails with invalid token."""
        websocket = AsyncMock(spec=WebSocket)

        with patch("therobotoverlord_api.websocket.auth.JWTService") as mock_jwt:
            mock_jwt.return_value.decode_token.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await authenticate_websocket(websocket, token="invalid_token")

            exc = cast("HTTPException", exc_info.value)
            assert exc.status_code == 401
            assert "Authentication failed" in str(exc.detail)
            websocket.close.assert_called_with(
                code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed"
            )

    @pytest.mark.asyncio
    async def test_authenticate_websocket_user_not_found(self):
        """Test authentication fails when user not found."""
        websocket = AsyncMock(spec=WebSocket)
        user_id = uuid4()

        mock_claims = MagicMock()
        mock_claims.sub = str(user_id)

        with patch("therobotoverlord_api.websocket.auth.JWTService") as mock_jwt:
            mock_jwt.return_value.decode_token.return_value = mock_claims

            with patch(
                "therobotoverlord_api.websocket.auth.UserRepository"
            ) as mock_repo:
                mock_repo.return_value.get_by_pk = AsyncMock(return_value=None)

                with pytest.raises(HTTPException) as exc_info:
                    await authenticate_websocket(websocket, token="valid_token")

                exc = cast("HTTPException", exc_info.value)
                assert exc.status_code == 401
                assert "Authentication failed" in str(exc.detail)
                websocket.close.assert_called_with(
                    code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed"
                )

    @pytest.mark.asyncio
    async def test_authenticate_websocket_inactive_user(self):
        """Test authentication fails when user is inactive."""
        websocket = AsyncMock(spec=WebSocket)
        user_id = uuid4()

        mock_claims = MagicMock()
        mock_claims.sub = str(user_id)

        user = User(
            pk=user_id,
            email="test@example.com",
            google_id="google123",
            username="testuser",
            role=UserRole.CITIZEN,
            is_active=False,
            created_at=datetime.now(UTC),
        )

        with patch("therobotoverlord_api.websocket.auth.JWTService") as mock_jwt:
            mock_jwt.return_value.decode_token.return_value = mock_claims

            with patch(
                "therobotoverlord_api.websocket.auth.UserRepository"
            ) as mock_repo:
                mock_repo.return_value.get_by_pk = AsyncMock(return_value=user)

                with pytest.raises(HTTPException) as exc_info:
                    await authenticate_websocket(websocket, token="valid_token")

                exc = cast("HTTPException", exc_info.value)
                assert exc.status_code == 401
                assert "Authentication failed" in str(exc.detail)
                websocket.close.assert_called_with(
                    code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed"
                )

    @pytest.mark.asyncio
    async def test_authenticate_websocket_success(self):
        """Test successful authentication."""
        websocket = AsyncMock(spec=WebSocket)
        user_id = uuid4()

        mock_claims = MagicMock()
        mock_claims.sub = str(user_id)

        user = User(
            pk=user_id,
            email="test@example.com",
            google_id="google123",
            username="testuser",
            role=UserRole.CITIZEN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        with patch("therobotoverlord_api.websocket.auth.JWTService") as mock_jwt:
            mock_jwt.return_value.decode_token.return_value = mock_claims

            with patch(
                "therobotoverlord_api.websocket.auth.UserRepository"
            ) as mock_repo:
                mock_repo.return_value.get_by_pk = AsyncMock(return_value=user)

                result = await authenticate_websocket(websocket, token="valid_token")

                assert result == user
                websocket.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_websocket_exception_handling(self):
        """Test exception handling during authentication."""
        websocket = AsyncMock(spec=WebSocket)

        with patch("therobotoverlord_api.websocket.auth.JWTService") as mock_jwt:
            mock_jwt.return_value.decode_token.side_effect = Exception("JWT error")

            with pytest.raises(HTTPException) as exc_info:
                await authenticate_websocket(websocket, token="valid_token")

            exc = cast("HTTPException", exc_info.value)
            assert exc.status_code == 401
            assert "Authentication failed" in str(exc.detail)
            websocket.close.assert_called_once_with(
                code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed"
            )


class TestWebSocketAuthorization:
    """Test WebSocket authorization functions."""

    @pytest.mark.asyncio
    async def test_authorize_channel_access_public_channels(self):
        """Test access to public channels."""
        user = User(
            pk=uuid4(),
            email="test@example.com",
            google_id="google123",
            username="citizen",
            role=UserRole.CITIZEN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Test public channels
        assert await authorize_channel_access(user, "announcements") is True
        assert await authorize_channel_access(user, "system_status") is True

    @pytest.mark.asyncio
    async def test_authorize_channel_access_user_specific_channels(self):
        """Test access to user-specific channels."""
        user = User(
            pk=uuid4(),
            email="test@example.com",
            google_id="google123",
            username="citizen",
            role=UserRole.CITIZEN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Test user's own channels
        assert await authorize_channel_access(user, f"user_{user.pk}") is True
        assert await authorize_channel_access(user, f"user_{user.pk}_queue") is True
        assert (
            await authorize_channel_access(user, f"user_{user.pk}_notifications")
            is True
        )

        # Test other user's channels
        other_user_id = uuid4()
        assert await authorize_channel_access(user, f"user_{other_user_id}") is False

    @pytest.mark.asyncio
    async def test_authorize_channel_access_role_based_channels(self):
        """Test access to role-based channels."""
        # Test citizen access
        citizen = User(
            pk=uuid4(),
            email="citizen@example.com",
            google_id="123",
            username="citizen",
            role=UserRole.CITIZEN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert await authorize_channel_access(citizen, "moderation") is False
        assert await authorize_channel_access(citizen, "admin") is False
        assert await authorize_channel_access(citizen, "superadmin") is False

        # Test moderator access
        moderator = User(
            pk=uuid4(),
            email="mod@example.com",
            google_id="456",
            username="moderator",
            role=UserRole.MODERATOR,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert await authorize_channel_access(moderator, "moderation") is True
        assert await authorize_channel_access(moderator, "admin") is False
        assert await authorize_channel_access(moderator, "superadmin") is False

        # Test admin access
        admin = User(
            pk=uuid4(),
            email="admin@example.com",
            google_id="789",
            username="admin",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert await authorize_channel_access(admin, "moderation") is True
        assert await authorize_channel_access(admin, "admin") is True
        assert await authorize_channel_access(admin, "superadmin") is False

        # Test superadmin access
        superadmin = User(
            pk=uuid4(),
            email="super@example.com",
            google_id="999",
            username="superadmin",
            role=UserRole.SUPERADMIN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert await authorize_channel_access(superadmin, "moderation") is True
        assert await authorize_channel_access(superadmin, "admin") is True
        assert await authorize_channel_access(superadmin, "superadmin") is True

    @pytest.mark.asyncio
    async def test_authorize_channel_access_topic_channels(self):
        """Test access to topic-based channels."""
        user = User(
            pk=uuid4(),
            email="test@example.com",
            google_id="google123",
            username="citizen",
            role=UserRole.CITIZEN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # All authenticated users can access topic channels
        assert await authorize_channel_access(user, "topic_123") is True
        assert await authorize_channel_access(user, "topic_456") is True

    @pytest.mark.asyncio
    async def test_authorize_channel_access_queue_channels(self):
        """Test access to queue-based channels."""
        user = User(
            pk=uuid4(),
            email="test@example.com",
            google_id="google123",
            username="citizen",
            role=UserRole.CITIZEN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # All authenticated users can access queue channels
        assert await authorize_channel_access(user, "queue_posts") is True
        assert await authorize_channel_access(user, "queue_topics") is True

    @pytest.mark.asyncio
    async def test_authorize_channel_access_unknown_channel(self):
        """Test access to unknown channels is denied."""
        user = User(
            pk=uuid4(),
            email="test@example.com",
            google_id="google123",
            username="citizen",
            role=UserRole.CITIZEN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        assert await authorize_channel_access(user, "unknown_channel") is False


class TestWebSocketRoleDecorator:
    """Test WebSocket role requirement decorator."""

    @pytest.mark.asyncio
    async def test_require_websocket_role_success(self):
        """Test role decorator allows access for authorized roles."""
        websocket = AsyncMock(spec=WebSocket)
        user = User(
            pk=uuid4(),
            email="admin@example.com",
            google_id="123",
            username="admin",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        @require_websocket_role("ADMIN", "SUPERADMIN")
        async def test_function(websocket: WebSocket, user: User):
            return "success"

        result = await test_function(websocket, user)
        assert result == "success"
        websocket.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_require_websocket_role_insufficient_permissions(self):
        """Test role decorator denies access for unauthorized roles."""
        websocket = AsyncMock(spec=WebSocket)
        user = User(
            pk=uuid4(),
            email="citizen@example.com",
            google_id="123",
            username="citizen",
            role=UserRole.CITIZEN,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        @require_websocket_role("ADMIN", "SUPERADMIN")
        async def test_function(websocket: WebSocket, user: User):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await test_function(websocket, user)

        exc = cast("HTTPException", exc_info.value)
        assert exc.status_code == 403
        assert "Insufficient permissions" in str(exc.detail)
        websocket.close.assert_called_once_with(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Insufficient permissions. Required: ('ADMIN', 'SUPERADMIN')",
        )
