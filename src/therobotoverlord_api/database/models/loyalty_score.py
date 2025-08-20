"""Loyalty Score models for The Robot Overlord API."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class ModerationEventType(str, Enum):
    """Types of moderation events that affect loyalty scores."""

    POST_MODERATION = "post_moderation"
    TOPIC_MODERATION = "topic_moderation"
    PRIVATE_MESSAGE_MODERATION = "private_message_moderation"
    APPEAL_RESOLUTION = "appeal_resolution"
    APPEAL_OUTCOME = "appeal_outcome"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class ContentType(str, Enum):
    """Content types for loyalty scoring."""

    POST = "post"
    TOPIC = "topic"
    PRIVATE_MESSAGE = "private_message"
    APPEAL = "appeal"


class LoyaltyEventOutcome(str, Enum):
    """Outcomes of moderation events."""

    APPROVED = "approved"
    REJECTED = "rejected"
    REMOVED = "removed"
    APPEAL_SUSTAINED = "appeal_sustained"
    APPEAL_DENIED = "appeal_denied"


class ModerationEvent(BaseModel):
    """A moderation event that affects loyalty score."""

    pk: UUID
    user_pk: UUID
    event_type: ModerationEventType
    content_type: ContentType
    content_pk: UUID
    outcome: LoyaltyEventOutcome
    score_delta: int
    previous_score: int
    new_score: int
    moderator_pk: UUID | None = None
    reason: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class LoyaltyScoreHistory(BaseModel):
    """Historical loyalty score data for a user."""

    user_pk: UUID
    score: int
    rank: int | None = None
    percentile_rank: float | None = None
    recorded_at: datetime
    event_pk: UUID | None = None  # The event that caused this score change

    class Config:
        from_attributes = True


class LoyaltyScoreBreakdown(BaseModel):
    """Detailed breakdown of a user's loyalty score components."""

    user_pk: UUID
    current_score: int
    post_score: int
    topic_score: int
    private_message_score: int
    appeal_adjustments: int
    manual_adjustments: int
    total_approved_posts: int
    total_rejected_posts: int
    total_approved_topics: int
    total_rejected_topics: int
    total_approved_messages: int
    total_rejected_messages: int
    last_updated: datetime


class LoyaltyScoreAdjustment(BaseModel):
    """Manual loyalty score adjustment request."""

    user_pk: UUID
    adjustment: int = Field(..., description="Score adjustment (positive or negative)")
    reason: str = Field(..., min_length=10, max_length=500)
    admin_notes: str | None = Field(None, max_length=1000)


class LoyaltyScoreStats(BaseModel):
    """System-wide loyalty score statistics."""

    total_users: int
    average_score: float
    median_score: int
    score_distribution: dict[str, int]
    top_10_percent_threshold: int
    topic_creation_threshold: int
    total_events_processed: int
    last_updated: datetime


class UserLoyaltyProfile(BaseModel):
    """Complete loyalty profile for a user."""

    user_pk: UUID
    username: str
    current_score: int
    rank: int | None = None
    percentile_rank: float | None = None
    breakdown: LoyaltyScoreBreakdown
    recent_events: list[ModerationEvent] = Field(default_factory=list)
    score_history: list[LoyaltyScoreHistory] = Field(default_factory=list)
    can_create_topics: bool
    next_threshold: int | None = None
    next_threshold_description: str | None = None


class LoyaltyEventFilters(BaseModel):
    """Filters for loyalty event queries."""

    event_type: ModerationEventType | None = None
    content_type: ContentType | None = None
    outcome: LoyaltyEventOutcome | None = None
    moderator_pk: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_score_delta: int | None = None
    max_score_delta: int | None = None


class LoyaltyEventResponse(BaseModel):
    """Paginated response for loyalty events."""

    events: list[ModerationEvent]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    filters_applied: LoyaltyEventFilters
