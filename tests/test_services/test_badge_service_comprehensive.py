"""Comprehensive tests for BadgeService."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.badge import Badge
from therobotoverlord_api.database.models.badge import BadgeCreate
from therobotoverlord_api.database.models.badge import BadgeEligibilityCheck
from therobotoverlord_api.database.models.badge import BadgeType
from therobotoverlord_api.database.models.badge import BadgeUpdate
from therobotoverlord_api.database.models.badge import UserBadge
from therobotoverlord_api.database.models.badge import UserBadgeSummary
from therobotoverlord_api.database.models.badge import UserBadgeWithDetails
from therobotoverlord_api.services.badge_service import BadgeService


class TestBadgeService:
    """Test class for BadgeService."""

    @pytest.fixture
    def service(self):
        """Create BadgeService instance."""
        return BadgeService()

    @pytest.fixture
    def mock_badge(self):
        """Mock Badge instance."""
        return Badge(
            pk=uuid4(),
            name="Test Badge",
            description="A test badge",
            image_url="https://example.com/badge.png",
            badge_type=BadgeType.POSITIVE,
            criteria_config={"type": "approved_posts", "count": 5},
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def mock_user_badge(self):
        """Mock UserBadge instance."""
        return UserBadge(
            pk=uuid4(),
            user_pk=uuid4(),
            badge_pk=uuid4(),
            awarded_at=datetime.now(UTC),
            awarded_by_event="test_event",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_get_all_badges(self, mock_badge_repo, service, mock_badge):
        """Test getting all active badges."""
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_active_badges.return_value = [mock_badge]
        mock_badge_repo.return_value = mock_repo_instance
        service.badge_repo = mock_repo_instance

        result = await service.get_all_badges()

        mock_repo_instance.get_active_badges.assert_called_once()
        assert result == [mock_badge]

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_get_badge_by_id(self, mock_badge_repo, service, mock_badge):
        """Test getting badge by ID."""
        badge_id = uuid4()
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_pk.return_value = mock_badge
        mock_badge_repo.return_value = mock_repo_instance
        service.badge_repo = mock_repo_instance

        result = await service.get_badge_by_id(badge_id)

        mock_repo_instance.get_by_pk.assert_called_once_with(badge_id)
        assert result == mock_badge

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_get_badge_by_name(self, mock_badge_repo, service, mock_badge):
        """Test getting badge by name."""
        badge_name = "Test Badge"
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_name.return_value = mock_badge
        mock_badge_repo.return_value = mock_repo_instance
        service.badge_repo = mock_repo_instance

        result = await service.get_badge_by_name(badge_name)

        mock_repo_instance.get_by_name.assert_called_once_with(badge_name)
        assert result == mock_badge

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_create_badge(self, mock_badge_repo, service, mock_badge):
        """Test creating a new badge."""
        badge_data = BadgeCreate(
            name="New Badge",
            description="A new badge",
            image_url="https://example.com/new.png",
            badge_type=BadgeType.POSITIVE,
            criteria_config={"type": "approved_posts", "count": 10},
        )
        mock_repo_instance = AsyncMock()
        mock_repo_instance.create_from_dict.return_value = mock_badge
        mock_badge_repo.return_value = mock_repo_instance
        service.badge_repo = mock_repo_instance

        result = await service.create_badge(badge_data)

        mock_repo_instance.create_from_dict.assert_called_once_with(
            badge_data.model_dump()
        )
        assert result == mock_badge

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_update_badge_with_data(self, mock_badge_repo, service, mock_badge):
        """Test updating a badge with data."""
        badge_id = uuid4()
        badge_data = BadgeUpdate(
            name="Updated Badge", description="Updated description"
        )
        mock_repo_instance = AsyncMock()
        mock_repo_instance.update_from_dict.return_value = mock_badge
        mock_badge_repo.return_value = mock_repo_instance
        service.badge_repo = mock_repo_instance

        result = await service.update_badge(badge_id, badge_data)

        mock_repo_instance.update_from_dict.assert_called_once_with(
            badge_id, {"name": "Updated Badge", "description": "Updated description"}
        )
        assert result == mock_badge

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_update_badge_no_data(self, mock_badge_repo, service, mock_badge):
        """Test updating a badge with no data returns existing badge."""
        badge_id = uuid4()
        badge_data = BadgeUpdate()  # Empty update
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_pk.return_value = mock_badge
        mock_badge_repo.return_value = mock_repo_instance
        service.badge_repo = mock_repo_instance

        result = await service.update_badge(badge_id, badge_data)

        mock_repo_instance.get_by_pk.assert_called_once_with(badge_id)
        assert result == mock_badge

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_delete_badge_success(self, mock_badge_repo, service):
        """Test deleting a badge successfully."""
        badge_id = uuid4()
        mock_repo_instance = AsyncMock()
        mock_repo_instance.update_from_dict.return_value = Badge(
            pk=badge_id,
            name="Test",
            description="Test",
            image_url="test.png",
            badge_type=BadgeType.POSITIVE,
            criteria_config={},
            is_active=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_badge_repo.return_value = mock_repo_instance
        service.badge_repo = mock_repo_instance

        result = await service.delete_badge(badge_id)

        mock_repo_instance.update_from_dict.assert_called_once_with(
            badge_id, {"is_active": False}
        )
        assert result is True

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_delete_badge_failure(self, mock_badge_repo, service):
        """Test deleting a badge that doesn't exist."""
        badge_id = uuid4()
        mock_repo_instance = AsyncMock()
        mock_repo_instance.update_from_dict.return_value = None
        mock_badge_repo.return_value = mock_repo_instance
        service.badge_repo = mock_repo_instance

        result = await service.delete_badge(badge_id)

        assert result is False

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    async def test_get_user_badges(self, mock_user_badge_repo, service):
        """Test getting user badges."""
        user_id = uuid4()
        mock_badge = Badge(
            pk=uuid4(),
            name="Test Badge",
            description="Test",
            image_url="test.png",
            badge_type=BadgeType.POSITIVE,
            criteria_config={},
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_badges = [
            UserBadgeWithDetails(
                pk=uuid4(),
                user_pk=user_id,
                badge_pk=uuid4(),
                awarded_at=datetime.now(UTC),
                awarded_by_event="test",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                badge=mock_badge,
            )
        ]
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_user_badges.return_value = mock_badges
        mock_user_badge_repo.return_value = mock_repo_instance
        service.user_badge_repo = mock_repo_instance

        result = await service.get_user_badges(user_id)

        mock_repo_instance.get_user_badges.assert_called_once_with(user_id)
        assert result == mock_badges

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    async def test_get_user_badge_summary(self, mock_user_badge_repo, service):
        """Test getting user badge summary."""
        user_id = uuid4()
        username = "testuser"
        mock_badges = []
        mock_counts = {"total": 5, "positive": 3, "negative": 2}
        mock_recent = []

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_user_badges.return_value = mock_badges
        mock_repo_instance.get_user_badge_counts.return_value = mock_counts
        mock_repo_instance.get_recent_user_badges.return_value = mock_recent
        mock_user_badge_repo.return_value = mock_repo_instance
        service.user_badge_repo = mock_repo_instance

        result = await service.get_user_badge_summary(user_id, username)

        assert isinstance(result, UserBadgeSummary)
        assert result.user_pk == user_id
        assert result.username == username
        assert result.total_badges == 5
        assert result.positive_badges == 3
        assert result.negative_badges == 2
        mock_repo_instance.get_recent_user_badges.assert_called_once_with(user_id, 3)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_manually_award_badge_success(
        self,
        mock_badge_repo,
        mock_user_badge_repo,
        service,
        mock_badge,
        mock_user_badge,
    ):
        """Test manually awarding a badge successfully."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        mock_badge_repo_instance = AsyncMock()
        mock_badge_repo_instance.get_by_pk.return_value = mock_badge
        mock_badge_repo.return_value = mock_badge_repo_instance
        service.badge_repo = mock_badge_repo_instance

        mock_user_badge_repo_instance = AsyncMock()
        mock_user_badge_repo_instance.has_badge.return_value = False
        mock_user_badge_repo_instance.award_badge.return_value = mock_user_badge
        mock_user_badge_repo.return_value = mock_user_badge_repo_instance
        service.user_badge_repo = mock_user_badge_repo_instance

        result = await service.manually_award_badge(
            user_id, badge_id, awarded_by_user_id
        )

        mock_user_badge_repo_instance.has_badge.assert_called_once_with(
            user_id, badge_id
        )
        mock_badge_repo_instance.get_by_pk.assert_called_once_with(badge_id)
        mock_user_badge_repo_instance.award_badge.assert_called_once()
        assert result == mock_user_badge

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    async def test_manually_award_badge_already_has(
        self, mock_user_badge_repo, service
    ):
        """Test manually awarding a badge user already has."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        mock_repo_instance = AsyncMock()
        mock_repo_instance.has_badge.return_value = True
        mock_user_badge_repo.return_value = mock_repo_instance
        service.user_badge_repo = mock_repo_instance

        result = await service.manually_award_badge(
            user_id, badge_id, awarded_by_user_id
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_manually_award_badge_inactive(
        self, mock_badge_repo, mock_user_badge_repo, service
    ):
        """Test manually awarding an inactive badge."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        inactive_badge = Badge(
            pk=badge_id,
            name="Inactive",
            description="Inactive badge",
            image_url="inactive.png",
            badge_type=BadgeType.POSITIVE,
            criteria_config={},
            is_active=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_badge_repo_instance = AsyncMock()
        mock_badge_repo_instance.get_by_pk.return_value = inactive_badge
        mock_badge_repo.return_value = mock_badge_repo_instance
        service.badge_repo = mock_badge_repo_instance

        mock_user_badge_repo_instance = AsyncMock()
        mock_user_badge_repo_instance.has_badge.return_value = False
        mock_user_badge_repo.return_value = mock_user_badge_repo_instance
        service.user_badge_repo = mock_user_badge_repo_instance

        result = await service.manually_award_badge(
            user_id, badge_id, awarded_by_user_id
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    async def test_revoke_badge_success(
        self, mock_user_badge_repo, service, mock_user_badge
    ):
        """Test revoking a badge successfully."""
        user_id = uuid4()
        badge_id = uuid4()

        mock_repo_instance = AsyncMock()
        mock_repo_instance.find_one_by.return_value = mock_user_badge
        mock_repo_instance.delete_by_pk.return_value = True
        mock_user_badge_repo.return_value = mock_repo_instance
        service.user_badge_repo = mock_repo_instance

        result = await service.revoke_badge(user_id, badge_id)

        mock_repo_instance.find_one_by.assert_called_once_with(
            user_pk=user_id, badge_pk=badge_id
        )
        mock_repo_instance.delete_by_pk.assert_called_once_with(mock_user_badge.pk)
        assert result is True

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    async def test_revoke_badge_not_found(self, mock_user_badge_repo, service):
        """Test revoking a badge user doesn't have."""
        user_id = uuid4()
        badge_id = uuid4()

        mock_repo_instance = AsyncMock()
        mock_repo_instance.find_one_by.return_value = None
        mock_user_badge_repo.return_value = mock_repo_instance
        service.user_badge_repo = mock_repo_instance

        result = await service.revoke_badge(user_id, badge_id)

        assert result is False

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    @patch("therobotoverlord_api.services.badge_service.BadgeRepository")
    async def test_evaluate_badge_criteria_for_user(
        self, mock_badge_repo, mock_user_badge_repo, service, mock_badge
    ):
        """Test evaluating badge criteria for user."""
        user_id = uuid4()

        mock_badge_repo_instance = AsyncMock()
        mock_badge_repo_instance.get_active_badges.return_value = [mock_badge]
        mock_badge_repo.return_value = mock_badge_repo_instance
        service.badge_repo = mock_badge_repo_instance

        mock_user_badge_repo_instance = AsyncMock()
        mock_user_badge_repo_instance.has_badge.return_value = False
        mock_user_badge_repo.return_value = mock_user_badge_repo_instance
        service.user_badge_repo = mock_user_badge_repo_instance

        with patch.object(service, "_check_badge_eligibility") as mock_check:
            mock_eligibility = BadgeEligibilityCheck(
                badge_pk=mock_badge.pk,
                badge_name=mock_badge.name,
                is_eligible=True,
                current_progress=5,
                required_progress=5,
                criteria_met=True,
                reason="Criteria met",
            )
            mock_check.return_value = mock_eligibility

            result = await service.evaluate_badge_criteria_for_user(user_id)

            assert len(result) == 1
            assert result[0] == mock_eligibility
            mock_check.assert_called_once_with(user_id, mock_badge)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.get_db_connection")
    async def test_check_approved_posts_criteria(
        self, mock_get_connection, service, mock_badge
    ):
        """Test checking approved posts criteria."""
        user_id = uuid4()
        criteria = {"type": "approved_posts", "count": 5}
        mock_badge.criteria_config = criteria

        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = 5
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await service._check_approved_posts_criteria(
            user_id, mock_badge, criteria
        )

        assert isinstance(result, BadgeEligibilityCheck)
        assert result.is_eligible is True
        assert result.current_progress == 5
        assert result.required_progress == 5

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.get_db_connection")
    async def test_check_rejected_posts_criteria(
        self, mock_get_connection, service, mock_badge
    ):
        """Test checking rejected posts criteria."""
        user_id = uuid4()
        criteria = {
            "type": "rejected_posts",
            "count": 3,
            "criteria": "strawman_fallacy",
        }
        mock_badge.criteria_config = criteria

        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = 2
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await service._check_rejected_posts_criteria(
            user_id, mock_badge, criteria
        )

        assert isinstance(result, BadgeEligibilityCheck)
        assert result.is_eligible is False
        assert result.current_progress == 2
        assert result.required_progress == 3

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.get_db_connection")
    async def test_check_successful_appeals_criteria(
        self, mock_get_connection, service, mock_badge
    ):
        """Test checking successful appeals criteria."""
        user_id = uuid4()
        criteria = {"type": "successful_appeals", "count": 2}
        mock_badge.criteria_config = criteria

        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = 3
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await service._check_successful_appeals_criteria(
            user_id, mock_badge, criteria
        )

        assert isinstance(result, BadgeEligibilityCheck)
        assert result.is_eligible is True
        assert result.current_progress == 3
        assert result.required_progress == 2

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.get_db_connection")
    async def test_check_first_approved_post_criteria(
        self, mock_get_connection, service, mock_badge
    ):
        """Test checking first approved post criteria."""
        user_id = uuid4()

        mock_connection = AsyncMock()
        mock_connection.fetchval.return_value = 1
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        result = await service._check_first_approved_post_criteria(user_id, mock_badge)

        assert isinstance(result, BadgeEligibilityCheck)
        assert result.is_eligible is True
        assert result.current_progress == 1
        assert result.required_progress == 1

    @pytest.mark.asyncio
    async def test_check_badge_eligibility_unknown_criteria(self, service, mock_badge):
        """Test checking badge eligibility with unknown criteria type."""
        user_id = uuid4()
        mock_badge.criteria_config = {"type": "unknown_type"}

        result = await service._check_badge_eligibility(user_id, mock_badge)

        assert isinstance(result, BadgeEligibilityCheck)
        assert result.is_eligible is False
        assert result.reason == "Unknown criteria type"

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    async def test_auto_award_eligible_badges(
        self, mock_user_badge_repo, service, mock_user_badge
    ):
        """Test automatically awarding eligible badges."""
        user_id = uuid4()
        event_type = "post_approved"

        mock_eligibility = BadgeEligibilityCheck(
            badge_pk=uuid4(),
            badge_name="Test Badge",
            is_eligible=True,
            current_progress=5,
            required_progress=5,
            criteria_met=True,
            reason="Criteria met",
        )

        mock_repo_instance = AsyncMock()
        mock_repo_instance.award_badge.return_value = mock_user_badge
        mock_user_badge_repo.return_value = mock_repo_instance
        service.user_badge_repo = mock_repo_instance

        with patch.object(service, "evaluate_badge_criteria_for_user") as mock_evaluate:
            mock_evaluate.return_value = [mock_eligibility]

            result = await service.auto_award_eligible_badges(user_id, event_type)

            assert len(result) == 1
            assert result[0] == mock_user_badge
            mock_repo_instance.award_badge.assert_called_once()

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    async def test_auto_award_eligible_badges_exception(
        self, mock_user_badge_repo, service
    ):
        """Test auto awarding badges with exception (race condition)."""
        user_id = uuid4()
        event_type = "post_approved"

        mock_eligibility = BadgeEligibilityCheck(
            badge_pk=uuid4(),
            badge_name="Test Badge",
            is_eligible=True,
            current_progress=5,
            required_progress=5,
            criteria_met=True,
            reason="Criteria met",
        )

        mock_repo_instance = AsyncMock()
        mock_repo_instance.award_badge.side_effect = Exception("Badge already awarded")
        mock_user_badge_repo.return_value = mock_repo_instance
        service.user_badge_repo = mock_repo_instance

        with patch.object(service, "evaluate_badge_criteria_for_user") as mock_evaluate:
            mock_evaluate.return_value = [mock_eligibility]

            result = await service.auto_award_eligible_badges(user_id, event_type)

            assert len(result) == 0  # Exception handled, no badges awarded

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.badge_service.UserBadgeRepository")
    async def test_get_badge_recipients(self, mock_user_badge_repo, service):
        """Test getting badge recipients."""
        badge_id = uuid4()
        limit = 50
        mock_badge = Badge(
            pk=badge_id,
            name="Test Badge",
            description="Test",
            image_url="test.png",
            badge_type=BadgeType.POSITIVE,
            criteria_config={},
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_recipients = [
            UserBadgeWithDetails(
                pk=uuid4(),
                user_pk=uuid4(),
                badge_pk=badge_id,
                awarded_at=datetime.now(UTC),
                awarded_by_event="test",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                badge=mock_badge,
            )
        ]

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_badge_recipients.return_value = mock_recipients
        mock_user_badge_repo.return_value = mock_repo_instance
        service.user_badge_repo = mock_repo_instance

        result = await service.get_badge_recipients(badge_id, limit)

        mock_repo_instance.get_badge_recipients.assert_called_once_with(badge_id, limit)
        assert result == mock_recipients
