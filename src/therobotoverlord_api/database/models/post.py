"""Post model for The Robot Overlord API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import ContentStatus


class Post(BaseDBModel):
    """Post database model."""

    topic_pk: UUID
    parent_post_pk: UUID | None = None
    author_pk: UUID
    content: str
    status: ContentStatus = ContentStatus.PENDING
    overlord_feedback: str | None = None
    submitted_at: datetime
    approved_at: datetime | None = None
    rejection_reason: str | None = None


class PostCreate(BaseModel):
    """Post creation model."""

    topic_pk: UUID
    parent_post_pk: UUID | None = None
    author_pk: UUID
    content: str
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PostUpdate(BaseModel):
    """Post update model."""

    content: str | None = None
    status: ContentStatus | None = None
    overlord_feedback: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PostWithAuthor(BaseModel):
    """Post with author information."""

    pk: UUID
    topic_pk: UUID
    parent_post_pk: UUID | None
    author_pk: UUID
    author_username: str
    content: str
    status: ContentStatus
    overlord_feedback: str | None
    submitted_at: datetime
    approved_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PostThread(BaseModel):
    """Post with reply information for thread display."""

    pk: UUID
    topic_pk: UUID
    parent_post_pk: UUID | None
    author_pk: UUID
    author_username: str
    content: str
    status: ContentStatus
    overlord_feedback: str | None
    submitted_at: datetime
    approved_at: datetime | None
    created_at: datetime
    reply_count: int = 0
    depth_level: int = 0

    model_config = ConfigDict(from_attributes=True)


class PostSummary(BaseModel):
    """Post summary for graveyard and profile views."""

    pk: UUID
    topic_pk: UUID
    topic_title: str
    content: str
    status: ContentStatus
    overlord_feedback: str | None
    submitted_at: datetime
    approved_at: datetime | None
    rejection_reason: str | None

    model_config = ConfigDict(from_attributes=True)
