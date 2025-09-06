"""Tests for user repository."""

from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.user import UserLeaderboard
from therobotoverlord_api.database.models.user import UserProfile
from therobotoverlord_api.database.models.user import UserUpdate
from therobotoverlord_api.database.repositories.user import UserRepository


class TestUserRepository:
    """Test UserRepository class."""

    @pytest.fixture
    def repository(self):
        """Create a UserRepository instance for testing."""
        return UserRepository()

    @pytest.fixture
    def sample_user_pk(self):
        """Sample user primary key."""
        return uuid4()

    def test_init(self, repository):
        """Test repository initialization."""
        assert repository.table_name == "users"

    def test_record_to_model(self, repository, mock_record, sample_user):
        """Test converting database record to User model."""
        with patch(
            "therobotoverlord_api.database.models.user.User.model_validate",
            return_value=sample_user,
        ) as mock_validate:
            result = repository._record_to_model(mock_record)

            mock_validate.assert_called_once_with(dict(mock_record.items()))
            assert result == sample_user

    @pytest.mark.asyncio
    async def test_create_user(self, repository, sample_user_create, sample_user):
        """Test creating a new user."""
        with patch.object(
            repository, "create_from_dict", return_value=sample_user
        ) as mock_create:
            result = await repository.create_user(sample_user_create)

            expected_data = sample_user_create.model_dump()
            mock_create.assert_called_once_with(expected_data)
            assert result == sample_user

    @pytest.mark.asyncio
    async def test_update_user(self, repository, sample_user_pk, sample_user):
        """Test updating an existing user."""
        user_update = UserUpdate(username="newname", loyalty_score=100)

        with patch.object(
            repository, "update_from_dict", return_value=sample_user
        ) as mock_update:
            result = await repository.update_user(sample_user_pk, user_update)

            expected_data = {"username": "newname", "loyalty_score": 100}
            mock_update.assert_called_once_with(sample_user_pk, expected_data)
            assert result == sample_user

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, repository, sample_user_pk):
        """Test updating user when not found."""
        user_update = UserUpdate(username="newname")

        with patch.object(
            repository, "update_from_dict", return_value=None
        ) as mock_update:
            result = await repository.update_user(sample_user_pk, user_update)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_by_google_id(self, repository, sample_user):
        """Test getting user by Google ID."""
        with patch.object(
            repository, "find_one_by", return_value=sample_user
        ) as mock_find:
            result = await repository.get_by_google_id("google123")

            mock_find.assert_called_once_with(google_id="google123")
            assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_by_email(self, repository, sample_user):
        """Test getting user by email."""
        with patch.object(
            repository, "find_one_by", return_value=sample_user
        ) as mock_find:
            result = await repository.get_by_email("test@example.com")

            mock_find.assert_called_once_with(email="test@example.com")
            assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_by_username(self, repository, sample_user):
        """Test getting user by username."""
        with patch.object(
            repository, "find_one_by", return_value=sample_user
        ) as mock_find:
            result = await repository.get_by_username("testuser")

            mock_find.assert_called_once_with(username="testuser")
            assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_leaderboard(self, repository):
        """Test getting user leaderboard."""
        mock_records = [
            {
                "user_pk": uuid4(),
                "username": "user1",
                "loyalty_score": 500,
                "rank": 1,
                "can_create_topics": True,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": None,
            },
            {
                "user_pk": uuid4(),
                "username": "user2",
                "loyalty_score": 400,
                "rank": 2,
                "can_create_topics": True,
                "created_at": "2023-01-02T00:00:00Z",
                "updated_at": None,
            },
        ]

        with patch(
            "therobotoverlord_api.database.repositories.user.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.get_leaderboard(limit=50)

            assert len(result) == 2
            assert all(isinstance(item, UserLeaderboard) for item in result)
            assert result[0].rank == 1
            assert result[1].rank == 2

            expected_query = "\n            SELECT * FROM leaderboard\n            ORDER BY rank ASC\n            LIMIT $1\n        "
            mock_connection.fetch.assert_called_once_with(expected_query, 50)

    @pytest.mark.asyncio
    async def test_get_user_rank(self, repository, sample_user_pk):
        """Test getting user's current rank."""
        with patch(
            "therobotoverlord_api.database.repositories.user.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = 5
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.get_user_rank(sample_user_pk)

            assert result == 5
            expected_query = "\n            SELECT rank FROM leaderboard\n            WHERE user_pk = $1\n        "
            mock_connection.fetchval.assert_called_once_with(
                expected_query, sample_user_pk
            )

    @pytest.mark.asyncio
    async def test_get_user_rank_not_found(self, repository, sample_user_pk):
        """Test getting rank when user not found."""
        with patch(
            "therobotoverlord_api.database.repositories.user.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = None
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.get_user_rank(sample_user_pk)

            assert result is None

    @pytest.mark.asyncio
    async def test_can_create_topic_true_default_percent(
        self, repository, sample_user_pk
    ):
        """Test can_create_topic when user has sufficient loyalty score (default 10%)."""
        with (
            patch.object(
                repository, "get_top_percent_loyalty_threshold", return_value=50
            ) as mock_threshold,
            patch(
                "therobotoverlord_api.database.repositories.user.get_db_connection"
            ) as mock_get_conn,
        ):
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = True
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.can_create_topic(sample_user_pk)

            assert result is True
            mock_threshold.assert_called_once_with(0.1)
            expected_query = "\n            SELECT loyalty_score >= $1 as can_create\n            FROM users\n            WHERE pk = $2\n        "
            mock_connection.fetchval.assert_called_once_with(
                expected_query, 50, sample_user_pk
            )

    @pytest.mark.asyncio
    async def test_can_create_topic_custom_percent(self, repository, sample_user_pk):
        """Test can_create_topic with custom percentage."""
        with (
            patch.object(
                repository, "get_top_percent_loyalty_threshold", return_value=100
            ) as mock_threshold,
            patch(
                "therobotoverlord_api.database.repositories.user.get_db_connection"
            ) as mock_get_conn,
        ):
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = True
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.can_create_topic(sample_user_pk, top_percent=0.05)

            assert result is True
            mock_threshold.assert_called_once_with(0.05)
            expected_query = "\n            SELECT loyalty_score >= $1 as can_create\n            FROM users\n            WHERE pk = $2\n        "
            mock_connection.fetchval.assert_called_once_with(
                expected_query, 100, sample_user_pk
            )

    @pytest.mark.asyncio
    async def test_can_create_topic_false(self, repository, sample_user_pk):
        """Test can_create_topic when user has insufficient loyalty score."""
        with (
            patch.object(
                repository, "get_top_percent_loyalty_threshold", return_value=50
            ),
            patch(
                "therobotoverlord_api.database.repositories.user.get_db_connection"
            ) as mock_get_conn,
        ):
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = False
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.can_create_topic(sample_user_pk)

            assert result is False

    @pytest.mark.asyncio
    async def test_can_create_topic_user_not_found(self, repository, sample_user_pk):
        """Test can_create_topic when user not found."""
        with (
            patch.object(
                repository, "get_top_percent_loyalty_threshold", return_value=50
            ),
            patch(
                "therobotoverlord_api.database.repositories.user.get_db_connection"
            ) as mock_get_conn,
        ):
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = None
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.can_create_topic(sample_user_pk)

            assert result is False

    @pytest.mark.asyncio
    async def test_get_top_percent_loyalty_threshold_default(self, repository):
        """Test get_top_percent_loyalty_threshold with default 10%."""
        with patch(
            "therobotoverlord_api.database.repositories.user.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = 75
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.get_top_percent_loyalty_threshold()

            assert result == 75
            expected_query = "\n            SELECT COALESCE(MIN(loyalty_score), 0) as threshold\n            FROM (\n                SELECT loyalty_score\n                FROM users\n                WHERE loyalty_score > 0\n                ORDER BY loyalty_score DESC, created_at ASC\n                LIMIT (SELECT GREATEST(1, CAST(COUNT(*) * $1 AS INTEGER)) FROM users WHERE loyalty_score > 0)\n            ) top_users\n        "
            mock_connection.fetchval.assert_called_once_with(expected_query, 0.1)

    @pytest.mark.asyncio
    async def test_get_top_percent_loyalty_threshold_custom(self, repository):
        """Test get_top_percent_loyalty_threshold with custom percentage."""
        with patch(
            "therobotoverlord_api.database.repositories.user.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = 150
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.get_top_percent_loyalty_threshold(0.05)

            assert result == 150
            expected_query = "\n            SELECT COALESCE(MIN(loyalty_score), 0) as threshold\n            FROM (\n                SELECT loyalty_score\n                FROM users\n                WHERE loyalty_score > 0\n                ORDER BY loyalty_score DESC, created_at ASC\n                LIMIT (SELECT GREATEST(1, CAST(COUNT(*) * $1 AS INTEGER)) FROM users WHERE loyalty_score > 0)\n            ) top_users\n        "
            mock_connection.fetchval.assert_called_once_with(expected_query, 0.05)

    @pytest.mark.asyncio
    async def test_get_top_percent_loyalty_threshold_no_users(self, repository):
        """Test get_top_percent_loyalty_threshold when no users exist."""
        with patch(
            "therobotoverlord_api.database.repositories.user.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = None
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.get_top_percent_loyalty_threshold()

            assert result == 0

    @pytest.mark.asyncio
    async def test_get_top_percent_loyalty_threshold_edge_cases(self, repository):
        """Test get_top_percent_loyalty_threshold with edge case percentages."""
        with patch(
            "therobotoverlord_api.database.repositories.user.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetchval.return_value = 200
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            # Test top 1%
            result = await repository.get_top_percent_loyalty_threshold(0.01)
            assert result == 200

            # Test top 50%
            mock_connection.fetchval.return_value = 25
            result = await repository.get_top_percent_loyalty_threshold(0.5)
            assert result == 25

            # Test top 100% (should include everyone)
            mock_connection.fetchval.return_value = 1
            result = await repository.get_top_percent_loyalty_threshold(1.0)
            assert result == 1

    @pytest.mark.asyncio
    async def test_can_create_topic_various_percentages(
        self, repository, sample_user_pk
    ):
        """Test can_create_topic with various percentage thresholds."""
        test_cases = [
            (0.01, 500),  # Top 1%, very high threshold
            (0.05, 200),  # Top 5%, high threshold
            (0.2, 50),  # Top 20%, moderate threshold
            (0.5, 10),  # Top 50%, low threshold
        ]

        for percent, threshold in test_cases:
            with (
                patch.object(
                    repository,
                    "get_top_percent_loyalty_threshold",
                    return_value=threshold,
                ) as mock_threshold,
                patch(
                    "therobotoverlord_api.database.repositories.user.get_db_connection"
                ) as mock_get_conn,
            ):
                mock_connection = AsyncMock()
                mock_connection.fetchval.return_value = True
                mock_get_conn.return_value.__aenter__.return_value = mock_connection

                result = await repository.can_create_topic(sample_user_pk, percent)

                assert result is True
                mock_threshold.assert_called_once_with(percent)
                expected_query = "\n            SELECT loyalty_score >= $1 as can_create\n            FROM users\n            WHERE pk = $2\n        "
                mock_connection.fetchval.assert_called_once_with(
                    expected_query, threshold, sample_user_pk
                )

    @pytest.mark.asyncio
    async def test_get_top_users(self, repository):
        """Test getting top users by loyalty score."""
        mock_records = [
            {
                "pk": uuid4(),
                "username": "topuser1",
                "loyalty_score": 1000,
                "role": "admin",
                "created_at": "2023-01-01T00:00:00Z",
            },
            {
                "pk": uuid4(),
                "username": "topuser2",
                "loyalty_score": 900,
                "role": "citizen",
                "created_at": "2023-01-02T00:00:00Z",
            },
        ]

        with patch(
            "therobotoverlord_api.database.repositories.user.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_connection.fetch.return_value = mock_records
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            result = await repository.get_top_users(limit=5)

            assert len(result) == 2
            assert all(isinstance(item, UserProfile) for item in result)
            assert result[0].loyalty_score == 1000
            assert result[1].loyalty_score == 900

            expected_query = "\n            SELECT pk, username, loyalty_score, role, created_at\n            FROM users\n            ORDER BY loyalty_score DESC\n            LIMIT $1\n        "
            mock_connection.fetch.assert_called_once_with(expected_query, 5)

    @pytest.mark.asyncio
    async def test_update_loyalty_score(self, repository, sample_user_pk, sample_user):
        """Test updating user's loyalty score."""
        with patch.object(
            repository, "update_from_dict", return_value=sample_user
        ) as mock_update:
            result = await repository.update_loyalty_score(sample_user_pk, 150)

            mock_update.assert_called_once_with(sample_user_pk, {"loyalty_score": 150})
            assert result == sample_user

    @pytest.mark.asyncio
    async def test_refresh_leaderboard(self, repository):
        """Test refreshing the materialized leaderboard view."""
        with patch(
            "therobotoverlord_api.database.repositories.user.get_db_connection"
        ) as mock_get_conn:
            mock_connection = AsyncMock()
            mock_get_conn.return_value.__aenter__.return_value = mock_connection

            await repository.refresh_leaderboard()

            expected_query = "REFRESH MATERIALIZED VIEW CONCURRENTLY leaderboard"
            mock_connection.execute.assert_called_once_with(expected_query)

    @pytest.mark.asyncio
    async def test_get_users_by_role(self, repository, sample_user):
        """Test getting users by role."""
        with patch.object(
            repository, "find_by", return_value=[sample_user]
        ) as mock_find:
            result = await repository.get_users_by_role("admin")

            mock_find.assert_called_once_with(role="admin")
            assert result == [sample_user]

    @pytest.mark.asyncio
    async def test_get_sanctioned_users(self, repository, sample_user):
        """Test getting sanctioned users."""
        with patch.object(
            repository, "find_by", return_value=[sample_user]
        ) as mock_find:
            result = await repository.get_sanctioned_users()

            mock_find.assert_called_once_with(is_sanctioned=True)
            assert result == [sample_user]

    @pytest.mark.asyncio
    async def test_get_banned_users(self, repository, sample_user):
        """Test getting banned users."""
        with patch.object(
            repository, "find_by", return_value=[sample_user]
        ) as mock_find:
            result = await repository.get_banned_users()

            mock_find.assert_called_once_with(is_banned=True)
            assert result == [sample_user]
