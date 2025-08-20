"""Loyalty Score service for The Robot Overlord API."""

import json

from uuid import UUID

from therobotoverlord_api.database.models.loyalty_score import ContentType
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventFilters
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventOutcome
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventResponse
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreAdjustment
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreBreakdown
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreStats
from therobotoverlord_api.database.models.loyalty_score import ModerationEvent
from therobotoverlord_api.database.models.loyalty_score import ModerationEventType
from therobotoverlord_api.database.models.loyalty_score import UserLoyaltyProfile
from therobotoverlord_api.database.repositories.loyalty_score import (
    LoyaltyScoreRepository,
)
from therobotoverlord_api.workers.redis_connection import get_redis_client


class LoyaltyScoreService:
    """Service for loyalty score management and analytics."""

    def __init__(self):
        self.repository = LoyaltyScoreRepository()
        self.cache_ttl = {
            "user_profile": 600,  # 10 minutes
            "score_breakdown": 300,  # 5 minutes
            "system_stats": 1800,  # 30 minutes
            "events": 180,  # 3 minutes
        }
        # Proprietary scoring algorithm parameters
        self._scoring_weights = {
            ContentType.POST: 1,
            ContentType.TOPIC: 5,
            ContentType.PRIVATE_MESSAGE: 1,
        }
        self._appeal_bonus = 2  # Extra points for sustained appeals
        self._appeal_penalty = 1  # Penalty for denied appeals

    async def get_user_loyalty_profile(self, user_pk: UUID) -> UserLoyaltyProfile:
        """Get complete loyalty profile for a user with caching."""
        cache_key = f"loyalty_profile:{user_pk}"

        # Try cache first
        redis_client = await get_redis_client()
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return UserLoyaltyProfile.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # Get from repository
        profile = await self.repository.get_user_loyalty_profile(user_pk)

        # Cache the result
        await redis_client.setex(
            cache_key,
            self.cache_ttl["user_profile"],
            json.dumps(profile.model_dump(), default=str),
        )

        return profile

    async def get_user_score_breakdown(self, user_pk: UUID) -> LoyaltyScoreBreakdown:
        """Get detailed score breakdown for a user."""
        cache_key = f"score_breakdown:{user_pk}"

        # Try cache first
        redis_client = await get_redis_client()
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return LoyaltyScoreBreakdown.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # Get from repository
        breakdown = await self.repository.get_score_breakdown(user_pk)

        # Cache the result
        await redis_client.setex(
            cache_key,
            self.cache_ttl["score_breakdown"],
            json.dumps(breakdown.model_dump(), default=str),
        )

        return breakdown

    async def get_user_events(
        self,
        user_pk: UUID,
        filters: LoyaltyEventFilters | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> LoyaltyEventResponse:
        """Get moderation events for a user with pagination."""
        return await self.repository.get_user_events(user_pk, filters, page, page_size)

    async def get_system_stats(self) -> LoyaltyScoreStats:
        """Get system-wide loyalty score statistics."""
        cache_key = "loyalty_system_stats"

        # Try cache first
        redis_client = await get_redis_client()
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return LoyaltyScoreStats.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                pass

        # Get from repository
        stats = await self.repository.get_system_stats()

        # Cache the result
        await redis_client.setex(
            cache_key,
            self.cache_ttl["system_stats"],
            json.dumps(stats.model_dump(), default=str),
        )

        return stats

    async def record_moderation_event(
        self,
        user_pk: UUID,
        event_type: ModerationEventType,
        content_type: ContentType,
        content_pk: UUID,
        outcome: LoyaltyEventOutcome,
        moderator_pk: UUID | None = None,
        reason: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ModerationEvent:
        """Record a moderation event and update loyalty score."""
        # Calculate score delta based on proprietary algorithm
        score_delta = self._calculate_score_delta(content_type, outcome, event_type)

        # Record the event
        event = await self.repository.record_moderation_event(
            user_pk=user_pk,
            event_type=event_type,
            content_type=content_type,
            content_pk=content_pk,
            outcome=outcome,
            score_delta=score_delta,
            moderator_pk=moderator_pk,
            reason=reason,
            metadata=metadata or {},
        )

        # Invalidate user caches
        await self._invalidate_user_cache(user_pk)

        # Invalidate system stats cache
        redis_client = await get_redis_client()
        await redis_client.delete("loyalty_system_stats")

        return event

    async def apply_manual_adjustment(
        self,
        adjustment: LoyaltyScoreAdjustment,
        admin_pk: UUID,
    ) -> ModerationEvent:
        """Apply manual loyalty score adjustment (admin only)."""
        event = await self.repository.apply_manual_adjustment(
            user_pk=adjustment.user_pk,
            adjustment=adjustment.adjustment,
            reason=adjustment.reason,
            admin_notes=adjustment.admin_notes,
            admin_pk=admin_pk,
        )

        # Invalidate caches
        await self._invalidate_user_cache(adjustment.user_pk)
        redis_client = await get_redis_client()
        await redis_client.delete("loyalty_system_stats")

        return event

    async def recalculate_user_score(self, user_pk: UUID) -> int:
        """Recalculate a user's loyalty score from scratch."""
        new_score = await self.repository.recalculate_user_score(user_pk)

        # Invalidate user caches
        await self._invalidate_user_cache(user_pk)

        return new_score

    async def get_score_thresholds(self) -> dict[str, int]:
        """Get current score thresholds for various privileges."""
        stats = await self.get_system_stats()
        return {
            "topic_creation": stats.topic_creation_threshold,
            "top_10_percent": stats.top_10_percent_threshold,
            "priority_moderation": 500,  # Hardcoded for now
            "extended_appeals": 1000,  # Hardcoded for now
        }

    async def get_users_by_score_range(
        self, min_score: int, max_score: int, limit: int = 100
    ) -> list[UserLoyaltyProfile]:
        """Get users within a specific score range."""
        return await self.repository.get_users_by_score_range(
            min_score, max_score, limit
        )

    async def get_recent_events(
        self,
        filters: LoyaltyEventFilters | None = None,
        limit: int = 100,
    ) -> list[ModerationEvent]:
        """Get recent moderation events across all users (admin only)."""
        return await self.repository.get_recent_events(filters, limit)

    def _calculate_score_delta(
        self,
        content_type: ContentType,
        outcome: LoyaltyEventOutcome,
        event_type: ModerationEventType,
    ) -> int:
        """Calculate score change based on proprietary algorithm."""
        base_weight = self._scoring_weights.get(content_type, 1)

        if outcome == LoyaltyEventOutcome.APPROVED:
            return base_weight
        if outcome == LoyaltyEventOutcome.REJECTED:
            return -base_weight
        if outcome == LoyaltyEventOutcome.REMOVED:
            # Administrative removal - moderate penalty
            return -base_weight
        if outcome == LoyaltyEventOutcome.APPEAL_SUSTAINED:
            # Bonus for successful appeals
            return base_weight + self._appeal_bonus
        if outcome == LoyaltyEventOutcome.APPEAL_DENIED:
            # Additional penalty for failed appeals
            return -self._appeal_penalty

        return 0

    async def _invalidate_user_cache(self, user_pk: UUID) -> None:
        """Invalidate all cached data for a user."""
        redis_client = await get_redis_client()
        cache_keys = [
            f"loyalty_profile:{user_pk}",
            f"score_breakdown:{user_pk}",
            f"loyalty:{user_pk}",  # From leaderboard service
        ]

        for key in cache_keys:
            await redis_client.delete(key)


# Global service instance
_loyalty_score_service: LoyaltyScoreService | None = None


async def get_loyalty_score_service() -> LoyaltyScoreService:
    """Get the loyalty score service instance."""
    global _loyalty_score_service  # noqa: PLW0603
    if _loyalty_score_service is None:
        _loyalty_score_service = LoyaltyScoreService()
    return _loyalty_score_service
