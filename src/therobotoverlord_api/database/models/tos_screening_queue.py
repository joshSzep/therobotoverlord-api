"""TOS Screening Queue models for The Robot Overlord API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from therobotoverlord_api.database.models.base import BaseDBModel


class PostTosScreeningQueue(BaseDBModel):
    """Post TOS screening queue database model."""

    post_pk: UUID
    priority: int = 1
    assigned_to: UUID | None = None
    assigned_at: datetime | None = None


class PostTosScreeningQueueCreate(BaseModel):
    """Post TOS screening queue creation model."""

    post_pk: UUID
    priority: int = 1

    model_config = ConfigDict(from_attributes=True)


class PostTosScreeningQueueUpdate(BaseModel):
    """Post TOS screening queue update model."""

    priority: int | None = None
    assigned_to: UUID | None = None
    assigned_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PostTosScreeningQueueWithDetails(BaseModel):
    """Post TOS screening queue with post and user details."""

    pk: UUID
    post_pk: UUID
    post_content: str
    post_author_username: str
    priority: int
    assigned_to: UUID | None
    assigned_to_username: str | None
    assigned_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
