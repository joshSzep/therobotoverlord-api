"""Tests for Flag database models."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

import pytest

from pydantic import ValidationError

from therobotoverlord_api.database.models.flag import Flag
from therobotoverlord_api.database.models.flag import FlagCreate
from therobotoverlord_api.database.models.flag import FlagStatus
from therobotoverlord_api.database.models.flag import FlagSummary
from therobotoverlord_api.database.models.flag import FlagUpdate


class TestFlagStatus:
    """Test FlagStatus enum."""

    def test_flag_status_values(self):
        """Test that all expected status values exist."""
        assert FlagStatus.PENDING == "pending"
        assert FlagStatus.REVIEWED == "reviewed"
        assert FlagStatus.DISMISSED == "dismissed"
        assert FlagStatus.UPHELD == "upheld"

    def test_flag_status_string_conversion(self):
        """Test string conversion of status values."""
        assert FlagStatus.PENDING.value == "pending"
        assert FlagStatus.UPHELD.value == "upheld"
        assert FlagStatus.DISMISSED.value == "dismissed"


class TestFlag:
    """Test Flag model."""

    def test_flag_post_creation(self):
        """Test creating a flag for a post."""
        flag_data = {
            "post_pk": uuid4(),
            "topic_pk": None,
            "status": FlagStatus.PENDING,
            "updated_at": datetime.now(UTC),
        }

        flag = Flag(
            pk=uuid4(),
            flagger_pk=uuid4(),
            reason="This post violates community guidelines",
            created_at=datetime.now(UTC),
            **flag_data,
        )
        assert flag.post_pk == flag_data["post_pk"]
        assert flag.topic_pk is None
        assert flag.reason == "This post violates community guidelines"
        assert flag.status == FlagStatus.PENDING

    def test_flag_topic_creation(self):
        """Test creating a flag for a topic."""
        flag_data = {
            "post_pk": None,
            "topic_pk": uuid4(),
            "status": FlagStatus.PENDING,
            "updated_at": datetime.now(UTC),
        }

        flag = Flag(
            pk=uuid4(),
            flagger_pk=uuid4(),
            reason="This topic contains inappropriate content",
            created_at=datetime.now(UTC),
            **flag_data,
        )
        assert flag.post_pk is None
        assert flag.topic_pk == flag_data["topic_pk"]
        assert flag.reason == "This topic contains inappropriate content"
        assert flag.status == FlagStatus.PENDING

    def test_flag_with_review_data(self):
        """Test flag with review information."""
        now = datetime.now(UTC)
        flag_data = {
            "post_pk": uuid4(),
            "topic_pk": None,
            "status": FlagStatus.UPHELD,
            "reviewed_by_pk": uuid4(),
            "reviewed_at": now,
            "review_notes": "Flag was justified",
            "updated_at": now,
        }

        flag = Flag(
            pk=uuid4(),
            flagger_pk=uuid4(),
            reason="Test flag",
            created_at=datetime.now(UTC),
            **flag_data,
        )
        assert flag.status == FlagStatus.UPHELD
        assert flag.reviewed_by_pk == flag_data["reviewed_by_pk"]
        assert flag.reviewed_at == now
        assert flag.review_notes == "Flag was justified"

    def test_flag_defaults(self):
        """Test flag default values."""
        flag = Flag(
            pk=uuid4(),
            post_pk=uuid4(),
            flagger_pk=uuid4(),
            reason="Test flag with defaults",
            created_at=datetime.now(UTC),
        )
        assert flag.status == FlagStatus.PENDING


class TestFlagCreate:
    """Test FlagCreate model."""

    def test_flag_create_with_post(self):
        """Test creating FlagCreate for a post."""
        flag_create = FlagCreate(post_pk=uuid4(), reason="This post is inappropriate")

        assert flag_create.post_pk is not None
        assert flag_create.topic_pk is None
        assert flag_create.reason == "This post is inappropriate"

    def test_flag_create_with_topic(self):
        """Test creating FlagCreate for a topic."""
        flag_create = FlagCreate(
            topic_pk=uuid4(), reason="This topic violates guidelines"
        )

        assert flag_create.post_pk is None
        assert flag_create.topic_pk is not None
        assert flag_create.reason == "This topic violates guidelines"

    def test_flag_create_reason_validation(self):
        """Test reason field validation."""
        # Test minimum length
        with pytest.raises(ValidationError) as exc_info:
            FlagCreate(post_pk=uuid4(), reason="short")
        assert "at least 10 characters" in str(exc_info.value)

        # Test maximum length
        long_reason = "x" * 501
        with pytest.raises(ValidationError) as exc_info:
            FlagCreate(post_pk=uuid4(), reason=long_reason)
        assert "at most 500 characters" in str(exc_info.value)

        # Test valid length
        valid_reason = "This is a valid reason for flagging content"
        flag_create = FlagCreate(post_pk=uuid4(), reason=valid_reason)
        assert flag_create.reason == valid_reason

    def test_flag_create_requires_reason(self):
        """Test that reason is required."""
        with pytest.raises(ValidationError) as exc_info:
            FlagCreate(post_pk=uuid4())  # type: ignore[call-arg]
        assert "Field required" in str(exc_info.value)


class TestFlagUpdate:
    """Test FlagUpdate model."""

    def test_flag_update_status_only(self):
        """Test updating only status."""
        flag_update = FlagUpdate(status=FlagStatus.UPHELD)  # type: ignore[call-arg]

        assert flag_update.status == FlagStatus.UPHELD
        assert flag_update.review_notes is None

    def test_flag_update_with_notes(self):
        """Test updating with review notes."""
        flag_update = FlagUpdate(
            status=FlagStatus.DISMISSED, review_notes="Flag was not justified"
        )

        assert flag_update.status == FlagStatus.DISMISSED
        assert flag_update.review_notes == "Flag was not justified"

    def test_flag_update_notes_validation(self):
        """Test review notes length validation."""
        # Test maximum length
        long_notes = "x" * 1001
        with pytest.raises(ValidationError) as exc_info:
            FlagUpdate(status=FlagStatus.UPHELD, review_notes=long_notes)
        assert "at most 1000 characters" in str(exc_info.value)

        # Test valid length
        valid_notes = "This is a valid review note"
        flag_update = FlagUpdate(status=FlagStatus.UPHELD, review_notes=valid_notes)
        assert flag_update.review_notes == valid_notes


class TestFlagSummary:
    """Test FlagSummary model."""

    def test_flag_summary_creation(self):
        """Test creating FlagSummary."""
        now = datetime.now(UTC)
        summary_data = {
            "pk": uuid4(),
            "post_pk": uuid4(),
            "topic_pk": None,
            "flagger_pk": uuid4(),
            "reason": "Test flagging reason",
            "status": FlagStatus.PENDING,
            "reviewed_by_pk": None,
            "reviewed_at": None,
            "created_at": now,
        }

        summary = FlagSummary(
            pk=summary_data["pk"],
            post_pk=summary_data["post_pk"],
            topic_pk=summary_data["topic_pk"],
            flagger_pk=summary_data["flagger_pk"],
            reason=summary_data["reason"],
            status=summary_data["status"],
            reviewed_by_pk=summary_data["reviewed_by_pk"],
            reviewed_at=summary_data["reviewed_at"],
            created_at=summary_data["created_at"],
        )
        assert summary.pk == summary_data["pk"]
        assert summary.post_pk == summary_data["post_pk"]
        assert summary.flagger_pk == summary_data["flagger_pk"]
        assert summary.status == FlagStatus.PENDING
        assert summary.created_at == now

    def test_flag_summary_with_review_data(self):
        """Test FlagSummary with review information."""
        now = datetime.now(UTC)
        summary_data = {
            "pk": uuid4(),
            "post_pk": None,
            "topic_pk": uuid4(),
            "flagger_pk": uuid4(),
            "reason": "Inappropriate topic",
            "status": FlagStatus.UPHELD,
            "reviewed_by_pk": uuid4(),
            "reviewed_at": now,
            "created_at": now,
        }

        summary = FlagSummary(
            pk=summary_data["pk"],
            post_pk=summary_data["post_pk"],
            topic_pk=summary_data["topic_pk"],
            flagger_pk=summary_data["flagger_pk"],
            reason=summary_data["reason"],
            status=summary_data["status"],
            reviewed_by_pk=summary_data["reviewed_by_pk"],
            reviewed_at=summary_data["reviewed_at"],
            created_at=summary_data["created_at"],
        )
        assert summary.topic_pk == summary_data["topic_pk"]
        assert summary.status == FlagStatus.UPHELD
        assert summary.reviewed_by_pk == summary_data["reviewed_by_pk"]
        assert summary.reviewed_at == now
