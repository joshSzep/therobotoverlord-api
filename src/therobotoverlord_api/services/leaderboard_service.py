"""Leaderboard service for The Robot Overlord API."""

import json

from uuid import UUID

from therobotoverlord_api.database.models.leaderboard import LeaderboardCursor
from therobotoverlord_api.database.models.leaderboard import LeaderboardEntry
from therobotoverlord_api.database.models.leaderboard import LeaderboardFilters
from therobotoverlord_api.database.models.leaderboard import LeaderboardResponse
from therobotoverlord_api.database.models.leaderboard import LeaderboardStats
from therobotoverlord_api.database.models.leaderboard import PaginationInfo
from therobotoverlord_api.database.models.leaderboard import PersonalLeaderboardStats
from therobotoverlord_api.database.models.leaderboard import UserRankLookup
from therobotoverlord_api.database.repositories.leaderboard import LeaderboardRepository
from therobotoverlord_api.workers.redis_connection import get_redis_client


class LeaderboardService:
    """Service for leaderboard business logic and caching."""

    def __init__(self):
        self.repository = LeaderboardRepository()
        self.cache_ttl = {
            "leaderboard_page": 300,  # 5 minutes
            "user_rank": 900,  # 15 minutes
            "top_users": 600,  # 10 minutes
            "stats": 1800,  # 30 minutes
        }

    async def get_leaderboard(
        self,
        limit: int = 50,
        cursor: str | None = None,
        filters: LeaderboardFilters | None = None,
        current_user_pk: UUID | None = None,
    ) -> LeaderboardResponse:
        """Get leaderboard with caching and pagination."""
        # Parse cursor
        parsed_cursor = None
        if cursor:
            try:
                parsed_cursor = LeaderboardCursor.decode(cursor)
            except ValueError:
                # Invalid cursor, start from beginning
                parsed_cursor = None

        # Generate cache key
        cache_key = self._generate_cache_key(
            "leaderboard",
            {
                "limit": limit,
                "cursor": cursor,
                "filters": filters.model_dump() if filters else {},
                "user": str(current_user_pk) if current_user_pk else None,
            },
        )

        # Try cache first
        redis_client = await get_redis_client()
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return LeaderboardResponse.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                # Invalid cache data, continue to database
                pass

        # Get data from repository
        entries, has_next = await self.repository.get_leaderboard_page(
            limit=limit,
            cursor=parsed_cursor,
            filters=filters,
            current_user_pk=current_user_pk,
        )

        # Get current user's position if not in results
        current_user_position = None
        if current_user_pk and not any(entry.is_current_user for entry in entries):
            user_rank = await self.repository.get_user_rank(current_user_pk)
            if user_rank and user_rank.found:
                # Get full entry for current user
                nearby_users = await self.repository.get_nearby_users(
                    current_user_pk, 0
                )
                if nearby_users:
                    current_user_position = nearby_users[0]

        # Calculate pagination info
        next_cursor = None
        if has_next and entries:
            last_entry = entries[-1]
            next_cursor = LeaderboardCursor(
                rank=last_entry.rank,
                user_pk=last_entry.user_pk,
                loyalty_score=last_entry.loyalty_score,
            ).encode()

        # Get total count (cached separately)
        stats = await self.get_leaderboard_stats()

        pagination = PaginationInfo(
            limit=limit,
            has_next=has_next,
            has_previous=parsed_cursor is not None,
            next_cursor=next_cursor,
            previous_cursor=None,  # Previous cursor logic would be complex, skip for now
            total_count=stats.total_users,
        )

        response = LeaderboardResponse(
            entries=entries,
            pagination=pagination,
            current_user_position=current_user_position,
            total_users=stats.total_users,
            last_updated=stats.last_updated,
            filters_applied=filters or LeaderboardFilters(),
        )

        # Cache the response
        await redis_client.setex(
            cache_key,
            self.cache_ttl["leaderboard_page"],
            json.dumps(response.model_dump(), default=str),
        )

        return response

    async def get_user_personal_stats(self, user_pk: UUID) -> PersonalLeaderboardStats:
        """Get personal leaderboard statistics for a user."""
        cache_key = f"personal_stats:{user_pk}"

        # Try cache first
        redis_client = await get_redis_client()
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return PersonalLeaderboardStats.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # Get current position
        user_rank = await self.repository.get_user_rank(user_pk)
        if not user_rank or not user_rank.found:
            raise ValueError(f"User {user_pk} not found in leaderboard")

        # Get nearby users
        nearby_users = await self.get_nearby_users(user_pk, 10)
        current_position = next((u for u in nearby_users if u.user_pk == user_pk), None)

        if not current_position:
            raise ValueError(f"Could not find current position for user {user_pk}")

        # Get rank history
        rank_history = await self.repository.get_user_rank_history(user_pk, 30)

        # Calculate percentile improvement
        percentile_improvement = None
        if len(rank_history) >= 2:
            current_percentile = current_position.percentile_rank
            old_percentile = rank_history[-1].percentile_rank
            percentile_improvement = (
                old_percentile - current_percentile
            )  # Positive = improvement

        # Calculate achievement progress (placeholder)
        achievement_progress = {
            "topic_creator": min(1.0, current_position.topics_created_count / 5.0),
            "loyalty_builder": min(
                1.0, max(0.0, current_position.loyalty_score) / 100.0
            ),
            "top_10_percent": 1.0
            if current_position.percentile_rank <= 0.1
            else current_position.percentile_rank / 0.1,
        }

        stats = PersonalLeaderboardStats(
            current_position=current_position,
            rank_history=rank_history,
            nearby_users=nearby_users,
            achievement_progress=achievement_progress,
            percentile_improvement=percentile_improvement,
        )

        # Cache the result
        await redis_client.setex(
            cache_key,
            self.cache_ttl["user_rank"],
            json.dumps(stats.model_dump(), default=str),
        )

        return stats

    async def get_top_users(self, limit: int = 10) -> list[LeaderboardEntry]:
        """Get top users with caching."""
        cache_key = f"top_users:{limit}"

        # Try cache first
        redis_client = await get_redis_client()
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return [LeaderboardEntry.model_validate(entry) for entry in data]
            except (json.JSONDecodeError, ValueError):
                pass

        # Get from repository
        entries = await self.repository.get_top_users(limit)

        # Cache the result
        await redis_client.setex(
            cache_key,
            self.cache_ttl["top_users"],
            json.dumps([entry.model_dump() for entry in entries], default=str),
        )

        return entries

    async def get_leaderboard_stats(self) -> LeaderboardStats:
        """Get leaderboard statistics with caching."""
        cache_key = "leaderboard_stats"

        # Try cache first
        redis_client = await get_redis_client()
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return LeaderboardStats.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # Get from repository
        stats = await self.repository.get_leaderboard_stats()

        # Cache the result
        await redis_client.setex(
            cache_key,
            self.cache_ttl["stats"],
            json.dumps(stats.model_dump(), default=str),
        )

        return stats

    async def search_users(self, search_term: str, limit: int = 20):
        """Search users by username."""
        # Don't cache search results as they're typically one-off queries
        return await self.repository.search_users(search_term, limit)

    async def get_users_by_percentile_range(
        self, start_percentile: float, end_percentile: float
    ) -> list[LeaderboardEntry]:
        """Get users within a specific percentile range."""
        if not 0 <= start_percentile <= 1 or not 0 <= end_percentile <= 1:
            raise ValueError("Percentiles must be between 0 and 1")
        if start_percentile >= end_percentile:
            raise ValueError("Start percentile must be less than end percentile")

        users = await self.repository.get_users_by_percentile_range(
            start_percentile, end_percentile
        )
        return users

    async def get_users_by_rank_range(
        self, start_rank: int, end_rank: int
    ) -> list[LeaderboardEntry]:
        """Get users within a specific rank range."""
        if start_rank < 1 or end_rank < 1:
            raise ValueError("Ranks must be positive integers")
        if start_rank > end_rank:
            raise ValueError("Start rank must be less than or equal to end rank")

        users = await self.repository.get_users_by_rank_range(start_rank, end_rank)
        return users

    async def get_nearby_users(
        self, user_pk: UUID, context_size: int = 10
    ) -> list[LeaderboardEntry]:
        """Get users near a specific user in the leaderboard."""
        return await self.repository.get_nearby_users(user_pk, context_size)

    async def invalidate_user_cache(self, user_pk: UUID):
        """Invalidate cache entries for a specific user."""
        redis_client = await get_redis_client()

        # Invalidate personal stats
        await redis_client.delete(f"personal_stats:{user_pk}")

        # Invalidate general caches (they might contain this user)
        patterns_to_delete = [
            "leaderboard:*",
            "top_users:*",
            "leaderboard_stats",
        ]

        for pattern in patterns_to_delete:
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)

    async def get_user_rank(self, user_pk: UUID) -> UserRankLookup:
        """Get user's rank information."""
        return await self.repository.get_user_rank(user_pk)

    async def invalidate_all_cache(self):
        """Invalidate all leaderboard caches."""
        redis_client = await get_redis_client()

        patterns_to_delete = [
            "leaderboard:*",
            "personal_stats:*",
            "top_users:*",
            "leaderboard_stats",
        ]

        for pattern in patterns_to_delete:
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)

    async def refresh_leaderboard_data(self) -> bool:
        """Refresh materialized view and invalidate caches."""
        success = await self.repository.refresh_leaderboard()
        if success:
            await self.invalidate_all_cache()
        return success

    def _generate_cache_key(self, prefix: str, params: dict) -> str:
        """Generate a consistent cache key from parameters."""
        # Sort parameters for consistent key generation
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params if v is not None)
        return f"{prefix}:{hash(param_str)}"


# Singleton instance
_leaderboard_service: LeaderboardService | None = None


async def get_leaderboard_service() -> LeaderboardService:
    """Get the leaderboard service instance."""
    global _leaderboard_service  # noqa: PLW0603
    if _leaderboard_service is None:
        _leaderboard_service = LeaderboardService()
    return _leaderboard_service
