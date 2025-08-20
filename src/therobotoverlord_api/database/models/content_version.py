"""Content versioning models for audit trail and restoration tracking."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import ContentType


class ContentVersion(BaseDBModel):
    """Content version model for audit trail."""

    content_type: ContentType
    content_pk: UUID
    version_number: int

    # Original content
    original_title: str | None = None
    original_content: str
    original_description: str | None = None

    # Edited content
    edited_title: str | None = None
    edited_content: str | None = None
    edited_description: str | None = None

    # Edit metadata
    edited_by: UUID | None = None
    edit_reason: str | None = None
    edit_type: str = (
        "appeal_restoration"  # 'appeal_restoration', 'moderator_edit', 'author_edit'
    )
    appeal_pk: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class ContentVersionCreate(BaseModel):
    """Model for creating content versions."""

    content_type: ContentType
    content_pk: UUID

    # Original content
    original_title: str | None = None
    original_content: str = Field(..., min_length=1, max_length=50000)
    original_description: str | None = Field(None, max_length=2000)

    # Edited content (optional)
    edited_title: str | None = Field(None, max_length=200)
    edited_content: str | None = Field(None, max_length=50000)
    edited_description: str | None = Field(None, max_length=2000)

    # Edit metadata
    edited_by: UUID | None = None
    edit_reason: str | None = Field(None, max_length=1000)
    edit_type: str = Field("appeal_restoration", max_length=50)
    appeal_pk: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class ContentVersionSummary(BaseModel):
    """Summary model for content version listings."""

    pk: UUID
    version_number: int
    content_type: ContentType
    content_pk: UUID

    # Edit metadata
    edited_by: UUID | None = None
    edit_reason: str | None = None
    edit_type: str
    appeal_pk: UUID | None = None
    created_at: datetime

    # Flags for what was changed
    has_title_change: bool = False
    has_content_change: bool = False
    has_description_change: bool = False

    model_config = ConfigDict(from_attributes=True)


class ContentVersionDiff(BaseModel):
    """Model for content version differences."""

    version_pk: UUID
    version_number: int
    content_type: ContentType
    content_pk: UUID

    # Change flags
    title_changed: bool = False
    content_changed: bool = False
    description_changed: bool = False

    # Changes detail
    changes: dict[str, dict[str, str | None]] = Field(default_factory=dict)

    # Edit metadata
    edit_metadata: dict[str, str | datetime | None] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ContentRestoration(BaseDBModel):
    """Content restoration tracking model."""

    appeal_pk: UUID
    content_type: ContentType
    content_pk: UUID
    content_version_pk: UUID

    restored_by: UUID
    restoration_reason: str | None = None
    original_status: str
    restored_status: str

    # Editing metadata
    content_was_edited: bool = False
    edit_summary: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ContentRestorationCreate(BaseModel):
    """Model for creating content restoration records."""

    appeal_pk: UUID
    content_type: ContentType
    content_pk: UUID
    content_version_pk: UUID

    restored_by: UUID
    restoration_reason: str | None = Field(None, max_length=1000)
    original_status: str = Field(..., max_length=50)
    restored_status: str = Field(..., max_length=50)

    # Editing metadata
    content_was_edited: bool = False
    edit_summary: str | None = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)


class RestorationResult(BaseModel):
    """Result model for content restoration operations."""

    success: bool
    content_type: ContentType
    content_pk: UUID
    version_pk: UUID | None = None
    restoration_pk: UUID | None = None

    # Result metadata
    content_edited: bool = False
    error_message: str | None = None
    metadata: dict[str, str | bool | None] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
