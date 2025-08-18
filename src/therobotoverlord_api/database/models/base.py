"""Base models and types for The Robot Overlord API database."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User role enumeration."""
    CITIZEN = "citizen"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class ContentStatus(str, Enum):
    """Content status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


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
    
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        use_enum_values = True


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
