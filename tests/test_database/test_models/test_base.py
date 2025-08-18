"""Tests for database base models."""

from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4

from therobotoverlord_api.database.models.base import AppealStatus
from therobotoverlord_api.database.models.base import BaseDBModel
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.base import FlagStatus
from therobotoverlord_api.database.models.base import ModerationOutcome
from therobotoverlord_api.database.models.base import QueueStatus
from therobotoverlord_api.database.models.base import SanctionType
from therobotoverlord_api.database.models.base import TimestampMixin
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.base import UserRole


class TestEnums:
    """Test enum classes."""

    def test_user_role_values(self):
        """Test UserRole enum values."""
        assert UserRole.CITIZEN == "citizen"
        assert UserRole.MODERATOR == "moderator"
        assert UserRole.ADMIN == "admin"
        assert UserRole.SUPERADMIN == "superadmin"

    def test_content_status_values(self):
        """Test ContentStatus enum values."""
        assert ContentStatus.PENDING == "pending"
        assert ContentStatus.APPROVED == "approved"
        assert ContentStatus.REJECTED == "rejected"

    def test_topic_status_values(self):
        """Test TopicStatus enum values."""
        assert TopicStatus.PENDING_APPROVAL == "pending_approval"
        assert TopicStatus.APPROVED == "approved"
        assert TopicStatus.REJECTED == "rejected"

    def test_queue_status_values(self):
        """Test QueueStatus enum values."""
        assert QueueStatus.PENDING == "pending"
        assert QueueStatus.PROCESSING == "processing"
        assert QueueStatus.COMPLETED == "completed"

    def test_appeal_status_values(self):
        """Test AppealStatus enum values."""
        assert AppealStatus.PENDING == "pending"
        assert AppealStatus.SUSTAINED == "sustained"
        assert AppealStatus.DENIED == "denied"

    def test_flag_status_values(self):
        """Test FlagStatus enum values."""
        assert FlagStatus.PENDING == "pending"
        assert FlagStatus.SUSTAINED == "sustained"
        assert FlagStatus.DISMISSED == "dismissed"

    def test_sanction_type_values(self):
        """Test SanctionType enum values."""
        assert SanctionType.POSTING_FREEZE == "posting_freeze"
        assert SanctionType.RATE_LIMIT == "rate_limit"

    def test_content_type_values(self):
        """Test ContentType enum values."""
        assert ContentType.TOPIC == "topic"
        assert ContentType.POST == "post"
        assert ContentType.PRIVATE_MESSAGE == "private_message"

    def test_moderation_outcome_values(self):
        """Test ModerationOutcome enum values."""
        assert ModerationOutcome.APPROVED == "approved"
        assert ModerationOutcome.REJECTED == "rejected"


class TestBaseDBModel:
    """Test BaseDBModel class."""

    def test_model_creation(self):
        """Test creating a BaseDBModel instance."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        model = BaseDBModel(
            pk=pk,
            created_at=created_at,
            updated_at=None,
        )

        assert model.pk == pk
        assert model.created_at == created_at
        assert model.updated_at is None

    def test_model_with_updated_at(self):
        """Test creating a BaseDBModel with updated_at."""
        pk = uuid4()
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        model = BaseDBModel(
            pk=pk,
            created_at=created_at,
            updated_at=updated_at,
        )

        assert model.pk == pk
        assert model.created_at == created_at
        assert model.updated_at == updated_at

    def test_model_config(self):
        """Test BaseDBModel configuration."""
        config = BaseDBModel.model_config
        assert config["from_attributes"] is True
        assert config["use_enum_values"] is True

    def test_model_validation_with_dict(self):
        """Test model validation from dictionary."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        data = {
            "pk": pk,
            "created_at": created_at,
            "updated_at": None,
        }

        model = BaseDBModel.model_validate(data)
        assert model.pk == pk
        assert model.created_at == created_at
        assert model.updated_at is None

    def test_model_dump(self):
        """Test model serialization."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        model = BaseDBModel(
            pk=pk,
            created_at=created_at,
            updated_at=None,
        )

        data = model.model_dump()
        assert data["pk"] == pk
        assert data["created_at"] == created_at
        assert data["updated_at"] is None

    def test_model_fields(self):
        """Test model field definitions."""
        fields = BaseDBModel.model_fields

        assert "pk" in fields
        assert "created_at" in fields
        assert "updated_at" in fields

        # Check field types
        assert fields["pk"].annotation == UUID
        assert fields["created_at"].annotation == datetime
        assert fields["updated_at"].annotation == datetime | None


class TestTimestampMixin:
    """Test TimestampMixin class."""

    def test_default_created_at(self):
        """Test that created_at gets a default value."""
        mixin = TimestampMixin()

        assert isinstance(mixin.created_at, datetime)
        assert mixin.created_at.tzinfo == UTC
        assert mixin.updated_at is None

    def test_custom_timestamps(self):
        """Test creating TimestampMixin with custom timestamps."""
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        mixin = TimestampMixin(
            created_at=created_at,
            updated_at=updated_at,
        )

        assert mixin.created_at == created_at
        assert mixin.updated_at == updated_at

    def test_mixin_config(self):
        """Test TimestampMixin configuration."""
        config = TimestampMixin.model_config
        assert config["from_attributes"] is True

    def test_mixin_validation_with_dict(self):
        """Test mixin validation from dictionary."""
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        data = {
            "created_at": created_at,
            "updated_at": updated_at,
        }

        mixin = TimestampMixin.model_validate(data)
        assert mixin.created_at == created_at
        assert mixin.updated_at == updated_at

    def test_mixin_fields(self):
        """Test mixin field definitions."""
        fields = TimestampMixin.model_fields

        assert "created_at" in fields
        assert "updated_at" in fields

        # Check field types
        assert fields["created_at"].annotation == datetime
        assert fields["updated_at"].annotation == datetime | None

        # Check that created_at has a default factory
        assert fields["created_at"].default_factory is not None
