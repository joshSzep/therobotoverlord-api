"""Simple tests for badges API endpoints."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


class TestBadgesAPISimple:
    """Simple test class for badges API endpoints."""

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_get_all_badges_success(self, mock_service):
        """Test getting all badges successfully."""
        mock_badges = [{"pk": uuid4(), "name": "Test Badge", "description": "A test badge"}]
        mock_service.get_all_badges = AsyncMock(return_value=mock_badges)

        from therobotoverlord_api.api.badges import get_all_badges
        
        result = await get_all_badges()
        
        mock_service.get_all_badges.assert_called_once()
        assert result == mock_badges

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_get_badge_success(self, mock_service):
        """Test getting a badge by ID successfully."""
        badge_id = uuid4()
        mock_badge = {"pk": badge_id, "name": "Test Badge", "description": "A test badge"}
        mock_service.get_badge_by_id = AsyncMock(return_value=mock_badge)

        from therobotoverlord_api.api.badges import get_badge
        
        result = await get_badge(badge_id)
        
        mock_service.get_badge_by_id.assert_called_once_with(badge_id)
        assert result == mock_badge

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_get_badge_not_found(self, mock_service):
        """Test getting a badge that doesn't exist."""
        badge_id = uuid4()
        mock_service.get_badge_by_id = AsyncMock(return_value=None)

        from therobotoverlord_api.api.badges import get_badge
        
        with pytest.raises(HTTPException) as exc_info:
            await get_badge(badge_id)
        
        assert exc_info.value.status_code == 404
        assert "Badge not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_get_user_badges_success(self, mock_service):
        """Test getting user badges successfully."""
        user_id = uuid4()
        mock_badges = [{"pk": uuid4(), "name": "Badge 1"}, {"pk": uuid4(), "name": "Badge 2"}]
        mock_service.get_user_badges = AsyncMock(return_value=mock_badges)

        from therobotoverlord_api.api.badges import get_user_badges
        
        result = await get_user_badges(user_id)
        
        mock_service.get_user_badges.assert_called_once_with(user_id)
        assert result == mock_badges

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.UserRepository")
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_get_user_badge_summary_success(self, mock_service, mock_user_repo):
        """Test getting user badge summary successfully."""
        user_id = uuid4()
        mock_user = type("User", (), {"pk": user_id, "username": "testuser"})()
        
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_pk.return_value = mock_user
        mock_user_repo.return_value = mock_repo_instance
        
        mock_summary = {"user_pk": user_id, "username": "testuser", "total_badges": 5}
        mock_service.get_user_badge_summary = AsyncMock(return_value=mock_summary)

        from therobotoverlord_api.api.badges import get_user_badge_summary
        
        result = await get_user_badge_summary(user_id)
        
        mock_repo_instance.get_by_pk.assert_called_once_with(user_id)
        mock_service.get_user_badge_summary.assert_called_once_with(user_id, mock_user.username)
        assert result == mock_summary

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.UserRepository")
    async def test_get_user_badge_summary_user_not_found(self, mock_user_repo):
        """Test getting badge summary for non-existent user."""
        user_id = uuid4()
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_pk.return_value = None
        mock_user_repo.return_value = mock_repo_instance

        from therobotoverlord_api.api.badges import get_user_badge_summary
        
        with pytest.raises(HTTPException) as exc_info:
            await get_user_badge_summary(user_id)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.RBACService")
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_check_user_badge_eligibility_own_user(self, mock_service, mock_rbac_service):
        """Test checking badge eligibility for own user."""
        user_id = uuid4()
        mock_user = type("User", (), {"pk": user_id})()
        mock_eligibility = [{"badge_id": uuid4(), "eligible": True}]
        mock_service.evaluate_badge_criteria_for_user = AsyncMock(return_value=mock_eligibility)

        from therobotoverlord_api.api.badges import check_user_badge_eligibility
        
        result = await check_user_badge_eligibility(user_id, mock_user)
        
        mock_service.evaluate_badge_criteria_for_user.assert_called_once_with(user_id)
        assert result == mock_eligibility

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.RBACService")
    async def test_check_user_badge_eligibility_forbidden(self, mock_rbac_service):
        """Test checking badge eligibility without permission."""
        user_id = uuid4()
        other_user_id = uuid4()
        mock_user = type("User", (), {"pk": user_id})()
        
        mock_rbac_instance = AsyncMock()
        mock_rbac_instance.is_user_moderator.return_value = False
        mock_rbac_service.return_value = mock_rbac_instance

        from therobotoverlord_api.api.badges import check_user_badge_eligibility
        
        with pytest.raises(HTTPException) as exc_info:
            await check_user_badge_eligibility(other_user_id, mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Cannot check other users' badge eligibility" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_delete_badge_success(self, mock_service):
        """Test deleting a badge successfully."""
        badge_id = uuid4()
        mock_user = type("User", (), {"pk": uuid4()})()
        mock_service.delete_badge = AsyncMock(return_value=True)

        from therobotoverlord_api.api.badges import delete_badge
        
        await delete_badge(badge_id, mock_user)
        
        mock_service.delete_badge.assert_called_once_with(badge_id)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_delete_badge_not_found(self, mock_service):
        """Test deleting a badge that doesn't exist."""
        badge_id = uuid4()
        mock_user = type("User", (), {"pk": uuid4()})()
        mock_service.delete_badge = AsyncMock(return_value=False)

        from therobotoverlord_api.api.badges import delete_badge
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_badge(badge_id, mock_user)
        
        assert exc_info.value.status_code == 404
        assert "Badge not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.UserRepository")
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_award_badge_manually_success(self, mock_service, mock_user_repo):
        """Test manually awarding a badge successfully."""
        user_id = uuid4()
        badge_id = uuid4()
        mock_user = type("User", (), {"pk": uuid4()})()
        
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_pk.return_value = mock_user
        mock_user_repo.return_value = mock_repo_instance
        
        mock_service.manually_award_badge = AsyncMock(return_value={"badge_id": badge_id})
        
        from therobotoverlord_api.api.badges import award_badge_manually
        
        result = await award_badge_manually(user_id, badge_id, mock_user)
        
        mock_repo_instance.get_by_pk.assert_called_once_with(user_id)
        mock_service.manually_award_badge.assert_called_once_with(user_id, badge_id, mock_user.pk)
        assert result["badge_id"] == badge_id
        assert "message" in result

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.UserRepository")
    async def test_award_badge_manually_user_not_found(self, mock_user_repo):
        """Test manually awarding badge to non-existent user."""
        user_id = uuid4()
        badge_id = uuid4()
        mock_user = type("User", (), {"pk": uuid4()})()
        
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_pk.return_value = None
        mock_user_repo.return_value = mock_repo_instance

        from therobotoverlord_api.api.badges import award_badge_manually
        
        with pytest.raises(HTTPException) as exc_info:
            await award_badge_manually(user_id, badge_id, mock_user)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_revoke_badge_success(self, mock_service):
        """Test revoking a badge successfully."""
        user_id = uuid4()
        badge_id = uuid4()
        mock_user = type("User", (), {"pk": uuid4()})()
        mock_service.revoke_badge = AsyncMock(return_value=True)
        
        from therobotoverlord_api.api.badges import revoke_badge
        
        await revoke_badge(user_id, badge_id, mock_user)
        
        mock_service.revoke_badge.assert_called_once_with(user_id, badge_id)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.badges.badge_service")
    async def test_revoke_badge_not_found(self, mock_service):
        """Test revoking a badge that user doesn't have."""
        user_id = uuid4()
        badge_id = uuid4()
        mock_user = type("User", (), {"pk": uuid4()})()
        mock_service.revoke_badge = AsyncMock(return_value=False)
        
        from therobotoverlord_api.api.badges import revoke_badge
        
        with pytest.raises(HTTPException) as exc_info:
            await revoke_badge(user_id, badge_id, mock_user)
        
        assert exc_info.value.status_code == 404
        assert "User does not have this badge" in str(exc_info.value.detail)
