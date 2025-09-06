"""User session model for The Robot Overlord API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from therobotoverlord_api.database.models.base import BaseDBModel


class UserSession(BaseDBModel):
    """User session database model."""

    user_pk: UUID
    session_token: str
    expires_at: datetime
    last_accessed_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None


class UserSessionCreate(BaseModel):
    """User session creation model."""

    user_pk: UUID
    session_token: str
    expires_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserSessionUpdate(BaseModel):
    """User session update model."""

    expires_at: datetime | None = None
    last_accessed_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    model_config = ConfigDict(from_attributes=True)
