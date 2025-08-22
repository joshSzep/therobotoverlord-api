"""Targeted tests for AuthService to improve coverage."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from therobotoverlord_api.auth.service import AuthService


class TestAuthServiceTargeted:
    """Targeted test class for AuthService."""

    @pytest.fixture
    def auth_service(self):
        """Create an AuthService instance with mocked dependencies."""
        service = AuthService()
        service.google_oauth = MagicMock()
        service.jwt_service = MagicMock()
        service.session_service = MagicMock()
        service.user_repository = MagicMock()

        # Make async methods
        service.google_oauth.get_authorization_url = MagicMock(
            return_value=("auth_url", "state")
        )
        service.session_service.revoke_session = AsyncMock(return_value=True)
        service.session_service.revoke_all_user_sessions = AsyncMock(return_value=2)
        service.user_repository.get_by_pk = AsyncMock()

        return service

    @pytest.mark.asyncio
    async def test_initiate_login(self, auth_service):
        """Test initiating login flow."""
        result = await auth_service.initiate_login()

        auth_service.google_oauth.get_authorization_url.assert_called_once()
        assert result == ("auth_url", "state")

    @pytest.mark.asyncio
    async def test_logout_success(self, auth_service):
        """Test successful logout."""
        session_id = "session_123"

        # Mock the session and user for WebSocket broadcasting
        mock_session = MagicMock()
        mock_session.user_id = uuid4()
        mock_user = MagicMock()
        mock_user.pk = mock_session.user_id
        mock_user.username = "testuser"

        auth_service.session_service.get_session = AsyncMock(return_value=mock_session)
        auth_service.user_repository.get_by_pk.return_value = mock_user

        result = await auth_service.logout(session_id)

        auth_service.session_service.revoke_session.assert_called_once_with(session_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_logout_all_sessions(self, auth_service):
        """Test logging out all sessions."""
        user_id = uuid4()

        # Mock the user for WebSocket broadcasting
        mock_user = MagicMock()
        mock_user.pk = user_id
        mock_user.username = "testuser"

        auth_service.user_repository.get_by_pk.return_value = mock_user

        result = await auth_service.logout_all_sessions(user_id)

        auth_service.session_service.revoke_all_user_sessions.assert_called_once_with(
            user_id
        )
        assert result == 2

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, auth_service):
        """Test getting user info."""
        user_id = uuid4()

        mock_user = {"pk": user_id, "username": "testuser"}
        auth_service.user_repository.get_by_pk.return_value = mock_user

        result = await auth_service.get_user_info(user_id)

        auth_service.user_repository.get_by_pk.assert_called_once_with(user_id)
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self, auth_service):
        """Test getting user info when user not found."""
        user_id = uuid4()

        auth_service.user_repository.get_by_pk.return_value = None

        result = await auth_service.get_user_info(user_id)

        auth_service.user_repository.get_by_pk.assert_called_once_with(user_id)
        assert result is None
