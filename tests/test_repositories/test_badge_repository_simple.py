"""Simple tests for BadgeRepository to improve coverage."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.repositories.badge import BadgeRepository
from therobotoverlord_api.database.repositories.badge import UserBadgeRepository


class TestBadgeRepositorySimple:
    """Simple test class for BadgeRepository."""

    @pytest.fixture
    def badge_repo(self):
        """Create a BadgeRepository instance."""
        return BadgeRepository()

    @pytest.fixture
    def mock_badge_record(self):
        """Create a mock badge record."""
        return {
            "pk": uuid4(),
            "name": "Test Badge",
            "description": "A test badge",
            "badge_type": "positive",
            "image_url": "https://example.com/badge.png",
            "criteria_config": {"min_score": 100},
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

    @pytest.mark.asyncio
    async def test_get_active_badges(self, badge_repo, mock_badge_record):
        """Test getting active badges."""
        with patch.object(badge_repo, "find_by", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = [mock_badge_record]

            result = await badge_repo.get_active_badges()

            mock_find.assert_called_once_with(is_active=True)
            assert result == [mock_badge_record]

    @pytest.mark.asyncio
    async def test_get_by_name(self, badge_repo, mock_badge_record):
        """Test getting badge by name."""
        with patch.object(
            badge_repo, "find_one_by", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = mock_badge_record

            result = await badge_repo.get_by_name("Test Badge")

            mock_find.assert_called_once_with(name="Test Badge")
            assert result == mock_badge_record

    @pytest.mark.asyncio
    async def test_get_badges_by_type(self, badge_repo, mock_badge_record):
        """Test getting badges by type."""
        with patch.object(badge_repo, "find_by", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = [mock_badge_record]

            result = await badge_repo.get_badges_by_type("positive")

            mock_find.assert_called_once_with(badge_type="positive", is_active=True)
            assert result == [mock_badge_record]

    def test_record_to_model(self, badge_repo, mock_badge_record):
        """Test converting record to model."""
        result = badge_repo._record_to_model(mock_badge_record)

        assert result.pk == mock_badge_record["pk"]
        assert result.name == mock_badge_record["name"]


class TestUserBadgeRepositorySimple:
    """Simple test class for UserBadgeRepository."""

    @pytest.fixture
    def user_badge_repo(self):
        """Create a UserBadgeRepository instance."""
        return UserBadgeRepository()

    @pytest.fixture
    def mock_user_badge_record(self):
        """Create a mock user badge record."""
        return {
            "pk": uuid4(),
            "user_pk": uuid4(),
            "badge_pk": uuid4(),
            "awarded_at": "2024-01-01T00:00:00Z",
            "awarded_for_post_pk": None,
            "awarded_for_topic_pk": None,
            "awarded_by_event": "manual",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_user_badges(self, mock_get_db, user_badge_repo):
        """Test getting user badges with details."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        mock_badge_details = {
            "user_badge_pk": uuid4(),
            "user_pk": uuid4(),
            "badge_pk": uuid4(),
            "awarded_at": "2024-01-01T00:00:00Z",
            "awarded_for_post_pk": None,
            "awarded_for_topic_pk": None,
            "awarded_by_event": "manual",
            "user_badge_created_at": "2024-01-01T00:00:00Z",
            "user_badge_updated_at": "2024-01-01T00:00:00Z",
            "name": "Test Badge",
            "description": "A test badge",
            "image_url": "https://example.com/badge.png",
            "badge_type": "positive",
            "criteria_config": {"min_score": 100},
            "is_active": True,
            "badge_created_at": "2024-01-01T00:00:00Z",
            "badge_updated_at": "2024-01-01T00:00:00Z",
            "username": "testuser",
        }
        mock_conn.fetch.return_value = [mock_badge_details]

        user_pk = uuid4()
        result = await user_badge_repo.get_user_badges(user_pk)

        mock_conn.fetch.assert_called_once()
        assert len(result) == 1

    def test_record_to_model(self, user_badge_repo, mock_user_badge_record):
        """Test converting record to model."""
        result = user_badge_repo._record_to_model(mock_user_badge_record)

        assert result.pk == mock_user_badge_record["pk"]
        assert result.user_pk == mock_user_badge_record["user_pk"]
        assert result.badge_pk == mock_user_badge_record["badge_pk"]
