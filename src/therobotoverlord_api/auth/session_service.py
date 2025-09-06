"""Session management service for The Robot Overlord API."""

import hashlib
import secrets

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from uuid import UUID

from therobotoverlord_api.auth.models import SessionInfo
from therobotoverlord_api.config.auth import get_auth_settings
from therobotoverlord_api.database.connection import get_db_connection


class SessionCreationError(Exception):
    """Raised when session creation fails."""


class SessionService:
    """Session management and refresh token handling service."""

    def __init__(self):
        self._settings = get_auth_settings()

    async def create_session(
        self,
        user_id: UUID,
        session_id: str,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SessionInfo:
        """Create a new user session."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._settings.refresh_token_lifetime)

        query = """
            INSERT INTO user_sessions (
                session_id, user_pk, refresh_token_hash, expires_at,
                created_at, last_used_at, last_used_ip, last_used_user_agent
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """

        refresh_token_hash = self._hash_token(refresh_token)

        async with get_db_connection() as connection:
            record = await connection.fetchrow(
                query,
                session_id,
                user_id,
                refresh_token_hash,
                expires_at,
                now,
                now,
                ip_address,
                user_agent,
            )

            if not record:
                raise SessionCreationError("Failed to create session")

            return SessionInfo(
                session_id=record["session_id"],
                user_pk=record["user_pk"],
                created_at=record["created_at"],
                last_used_at=record["last_used_at"],
                last_used_ip=str(record["last_used_ip"])
                if record["last_used_ip"]
                else None,
                last_used_user_agent=record["last_used_user_agent"],
                is_revoked=record["is_revoked"],
                reuse_detected=record["reuse_detected"],
            )

    async def get_session(self, session_id: str) -> SessionInfo | None:
        """Get session information by session ID."""
        query = """
            SELECT
                session_id,
                user_pk,
                created_at,
                last_used_at,
                last_used_ip,
                last_used_user_agent,
                is_revoked,
                reuse_detected
            FROM user_sessions
            WHERE session_id = $1 AND expires_at > NOW() AND is_revoked = FALSE
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, session_id)
            if not record:
                return None

            return SessionInfo(
                session_id=record["session_id"],
                user_pk=record["user_pk"],
                created_at=record["created_at"],
                last_used_at=record["last_used_at"],
                last_used_ip=str(record["last_used_ip"])
                if record["last_used_ip"]
                else None,
                last_used_user_agent=record["last_used_user_agent"],
                is_revoked=record["is_revoked"],
                reuse_detected=record["reuse_detected"],
            )

    async def validate_refresh_token(
        self,
        session_id: str,
        refresh_token: str,
    ) -> bool:
        """Validate refresh token against stored hash."""
        query = """
            SELECT refresh_token_hash, reuse_detected
            FROM user_sessions
            WHERE session_id = $1 AND expires_at > NOW() AND is_revoked = FALSE
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, session_id)
            if not record:
                return False

            # Check if reuse detected
            if record["reuse_detected"]:
                return False

            # Verify token hash
            stored_hash = record["refresh_token_hash"]
            return self._verify_token_hash(refresh_token, stored_hash)

    async def rotate_refresh_token(
        self,
        session_id: str,
        old_refresh_token: str,
        new_refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """Rotate refresh token with reuse detection."""
        # First validate the old token
        if not await self.validate_refresh_token(session_id, old_refresh_token):
            # Mark session as compromised if old token is invalid
            await self._mark_session_compromised(session_id)
            return False

        # Update with new token hash
        new_token_hash = self._hash_token(new_refresh_token)
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._settings.refresh_token_lifetime)

        query = """
            UPDATE user_sessions
            SET refresh_token_hash = $1,
                expires_at = $2,
                last_used_at = $3,
                last_used_ip = $4,
                last_used_user_agent = $5,
                rotated_at = $6
            WHERE session_id = $7 AND is_revoked = FALSE
            RETURNING session_id
        """

        async with get_db_connection() as connection:
            result = await connection.fetchrow(
                query,
                new_token_hash,
                expires_at,
                now,
                ip_address,
                user_agent,
                now,
                session_id,
            )
            return result is not None

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a specific session."""
        query = """
            UPDATE user_sessions
            SET is_revoked = TRUE, revoked_at = NOW()
            WHERE session_id = $1
            RETURNING session_id
        """

        async with get_db_connection() as connection:
            result = await connection.fetchrow(query, session_id)
            return result is not None

    async def revoke_all_user_sessions(self, user_id: UUID) -> int:
        """Revoke all sessions for a user."""
        query = """
            UPDATE user_sessions
            SET is_revoked = TRUE, revoked_at = NOW()
            WHERE user_pk = $1 AND is_revoked = FALSE
            RETURNING session_id
        """

        async with get_db_connection() as connection:
            results = await connection.fetch(query, user_id)
            return len(results)

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        query = """
            DELETE FROM user_sessions
            WHERE expires_at < NOW() OR (
                is_revoked = TRUE AND revoked_at < NOW() - INTERVAL '7 days'
            )
            RETURNING session_id
        """

        async with get_db_connection() as connection:
            results = await connection.fetch(query)
            return len(results)

    async def get_user_sessions(self, user_id: UUID) -> list[SessionInfo]:
        """Get all active sessions for a user."""
        query = """
            SELECT session_id, user_pk, created_at, last_used_at,
                   last_used_ip, last_used_user_agent, is_revoked, reuse_detected
            FROM user_sessions
            WHERE user_pk = $1 AND expires_at > NOW() AND is_revoked = FALSE
            ORDER BY last_used_at DESC
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, user_id)
            return [
                SessionInfo(
                    session_id=record["session_id"],
                    user_pk=record["user_pk"],
                    created_at=record["created_at"],
                    last_used_at=record["last_used_at"],
                    last_used_ip=str(record["last_used_ip"])
                    if record["last_used_ip"]
                    else None,
                    last_used_user_agent=record["last_used_user_agent"],
                    is_revoked=record["is_revoked"],
                    reuse_detected=record["reuse_detected"],
                )
                for record in records
            ]

    async def _mark_session_compromised(self, session_id: str) -> None:
        """Mark session as compromised due to token reuse."""
        query = """
            UPDATE user_sessions
            SET reuse_detected = TRUE, is_revoked = TRUE, revoked_at = NOW()
            WHERE session_id = $1
        """

        async with get_db_connection() as connection:
            await connection.execute(query, session_id)

    def _hash_token(self, token: str) -> str:
        """Hash refresh token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def _verify_token_hash(self, token: str, stored_hash: str) -> bool:
        """Verify token against stored hash."""
        return secrets.compare_digest(self._hash_token(token), stored_hash)
