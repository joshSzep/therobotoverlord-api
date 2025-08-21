"""Tests for badge models."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

from therobotoverlord_api.database.models.badge import Badge
from therobotoverlord_api.database.models.badge import BadgeCreate
from therobotoverlord_api.database.models.badge import BadgeEligibilityCheck
from therobotoverlord_api.database.models.badge import BadgeType
from therobotoverlord_api.database.models.badge import BadgeUpdate
from therobotoverlord_api.database.models.badge import UserBadge
from therobotoverlord_api.database.models.badge import UserBadgeCreate
from therobotoverlord_api.database.models.badge import UserBadgeSummary
from therobotoverlord_api.database.models.badge import UserBadgeWithDetails


class TestBadge:
    """Test Badge model."""

    def test_badge_creation(self):
        """Test creating a Badge instance."""
        pk = uuid4()
        created_at = datetime.now(UTC)
        criteria_config = {"type": "approved_posts", "count": 10}

        badge = Badge(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            name="First Post",
            description="Your first approved post",
            badge_type=BadgeType.POSITIVE,
            criteria_config=criteria_config,
            image_url="https://example.com/icon.png",
            is_active=True,
        )

        assert badge.pk == pk
        assert badge.created_at == created_at
        assert badge.updated_at is None
        assert badge.name == "First Post"
        assert badge.description == "Your first approved post"
        assert badge.badge_type == BadgeType.POSITIVE
        assert badge.criteria_config == criteria_config
        assert badge.image_url == "https://example.com/icon.png"
        assert badge.is_active is True

    def test_badge_default_values(self):
        """Test Badge model default values."""
        badge = Badge(
            pk=uuid4(),
            created_at=datetime.now(UTC),
            name="Test Badge",
            description="Test description",
            badge_type=BadgeType.NEGATIVE,
            image_url="https://example.com/test.png",
            criteria_config={"type": "test"},
        )

        assert badge.updated_at is None
        assert badge.is_active is True


class TestBadgeCreate:
    """Test BadgeCreate model."""

    def test_badge_create_valid(self):
        """Test creating a valid BadgeCreate instance."""
        criteria_config = {"type": "approved_posts", "count": 10}

        badge_create = BadgeCreate(
            name="New Badge",
            description="A new badge",
            badge_type=BadgeType.POSITIVE,
            criteria_config=criteria_config,
            image_url="https://example.com/icon.png",
        )

        assert badge_create.name == "New Badge"
        assert badge_create.description == "A new badge"
        assert badge_create.badge_type == BadgeType.POSITIVE
        assert badge_create.criteria_config == criteria_config
        assert badge_create.image_url == "https://example.com/icon.png"


class TestBadgeUpdate:
    """Test BadgeUpdate model."""

    def test_badge_update_partial(self):
        """Test partial update of badge."""
        badge_update = BadgeUpdate(
            name="Updated Name",
            description="Updated description",
        )

        assert badge_update.name == "Updated Name"
        assert badge_update.description == "Updated description"
        assert badge_update.badge_type is None
        assert badge_update.criteria_config is None
        assert badge_update.image_url is None
        assert badge_update.is_active is None


class TestUserBadge:
    """Test UserBadge model."""

    def test_user_badge_creation(self):
        """Test creating a UserBadge instance."""
        pk = uuid4()
        user_pk = uuid4()
        badge_pk = uuid4()
        awarded_at = datetime.now(UTC)

        user_badge = UserBadge(
            pk=pk,
            created_at=awarded_at,
            updated_at=None,
            user_pk=user_pk,
            badge_pk=badge_pk,
            awarded_at=awarded_at,
        )

        assert user_badge.pk == pk
        assert user_badge.created_at == awarded_at
        assert user_badge.updated_at is None
        assert user_badge.user_pk == user_pk
        assert user_badge.badge_pk == badge_pk
        assert user_badge.awarded_at == awarded_at


class TestUserBadgeCreate:
    """Test UserBadgeCreate model."""

    def test_user_badge_create_minimal(self):
        """Test creating a minimal UserBadgeCreate instance."""
        user_pk = uuid4()
        badge_pk = uuid4()

        user_badge_create = UserBadgeCreate(
            user_pk=user_pk,
            badge_pk=badge_pk,
        )

        assert user_badge_create.user_pk == user_pk
        assert user_badge_create.badge_pk == badge_pk


class TestUserBadgeSummary:
    """Test UserBadgeSummary model."""

    def test_user_badge_summary_creation(self):
        """Test creating a UserBadgeSummary instance."""
        user_pk = uuid4()

        summary = UserBadgeSummary(
            user_pk=user_pk,
            username="testuser",
            total_badges=5,
            positive_badges=3,
            negative_badges=2,
        )

        assert summary.user_pk == user_pk
        assert summary.username == "testuser"
        assert summary.total_badges == 5
        assert summary.positive_badges == 3
        assert summary.negative_badges == 2


class TestUserBadgeWithDetails:
    """Test UserBadgeWithDetails model."""

    def test_user_badge_with_details_creation(self):
        """Test creating a UserBadgeWithDetails instance."""
        pk = uuid4()
        user_pk = uuid4()
        badge_pk = uuid4()
        awarded_at = datetime.now(UTC)

        badge = Badge(
            pk=badge_pk,
            created_at=datetime.now(UTC),
            name="Test Badge",
            description="Test description",
            badge_type=BadgeType.POSITIVE,
            image_url="https://example.com/icon.png",
            criteria_config={"type": "test"},
        )

        details = UserBadgeWithDetails(
            pk=pk,
            created_at=awarded_at,
            user_pk=user_pk,
            badge_pk=badge_pk,
            awarded_at=awarded_at,
            badge=badge,
            username="testuser",
        )

        assert details.pk == pk
        assert details.user_pk == user_pk
        assert details.badge_pk == badge_pk
        assert details.awarded_at == awarded_at
        assert details.badge == badge
        assert details.username == "testuser"


class TestBadgeEligibilityCheck:
    """Test BadgeEligibilityCheck model."""

    def test_badge_eligibility_check_eligible(self):
        """Test creating an eligible BadgeEligibilityCheck instance."""
        badge_pk = uuid4()

        check = BadgeEligibilityCheck(
            badge_pk=badge_pk,
            badge_name="Test Badge",
            is_eligible=True,
            current_progress=10,
            required_progress=10,
            criteria_met=True,
            reason="All criteria met",
        )

        assert check.badge_pk == badge_pk
        assert check.badge_name == "Test Badge"
        assert check.is_eligible is True
        assert check.current_progress == 10
        assert check.required_progress == 10
        assert check.criteria_met is True
        assert check.reason == "All criteria met"


class TestBadgeType:
    """Test BadgeType enum."""

    def test_badge_type_values(self):
        """Test BadgeType enum values."""
        assert BadgeType.POSITIVE == "positive"
        assert BadgeType.NEGATIVE == "negative"

    def test_badge_type_iteration(self):
        """Test iterating over BadgeType enum."""
        types = list(BadgeType)
        assert len(types) == 2
        assert BadgeType.POSITIVE in types
        assert BadgeType.NEGATIVE in types
