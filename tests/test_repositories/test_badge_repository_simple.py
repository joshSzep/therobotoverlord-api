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

    @pytest.mark.asyncio
    async def test_has_badge_true(self, user_badge_repo, mock_user_badge_record):
        """Test checking if user has badge when they do."""
        with patch.object(
            user_badge_repo, "find_one_by", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = mock_user_badge_record

            user_pk = uuid4()
            badge_pk = uuid4()
            result = await user_badge_repo.has_badge(user_pk, badge_pk)

            mock_find.assert_called_once_with(user_pk=user_pk, badge_pk=badge_pk)
            assert result is True

    @pytest.mark.asyncio
    async def test_has_badge_false(self, user_badge_repo):
        """Test checking if user has badge when they don't."""
        with patch.object(
            user_badge_repo, "find_one_by", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = None

            user_pk = uuid4()
            badge_pk = uuid4()
            result = await user_badge_repo.has_badge(user_pk, badge_pk)

            mock_find.assert_called_once_with(user_pk=user_pk, badge_pk=badge_pk)
            assert result is False

    @pytest.mark.asyncio
    async def test_award_badge(self, user_badge_repo, mock_user_badge_record):
        """Test awarding a badge to a user."""
        with patch.object(
            user_badge_repo, "create_from_dict", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_user_badge_record

            badge_data = {
                "user_pk": uuid4(),
                "badge_pk": uuid4(),
                "awarded_by_event": "manual",
            }
            result = await user_badge_repo.award_badge(badge_data)

            mock_create.assert_called_once_with(badge_data)
            assert result == mock_user_badge_record

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_user_badge_counts(self, mock_get_db, user_badge_repo):
        """Test getting badge counts for a user."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        mock_records = [
            {"badge_type": "positive", "count": 5},
            {"badge_type": "negative", "count": 2},
        ]
        mock_conn.fetch.return_value = mock_records

        user_pk = uuid4()
        result = await user_badge_repo.get_user_badge_counts(user_pk)

        mock_conn.fetch.assert_called_once()
        assert result["positive"] == 5
        assert result["negative"] == 2
        assert result["total"] == 7

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_user_badge_counts_empty(self, mock_get_db, user_badge_repo):
        """Test getting badge counts for a user with no badges."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        user_pk = uuid4()
        result = await user_badge_repo.get_user_badge_counts(user_pk)

        assert result["positive"] == 0
        assert result["negative"] == 0
        assert result["total"] == 0

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_recent_user_badges(self, mock_get_db, user_badge_repo):
        """Test getting recent user badges."""
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
            "name": "Recent Badge",
            "description": "A recent badge",
            "image_url": "https://example.com/recent.png",
            "badge_type": "positive",
            "criteria_config": {"min_score": 50},
            "is_active": True,
            "badge_created_at": "2024-01-01T00:00:00Z",
            "badge_updated_at": "2024-01-01T00:00:00Z",
            "username": "testuser",
        }
        mock_conn.fetch.return_value = [mock_badge_details]

        user_pk = uuid4()
        result = await user_badge_repo.get_recent_user_badges(user_pk, limit=3)

        mock_conn.fetch.assert_called_once()
        assert len(result) == 1
        assert result[0].badge.name == "Recent Badge"
        assert result[0].username == "testuser"

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_recent_user_badges_empty(self, mock_get_db, user_badge_repo):
        """Test getting recent user badges when user has none."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        user_pk = uuid4()
        result = await user_badge_repo.get_recent_user_badges(user_pk)

        assert result == []

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_badge_recipients(self, mock_get_db, user_badge_repo):
        """Test getting badge recipients."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        mock_recipient_details = {
            "user_badge_pk": uuid4(),
            "user_pk": uuid4(),
            "badge_pk": uuid4(),
            "awarded_at": "2024-01-01T00:00:00Z",
            "awarded_for_post_pk": uuid4(),
            "awarded_for_topic_pk": None,
            "awarded_by_event": "post_upvote",
            "user_badge_created_at": "2024-01-01T00:00:00Z",
            "user_badge_updated_at": "2024-01-01T00:00:00Z",
            "name": "Popular Badge",
            "description": "A popular badge",
            "image_url": "https://example.com/popular.png",
            "badge_type": "positive",
            "criteria_config": {"min_upvotes": 10},
            "is_active": True,
            "badge_created_at": "2024-01-01T00:00:00Z",
            "badge_updated_at": "2024-01-01T00:00:00Z",
            "username": "recipient1",
        }
        mock_conn.fetch.return_value = [mock_recipient_details]

        badge_pk = uuid4()
        result = await user_badge_repo.get_badge_recipients(badge_pk, limit=50)

        mock_conn.fetch.assert_called_once()
        assert len(result) == 1
        assert result[0].badge.name == "Popular Badge"
        assert result[0].username == "recipient1"
        assert (
            result[0].awarded_for_post_pk
            == mock_recipient_details["awarded_for_post_pk"]
        )

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_badge_recipients_empty(self, mock_get_db, user_badge_repo):
        """Test getting badge recipients when no one has the badge."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        badge_pk = uuid4()
        result = await user_badge_repo.get_badge_recipients(badge_pk)

        assert result == []

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_user_badges_empty(self, mock_get_db, user_badge_repo):
        """Test getting user badges when user has none."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        user_pk = uuid4()
        result = await user_badge_repo.get_user_badges(user_pk)

        assert result == []

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_user_badges_multiple(self, mock_get_db, user_badge_repo):
        """Test getting multiple user badges."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        mock_badge_1 = {
            "user_badge_pk": uuid4(),
            "user_pk": uuid4(),
            "badge_pk": uuid4(),
            "awarded_at": "2024-01-01T00:00:00Z",
            "awarded_for_post_pk": None,
            "awarded_for_topic_pk": uuid4(),
            "awarded_by_event": "topic_creation",
            "user_badge_created_at": "2024-01-01T00:00:00Z",
            "user_badge_updated_at": "2024-01-01T00:00:00Z",
            "name": "First Badge",
            "description": "First badge description",
            "image_url": "https://example.com/first.png",
            "badge_type": "positive",
            "criteria_config": {"min_topics": 1},
            "is_active": True,
            "badge_created_at": "2024-01-01T00:00:00Z",
            "badge_updated_at": "2024-01-01T00:00:00Z",
            "username": "testuser",
        }

        mock_badge_2 = {
            "user_badge_pk": uuid4(),
            "user_pk": uuid4(),
            "badge_pk": uuid4(),
            "awarded_at": "2024-01-02T00:00:00Z",
            "awarded_for_post_pk": uuid4(),
            "awarded_for_topic_pk": None,
            "awarded_by_event": "post_quality",
            "user_badge_created_at": "2024-01-02T00:00:00Z",
            "user_badge_updated_at": "2024-01-02T00:00:00Z",
            "name": "Second Badge",
            "description": "Second badge description",
            "image_url": "https://example.com/second.png",
            "badge_type": "negative",
            "criteria_config": {"max_violations": 0},
            "is_active": True,
            "badge_created_at": "2024-01-02T00:00:00Z",
            "badge_updated_at": "2024-01-02T00:00:00Z",
            "username": "testuser",
        }

        mock_conn.fetch.return_value = [mock_badge_1, mock_badge_2]

        user_pk = uuid4()
        result = await user_badge_repo.get_user_badges(user_pk)

        assert len(result) == 2
        assert result[0].badge.name == "First Badge"
        assert result[0].awarded_for_topic_pk == mock_badge_1["awarded_for_topic_pk"]
        assert result[1].badge.name == "Second Badge"
        assert result[1].awarded_for_post_pk == mock_badge_2["awarded_for_post_pk"]

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_recent_user_badges_with_default_limit(
        self, mock_get_db, user_badge_repo
    ):
        """Test getting recent user badges with default limit."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        user_pk = uuid4()
        result = await user_badge_repo.get_recent_user_badges(user_pk)

        # Verify default limit of 5 is used
        call_args = mock_conn.fetch.call_args[0]
        assert call_args[2] == 5  # limit parameter

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_badge_recipients_with_default_limit(
        self, mock_get_db, user_badge_repo
    ):
        """Test getting badge recipients with default limit."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        badge_pk = uuid4()
        result = await user_badge_repo.get_badge_recipients(badge_pk)

        # Verify default limit of 100 is used
        call_args = mock_conn.fetch.call_args[0]
        assert call_args[2] == 100  # limit parameter

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_user_badge_counts_single_type(
        self, mock_get_db, user_badge_repo
    ):
        """Test getting badge counts when user only has one type."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        mock_records = [
            {"badge_type": "positive", "count": 3},
        ]
        mock_conn.fetch.return_value = mock_records

        user_pk = uuid4()
        result = await user_badge_repo.get_user_badge_counts(user_pk)

        assert result["positive"] == 3
        assert result["negative"] == 0  # Should remain 0
        assert result["total"] == 3

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.badge.get_db_connection")
    async def test_get_badge_recipients_multiple(self, mock_get_db, user_badge_repo):
        """Test getting multiple badge recipients."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        recipient_1 = {
            "user_badge_pk": uuid4(),
            "user_pk": uuid4(),
            "badge_pk": uuid4(),
            "awarded_at": "2024-01-01T00:00:00Z",
            "awarded_for_post_pk": None,
            "awarded_for_topic_pk": None,
            "awarded_by_event": "manual",
            "user_badge_created_at": "2024-01-01T00:00:00Z",
            "user_badge_updated_at": "2024-01-01T00:00:00Z",
            "name": "Shared Badge",
            "description": "A shared badge",
            "image_url": "https://example.com/shared.png",
            "badge_type": "positive",
            "criteria_config": {"min_score": 100},
            "is_active": True,
            "badge_created_at": "2024-01-01T00:00:00Z",
            "badge_updated_at": "2024-01-01T00:00:00Z",
            "username": "user1",
        }

        recipient_2 = {
            "user_badge_pk": uuid4(),
            "user_pk": uuid4(),
            "badge_pk": uuid4(),
            "awarded_at": "2024-01-02T00:00:00Z",
            "awarded_for_post_pk": uuid4(),
            "awarded_for_topic_pk": None,
            "awarded_by_event": "post_quality",
            "user_badge_created_at": "2024-01-02T00:00:00Z",
            "user_badge_updated_at": "2024-01-02T00:00:00Z",
            "name": "Shared Badge",
            "description": "A shared badge",
            "image_url": "https://example.com/shared.png",
            "badge_type": "positive",
            "criteria_config": {"min_score": 100},
            "is_active": True,
            "badge_created_at": "2024-01-01T00:00:00Z",
            "badge_updated_at": "2024-01-01T00:00:00Z",
            "username": "user2",
        }

        mock_conn.fetch.return_value = [recipient_1, recipient_2]

        badge_pk = uuid4()
        result = await user_badge_repo.get_badge_recipients(badge_pk)

        assert len(result) == 2
        assert result[0].username == "user1"
        assert result[1].username == "user2"
        assert result[0].badge.name == "Shared Badge"
        assert result[1].badge.name == "Shared Badge"
