"""User session repository for The Robot Overlord API."""

from datetime import UTC
from datetime import datetime
from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.user_session import UserSession
from therobotoverlord_api.database.models.user_session import UserSessionCreate
from therobotoverlord_api.database.models.user_session import UserSessionUpdate
from therobotoverlord_api.database.repositories.base import BaseRepository


class UserSessionRepository(BaseRepository[UserSession]):
    """Repository for user session operations."""

    def __init__(self):
        super().__init__("user_sessions")

    def _record_to_model(self, record: Record) -> UserSession:
        """Convert database record to UserSession model."""
        return UserSession.model_validate(record)

    async def create_session(self, session_data: UserSessionCreate) -> UserSession:
        """Create a new user session."""
        data = session_data.model_dump()
        data["created_at"] = datetime.now(UTC)
        data["last_accessed_at"] = datetime.now(UTC)
        return await self.create_from_dict(data)

    async def update_session(
        self, session_pk: UUID, session_data: UserSessionUpdate
    ) -> UserSession | None:
        """Update an existing user session."""
        data = session_data.model_dump(exclude_unset=True)
        return await self.update_from_dict(session_pk, data)

    async def get_by_token(self, session_token: str) -> UserSession | None:
        """Get session by token."""
        return await self.find_one_by(session_token=session_token)

    async def get_by_user(self, user_pk: UUID) -> list[UserSession]:
        """Get all sessions for a user."""
        return await self.find_by(user_pk=user_pk)

    async def get_active_sessions(self, user_pk: UUID) -> list[UserSession]:
        """Get active (non-expired) sessions for a user."""
        query = """
            SELECT * FROM user_sessions
            WHERE user_pk = $1 AND expires_at > NOW()
            ORDER BY last_accessed_at DESC
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, user_pk)
            return [self._record_to_model(record) for record in records]

    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of deleted sessions."""
        query = """
            DELETE FROM user_sessions
            WHERE expires_at <= NOW()
        """

        async with get_db_connection() as connection:
            result = await connection.execute(query)
            # Extract count from result string like "DELETE 5"
            return int(result.split()[-1]) if result else 0

    async def revoke_session(self, session_token: str) -> bool:
        """Revoke a session by deleting it."""
        query = """
            DELETE FROM user_sessions
            WHERE session_token = $1
        """

        async with get_db_connection() as connection:
            result = await connection.execute(query, session_token)
            return result == "DELETE 1"

    async def revoke_all_user_sessions(self, user_pk: UUID) -> int:
        """Revoke all sessions for a user."""
        query = """
            DELETE FROM user_sessions
            WHERE user_pk = $1
        """

        async with get_db_connection() as connection:
            result = await connection.execute(query, user_pk)
            return int(result.split()[-1]) if result else 0

    async def update_last_accessed(self, session_token: str) -> UserSession | None:
        """Update the last accessed time for a session."""
        query = """
            UPDATE user_sessions
            SET last_accessed_at = NOW()
            WHERE session_token = $1
            RETURNING *
        """

        async with get_db_connection() as connection:
            record = await connection.fetchrow(query, session_token)
            return self._record_to_model(record) if record else None


def get_user_session_repository() -> UserSessionRepository:
    """Get user session repository instance."""
    return UserSessionRepository()
