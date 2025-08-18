"""User repository for The Robot Overlord API."""

from typing import List, Optional
from uuid import UUID

from asyncpg import Record

from ..connection import get_db_connection
from ..models.user import User, UserCreate, UserUpdate, UserLeaderboard, UserProfile
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for user operations."""
    
    def __init__(self):
        super().__init__("users")
    
    def _record_to_model(self, record: Record) -> User:
        """Convert database record to User model."""
        return User(**dict(record))
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        data = user_data.model_dump()
        return await self.create(data)
    
    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        """Update an existing user."""
        data = user_data.model_dump(exclude_unset=True)
        return await self.update(user_id, data)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return await self.find_one_by(email=email)
    
    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        return await self.find_one_by(google_id=google_id)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self.find_one_by(username=username)
    
    async def get_leaderboard(self, limit: int = 100) -> List[UserLeaderboard]:
        """Get user leaderboard from materialized view."""
        query = """
            SELECT * FROM user_leaderboard 
            ORDER BY rank ASC 
            LIMIT $1
        """
        
        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [UserLeaderboard(**dict(record)) for record in records]
    
    async def get_user_rank(self, user_id: UUID) -> Optional[int]:
        """Get a user's current rank."""
        query = """
            SELECT rank FROM user_leaderboard 
            WHERE user_id = $1
        """
        
        async with get_db_connection() as connection:
            return await connection.fetchval(query, user_id)
    
    async def can_create_topics(self, user_id: UUID) -> bool:
        """Check if user can create topics (top 10% loyalty)."""
        query = """
            SELECT can_create_topics FROM user_leaderboard 
            WHERE user_id = $1
        """
        
        async with get_db_connection() as connection:
            result = await connection.fetchval(query, user_id)
            return result or False
    
    async def get_top_users(self, limit: int = 10) -> List[UserProfile]:
        """Get top users by loyalty score."""
        query = """
            SELECT id, username, loyalty_score, role, created_at
            FROM users 
            WHERE loyalty_score > 0
            ORDER BY loyalty_score DESC, created_at ASC
            LIMIT $1
        """
        
        async with get_db_connection() as connection:
            records = await connection.fetch(query, limit)
            return [UserProfile(**dict(record)) for record in records]
    
    async def update_loyalty_score(self, user_id: UUID, new_score: int) -> Optional[User]:
        """Update user's loyalty score."""
        return await self.update(user_id, {"loyalty_score": new_score})
    
    async def refresh_leaderboard(self) -> None:
        """Refresh the materialized leaderboard view."""
        query = "REFRESH MATERIALIZED VIEW CONCURRENTLY user_leaderboard"
        
        async with get_db_connection() as connection:
            await connection.execute(query)
    
    async def get_users_by_role(self, role: str) -> List[User]:
        """Get all users with a specific role."""
        return await self.find_by(role=role)
    
    async def get_sanctioned_users(self) -> List[User]:
        """Get all currently sanctioned users."""
        return await self.find_by(is_sanctioned=True)
    
    async def get_banned_users(self) -> List[User]:
        """Get all banned users."""
        return await self.find_by(is_banned=True)
