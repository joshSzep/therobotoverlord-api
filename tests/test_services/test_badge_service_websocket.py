"""Tests for badge service WebSocket integration."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.services.badge_service import BadgeService
from therobotoverlord_api.websocket.manager import WebSocketManager


class TestBadgeServiceWebSocket:
    """Test badge service WebSocket integration."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        return AsyncMock(spec=WebSocketManager)

    @pytest.fixture
    def mock_badge_repo(self):
        """Create mock badge repository."""
        repo = AsyncMock()
        repo.get_by_pk = AsyncMock()
        repo.award_badge = AsyncMock()
        return repo

    @pytest.fixture
    def mock_user_badge_repo(self):
        """Create mock user badge repository."""
        repo = AsyncMock()
        repo.has_badge = AsyncMock()
        repo.award_badge = AsyncMock()
        return repo

    @pytest.fixture
    def badge_service(self, mock_badge_repo, mock_user_badge_repo):
        """Create badge service instance."""
        service = BadgeService()
        service.badge_repo = mock_badge_repo
        service.user_badge_repo = mock_user_badge_repo
        return service

    @pytest.mark.asyncio
    async def test_manually_award_badge_with_websocket_broadcast(
        self,
        badge_service,
        mock_badge_repo,
        mock_user_badge_repo,
        mock_websocket_manager,
    ):
        """Test manually awarding badge with WebSocket broadcast."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        # Mock badge exists and user doesn't have it
        mock_badge = type(
            "Badge",
            (),
            {
                "pk": badge_id,
                "is_active": True,
                "name": "Test Badge",
                "description": "Test Description",
                "image_url": "https://example.com/badge.png",
            },
        )()

        mock_badge_repo.get_by_pk.return_value = mock_badge
        mock_user_badge_repo.has_badge.return_value = False
        mock_user_badge_repo.award_badge.return_value = {
            "pk": uuid4(),
            "badge_id": badge_id,
            "user_id": user_id,
        }

        with patch(
            "therobotoverlord_api.services.badge_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            result = await badge_service.manually_award_badge(
                user_id=user_id,
                badge_id=badge_id,
                awarded_by_user_id=awarded_by_user_id,
                websocket_manager=mock_websocket_manager,
            )

            assert result is not None

            # Verify badge earned notification was broadcasted
            mock_broadcaster.broadcast_badge_earned.assert_called_once_with(
                user_id=user_id,
                badge_id=badge_id,
                badge_name="Test Badge",
                badge_description="Test Description",
                badge_icon="https://example.com/badge.png",
            )

    @pytest.mark.asyncio
    async def test_manually_award_badge_user_already_has_badge(
        self,
        badge_service,
        mock_badge_repo,
        mock_user_badge_repo,
        mock_websocket_manager,
    ):
        """Test manually awarding badge when user already has it."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        # Mock user already has badge
        mock_user_badge_repo.has_badge.return_value = True

        with patch(
            "therobotoverlord_api.services.badge_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            result = await badge_service.manually_award_badge(
                user_id=user_id,
                badge_id=badge_id,
                awarded_by_user_id=awarded_by_user_id,
                websocket_manager=mock_websocket_manager,
            )

            assert result is None

            # Should not broadcast if user already has badge
            mock_broadcaster.broadcast_badge_earned.assert_not_called()

    @pytest.mark.asyncio
    async def test_manually_award_badge_inactive_badge(
        self,
        badge_service,
        mock_badge_repo,
        mock_user_badge_repo,
        mock_websocket_manager,
    ):
        """Test manually awarding inactive badge."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        # Mock inactive badge
        mock_badge = type(
            "Badge",
            (),
            {
                "pk": badge_id,
                "is_active": False,
                "name": "Inactive Badge",
                "description": "This badge is inactive",
                "image_url": "https://example.com/inactive.png",
            },
        )()

        mock_badge_repo.get_by_pk.return_value = mock_badge
        mock_user_badge_repo.has_badge.return_value = False

        with patch(
            "therobotoverlord_api.services.badge_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            result = await badge_service.manually_award_badge(
                user_id=user_id,
                badge_id=badge_id,
                awarded_by_user_id=awarded_by_user_id,
                websocket_manager=mock_websocket_manager,
            )

            assert result is None

            # Should not broadcast for inactive badge
            mock_broadcaster.broadcast_badge_earned.assert_not_called()

    @pytest.mark.asyncio
    async def test_manually_award_badge_nonexistent_badge(
        self,
        badge_service,
        mock_badge_repo,
        mock_user_badge_repo,
        mock_websocket_manager,
    ):
        """Test manually awarding non-existent badge."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        # Mock badge not found
        mock_badge_repo.get_by_pk.return_value = None

        with patch(
            "therobotoverlord_api.services.badge_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            result = await badge_service.manually_award_badge(
                user_id=user_id,
                badge_id=badge_id,
                awarded_by_user_id=awarded_by_user_id,
                websocket_manager=mock_websocket_manager,
            )

            assert result is None

            # Should not broadcast for non-existent badge
            mock_broadcaster.broadcast_badge_earned.assert_not_called()

    @pytest.mark.asyncio
    async def test_manually_award_badge_without_websocket_manager(
        self, badge_service, mock_badge_repo, mock_user_badge_repo
    ):
        """Test manually awarding badge without WebSocket manager."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        # Mock badge exists and user doesn't have it
        mock_badge = type(
            "Badge",
            (),
            {
                "pk": badge_id,
                "is_active": True,
                "name": "Test Badge",
                "description": "Test Description",
                "image_url": "https://example.com/badge.png",
            },
        )()

        mock_badge_repo.get_by_pk.return_value = mock_badge
        mock_user_badge_repo.has_badge.return_value = False
        mock_user_badge_repo.award_badge.return_value = {
            "pk": uuid4(),
            "badge_id": badge_id,
            "user_id": user_id,
        }

        # Should not raise exception when websocket_manager is None
        result = await badge_service.manually_award_badge(
            user_id=user_id,
            badge_id=badge_id,
            awarded_by_user_id=awarded_by_user_id,
            websocket_manager=None,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_evaluate_badge_criteria_with_websocket_broadcast(
        self,
        badge_service,
        mock_badge_repo,
        mock_user_badge_repo,
        mock_websocket_manager,
    ):
        """Test evaluating badge criteria with WebSocket broadcasts."""
        user_id = uuid4()

        # Mock active badges
        mock_badges = [
            type(
                "Badge",
                (),
                {
                    "pk": uuid4(),
                    "is_active": True,
                    "name": "First Post",
                    "description": "Created your first post",
                    "image_url": "https://example.com/first-post.png",
                    "criteria_config": {"posts": 1},
                },
            )(),
            type(
                "Badge",
                (),
                {
                    "pk": uuid4(),
                    "is_active": True,
                    "name": "Prolific Poster",
                    "description": "Created 10 posts",
                    "image_url": "https://example.com/prolific.png",
                    "criteria_config": {"posts": 10},
                },
            )(),
        ]

        mock_badge_repo.get_active_badges.return_value = mock_badges
        mock_user_badge_repo.has_badge.return_value = False
        mock_user_badge_repo.award_badge.return_value = {"pk": uuid4()}

        with patch(
            "therobotoverlord_api.services.badge_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            # Mock badge eligibility check to award first badge
            with patch.object(badge_service, "_check_badge_eligibility") as mock_check:
                from therobotoverlord_api.database.models.badge import (
                    BadgeEligibilityCheck,
                )

                mock_check.side_effect = [
                    BadgeEligibilityCheck(
                        badge_pk=mock_badges[0].pk,
                        badge_name=mock_badges[0].name,
                        is_eligible=True,
                        current_progress=1,
                        required_progress=1,
                        criteria_met=True,
                        reason="Criteria met",
                    ),
                    BadgeEligibilityCheck(
                        badge_pk=mock_badges[1].pk,
                        badge_name=mock_badges[1].name,
                        is_eligible=False,
                        current_progress=0,
                        required_progress=10,
                        criteria_met=False,
                        reason="Criteria not met",
                    ),
                ]  # First badge earned, second not

                awarded_badges = await badge_service.evaluate_badge_criteria_for_user(
                    user_id=user_id, websocket_manager=mock_websocket_manager
                )

                assert len(awarded_badges) == 1

                # Verify badge earned notification was broadcasted
                mock_broadcaster.broadcast_badge_earned.assert_called_once_with(
                    user_id=user_id,
                    badge_id=mock_badges[0].pk,
                    badge_name="First Post",
                    badge_description="Created your first post",
                    badge_icon="https://example.com/first-post.png",
                )

    @pytest.mark.asyncio
    async def test_badge_websocket_error_handling(
        self,
        badge_service,
        mock_badge_repo,
        mock_user_badge_repo,
        mock_websocket_manager,
    ):
        """Test badge service handles WebSocket errors gracefully."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        # Mock badge exists and user doesn't have it
        mock_badge = type(
            "Badge",
            (),
            {
                "pk": badge_id,
                "is_active": True,
                "name": "Test Badge",
                "description": "Test Description",
                "image_url": "https://example.com/badge.png",
            },
        )()

        mock_badge_repo.get_by_pk.return_value = mock_badge
        mock_user_badge_repo.has_badge.return_value = False
        mock_user_badge_repo.award_badge.return_value = {
            "pk": uuid4(),
            "badge_id": badge_id,
            "user_id": user_id,
        }

        with patch(
            "therobotoverlord_api.services.badge_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_broadcaster.broadcast_badge_earned.side_effect = Exception(
                "WebSocket error"
            )
            mock_get_broadcaster.return_value = mock_broadcaster

            # Should not raise exception even if WebSocket fails
            result = await badge_service.manually_award_badge(
                user_id=user_id,
                badge_id=badge_id,
                awarded_by_user_id=awarded_by_user_id,
                websocket_manager=mock_websocket_manager,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_bulk_badge_awarding_with_websocket(
        self,
        badge_service,
        mock_badge_repo,
        mock_user_badge_repo,
        mock_websocket_manager,
    ):
        """Test bulk badge awarding with WebSocket broadcasts."""
        user_ids = [uuid4(), uuid4(), uuid4()]
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        # Mock badge exists
        mock_badge = type(
            "Badge",
            (),
            {
                "pk": badge_id,
                "is_active": True,
                "name": "Community Badge",
                "description": "Awarded to community members",
                "image_url": "https://example.com/community.png",
            },
        )()

        mock_badge_repo.get_by_pk.return_value = mock_badge
        mock_user_badge_repo.has_badge.return_value = False
        mock_user_badge_repo.award_badge.return_value = {"pk": uuid4()}

        with patch(
            "therobotoverlord_api.services.badge_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            # Award badge to multiple users
            for user_id in user_ids:
                await badge_service.manually_award_badge(
                    user_id=user_id,
                    badge_id=badge_id,
                    awarded_by_user_id=awarded_by_user_id,
                    websocket_manager=mock_websocket_manager,
                )

            # Verify all broadcasts were made
            assert mock_broadcaster.broadcast_badge_earned.call_count == 3

            # Verify each user got their notification
            for i, user_id in enumerate(user_ids):
                call_args = mock_broadcaster.broadcast_badge_earned.call_args_list[i]
                assert call_args[1]["user_id"] == user_id
                assert call_args[1]["badge_id"] == badge_id

    @pytest.mark.asyncio
    async def test_badge_earned_with_optional_icon(
        self,
        badge_service,
        mock_badge_repo,
        mock_user_badge_repo,
        mock_websocket_manager,
    ):
        """Test badge earned broadcast with optional icon field."""
        user_id = uuid4()
        badge_id = uuid4()
        awarded_by_user_id = uuid4()

        # Mock badge without image_url
        mock_badge = type(
            "Badge",
            (),
            {
                "pk": badge_id,
                "is_active": True,
                "name": "Text Badge",
                "description": "Badge without icon",
                "image_url": None,
            },
        )()

        mock_badge_repo.get_by_pk.return_value = mock_badge
        mock_user_badge_repo.has_badge.return_value = False
        mock_user_badge_repo.award_badge.return_value = {
            "pk": uuid4(),
            "badge_id": badge_id,
            "user_id": user_id,
        }

        with patch(
            "therobotoverlord_api.services.badge_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            result = await badge_service.manually_award_badge(
                user_id=user_id,
                badge_id=badge_id,
                awarded_by_user_id=awarded_by_user_id,
                websocket_manager=mock_websocket_manager,
            )

            assert result is not None

            # Verify broadcast with None icon
            mock_broadcaster.broadcast_badge_earned.assert_called_once_with(
                user_id=user_id,
                badge_id=badge_id,
                badge_name="Text Badge",
                badge_description="Badge without icon",
                badge_icon=None,
            )

    @pytest.mark.asyncio
    async def test_automatic_badge_awarding_with_websocket(
        self,
        badge_service,
        mock_badge_repo,
        mock_user_badge_repo,
        mock_websocket_manager,
    ):
        """Test automatic badge awarding through criteria evaluation."""
        user_id = uuid4()

        # Mock badge that meets criteria
        mock_badge = type(
            "Badge",
            (),
            {
                "pk": uuid4(),
                "is_active": True,
                "name": "Auto Badge",
                "description": "Automatically awarded badge",
                "image_url": "https://example.com/auto.png",
                "criteria_config": {"posts": 5},
            },
        )()

        mock_badge_repo.get_active_badges.return_value = [mock_badge]
        mock_user_badge_repo.has_badge.return_value = False
        mock_user_badge_repo.award_badge.return_value = {"pk": uuid4()}

        with patch(
            "therobotoverlord_api.services.badge_service.get_event_broadcaster"
        ) as mock_get_broadcaster:
            mock_broadcaster = AsyncMock()
            mock_get_broadcaster.return_value = mock_broadcaster

            with patch.object(badge_service, "_check_badge_eligibility") as mock_check:
                from therobotoverlord_api.database.models.badge import (
                    BadgeEligibilityCheck,
                )

                mock_check.return_value = BadgeEligibilityCheck(
                    badge_pk=mock_badge.pk,
                    badge_name=mock_badge.name,
                    is_eligible=True,
                    current_progress=1,
                    required_progress=1,
                    criteria_met=True,
                    reason="Criteria met",
                )  # Criteria met

                awarded_badges = await badge_service.evaluate_badge_criteria_for_user(
                    user_id=user_id, websocket_manager=mock_websocket_manager
                )

                assert len(awarded_badges) == 1

                # Verify automatic badge earned notification
                mock_broadcaster.broadcast_badge_earned.assert_called_once_with(
                    user_id=user_id,
                    badge_id=mock_badge.pk,
                    badge_name="Auto Badge",
                    badge_description="Automatically awarded badge",
                    badge_icon="https://example.com/auto.png",
                )
