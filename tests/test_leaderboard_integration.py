"""Integration tests for leaderboard pagination and filtering."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.leaderboard import LeaderboardCursor

# Import fixtures from leaderboard_fixtures
from therobotoverlord_api.database.models.leaderboard import LeaderboardFilters
from therobotoverlord_api.database.repositories.leaderboard import LeaderboardRepository
from therobotoverlord_api.services.leaderboard_service import LeaderboardService


class TestLeaderboardIntegration:
    """Integration tests for leaderboard system components."""

    @pytest.fixture
    def repository(self):
        """Create repository instance."""
        return LeaderboardRepository()

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        mock_client = AsyncMock()
        mock_client.get.return_value = None
        mock_client.setex.return_value = None
        mock_client.delete.return_value = None
        mock_client.keys.return_value = []
        return mock_client

    @pytest.fixture
    def service(self, repository, mock_redis_client):
        """Create service instance with real repository and mocked Redis."""
        service = LeaderboardService()
        service.repository = repository
        return service

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.services.leaderboard_service.get_redis_client")
    async def test_pagination_consistency_across_pages(
        self,
        mock_get_redis_client,
        service,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        mock_redis_client,
    ):
        """Test that pagination maintains consistency across multiple pages."""
        # Setup Redis mock
        mock_get_redis_client.return_value = mock_redis_client
        # Setup cache miss to force repository calls
        mock_redis_client.get.return_value = None

        # Create larger dataset for pagination testing
        all_rows = []
        for i in range(25):  # 25 users total
            row_data = {
                "user_pk": uuid4(),
                "username": f"citizen_{i:02d}",
                "loyalty_score": 1000 - i * 10,  # Descending scores
                "rank": i + 1,
                "percentile_rank": i / 24.0,  # 0 to 1
                "topics_created_count": max(0, 5 - i // 5),
                "topic_creation_enabled": i < 5,
                "user_created_at": datetime.now(UTC),
                "is_current_user": False,
            }
            all_rows.append(row_data)

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection

            # First page (rows 0-9, plus one extra for has_next detection)
            mock_conn.fetch.side_effect = [
                [sample_db_leaderboard_rows[i] for i in range(11)],  # 11 rows (10 + 1)
                *[[] for _ in range(10)],  # Badge queries for each user
                [],  # Distribution query for stats
                [],  # Top users query for stats
                [],  # Total users query for stats
            ]

            page1 = await service.get_leaderboard(limit=10)

            assert len(page1.entries) == 10
            assert page1.pagination.has_next is True
            assert page1.pagination.next_cursor is not None

            # Verify first page data
            assert page1.entries[0].rank == 1
            assert page1.entries[9].rank == 10

            # Reset mock for second page
            mock_conn.reset_mock()

            # Second page using cursor from first page
            cursor = page1.pagination.next_cursor
            mock_conn.fetch.side_effect = [
                [sample_db_leaderboard_rows[i] for i in range(10, 21)],  # Rows 10-20
                *[[] for _ in range(10)],  # Badge queries
                [],  # Distribution query for stats
                [],  # Top users query for stats
                [],  # Total users query for stats
            ]

            page2 = await service.get_leaderboard(limit=10, cursor=cursor)

            assert len(page2.entries) == 10
            assert page2.pagination.has_next is True

            # Verify no overlap between pages
            page1_user_pks = {entry.user_pk for entry in page1.entries}
            page2_user_pks = {entry.user_pk for entry in page2.entries}
            assert len(page1_user_pks.intersection(page2_user_pks)) == 0

            # Verify rank continuity
            assert page2.entries[0].rank == 11
            assert page2.entries[9].rank == 20

    @pytest.mark.asyncio
    async def test_filtering_with_pagination(
        self,
        service,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        mock_redis_client,
    ):
        """Test that filtering works correctly with pagination."""

        # Create filters
        filters = LeaderboardFilters(
            min_loyalty_score=50,
            max_loyalty_score=150,
            topic_creators_only=True,
        )

        # Mock filtered results (only users with scores 50-150 who can create topics)
        filtered_rows = [
            row
            for row in sample_db_leaderboard_rows[:8]  # First 8 users
            if 50 <= row["loyalty_score"] <= 150 and row["topic_creation_enabled"]
        ]

        with (
            patch(
                "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
                mock_get_db_connection,
            ),
            patch(
                "therobotoverlord_api.services.leaderboard_service.get_redis_client",
                return_value=mock_redis_client,
            ),
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.side_effect = [
                filtered_rows[:6],  # 5 results + 1 for has_next detection
                *[[] for _ in range(5)],  # Badge queries for each user
                [],  # Stats query - total users
                [],  # Stats query - active users
                [],  # Stats query - score distribution
            ]

            result = await service.get_leaderboard(limit=5, filters=filters)

            assert len(result.entries) == 5

            # Verify all results match filter criteria
            for entry in result.entries:
                assert 50 <= entry.loyalty_score <= 150
                assert entry.topic_creation_enabled is True

            # Verify the query included filter conditions
            call_args = mock_conn.fetch.call_args_list[0]
            query = call_args[0][0]
            assert "loyalty_score >= $" in query
            assert "loyalty_score <= $" in query

    @pytest.mark.asyncio
    async def test_search_with_pagination(
        self,
        service,
        mock_get_db_connection,
        mock_redis_client,
    ):
        """Test that search functionality works with pagination."""
        # Setup cache miss
        mock_redis_client.get.return_value = None

        # Mock search results with similarity scores
        search_results = []
        for i in range(15):
            result = {
                "user_pk": uuid4(),
                "username": f"search_citizen_{i}",
                "rank": i + 10,  # Starting from rank 10
                "loyalty_score": 100 - i,
                "match_score": 0.9 - i * 0.05,  # Decreasing similarity
            }
            search_results.append(result)

        with (
            patch(
                "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
                mock_get_db_connection,
            ),
            patch(
                "therobotoverlord_api.services.leaderboard_service.get_redis_client",
                return_value=mock_redis_client,
            ),
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.return_value = search_results[:10]  # First 10 results

            results = await service.search_users("citizen", limit=10)

            assert len(results) == 10

            # Verify results are ordered by match score (descending)
            for i in range(len(results) - 1):
                assert results[i].match_score >= results[i + 1].match_score

            # Verify search query was used
            call_args = mock_conn.fetch.call_args_list[0]
            query = call_args[0][0]
            assert "similarity(username, $1)" in query
            assert "ORDER BY match_score DESC" in query

    @pytest.mark.asyncio
    async def test_nearby_users_context_window(
        self,
        service,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        mock_redis_client,
    ):
        """Test that nearby users provides correct context window."""
        target_user_pk = uuid4()
        target_rank = 50
        context_size = 10

        # Mock user rank lookup
        user_rank_data = {
            "user_pk": target_user_pk,
            "username": "target_user",
            "rank": target_rank,
            "loyalty_score": 100,
            "percentile_rank": 0.5,
        }

        # Mock nearby users (ranks 45-54, centered on rank 50)
        nearby_rows = []
        for i in range(target_rank - 5, target_rank + 5):  # Ranks 45-54
            row = {
                "user_pk": target_user_pk if i == target_rank else uuid4(),
                "username": f"user_rank_{i}",
                "rank": i,
                "loyalty_score": 200 - i,
                "percentile_rank": (i - 1) / 100.0,
                "topics_created_count": 0,
                "topic_creation_enabled": False,
                "user_created_at": datetime.now(UTC),
                "is_current_user": i == target_rank,
            }
            nearby_rows.append(row)

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetchrow.return_value = user_rank_data  # User rank lookup
            mock_conn.fetch.side_effect = [
                nearby_rows,  # Nearby users query
                *[[] for _ in range(10)],  # Badge queries
            ]

            results = await service.get_nearby_users(
                target_user_pk, context_size=context_size
            )

            assert len(results) == context_size

            # Verify the target user is in the results and highlighted
            target_entry = next(
                (entry for entry in results if entry.user_pk == target_user_pk), None
            )
            assert target_entry is not None
            assert target_entry.is_current_user is True
            assert target_entry.rank == target_rank

            # Verify results are ordered by rank
            ranks = [entry.rank for entry in results]
            assert ranks == sorted(ranks)

            # Verify context window is centered around target user
            target_index = next(
                i for i, entry in enumerate(results) if entry.user_pk == target_user_pk
            )
            # Should be roughly in the middle (allowing for edge cases)
            assert 2 <= target_index <= 7

    @pytest.mark.asyncio
    async def test_rank_range_queries(
        self,
        service,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        mock_redis_client,
    ):
        """Test rank range queries return correct users."""
        # Setup cache miss
        mock_redis_client.get.return_value = None

        start_rank = 10
        end_rank = 15

        # Mock users in rank range
        range_rows = []
        for rank in range(start_rank, end_rank + 1):
            row = {
                "user_pk": uuid4(),
                "username": f"rank_{rank}_user",
                "rank": rank,
                "loyalty_score": 200 - rank,
                "percentile_rank": (rank - 1) / 100.0,
                "topics_created_count": 0,
                "topic_creation_enabled": False,
                "user_created_at": datetime.now(UTC),
                "is_current_user": False,
            }
            range_rows.append(row)

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.side_effect = [
                range_rows,  # Users in rank range
                *[[] for _ in range(6)],  # Badge queries
            ]

            results = await service.get_users_by_rank_range(
                start_rank=start_rank, end_rank=end_rank
            )

            assert len(results) == 6  # Ranks 10-15 inclusive

            # Verify all users are in the specified rank range
            for entry in results:
                assert start_rank <= entry.rank <= end_rank

            # Verify results are ordered by rank
            ranks = [entry.rank for entry in results]
            assert ranks == sorted(ranks)
            assert ranks == list(range(start_rank, end_rank + 1))

    @pytest.mark.asyncio
    async def test_percentile_range_queries(
        self,
        service,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        mock_redis_client,
    ):
        """Test percentile range queries return correct users."""
        # Setup cache miss
        mock_redis_client.get.return_value = None

        start_percentile = 0.0
        end_percentile = 0.1  # Top 10%

        # Mock top 10% users
        top_users = []
        for i in range(10):  # Top 10 users (assuming 100 total)
            row = {
                "user_pk": uuid4(),
                "username": f"top_{i}_user",
                "rank": i + 1,
                "loyalty_score": 1000 - i * 10,
                "percentile_rank": i / 99.0,  # 0 to ~0.09
                "topics_created_count": 5,
                "topic_creation_enabled": True,
                "user_created_at": datetime.now(UTC),
                "is_current_user": False,
            }
            top_users.append(row)

        with patch(
            "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
            mock_get_db_connection,
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.side_effect = [
                top_users,  # Top percentile users
                *[[] for _ in range(10)],  # Badge queries
            ]

            results = await service.get_users_by_percentile_range(
                start_percentile, end_percentile
            )

            assert len(results) == 10

            # Verify all users are in the specified percentile range
            for entry in results:
                assert start_percentile <= entry.percentile_rank <= end_percentile

            # Verify results are ordered by rank (ascending)
            ranks = [entry.rank for entry in results]
            assert ranks == sorted(ranks)
            assert ranks == list(range(1, 11))  # Ranks 1-10

    @pytest.mark.asyncio
    async def test_cache_invalidation_flow(
        self,
        service,
        mock_redis_client,
    ):
        """Test that cache invalidation works correctly across operations."""
        user_pk = uuid4()

        # Setup cache keys that should be invalidated
        cache_keys = [
            f"leaderboard:user:stats:{user_pk}".encode(),
            b"leaderboard:page:1",
            b"leaderboard:stats",
            b"leaderboard:top:10",
        ]
        mock_redis_client.keys.return_value = cache_keys

        # Patch get_redis_client to return our mock
        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            # Test cache invalidation
            await service.invalidate_user_cache(user_pk)

            # Verify cache keys were searched with correct patterns
            mock_redis_client.keys.assert_called()
        call_args = mock_redis_client.keys.call_args_list

        # Should search for general leaderboard keys (user-specific deletion is direct)
        patterns_used = [call[0][0] for call in call_args]
        expected_patterns = ["leaderboard:*", "top_users:*", "leaderboard_stats"]

        # Check that expected patterns were used
        for expected_pattern in expected_patterns:
            assert any(expected_pattern == pattern for pattern in patterns_used), (
                f"Expected pattern '{expected_pattern}' not found in {patterns_used}"
            )

        # Verify cache deletion was called
        mock_redis_client.delete.assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_pagination_stability(
        self,
        service,
        mock_get_db_connection,
        sample_db_leaderboard_rows,
        mock_redis_client,
    ):
        """Test that cursor-based pagination remains stable during concurrent updates."""
        # Setup cache miss
        mock_redis_client.get.return_value = None

        # Simulate a scenario where rankings change between page requests
        # First page request
        initial_rows = sample_db_leaderboard_rows[:11]  # 10 + 1 for has_next

        with (
            patch(
                "therobotoverlord_api.database.repositories.leaderboard.get_db_connection",
                mock_get_db_connection,
            ),
            patch(
                "therobotoverlord_api.services.leaderboard_service.get_redis_client",
                return_value=mock_redis_client,
            ),
        ):
            mock_conn = mock_get_db_connection().mock_connection
            mock_conn.fetch.side_effect = [
                initial_rows,
                *[[] for _ in range(10)],  # Badge queries
                [],  # Distribution query for stats
                [],  # Top users query for stats
                [],  # Total users query for stats
            ]

            page1 = await service.get_leaderboard(limit=10)
            cursor = page1.pagination.next_cursor

            # Reset mock for second page
            mock_conn.reset_mock()

            # Second page request - simulate that some users' scores changed
            # but cursor-based pagination should still work correctly
            modified_rows = []
            for i, row in enumerate(sample_db_leaderboard_rows[10:21]):
                # Simulate slight score changes but maintain cursor logic
                modified_row = row.copy()
                if i % 2 == 0:  # Every other user got a small score boost
                    modified_row["loyalty_score"] += 5
                modified_rows.append(modified_row)

            mock_conn.fetch.side_effect = [
                modified_rows,
                *[[] for _ in range(10)],  # Badge queries
                [],  # Distribution query for stats
                [],  # Top users query for stats
                [],  # Total users query for stats
            ]

            page2 = await service.get_leaderboard(limit=10, cursor=cursor)

            # Verify no duplicate users between pages despite score changes
            page1_user_pks = {entry.user_pk for entry in page1.entries}
            page2_user_pks = {entry.user_pk for entry in page2.entries}
            assert len(page1_user_pks.intersection(page2_user_pks)) == 0

            # Verify cursor was used correctly in the query
            call_args = mock_conn.fetch.call_args_list[0]
            query = call_args[0][0]
            params = call_args[0][1:]

            # Should include cursor conditions in WHERE clause
            assert "rank > $" in query
            # Decode cursor to check parameters

            decoded_cursor = LeaderboardCursor.decode(cursor)
            assert decoded_cursor.rank in params
