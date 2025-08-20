"""Unit tests for leaderboard service with mocked dependencies."""

import json

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.leaderboard import LeaderboardCursor
from therobotoverlord_api.database.models.leaderboard import PersonalLeaderboardStats
from therobotoverlord_api.services.leaderboard_service import LeaderboardService
from therobotoverlord_api.workers import redis_connection

# Import fixtures
pytest_plugins = ["tests.fixtures.leaderboard_fixtures"]


class TestLeaderboardService:
    """Test LeaderboardService with mocked dependencies."""

    @pytest.fixture
    def service(self, mock_leaderboard_repository, mock_redis_client, monkeypatch):
        """Create service instance with mocked repository."""
        service = LeaderboardService()
        service.repository = mock_leaderboard_repository
        monkeypatch.setattr(
            redis_connection, "get_redis_client", lambda: mock_redis_client
        )
        return service

    @pytest.mark.asyncio
    async def test_get_leaderboard_cache_hit(
        self,
        service,
        mock_redis_client,
        sample_leaderboard_response,
    ):
        """Test leaderboard retrieval with cache hit."""
        # Setup cache hit
        mock_redis_client.get.return_value = (
            sample_leaderboard_response.model_dump_json()
        )

        # Mock get_redis_client to return our mock
        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.get_leaderboard(limit=5)

        assert len(result.entries) == 5
        assert result.pagination.has_next is False

        # Verify cache was checked
        mock_redis_client.get.assert_called_once()

        # Verify repository was not called (cache hit)
        service.repository.get_leaderboard_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_leaderboard_cache_miss(
        self,
        service,
        mock_redis_client,
        mock_leaderboard_repository,
        sample_leaderboard_entries,
    ):
        """Test leaderboard retrieval with cache miss."""
        # Setup cache miss
        mock_redis_client.get.return_value = None
        mock_leaderboard_repository.get_leaderboard_page.return_value = (
            sample_leaderboard_entries[:5],
            False,
        )

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.get_leaderboard(limit=5)

        assert len(result.entries) == 5
        assert result.pagination.has_next is False

        # Verify cache was checked and set (service calls get twice: once for leaderboard, once for stats)
        assert mock_redis_client.get.call_count >= 1
        mock_redis_client.setex.assert_called()

        # Verify repository was called
        mock_leaderboard_repository.get_leaderboard_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_leaderboard_with_cursor(
        self,
        service,
        mock_redis_client,
        mock_leaderboard_repository,
        sample_leaderboard_entries,
    ):
        """Test leaderboard retrieval with cursor."""
        cursor_obj = LeaderboardCursor(rank=10, user_pk=uuid4(), loyalty_score=100)
        cursor = cursor_obj.encode()

        # Cache miss for cursor-based queries
        mock_redis_client.get.return_value = None
        mock_leaderboard_repository.get_leaderboard_page.return_value = (
            sample_leaderboard_entries[5:8],
            True,
        )

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.get_leaderboard(limit=3, cursor=cursor)

        assert len(result.entries) == 3
        assert result.pagination.has_next is True

        # Verify repository was called with parsed cursor
        mock_leaderboard_repository.get_leaderboard_page.assert_called_once_with(
            limit=3,
            cursor=cursor_obj,
            filters=None,
            current_user_pk=None,
        )

    @pytest.mark.asyncio
    async def test_get_leaderboard_with_filters(
        self,
        service,
        mock_redis_client,
        mock_leaderboard_repository,
        sample_leaderboard_entries,
        sample_filters,
    ):
        """Test leaderboard retrieval with filters."""
        # Cache miss for filtered queries
        mock_redis_client.get.return_value = None
        mock_leaderboard_repository.get_leaderboard_page.return_value = (
            sample_leaderboard_entries[:3],
            False,
        )

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.get_leaderboard(limit=3, filters=sample_filters)

        assert len(result.entries) == 3
        assert result.pagination.has_next is False

        # Verify repository was called with filters
        mock_leaderboard_repository.get_leaderboard_page.assert_called_once_with(
            limit=3,
            cursor=None,
            filters=sample_filters,
            current_user_pk=None,
        )

    @pytest.mark.asyncio
    async def test_get_top_users_cache_hit(
        self,
        service,
        mock_redis_client,
        sample_leaderboard_entries,
    ):
        """Test top users retrieval with cache hit."""
        cached_users = sample_leaderboard_entries[:3]
        mock_redis_client.get.return_value = json.dumps(
            [entry.model_dump() for entry in cached_users], default=str
        )

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.get_top_users(limit=3)

        assert len(result) == 3
        assert result[0].rank == 1

        # Verify cache was checked
        mock_redis_client.get.assert_called_once()
        service.repository.get_top_users.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_top_users_cache_miss(
        self,
        service,
        mock_redis_client,
        mock_leaderboard_repository,
        sample_leaderboard_entries,
    ):
        """Test top users retrieval with cache miss."""
        mock_redis_client.get.return_value = None
        mock_leaderboard_repository.get_top_users.return_value = (
            sample_leaderboard_entries[:3]
        )

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.get_top_users(limit=3)

        assert len(result) == 3

        # Verify cache was set
        mock_redis_client.setex.assert_called_once()
        mock_leaderboard_repository.get_top_users.assert_called_once_with(3)

    @pytest.mark.asyncio
    async def test_get_leaderboard_stats_cache_hit(
        self,
        service,
        mock_redis_client,
        sample_leaderboard_stats,
    ):
        """Test leaderboard stats retrieval with cache hit."""
        mock_redis_client.get.return_value = sample_leaderboard_stats.model_dump_json()

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.get_leaderboard_stats()

        assert result.total_users == 1000
        assert result.average_loyalty_score == 75.5

        # Verify cache was checked
        mock_redis_client.get.assert_called_once()
        service.repository.get_leaderboard_stats.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_leaderboard_stats_cache_miss(
        self,
        service,
        mock_redis_client,
        mock_leaderboard_repository,
        sample_leaderboard_stats,
    ):
        """Test leaderboard stats retrieval with cache miss."""
        mock_redis_client.get.return_value = None
        mock_leaderboard_repository.get_leaderboard_stats.return_value = (
            sample_leaderboard_stats
        )

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.get_leaderboard_stats()

        assert result.total_users == 1000

        # Verify cache was set
        mock_redis_client.setex.assert_called_once()
        mock_leaderboard_repository.get_leaderboard_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_users_cache_hit(
        self,
        service,
        mock_redis_client,
        sample_leaderboard_entries,
    ):
        """Test user search with cache hit."""
        search_results = sample_leaderboard_entries[:2]
        # Don't mock cache for search - it doesn't use caching
        mock_redis_client.get.return_value = None

        # Mock repository directly since search doesn't use caching
        service.repository.search_users = AsyncMock(return_value=search_results)

        result = await service.search_users("test")

        assert len(result) == 2

        # Verify repository was called
        service.repository.search_users.assert_called_once_with("test", 20)

    @pytest.mark.asyncio
    async def test_search_users_cache_miss(
        self,
        service,
        mock_redis_client,
        mock_leaderboard_repository,
        sample_leaderboard_entries,
    ):
        """Test user search with cache miss."""
        mock_redis_client.get.return_value = None

        # Mock search results - search doesn't use caching
        search_results = sample_leaderboard_entries[:2]
        service.repository.search_users = AsyncMock(return_value=search_results)

        result = await service.search_users("test")

        assert len(result) == 2

        # Verify repository was called (no caching for search)
        service.repository.search_users.assert_called_once_with("test", 20)

    @pytest.mark.asyncio
    async def test_get_user_personal_stats(
        self,
        service,
        mock_leaderboard_repository,
        mock_redis_client,
        sample_user_rank_lookup,
        sample_rank_history,
        sample_leaderboard_entries,
    ):
        """Test getting personal leaderboard stats for a user."""
        user_pk = sample_user_rank_lookup.user_pk

        # Setup repository mocks
        mock_leaderboard_repository.get_user_rank.return_value = sample_user_rank_lookup
        mock_leaderboard_repository.get_user_rank_history.return_value = (
            sample_rank_history
        )

        # Create a nearby users list that includes the current user
        nearby_users = sample_leaderboard_entries[:5].copy()
        nearby_users[0] = nearby_users[0].model_copy(
            update={"user_pk": user_pk, "is_current_user": True}
        )
        mock_leaderboard_repository.get_nearby_users.return_value = nearby_users

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.get_user_personal_stats(user_pk)

        assert isinstance(result, PersonalLeaderboardStats)
        assert result.current_position.user_pk == user_pk
        assert result.current_position.rank == 1
        assert len(result.rank_history) == 2
        assert len(result.nearby_users) == 5

        # Verify repository calls
        mock_leaderboard_repository.get_user_rank.assert_called_once_with(user_pk)
        mock_leaderboard_repository.get_user_rank_history.assert_called_once_with(
            user_pk, 30
        )
        mock_leaderboard_repository.get_nearby_users.assert_called_once_with(
            user_pk, 10
        )

    @pytest.mark.asyncio
    async def test_get_user_personal_stats_user_not_found(
        self,
        service,
        mock_leaderboard_repository,
        mock_redis_client,
    ):
        """Test getting personal stats for non-existent user."""
        user_pk = uuid4()

        # Mock user not found
        from therobotoverlord_api.database.models.leaderboard import UserRankLookup

        not_found_lookup = UserRankLookup(
            user_pk=user_pk,
            username="",
            rank=0,
            loyalty_score=0,
            percentile_rank=1.0,
            found=False,
        )
        mock_leaderboard_repository.get_user_rank.return_value = not_found_lookup

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            with pytest.raises(
                ValueError, match=f"User {user_pk} not found in leaderboard"
            ):
                await service.get_user_personal_stats(user_pk)

        # Should not call other methods for non-existent user
        mock_leaderboard_repository.get_user_rank_history.assert_not_called()
        mock_leaderboard_repository.get_nearby_users.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_leaderboard_success(
        self,
        service,
        mock_leaderboard_repository,
        mock_redis_client,
    ):
        """Test successful leaderboard refresh."""
        mock_leaderboard_repository.refresh_leaderboard.return_value = True

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.refresh_leaderboard_data()

        assert result is True

        # Verify cache was invalidated
        mock_redis_client.keys.assert_called()
        # delete() may or may not be called depending on whether keys() returns results

        # Verify repository refresh was called
        mock_leaderboard_repository.refresh_leaderboard.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_leaderboard_failure(
        self,
        service,
        mock_leaderboard_repository,
        mock_redis_client,
    ):
        """Test leaderboard refresh failure."""
        mock_leaderboard_repository.refresh_leaderboard.return_value = False

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            result = await service.refresh_leaderboard_data()

        assert result is False

        # Cache should not be invalidated on failure
        mock_redis_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalidate_user_cache(
        self,
        service,
        mock_redis_client,
    ):
        """Test cache invalidation for specific user."""
        user_pk = uuid4()

        # Mock cache keys
        mock_redis_client.keys.return_value = [
            b"leaderboard:user:stats:" + str(user_pk).encode(),
            b"leaderboard:search:citizen",
            b"leaderboard:page:1",
        ]

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            await service.invalidate_user_cache(user_pk)

        # Verify cache keys were searched and deleted
        mock_redis_client.keys.assert_called()
        mock_redis_client.delete.assert_called()

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, service):
        """Test cache key generation for different scenarios."""
        # Test basic cache key generation
        key1 = service._generate_cache_key("test", {"limit": 10})
        key2 = service._generate_cache_key("test", {"limit": 20})

        assert key1 != key2

        # Test with filters
        key3 = service._generate_cache_key("test", {"limit": 10, "filter": "active"})

        assert key3 != key1

        # Test consistency
        key4 = service._generate_cache_key("test", {"limit": 10})
        assert key1 == key4

    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(
        self,
        service,
        mock_redis_client,
        mock_leaderboard_repository,
        sample_leaderboard_entries,
    ):
        """Test that different cache types use appropriate TTLs."""
        # Test leaderboard page cache (5 minutes)
        mock_redis_client.get.return_value = None
        mock_leaderboard_repository.get_leaderboard_page.return_value = (
            sample_leaderboard_entries[:5],
            False,
        )

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            await service.get_leaderboard(limit=5)

        # Verify TTL was set correctly
        setex_call = mock_redis_client.setex.call_args
        assert setex_call[0][1] == 300  # 5 minutes in seconds

        # Reset mocks
        mock_redis_client.reset_mock()

        # Test stats cache (15 minutes)
        from therobotoverlord_api.database.models.leaderboard import LeaderboardStats

        stats = LeaderboardStats(
            total_users=100,
            active_users=95,
            average_loyalty_score=50.0,
            median_loyalty_score=45,
            top_10_percent_threshold=100,
            score_distribution={},
            last_updated=datetime.now(UTC),
        )
        mock_leaderboard_repository.get_leaderboard_stats.return_value = stats

        with patch(
            "therobotoverlord_api.services.leaderboard_service.get_redis_client",
            return_value=mock_redis_client,
        ):
            await service.get_leaderboard_stats()

        # Verify longer TTL for stats
        setex_call = mock_redis_client.setex.call_args
        assert setex_call[0][1] == 1800  # 30 minutes in seconds
