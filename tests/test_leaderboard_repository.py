"""Unit tests for leaderboard repository with mocked database."""

from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.leaderboard import LeaderboardCursor
from therobotoverlord_api.database.repositories.leaderboard import LeaderboardRepository

# Import fixtures
pytest_plugins = ["tests.fixtures.leaderboard_fixtures"]


class TestLeaderboardRepository:
    """Test LeaderboardRepository with mocked database connections."""

    @pytest.fixture
    def repository(self):
        """Create repository instance for testing."""
        return LeaderboardRepository()

    @pytest.mark.asyncio
    async def test_get_leaderboard_page_basic(
        self,
        repository,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        sample_db_badge_rows,
    ):
        """Test basic leaderboard page retrieval."""
        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            # Mock the database responses
            mock_conn = mock_get_db_connection().mock_connection
            # Need enough badge responses for all users in the result set
            badge_responses = [sample_db_badge_rows] + [
                [] for _ in range(10)
            ]  # First user has badges, rest have none
            mock_conn.fetch.side_effect = [
                sample_db_leaderboard_rows[
                    :5
                ],  # Main leaderboard query - limit to 5 users
                *badge_responses,  # Badge queries for each user
            ]

            # Test the method
            entries, has_next = await repository.get_leaderboard_page(limit=5)

            # Verify results
            assert len(entries) == 5
            assert has_next is False
            assert entries[0].username == "db_citizen_0"
            assert entries[0].rank == 1
            assert entries[0].loyalty_score == 200

            # Verify database was called
            mock_conn.fetch.assert_called()

    @pytest.mark.asyncio
    async def test_get_leaderboard_page_with_cursor(
        self,
        repository,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
    ):
        """Test leaderboard page retrieval with cursor pagination."""
        cursor = LeaderboardCursor(rank=10, user_pk=uuid4(), loyalty_score=100)

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.side_effect = [
                sample_db_leaderboard_rows[
                    :3
                ],  # Return 3 rows (limit=2, so has_next=True)
                [],  # Badges for users
                [],
                [],
            ]

            entries, has_next = await repository.get_leaderboard_page(
                limit=2, cursor=cursor
            )

            assert len(entries) == 2  # Should return limit, not the extra row
            assert has_next is True  # Should detect there's a next page

    @pytest.mark.asyncio
    async def test_get_leaderboard_page_with_filters(
        self,
        repository,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        sample_filters,
    ):
        """Test leaderboard page retrieval with filters."""
        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            # Limit to 5 users to match the limit parameter
            limited_rows = sample_db_leaderboard_rows[:5]
            # Provide badge responses for each user
            badge_responses = [[] for _ in range(len(limited_rows))]
            mock_conn.fetch.side_effect = [
                limited_rows,  # Main leaderboard query
                *badge_responses,  # Badge queries for each user
            ]

            entries, has_next = await repository.get_leaderboard_page(
                limit=5, filters=sample_filters
            )

            # Verify the query was built with filter conditions
            call_args = mock_conn.fetch.call_args_list[0]
            query = call_args[0][0]  # First positional argument is the query

            # Should contain filter conditions
            assert "b.name = $" in query  # Badge filter
            assert "lr.loyalty_score >= $" in query  # Min loyalty score
            assert "lr.loyalty_score <= $" in query  # Max loyalty score
            assert "lr.username ILIKE $" in query  # Username search

    @pytest.mark.asyncio
    async def test_get_user_rank_found(
        self,
        repository,
        mock_get_db_connection,
        mock_database_rows,
    ):
        """Test getting user rank when user exists."""
        user_pk = uuid4()
        mock_row = mock_database_rows(
            user_pk=user_pk,
            username="test_user",
            rank=42,
            loyalty_score=150,
            percentile_rank=0.42,
        )

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetchrow.return_value = mock_row

            result = await repository.get_user_rank(user_pk)

            assert result is not None
            assert result.found is True
            assert result.user_pk == user_pk
            assert result.username == "test_user"
            assert result.rank == 42
            assert result.loyalty_score == 150
            assert result.percentile_rank == 0.42

    @pytest.mark.asyncio
    async def test_get_user_rank_not_found(
        self,
        repository,
        mock_get_db_connection,
    ):
        """Test getting user rank when user doesn't exist."""
        user_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetchrow.return_value = None

            result = await repository.get_user_rank(user_pk)

            assert result is not None
            assert result.found is False
            assert result.user_pk == user_pk
            assert result.username == ""
            assert result.rank == 0
            assert result.loyalty_score == 0
            assert result.percentile_rank == 1.0

    @pytest.mark.asyncio
    async def test_get_nearby_users(
        self,
        repository,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        mock_database_rows,
    ):
        """Test getting users near a specific rank."""
        user_pk = uuid4()

        # Mock user rank lookup
        user_rank_row = mock_database_rows(
            user_pk=user_pk,
            username="target_user",
            rank=50,
            loyalty_score=100,
            percentile_rank=0.5,
        )

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetchrow.return_value = user_rank_row  # For get_user_rank call
            # Limit to 5 users to match the context_size parameter
            limited_rows = sample_db_leaderboard_rows[:5]
            # Provide badge responses for each user
            badge_responses = [[] for _ in range(len(limited_rows))]
            mock_conn.fetch.side_effect = [
                limited_rows,  # Nearby users query
                *badge_responses,  # Badge queries for each user
            ]

            result = await repository.get_nearby_users(user_pk, context_size=5)

            assert len(result) == 5
            # Verify the query used rank range
            call_args = mock_conn.fetch.call_args_list[0]
            query = call_args[0][0]
            assert "rank BETWEEN $2 AND $3" in query

    @pytest.mark.asyncio
    async def test_get_nearby_users_user_not_found(
        self,
        repository,
        mock_get_db_connection,
    ):
        """Test getting nearby users when target user doesn't exist."""
        user_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetchrow.return_value = None  # User not found

            result = await repository.get_nearby_users(user_pk, context_size=5)

            assert result == []

    @pytest.mark.asyncio
    async def test_search_users(
        self,
        repository,
        mock_get_db_connection,
        mock_database_rows,
    ):
        """Test searching users by username."""
        search_rows = [
            mock_database_rows(
                user_pk=uuid4(),
                username="citizen_search",
                rank=25,
                loyalty_score=75,
                match_score=0.9,
            ),
            mock_database_rows(
                user_pk=uuid4(),
                username="search_citizen",
                rank=30,
                loyalty_score=70,
                match_score=0.8,
            ),
        ]

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.return_value = search_rows

            results = await repository.search_users("citizen", limit=20)

            assert len(results) == 2
            assert results[0].username == "citizen_search"
            assert results[0].match_score == 0.9
            assert results[1].username == "search_citizen"
            assert results[1].match_score == 0.8

            # Verify similarity search was used
            call_args = mock_conn.fetch.call_args_list[0]
            query = call_args[0][0]
            assert "similarity(username, $1)" in query

    @pytest.mark.asyncio
    async def test_get_leaderboard_stats(
        self,
        repository,
        mock_get_db_connection,
        sample_db_stats_row,
        sample_db_distribution_rows,
    ):
        """Test getting leaderboard statistics."""
        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetchrow.return_value = sample_db_stats_row
            mock_conn.fetch.return_value = sample_db_distribution_rows

            stats = await repository.get_leaderboard_stats()

            assert stats.total_users == 1000
            assert stats.active_users == 1000  # Same as total for materialized view
            assert stats.average_loyalty_score == 75.5
            assert stats.median_loyalty_score == 65
            assert stats.top_10_percent_threshold == 150

            # Check score distribution
            assert stats.score_distribution["negative"] == 50
            assert stats.score_distribution["1-10"] == 200

    @pytest.mark.asyncio
    async def test_get_user_rank_history(
        self,
        repository,
        mock_get_db_connection,
        mock_database_rows,
    ):
        """Test getting user rank history."""
        user_pk = uuid4()
        history_rows = [
            mock_database_rows(
                rank=45,
                loyalty_score=140,
                percentile_rank=0.45,
                snapshot_date=date.today(),
                previous_rank=48,
            ),
            mock_database_rows(
                rank=48,
                loyalty_score=130,
                percentile_rank=0.48,
                snapshot_date=date(2025, 8, 18),
                previous_rank=None,
            ),
        ]

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.return_value = history_rows

            history = await repository.get_user_rank_history(user_pk, days=30)

            assert len(history) == 2
            assert history[0].rank == 45
            assert history[0].rank_change == 3  # 48 - 45 = 3 (improvement)
            assert history[1].rank == 48
            assert history[1].rank_change is None  # No previous rank

    @pytest.mark.asyncio
    async def test_get_top_users(
        self,
        repository,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
    ):
        """Test getting top users."""
        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.side_effect = [
                sample_db_leaderboard_rows[:3],  # Top 3 users
                [],  # Badges for users
                [],
                [],
            ]

            top_users = await repository.get_top_users(limit=3)

            assert len(top_users) == 3
            assert top_users[0].rank == 1
            assert top_users[1].rank == 2
            assert top_users[2].rank == 3

            # Verify query ordered by rank
            call_args = mock_conn.fetch.call_args_list[0]
            query = call_args[0][0]
            assert "ORDER BY rank ASC" in query
            assert "LIMIT $1" in query

    @pytest.mark.asyncio
    async def test_refresh_leaderboard_success(
        self,
        repository,
        mock_get_db_connection,
    ):
        """Test successful leaderboard refresh."""
        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.execute.return_value = None

            result = await repository.refresh_leaderboard()

            assert result is True
            mock_conn.execute.assert_called_once_with(
                "SELECT refresh_leaderboard_rankings()"
            )

    @pytest.mark.asyncio
    async def test_refresh_leaderboard_failure(
        self,
        repository,
        mock_get_db_connection,
    ):
        """Test leaderboard refresh failure."""
        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.execute.side_effect = Exception("Database error")

            result = await repository.refresh_leaderboard()

            assert result is False

    @pytest.mark.asyncio
    async def test_create_daily_snapshot_success(
        self,
        repository,
        mock_get_db_connection,
    ):
        """Test successful daily snapshot creation."""
        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.execute.return_value = None

            result = await repository.create_daily_snapshot()

            assert result is True
            mock_conn.execute.assert_called_once_with(
                "SELECT create_daily_leaderboard_snapshot()"
            )

    @pytest.mark.asyncio
    async def test_create_daily_snapshot_failure(
        self,
        repository,
        mock_get_db_connection,
    ):
        """Test daily snapshot creation failure."""
        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.execute.side_effect = Exception("Database error")

            result = await repository.create_daily_snapshot()

            assert result is False

    @pytest.mark.asyncio
    async def test_get_user_badges(
        self,
        repository,
        mock_get_db_connection,
        sample_db_badge_rows,
    ):
        """Test getting user badges (private method)."""
        user_pk = uuid4()

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.return_value = sample_db_badge_rows

            # Access private method for testing
            badges = await repository._get_user_badges(mock_conn, user_pk)

            assert len(badges) == 2
            assert badges[0].name == "Logic Master"
            assert badges[1].name == "Evidence Defender"

    @pytest.mark.asyncio
    async def test_leaderboard_page_current_user_highlighting(
        self,
        repository,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        sample_db_badge_rows,
    ):
        """Test that current user is properly highlighted in results."""
        current_user_pk = sample_db_leaderboard_rows[2]["user_pk"]  # Third user

        # Limit to 5 users and ensure current user is in the result set
        limited_rows = sample_db_leaderboard_rows[:5]

        # Configure mock to simulate SQL CASE statement logic for is_current_user
        for row in limited_rows:
            # Update the internal _data dict to include is_current_user
            row._data["is_current_user"] = row["user_pk"] == current_user_pk
            # Also set as attribute for direct access
            row.is_current_user = row["user_pk"] == current_user_pk

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            # Mock the database responses
            mock_conn = mock_get_db_connection().mock_connection
            # Need enough badge responses for all users in the result set
            badge_responses = [sample_db_badge_rows] + [
                [] for _ in range(len(limited_rows))
            ]
            mock_conn.fetch.side_effect = [
                limited_rows,  # Main leaderboard query - limit to 5 users
                *badge_responses[: len(limited_rows)],  # Badge queries for each user
            ]

            entries, has_next = await repository.get_leaderboard_page(
                limit=5, current_user_pk=current_user_pk
            )

            # Verify current user is highlighted
            current_user_entry = next(
                (entry for entry in entries if entry.is_current_user), None
            )
            assert current_user_entry is not None
            assert current_user_entry.user_pk == current_user_pk
