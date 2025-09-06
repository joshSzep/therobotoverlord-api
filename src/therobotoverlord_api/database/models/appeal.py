"""Appeal models for The Robot Overlord API."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from therobotoverlord_api.database.models.base import AppealStatus
from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import ContentType


class AppealType(str, Enum):
    """Appeal type enum matching database schema."""

    SANCTION_APPEAL = "sanction_appeal"
    FLAG_APPEAL = "flag_appeal"
    CONTENT_RESTORATION = "content_restoration"


class Appeal(BaseDBModel):
    """Appeal database model matching schema."""

    user_pk: UUID  # User making the appeal (matches DB schema)
    sanction_pk: UUID | None = None  # References sanctions table
    flag_pk: UUID | None = None  # References flags table
    appeal_type: AppealType
    appeal_reason: str  # User's reason for appeal (matches DB column name)
    status: AppealStatus = AppealStatus.PENDING

    # Review details
    reviewed_by: UUID | None = None
    review_notes: str | None = None
    reviewed_at: datetime | None = None

    # Content restoration fields
    restoration_completed: bool = False
    restoration_completed_at: datetime | None = None
    restoration_metadata: dict | None = None


class AppealCreate(BaseModel):
    """Appeal creation model."""

    # Legacy fields for backward compatibility with tests
    content_type: ContentType | None = None
    content_pk: UUID | None = None
    appeal_type: AppealType
    reason: str = Field(..., min_length=20, max_length=1000)
    evidence: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AppealUpdate(BaseModel):
    """Appeal update model."""

    status: AppealStatus | None = None
    reviewed_by: UUID | None = None
    review_notes: str | None = Field(None, max_length=1000)
    reviewed_at: datetime | None = None
    restoration_completed: bool | None = None
    restoration_completed_at: datetime | None = None
    restoration_metadata: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class AppealDecision(BaseModel):
    """Appeal decision model for moderator actions."""

    review_notes: str | None = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)


class AppealWithContent(BaseModel):
    """Appeal with associated content information."""

    pk: UUID
    user_pk: UUID
    appellant_username: str
    sanction_pk: UUID | None
    flag_pk: UUID | None
    appeal_type: AppealType
    status: AppealStatus
    appeal_reason: str
    reviewed_by: UUID | None
    reviewer_username: str | None
    review_notes: str | None
    reviewed_at: datetime | None
    restoration_completed: bool
    restoration_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    # Associated content details
    sanction_type: str | None = None  # If appealing a sanction
    sanction_reason: str | None = None
    flag_reason: str | None = None  # If appealing a flag
    flagged_content_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AppealEligibility(BaseModel):
    """Appeal eligibility check result."""

    eligible: bool
    reason: str | None = None
    cooldown_expires_at: datetime | None = None
    appeals_remaining: int | None = None
    max_appeals_per_day: int
    appeals_used_today: int

    model_config = ConfigDict(from_attributes=True)


class AppealStats(BaseModel):
    """Appeal statistics for moderators."""

    total_pending: int
    total_under_review: int
    total_sustained: int
    total_denied: int
    total_withdrawn: int
    total_count: int  # Total appeals across all statuses
    total_today: int  # Appeals submitted today
    average_review_time_hours: float | None
    appeals_by_type: dict[str, int]
    top_appellants: list[dict[str, str | int]]
    reviewer_stats: list[dict[str, str | int]]

    model_config = ConfigDict(from_attributes=True)


class AppealResponse(BaseModel):
    """Paginated appeal response."""

    appeals: list[AppealWithContent]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

    model_config = ConfigDict(from_attributes=True)


class AppealRateLimits(BaseModel):
    """Rate limiting configuration for appeals."""

    max_appeals_per_day: int = 3
    max_appeals_per_content: int = 1
    cooldown_hours: int = 24
    loyalty_score_bonus_appeals: dict[int, int] = Field(
        default_factory=lambda: {
            100: 1,  # +1 appeal per day at 100+ loyalty
            500: 2,  # +2 appeals per day at 500+ loyalty
            1000: 3,  # +3 appeals per day at 1000+ loyalty
        }
    )
    content_age_limit_days: int = 7  # Appeals must be within 7 days

    model_config = ConfigDict(from_attributes=True)
