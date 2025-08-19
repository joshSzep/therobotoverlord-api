"""Base models and types for The Robot Overlord API database."""

from datetime import UTC
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class UserRole(str, Enum):
    """User role enumeration."""

    CITIZEN = "citizen"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class ContentStatus(str, Enum):
    """Content status enumeration."""

    SUBMITTED = "submitted"
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    APPROVED = "approved"
    REJECTED = "rejected"
    TOS_VIOLATION = "tos_violation"


class TopicStatus(str, Enum):
    """Topic status enumeration."""

    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class QueueStatus(str, Enum):
    """Queue processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QueueType(str, Enum):
    """Queue type enumeration."""

    TOPIC_MODERATION = "topic_moderation"
    POST_MODERATION = "post_moderation"
    PRIVATE_MESSAGE = "private_message"


class AppealStatus(str, Enum):
    """Appeal status enumeration."""

    PENDING = "pending"
    SUSTAINED = "sustained"
    DENIED = "denied"


class FlagStatus(str, Enum):
    """Flag status enumeration."""

    PENDING = "pending"
    SUSTAINED = "sustained"
    DISMISSED = "dismissed"


class SanctionType(str, Enum):
    """Sanction type enumeration."""

    POSTING_FREEZE = "posting_freeze"
    RATE_LIMIT = "rate_limit"


class ContentType(str, Enum):
    """Content type enumeration."""

    TOPIC = "topic"
    POST = "post"
    PRIVATE_MESSAGE = "private_message"


class ModerationOutcome(str, Enum):
    """Moderation outcome enumeration."""

    APPROVED = "approved"
    REJECTED = "rejected"


class BaseDBModel(BaseModel):
    """Base model for database entities."""

    pk: UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
