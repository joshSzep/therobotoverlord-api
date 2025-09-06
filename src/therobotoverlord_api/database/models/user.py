"""User model for The Robot Overlord API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import UserRole


class User(BaseDBModel):
    """User database model."""

    email: str
    google_id: str | None = None
    username: str
    password_hash: str | None = None
    role: UserRole = UserRole.CITIZEN
    loyalty_score: int = 0
    is_banned: bool = False
    is_sanctioned: bool = False
    is_active: bool = True
    email_verified: bool = False


class UserCreate(BaseModel):
    """User creation model."""

    email: str
    google_id: str | None = None
    username: str
    password_hash: str | None = None
    role: UserRole = UserRole.CITIZEN
    email_verified: bool = False

    model_config = ConfigDict(use_enum_values=True)


class UserUpdate(BaseModel):
    """User update model."""

    username: str | None = None
    role: UserRole | None = None
    loyalty_score: int | None = None
    is_banned: bool | None = None
    is_sanctioned: bool | None = None
    email_verified: bool | None = None
    google_id: str | None = None


class UserLeaderboard(BaseModel):
    """User leaderboard entry model."""

    user_pk: UUID
    username: str
    loyalty_score: int
    rank: int
    can_create_topics: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    """Public user profile model."""

    pk: UUID
    username: str
    loyalty_score: int
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
