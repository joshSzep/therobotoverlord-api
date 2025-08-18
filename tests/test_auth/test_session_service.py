"""Tests for session service."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.auth.models import SessionInfo
from therobotoverlord_api.auth.session_service import SessionService


class TestSessionService:
    """Test session service functionality."""

    @pytest.fixture
    def session_service(self):
        """Create session service instance."""
        return SessionService()

    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock()
        return mock_conn

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_service, mock_db_connection):
        """Test successful session creation."""
        user_id = uuid4()
        session_id = "test_session_id"
        refresh_token = "test_refresh_token"
        ip_address = "127.0.0.1"
        user_agent = "Test User Agent"

        now = datetime.now(UTC)
        mock_record = {
            "session_id": session_id,
            "user_pk": user_id,
            "created_at": now,
            "last_used_at": now,
            "last_used_ip": ip_address,
            "last_used_user_agent": user_agent,
            "is_revoked": False,
            "reuse_detected": False,
        }
        mock_db_connection.fetchrow.return_value = mock_record

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            session_info = await session_service.create_session(
                user_id=user_id,
                session_id=session_id,
                refresh_token=refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        assert isinstance(session_info, SessionInfo)
        assert session_info.session_id == session_id
        assert session_info.user_id == user_id
        assert session_info.is_revoked is False
        mock_db_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_success(self, session_service, mock_db_connection):
        """Test successful session retrieval."""
        session_id = "test_session_id"
        user_id = uuid4()

        mock_record = {
            "session_id": session_id,
            "user_pk": user_id,
            "created_at": datetime.now(UTC),
            "last_used_at": datetime.now(UTC),
            "last_used_ip": "127.0.0.1",
            "last_used_user_agent": "Test Agent",
            "is_revoked": False,
            "reuse_detected": False,
        }
        mock_db_connection.fetchrow.return_value = mock_record

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            session_info = await session_service.get_session(session_id)

        assert isinstance(session_info, SessionInfo)
        assert session_info.session_id == session_id
        assert session_info.user_id == user_id

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_service, mock_db_connection):
        """Test session not found."""
        session_id = "nonexistent_session"
        mock_db_connection.fetchrow.return_value = None

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            session_info = await session_service.get_session(session_id)

        assert session_info is None

    @pytest.mark.asyncio
    async def test_validate_refresh_token_valid(
        self, session_service, mock_db_connection
    ):
        """Test validation of valid refresh token."""
        session_id = "test_session_id"
        refresh_token = "test_refresh_token"

        mock_record = {
            "refresh_token_hash": session_service._hash_token(refresh_token),
            "is_revoked": False,
            "reuse_detected": False,
        }
        mock_db_connection.fetchrow.return_value = mock_record

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            is_valid = await session_service.validate_refresh_token(
                session_id, refresh_token
            )

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_refresh_token_invalid(
        self, session_service, mock_db_connection
    ):
        """Test validation of invalid refresh token."""
        session_id = "test_session_id"
        refresh_token = "test_refresh_token"
        wrong_token = "wrong_refresh_token"

        mock_record = {
            "refresh_token_hash": session_service._hash_token(wrong_token),
            "is_revoked": False,
            "reuse_detected": False,
        }
        mock_db_connection.fetchrow.return_value = mock_record

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            is_valid = await session_service.validate_refresh_token(
                session_id, refresh_token
            )

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_refresh_token_revoked(
        self, session_service, mock_db_connection
    ):
        """Test validation of revoked session token."""
        session_id = "test_session_id"
        refresh_token = "test_refresh_token"

        mock_record = {
            "refresh_token_hash": session_service._hash_token(refresh_token),
            "is_revoked": True,
            "reuse_detected": False,
        }
        mock_db_connection.fetchrow.return_value = mock_record

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            is_valid = await session_service.validate_refresh_token(
                session_id, refresh_token
            )

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_rotate_refresh_token_success(
        self, session_service, mock_db_connection
    ):
        """Test successful refresh token rotation."""
        session_id = "test_session_id"
        old_token = "old_refresh_token"
        new_token = "new_refresh_token"

        # Mock validate_refresh_token to return True
        with patch.object(session_service, "validate_refresh_token", return_value=True):
            mock_db_connection.fetchrow.return_value = {"session_id": session_id}

            with patch(
                "therobotoverlord_api.auth.session_service.get_db_connection"
            ) as mock_get_conn:
                mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

                success = await session_service.rotate_refresh_token(
                    session_id=session_id,
                    old_refresh_token=old_token,
                    new_refresh_token=new_token,
                    ip_address="127.0.0.1",
                    user_agent="Test Agent",
                )

        assert success is True

    @pytest.mark.asyncio
    async def test_rotate_refresh_token_invalid_old_token(
        self, session_service, mock_db_connection
    ):
        """Test refresh token rotation with invalid old token."""
        session_id = "test_session_id"
        old_token = "invalid_old_token"
        new_token = "new_refresh_token"

        # Mock validate_refresh_token to return False
        with patch.object(
            session_service, "validate_refresh_token", return_value=False
        ):
            with patch.object(
                session_service, "_mark_session_compromised"
            ) as mock_mark_compromised:
                success = await session_service.rotate_refresh_token(
                    session_id=session_id,
                    old_refresh_token=old_token,
                    new_refresh_token=new_token,
                )

        assert success is False
        mock_mark_compromised.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_revoke_session_success(self, session_service, mock_db_connection):
        """Test successful session revocation."""
        session_id = "test_session_id"
        mock_db_connection.fetchrow.return_value = {"session_id": session_id}

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            success = await session_service.revoke_session(session_id)

        assert success is True
        mock_db_connection.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_session_not_found(self, session_service, mock_db_connection):
        """Test revoking non-existent session."""
        session_id = "nonexistent_session"
        mock_db_connection.fetchrow.return_value = None

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            success = await session_service.revoke_session(session_id)

        assert success is False

    @pytest.mark.asyncio
    async def test_revoke_all_user_sessions(self, session_service, mock_db_connection):
        """Test revoking all sessions for a user."""
        user_id = uuid4()
        mock_records = [{"session_id": "session_1"}, {"session_id": "session_2"}]
        mock_db_connection.fetch.return_value = mock_records

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            count = await session_service.revoke_all_user_sessions(user_id)

        assert count == 2
        mock_db_connection.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_service, mock_db_connection):
        """Test cleanup of expired sessions."""
        mock_records = [{"session_id": "expired_1"}, {"session_id": "expired_2"}]
        mock_db_connection.fetch.return_value = mock_records

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            count = await session_service.cleanup_expired_sessions()

        assert count == 2
        mock_db_connection.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, session_service, mock_db_connection):
        """Test getting user sessions."""
        user_id = uuid4()
        mock_records = [
            {
                "session_id": "session_1",
                "user_pk": user_id,
                "created_at": datetime.now(UTC),
                "last_used_at": datetime.now(UTC),
                "last_used_ip": "127.0.0.1",
                "last_used_user_agent": "Browser 1",
                "is_revoked": False,
                "reuse_detected": False,
            },
            {
                "session_id": "session_2",
                "user_pk": user_id,
                "created_at": datetime.now(UTC),
                "last_used_at": datetime.now(UTC),
                "last_used_ip": "192.168.1.100",
                "last_used_user_agent": "Browser 2",
                "is_revoked": False,
                "reuse_detected": False,
            },
        ]
        mock_db_connection.fetch.return_value = mock_records

        with patch(
            "therobotoverlord_api.auth.session_service.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_db_connection

            sessions = await session_service.get_user_sessions(user_id)

        assert len(sessions) == 2
        assert all(isinstance(session, SessionInfo) for session in sessions)
        assert sessions[0].session_id == "session_1"
        assert sessions[1].session_id == "session_2"

    def test_hash_token(self, session_service):
        """Test token hashing."""
        token = "test_refresh_token"
        hash1 = session_service._hash_token(token)
        hash2 = session_service._hash_token(token)

        # Same token should produce same hash
        assert hash1 == hash2

        # Different tokens should produce different hashes
        different_token = "different_refresh_token"
        hash3 = session_service._hash_token(different_token)
        assert hash1 != hash3

        # Hash should be hex string
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex digest length

    def test_verify_token_hash(self, session_service):
        """Test token hash verification."""
        token = "test_refresh_token"
        stored_hash = session_service._hash_token(token)

        # Correct token should verify
        assert session_service._verify_token_hash(token, stored_hash) is True

        # Wrong token should not verify
        wrong_token = "wrong_refresh_token"
        assert session_service._verify_token_hash(wrong_token, stored_hash) is False
