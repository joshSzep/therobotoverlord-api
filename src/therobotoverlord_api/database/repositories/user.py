"""User repository for The Robot Overlord API."""

from uuid import UUID

from asyncpg import Record

from therobotoverlord_api.database.connection import get_db_connection
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserCreate
from therobotoverlord_api.database.models.user import UserLeaderboard
from therobotoverlord_api.database.models.user import UserProfile
from therobotoverlord_api.database.models.user import UserUpdate
from therobotoverlord_api.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for user operations."""

    def __init__(self):
        super().__init__("users")

    def _record_to_model(self, record: Record) -> User:
        """Convert database record to User model."""
        return User.model_validate(record)

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        data = user_data.model_dump()
        return await self.create_from_dict(data)

    async def update_user(self, user_pk: UUID, user_data: UserUpdate) -> User | None:
        """Update an existing user."""
        data = user_data.model_dump(exclude_unset=True)
        return await self.update_from_dict(user_pk, data)

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Get user by Google ID."""
        return await self.find_one_by(google_id=google_id)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        return await self.find_one_by(email=email)

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        return await self.find_one_by(username=username)

    async def get_leaderboard(self, limit: int = 100) -> list[UserLeaderboard]:
        """Get user leaderboard from materialized view."""
        query = """
            SELECT * FROM leaderboard
            ORDER BY rank ASC
            LIMIT $1
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [UserLeaderboard.model_validate(record) for record in records]

    async def get_user_rank(self, user_pk: UUID) -> int | None:
        """Get a user's current rank."""
        query = """
            SELECT rank FROM leaderboard
            WHERE user_pk = $1
        """

        async with get_db_connection() as connection:
            return await connection.fetchval(query, user_pk)

    async def can_create_topic(self, user_pk: UUID, top_percent: float = 0.1) -> bool:
        """Check if user can create topics based on top N% loyalty score."""
        threshold = await self.get_top_percent_loyalty_threshold(top_percent)

        query = """
            SELECT loyalty_score >= $1 as can_create
            FROM users
            WHERE pk = $2
        """

        async with get_db_connection() as connection:
            result = await connection.fetchval(query, threshold, user_pk)
            return result or False

    async def get_top_percent_loyalty_threshold(self, top_percent: float = 0.1) -> int:
        """Get the minimum loyalty score required to be in the top N%.

        Args:
            top_percent: The percentage as a decimal (0.1 for 10%, 0.05 for 5%, etc.)
        """
        query = """
            SELECT COALESCE(MIN(loyalty_score), 0) as threshold
            FROM (
                SELECT loyalty_score
                FROM users
                WHERE loyalty_score > 0
                ORDER BY loyalty_score DESC, created_at ASC
                LIMIT (SELECT GREATEST(1, CAST(COUNT(*) * $1 AS INTEGER)) FROM users WHERE loyalty_score > 0)
            ) top_users
        """

        async with get_db_connection() as connection:
            result = await connection.fetchval(query, top_percent)
            return result or 0

    async def get_top_users(self, limit: int = 10) -> list[UserProfile]:
        """Get top users by loyalty score."""
        query = """
            SELECT pk, username, loyalty_score, role, created_at
            FROM users
            ORDER BY loyalty_score DESC
            LIMIT $1
        """

        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [
                UserProfile(
                    pk=record["pk"],
                    username=record["username"],
                    loyalty_score=record["loyalty_score"],
                    role=record["role"],
                    created_at=record["created_at"],
                )
                for record in records
            ]

    async def update_loyalty_score(self, user_pk: UUID, new_score: int) -> User | None:
        """Update user's loyalty score."""
        return await self.update_from_dict(user_pk, {"loyalty_score": new_score})

    async def refresh_leaderboard(self) -> None:
        """Refresh the materialized leaderboard view."""
        query = "REFRESH MATERIALIZED VIEW CONCURRENTLY leaderboard"

        async with get_db_connection() as connection:
            await connection.execute(query)

    async def get_users_by_role(self, role: str) -> list[User]:
        """Get all users with a specific role."""
        return await self.find_by(role=role)

    async def get_sanctioned_users(self) -> list[User]:
        """Get all currently sanctioned users."""
        return await self.find_by(is_sanctioned=True)

    async def get_banned_users(self) -> list[User]:
        """Get all banned users."""
        return await self.find_by(is_banned=True)


def get_user_repository() -> UserRepository:
    """Get user repository instance."""
    return UserRepository()
