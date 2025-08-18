"""User model for The Robot Overlord API."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base import BaseDBModel, UserRole


class User(BaseDBModel):
    """User database model."""
    
    email: str
    google_id: str
    username: str
    role: UserRole = UserRole.CITIZEN
    loyalty_score: int = 0
    is_banned: bool = False
    is_sanctioned: bool = False
    email_verified: bool = False


class UserCreate(BaseModel):
    """User creation model."""
    
    email: str
    google_id: str
    username: str
    role: UserRole = UserRole.CITIZEN
    email_verified: bool = False


class UserUpdate(BaseModel):
    """User update model."""
    
    username: Optional[str] = None
    role: Optional[UserRole] = None
    loyalty_score: Optional[int] = None
    is_banned: Optional[bool] = None
    is_sanctioned: Optional[bool] = None
    email_verified: Optional[bool] = None


class UserLeaderboard(BaseModel):
    """User leaderboard entry model."""
    
    user_id: UUID
    username: str
    loyalty_score: int
    rank: int
    can_create_topics: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Public user profile model."""
    
    id: UUID
    username: str
    loyalty_score: int
    role: UserRole
    created_at: datetime
    
    class Config:
        from_attributes = True
