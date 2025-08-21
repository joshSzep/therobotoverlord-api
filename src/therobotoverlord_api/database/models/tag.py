"""Tag models for The Robot Overlord API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict

from therobotoverlord_api.database.models.base import BaseDBModel


class Tag(BaseDBModel):
    """Tag database model."""

    name: str
    description: str | None = None
    color: str | None = None


class TagCreate(BaseModel):
    """Tag creation model."""

    name: str
    description: str | None = None
    color: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TagUpdate(BaseModel):
    """Tag update model."""

    name: str | None = None
    description: str | None = None
    color: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TagDetail(BaseDBModel):
    """Tag with additional details like topic count."""

    name: str
    description: str | None = None
    color: str | None = None
    topic_count: int

    model_config = ConfigDict(from_attributes=True)


class TopicTag(BaseDBModel):
    """Topic tag junction model."""

    topic_pk: UUID
    tag_pk: UUID


class TopicTagCreate(BaseModel):
    """Topic tag creation model."""

    topic_pk: UUID
    tag_pk: UUID

    model_config = ConfigDict(from_attributes=True)


class TopicTagWithDetails(BaseModel):
    """Topic tag with tag details."""

    pk: UUID
    topic_pk: UUID
    tag_pk: UUID
    tag_name: str
    tag_description: str | None
    tag_color: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagWithTopicCount(BaseModel):
    """Tag with topic count for listings."""

    pk: UUID
    name: str
    description: str | None
    color: str | None = None
    topic_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
