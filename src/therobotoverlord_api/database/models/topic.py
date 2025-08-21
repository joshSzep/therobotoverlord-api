"""Topic model for The Robot Overlord API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import TopicStatus


class Topic(BaseDBModel):
    """Topic database model."""

    title: str
    description: str
    author_pk: UUID | None = None
    created_by_overlord: bool = False
    status: TopicStatus = TopicStatus.PENDING_APPROVAL
    approved_at: datetime | None = None
    approved_by: UUID | None = None


class TopicCreate(BaseModel):
    """Topic creation model."""

    title: str
    description: str
    author_pk: UUID | None = None
    created_by_overlord: bool = False

    model_config = ConfigDict(from_attributes=True)


class TopicUpdate(BaseModel):
    """Topic update model."""

    title: str | None = None
    description: str | None = None
    status: TopicStatus | None = None
    approved_at: datetime | None = None
    approved_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class TopicWithAuthor(BaseModel):
    """Topic with author information."""

    pk: UUID
    title: str
    description: str
    author_pk: UUID | None
    author_username: str | None
    created_by_overlord: bool
    status: TopicStatus
    approved_at: datetime | None
    approved_by: UUID | None
    created_at: datetime
    updated_at: datetime | None
    tags: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class TopicSummary(BaseModel):
    """Topic summary for lists and feeds."""

    pk: UUID
    title: str
    description: str
    author_username: str | None
    created_by_overlord: bool
    status: TopicStatus
    created_at: datetime
    post_count: int = 0
    tags: list[str] = []

    model_config = ConfigDict(from_attributes=True)
