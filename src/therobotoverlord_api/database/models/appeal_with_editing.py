"""Enhanced appeal models with content editing capability."""

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class AppealDecisionWithEdit(BaseModel):
    """Appeal decision model with optional content editing."""

    review_notes: str | None = Field(None, max_length=1000)

    # Content editing fields (optional)
    edit_content: bool = False
    edited_title: str | None = Field(None, max_length=200)
    edited_content: str | None = Field(None, max_length=10000)
    edited_description: str | None = Field(None, max_length=1000)
    edit_reason: str | None = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class AppealUpdateWithRestoration(BaseModel):
    """Appeal update model with restoration metadata."""

    status: str | None = None
    reviewed_by: str | None = None
    review_notes: str | None = Field(None, max_length=1000)
    reviewed_at: str | None = None

    # Restoration tracking
    restoration_completed: bool = False
    restoration_completed_at: str | None = None
    restoration_metadata: dict[str, str | bool | None] | None = Field(
        default_factory=dict
    )

    model_config = ConfigDict(from_attributes=True)
