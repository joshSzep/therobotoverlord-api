"""Simple tests for loyalty score API endpoints."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


class TestLoyaltyScoreAPISimple:
    """Simple test class for loyalty score API endpoints."""

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.loyalty_score.get_loyalty_score_service")
    async def test_get_my_loyalty_profile_success(self, mock_get_service):
        """Test getting current user's loyalty profile successfully."""
        mock_service = AsyncMock()
        mock_profile = {"user_pk": uuid4(), "current_score": 150, "rank": 5}
        mock_service.get_user_loyalty_profile.return_value = mock_profile
        mock_get_service.return_value = mock_service

        # Mock user
        mock_user = type("User", (), {"pk": uuid4()})()

        from therobotoverlord_api.api.loyalty_score import get_my_loyalty_profile
        
        result = await get_my_loyalty_profile(mock_user)
        
        mock_service.get_user_loyalty_profile.assert_called_once_with(mock_user.pk)
        assert result == mock_profile

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.loyalty_score.get_loyalty_score_service")
    async def test_get_my_loyalty_profile_not_found(self, mock_get_service):
        """Test getting loyalty profile when user not found."""
        mock_service = AsyncMock()
        mock_service.get_user_loyalty_profile.side_effect = ValueError("User not found")
        mock_get_service.return_value = mock_service

        # Mock user
        mock_user = type("User", (), {"pk": uuid4()})()

        from therobotoverlord_api.api.loyalty_score import get_my_loyalty_profile
        
        with pytest.raises(HTTPException) as exc_info:
            await get_my_loyalty_profile(mock_user)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.loyalty_score.get_loyalty_score_service")
    async def test_get_user_loyalty_profile_success(self, mock_get_service):
        """Test getting specific user's loyalty profile successfully."""
        user_pk = uuid4()
        mock_service = AsyncMock()
        mock_profile = {"user_pk": user_pk, "current_score": 100, "rank": 10}
        mock_service.get_user_loyalty_profile.return_value = mock_profile
        mock_get_service.return_value = mock_service

        from therobotoverlord_api.api.loyalty_score import get_user_loyalty_profile
        
        result = await get_user_loyalty_profile(user_pk)
        
        mock_service.get_user_loyalty_profile.assert_called_once_with(user_pk)
        assert result == mock_profile

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.loyalty_score.get_loyalty_score_service")
    async def test_get_my_score_breakdown_success(self, mock_get_service):
        """Test getting current user's score breakdown successfully."""
        mock_service = AsyncMock()
        mock_breakdown = {"topics": 50, "posts": 75, "comments": 25}
        mock_service.get_user_score_breakdown.return_value = mock_breakdown
        mock_get_service.return_value = mock_service

        # Mock user
        mock_user = type("User", (), {"pk": uuid4()})()

        from therobotoverlord_api.api.loyalty_score import get_my_score_breakdown
        
        result = await get_my_score_breakdown(mock_user)
        
        mock_service.get_user_score_breakdown.assert_called_once_with(mock_user.pk)
        assert result == mock_breakdown

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.loyalty_score.get_loyalty_score_service")
    async def test_get_user_score_breakdown_success(self, mock_get_service):
        """Test getting specific user's score breakdown successfully."""
        user_pk = uuid4()
        mock_service = AsyncMock()
        mock_breakdown = {"topics": 30, "posts": 60, "comments": 10}
        mock_service.get_user_score_breakdown.return_value = mock_breakdown
        mock_get_service.return_value = mock_service

        from therobotoverlord_api.api.loyalty_score import get_user_score_breakdown
        
        result = await get_user_score_breakdown(user_pk)
        
        mock_service.get_user_score_breakdown.assert_called_once_with(user_pk)
        assert result == mock_breakdown

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.api.loyalty_score.get_loyalty_score_service")
    async def test_get_user_score_breakdown_not_found(self, mock_get_service):
        """Test getting score breakdown when user not found."""
        user_pk = uuid4()
        mock_service = AsyncMock()
        mock_service.get_user_score_breakdown.side_effect = ValueError("User not found")
        mock_get_service.return_value = mock_service

        from therobotoverlord_api.api.loyalty_score import get_user_score_breakdown
        
        with pytest.raises(HTTPException) as exc_info:
            await get_user_score_breakdown(user_pk)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
