"""Flag database models for content reporting and moderation."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from therobotoverlord_api.database.models.base import BaseDBModel


class FlagStatus(str, Enum):
    """Status of a content flag."""

    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    UPHELD = "upheld"


class Flag(BaseDBModel):
    """Flag model for content reporting."""

    post_pk: UUID | None = None
    topic_pk: UUID | None = None
    flagger_pk: UUID
    reason: str
    status: FlagStatus = FlagStatus.PENDING
    reviewed_by_pk: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class FlagCreate(BaseModel):
    """Model for creating a new flag."""

    post_pk: UUID | None = None
    topic_pk: UUID | None = None
    reason: str = Field(..., min_length=10, max_length=500)


class FlagUpdate(BaseModel):
    """Model for updating a flag during review."""

    status: FlagStatus
    review_notes: str | None = Field(None, max_length=1000)


class FlagSummary(BaseModel):
    """Summary model for flag listings."""

    pk: UUID
    post_pk: UUID | None
    topic_pk: UUID | None
    flagger_pk: UUID
    reason: str
    status: FlagStatus
    reviewed_by_pk: UUID | None
    reviewed_at: datetime | None
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True
