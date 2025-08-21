"""Simple coverage tests for BadgeService."""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from therobotoverlord_api.services.badge_service import BadgeService


class TestBadgeServiceSimple:
    """Simple tests to improve BadgeService coverage."""

    @pytest.fixture
    def badge_service(self):
        """Create BadgeService with mocked repositories."""
        service = BadgeService()
        service.badge_repo = AsyncMock()
        service.user_badge_repo = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_get_all_badges(self, badge_service):
        """Test getting all badges."""
        badge_service.badge_repo.get_active_badges.return_value = []
        
        result = await badge_service.get_all_badges()
        
        badge_service.badge_repo.get_active_badges.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_badge_by_id(self, badge_service):
        """Test getting badge by ID."""
        badge_id = uuid4()
        badge_service.badge_repo.get_by_pk.return_value = None
        
        result = await badge_service.get_badge_by_id(badge_id)
        
        badge_service.badge_repo.get_by_pk.assert_called_once_with(badge_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_badge_by_name(self, badge_service):
        """Test getting badge by name."""
        badge_service.badge_repo.get_by_name.return_value = None
        
        result = await badge_service.get_badge_by_name("test_badge")
        
        badge_service.badge_repo.get_by_name.assert_called_once_with("test_badge")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_badge(self, badge_service):
        """Test creating a badge."""
        from therobotoverlord_api.database.models.badge import BadgeCreate
        
        badge_data = BadgeCreate(
            name="Test Badge",
            description="A test badge",
            badge_type="positive",
            image_url="https://example.com/badge.png",
            criteria_config={"posts": 10},
            points=100
        )
        
        mock_badge = {"pk": uuid4(), "name": "Test Badge"}
        badge_service.badge_repo.create_from_dict.return_value = mock_badge
        
        result = await badge_service.create_badge(badge_data)
        
        badge_service.badge_repo.create_from_dict.assert_called_once()
        assert result == mock_badge

    @pytest.mark.asyncio
    async def test_update_badge(self, badge_service):
        """Test updating a badge."""
        from therobotoverlord_api.database.models.badge import BadgeUpdate
        
        badge_id = uuid4()
        badge_data = BadgeUpdate(description="Updated description")
        
        mock_badge = {"pk": badge_id, "description": "Updated description"}
        badge_service.badge_repo.update_from_dict.return_value = mock_badge
        
        result = await badge_service.update_badge(badge_id, badge_data)
        
        badge_service.badge_repo.update_from_dict.assert_called_once()
        assert result == mock_badge

    @pytest.mark.asyncio
    async def test_delete_badge(self, badge_service):
        """Test deleting a badge."""
        badge_id = uuid4()
        badge_service.badge_repo.update_from_dict.return_value = {"pk": badge_id}
        
        result = await badge_service.delete_badge(badge_id)
        
        badge_service.badge_repo.update_from_dict.assert_called_once_with(badge_id, {"is_active": False})
        assert result is True

    @pytest.mark.asyncio
    async def test_get_user_badges(self, badge_service):
        """Test getting user badges."""
        user_id = uuid4()
        badge_service.user_badge_repo.get_user_badges.return_value = []
        
        result = await badge_service.get_user_badges(user_id)
        
        badge_service.user_badge_repo.get_user_badges.assert_called_once_with(user_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_manually_award_badge(self, badge_service):
        """Test manually awarding badge."""
        badge_id = uuid4()
        user_id = uuid4()
        awarded_by_user_id = uuid4()
        
        # Mock user doesn't have badge
        badge_service.user_badge_repo.has_badge.return_value = False
        
        # Mock badge exists and is active
        mock_badge = type("Badge", (), {"pk": badge_id, "is_active": True})()
        badge_service.badge_repo.get_by_pk.return_value = mock_badge
        
        # Mock award creation
        mock_user_badge = {"pk": uuid4(), "badge_id": badge_id, "user_id": user_id}
        badge_service.user_badge_repo.award_badge.return_value = mock_user_badge
        
        result = await badge_service.manually_award_badge(user_id, badge_id, awarded_by_user_id)
        
        badge_service.user_badge_repo.has_badge.assert_called_with(user_id, badge_id)
        badge_service.badge_repo.get_by_pk.assert_called_with(badge_id)
        badge_service.user_badge_repo.award_badge.assert_called_once()
        assert result == mock_user_badge

    @pytest.mark.asyncio
    async def test_revoke_badge(self, badge_service):
        """Test revoking badge."""
        user_id = uuid4()
        badge_id = uuid4()
        
        # Mock finding user badge
        mock_user_badge = type("UserBadge", (), {"pk": uuid4()})()
        badge_service.user_badge_repo.find_one_by.return_value = mock_user_badge

        # Mock deletion
        badge_service.user_badge_repo.delete_by_pk.return_value = True
        
        result = await badge_service.revoke_badge(user_id, badge_id)
        
        badge_service.user_badge_repo.find_one_by.assert_called_with(user_pk=user_id, badge_pk=badge_id)
        badge_service.user_badge_repo.delete_by_pk.assert_called_with(mock_user_badge.pk)
        assert result is True

    @pytest.mark.asyncio
    async def test_evaluate_badge_criteria_for_user(self, badge_service):
        """Test evaluating badge criteria."""
        user_id = uuid4()
        
        # Mock active badges
        badge_service.badge_repo.get_active_badges.return_value = []
        
        result = await badge_service.evaluate_badge_criteria_for_user(user_id)
        
        badge_service.badge_repo.get_active_badges.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_badge_summary(self, badge_service):
        """Test getting user badge summary."""
        user_id = uuid4()
        username = "testuser"
        
        # Mock repository calls
        badge_service.user_badge_repo.get_user_badges.return_value = []
        badge_service.user_badge_repo.get_user_badge_counts.return_value = {
            "total": 5, "positive": 3, "negative": 2
        }
        badge_service.user_badge_repo.get_recent_user_badges.return_value = []
        
        result = await badge_service.get_user_badge_summary(user_id, username)
        
        badge_service.user_badge_repo.get_user_badges.assert_called_with(user_id)
        badge_service.user_badge_repo.get_user_badge_counts.assert_called_with(user_id)
        badge_service.user_badge_repo.get_recent_user_badges.assert_called_with(user_id, 3)
        assert hasattr(result, "total_badges")
