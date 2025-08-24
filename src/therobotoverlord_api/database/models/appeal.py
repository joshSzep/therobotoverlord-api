"""Appeal models for The Robot Overlord API."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import ContentType


class AppealStatus(str, Enum):
    """Appeal status enumeration."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    SUSTAINED = "sustained"  # Appeal granted, original decision overturned
    DENIED = "denied"  # Appeal rejected, original decision upheld
    WITHDRAWN = "withdrawn"  # User withdrew the appeal


class AppealType(str, Enum):
    """Type of content being appealed."""

    TOPIC_REJECTION = "topic_rejection"
    POST_REJECTION = "post_rejection"
    POST_REMOVAL = "post_removal"
    PRIVATE_MESSAGE_REJECTION = "private_message_rejection"
    SANCTION = "sanction"


class Appeal(BaseDBModel):
    """Appeal database model."""

    appellant_pk: UUID  # User making the appeal
    content_type: ContentType  # TOPIC, POST, PRIVATE_MESSAGE
    content_pk: UUID  # ID of the appealed content
    appeal_type: AppealType
    status: AppealStatus = AppealStatus.PENDING

    # Appeal details
    reason: str  # User's reason for appeal
    evidence: str | None = None  # Additional evidence/context

    # Review details
    reviewed_by: UUID | None = None  # Moderator/admin who reviewed
    review_notes: str | None = None  # Internal review notes
    decision_reason: str | None = None  # Reason for sustain/deny decision

    # Timestamps
    submitted_at: datetime
    reviewed_at: datetime | None = None

    # Rate limiting
    previous_appeals_count: int = 0  # Number of previous appeals by this user

    # Priority scoring (based on user loyalty score)
    priority_score: int = 0


class AppealCreate(BaseModel):
    """Appeal creation model."""

    content_type: ContentType
    content_pk: UUID
    appeal_type: AppealType
    reason: str = Field(..., min_length=20, max_length=1000)
    evidence: str | None = Field(None, max_length=2000)

    model_config = ConfigDict(from_attributes=True)


class AppealUpdate(BaseModel):
    """Appeal update model."""

    status: AppealStatus | None = None
    reviewed_by: UUID | None = None
    review_notes: str | None = Field(None, max_length=1000)
    decision_reason: str | None = Field(None, max_length=1000)
    reviewed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AppealDecision(BaseModel):
    """Appeal decision model for moderator actions."""

    decision_reason: str = Field(..., min_length=10, max_length=1000)
    review_notes: str | None = Field(None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)


class AppealWithContent(BaseModel):
    """Appeal with associated content information."""

    pk: UUID
    appellant_pk: UUID
    appellant_username: str
    content_type: ContentType
    content_pk: UUID
    appeal_type: AppealType
    status: AppealStatus
    reason: str
    evidence: str | None
    reviewed_by: UUID | None
    reviewer_username: str | None
    review_notes: str | None
    decision_reason: str | None
    submitted_at: datetime
    reviewed_at: datetime | None
    priority_score: int
    created_at: datetime
    updated_at: datetime | None

    # Content details
    content_title: str | None = None  # For topics
    content_text: str | None = None  # Truncated content

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
