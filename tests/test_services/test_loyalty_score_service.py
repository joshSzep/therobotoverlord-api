"""Tests for loyalty score service."""

import json

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

import therobotoverlord_api.services.loyalty_score_service

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
from therobotoverlord_api.services.loyalty_score_service import LoyaltyScoreService
from therobotoverlord_api.services.loyalty_score_service import (
    get_loyalty_score_service,
)


@pytest.mark.asyncio
class TestLoyaltyScoreService:
    """Test cases for LoyaltyScoreService."""

    @pytest.fixture
    def service(self):
        """Create a LoyaltyScoreService instance for testing."""
        return LoyaltyScoreService()

    @pytest.fixture
    def sample_user_pk(self):
        """Sample user UUID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_content_pk(self):
        """Sample content UUID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_moderator_pk(self):
        """Sample moderator UUID for testing."""
        return uuid4()

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.setex = AsyncMock()
        mock_client.delete = AsyncMock()
        return mock_client

    @pytest.fixture
    def sample_user_profile(self, sample_user_pk):
        """Sample UserLoyaltyProfile for testing."""
        return UserLoyaltyProfile(
            user_pk=sample_user_pk,
            username="testuser",
            current_score=100,
            rank=5,
            percentile_rank=0.85,
            can_create_topics=True,
            breakdown=LoyaltyScoreBreakdown(
                user_pk=sample_user_pk,
                current_score=100,
                post_score=50,
                topic_score=30,
                private_message_score=10,
                appeal_adjustments=5,
                manual_adjustments=5,
                total_approved_posts=10,
                total_rejected_posts=2,
                total_approved_topics=6,
                total_rejected_topics=0,
                total_approved_messages=5,
                total_rejected_messages=1,
                last_updated=datetime.now(UTC),
            ),
            recent_events=[],
            score_history=[],
        )

    @pytest.fixture
    def sample_score_breakdown(self, sample_user_pk):
        """Sample LoyaltyScoreBreakdown for testing."""
        return LoyaltyScoreBreakdown(
            user_pk=sample_user_pk,
            current_score=100,
            post_score=50,
            topic_score=30,
            private_message_score=10,
            appeal_adjustments=5,
            manual_adjustments=5,
            total_approved_posts=10,
            total_rejected_posts=2,
            total_approved_topics=6,
            total_rejected_topics=0,
            total_approved_messages=5,
            total_rejected_messages=1,
            last_updated=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_system_stats(self):
        """Sample LoyaltyScoreStats for testing."""
        return LoyaltyScoreStats(
            total_users=1000,
            average_score=45.5,
            median_score=40,
            top_10_percent_threshold=80,
            topic_creation_threshold=30,
            total_events_processed=5000,
            last_updated=datetime.now(UTC),
            score_distribution={
                "negative": 50,
                "zero": 100,
                "1-10": 200,
                "11-50": 400,
                "51-100": 200,
                "100+": 50,
            },
        )

    @pytest.fixture
    def sample_moderation_event(
        self, sample_user_pk, sample_content_pk, sample_moderator_pk
    ):
        """Sample ModerationEvent for testing."""
        return ModerationEvent(
            pk=uuid4(),
            user_pk=sample_user_pk,
            event_type=ModerationEventType.POST_MODERATION,
            content_type=ContentType.POST,
            content_pk=sample_content_pk,
            outcome=LoyaltyEventOutcome.APPROVED,
            score_delta=1,
            previous_score=99,
            new_score=100,
            moderator_pk=sample_moderator_pk,
            reason="Good content",
            metadata={},
            created_at=datetime.now(UTC),
        )

    def test_init(self, service):
        """Test service initialization."""
        assert service.repository is not None
        assert service.cache_ttl["user_profile"] == 600
        assert service.cache_ttl["score_breakdown"] == 300
        assert service.cache_ttl["system_stats"] == 1800
        assert service.cache_ttl["events"] == 180
        assert service._scoring_weights[ContentType.POST] == 1
        assert service._scoring_weights[ContentType.TOPIC] == 5
        assert service._scoring_weights[ContentType.PRIVATE_MESSAGE] == 1
        assert service._appeal_bonus == 2
        assert service._appeal_penalty == 1

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_get_user_loyalty_profile_cache_hit(
        self,
        mock_get_redis,
        service,
        sample_user_pk,
        sample_user_profile,
        mock_redis_client,
    ):
        """Test getting user loyalty profile from cache."""
        mock_get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = json.dumps(
            sample_user_profile.model_dump(), default=str
        )

        result = await service.get_user_loyalty_profile(sample_user_pk)

        assert isinstance(result, UserLoyaltyProfile)
        assert result.user_pk == sample_user_pk
        mock_redis_client.get.assert_called_once_with(
            f"loyalty_profile:{sample_user_pk}"
        )

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_get_user_loyalty_profile_cache_miss(
        self,
        mock_get_redis,
        service,
        sample_user_pk,
        sample_user_profile,
        mock_redis_client,
    ):
        """Test getting user loyalty profile from repository when cache misses."""
        mock_get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = None
        service.repository.get_user_loyalty_profile = AsyncMock(
            return_value=sample_user_profile
        )

        result = await service.get_user_loyalty_profile(sample_user_pk)

        assert isinstance(result, UserLoyaltyProfile)
        assert result.user_pk == sample_user_pk
        service.repository.get_user_loyalty_profile.assert_called_once_with(
            sample_user_pk
        )
        mock_redis_client.setex.assert_called_once()

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_get_user_loyalty_profile_cache_invalid_json(
        self,
        mock_get_redis,
        service,
        sample_user_pk,
        sample_user_profile,
        mock_redis_client,
    ):
        """Test handling invalid JSON in cache."""
        mock_get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = "invalid json"
        service.repository.get_user_loyalty_profile = AsyncMock(
            return_value=sample_user_profile
        )

        result = await service.get_user_loyalty_profile(sample_user_pk)

        assert isinstance(result, UserLoyaltyProfile)
        service.repository.get_user_loyalty_profile.assert_called_once_with(
            sample_user_pk
        )

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_get_user_score_breakdown_cache_hit(
        self,
        mock_get_redis,
        service,
        sample_user_pk,
        sample_score_breakdown,
        mock_redis_client,
    ):
        """Test getting score breakdown from cache."""
        mock_get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = json.dumps(
            sample_score_breakdown.model_dump(), default=str
        )

        result = await service.get_user_score_breakdown(sample_user_pk)

        assert isinstance(result, LoyaltyScoreBreakdown)
        assert result.user_pk == sample_user_pk
        mock_redis_client.get.assert_called_once_with(
            f"score_breakdown:{sample_user_pk}"
        )

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_get_user_score_breakdown_cache_miss(
        self,
        mock_get_redis,
        service,
        sample_user_pk,
        sample_score_breakdown,
        mock_redis_client,
    ):
        """Test getting score breakdown from repository when cache misses."""
        mock_get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = None
        service.repository.get_score_breakdown = AsyncMock(
            return_value=sample_score_breakdown
        )

        result = await service.get_user_score_breakdown(sample_user_pk)

        assert isinstance(result, LoyaltyScoreBreakdown)
        assert result.user_pk == sample_user_pk
        service.repository.get_score_breakdown.assert_called_once_with(sample_user_pk)
        mock_redis_client.setex.assert_called_once()

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_get_user_score_breakdown_cache_invalid_json(
        self,
        mock_get_redis,
        service,
        sample_user_pk,
        sample_score_breakdown,
        mock_redis_client,
    ):
        """Test handling invalid JSON in cache for score breakdown."""
        mock_get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = "invalid json"
        service.repository.get_score_breakdown = AsyncMock(
            return_value=sample_score_breakdown
        )

        result = await service.get_user_score_breakdown(sample_user_pk)

        assert isinstance(result, LoyaltyScoreBreakdown)
        service.repository.get_score_breakdown.assert_called_once_with(sample_user_pk)

    async def test_get_user_events(self, service, sample_user_pk):
        """Test getting user events."""
        filters = LoyaltyEventFilters(event_type=ModerationEventType.POST_MODERATION)
        mock_response = LoyaltyEventResponse(
            events=[],
            total_count=0,
            page=1,
            page_size=50,
            has_next=False,
            filters_applied=filters,
        )
        service.repository.get_user_events = AsyncMock(return_value=mock_response)

        result = await service.get_user_events(sample_user_pk, filters, 1, 50)

        assert isinstance(result, LoyaltyEventResponse)
        service.repository.get_user_events.assert_called_once_with(
            sample_user_pk, filters, 1, 50
        )

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_get_system_stats_cache_hit(
        self, mock_get_redis, service, sample_system_stats, mock_redis_client
    ):
        """Test getting system stats from cache."""
        mock_get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = json.dumps(
            sample_system_stats.model_dump(), default=str
        )

        result = await service.get_system_stats()

        assert isinstance(result, LoyaltyScoreStats)
        assert result.total_users == 1000
        mock_redis_client.get.assert_called_once_with("loyalty_system_stats")

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_get_system_stats_cache_miss(
        self, mock_get_redis, service, sample_system_stats, mock_redis_client
    ):
        """Test getting system stats from repository when cache misses."""
        mock_get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = None
        service.repository.get_system_stats = AsyncMock(
            return_value=sample_system_stats
        )

        result = await service.get_system_stats()

        assert isinstance(result, LoyaltyScoreStats)
        assert result.total_users == 1000
        service.repository.get_system_stats.assert_called_once()
        mock_redis_client.setex.assert_called_once()

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_get_system_stats_cache_invalid_json(
        self, mock_get_redis, service, sample_system_stats, mock_redis_client
    ):
        """Test handling invalid JSON in cache for system stats."""
        mock_get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = "invalid json"
        service.repository.get_system_stats = AsyncMock(
            return_value=sample_system_stats
        )

        result = await service.get_system_stats()

        assert isinstance(result, LoyaltyScoreStats)
        service.repository.get_system_stats.assert_called_once()

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_record_moderation_event(
        self,
        mock_get_redis,
        service,
        sample_user_pk,
        sample_content_pk,
        sample_moderator_pk,
        sample_moderation_event,
        mock_redis_client,
    ):
        """Test recording a moderation event."""
        mock_get_redis.return_value = mock_redis_client
        service.repository.record_moderation_event = AsyncMock(
            return_value=sample_moderation_event
        )

        result = await service.record_moderation_event(
            user_pk=sample_user_pk,
            event_type=ModerationEventType.POST_MODERATION,
            content_type=ContentType.POST,
            content_pk=sample_content_pk,
            outcome=LoyaltyEventOutcome.APPROVED,
            moderator_pk=sample_moderator_pk,
            reason="Good content",
            metadata={"test": "data"},
        )

        assert isinstance(result, ModerationEvent)
        assert result.user_pk == sample_user_pk
        service.repository.record_moderation_event.assert_called_once()
        # Verify cache invalidation
        assert mock_redis_client.delete.call_count >= 2  # User cache + system stats

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_apply_manual_adjustment(
        self,
        mock_get_redis,
        service,
        sample_user_pk,
        sample_moderation_event,
        mock_redis_client,
    ):
        """Test applying manual score adjustment."""
        mock_get_redis.return_value = mock_redis_client
        service.repository.apply_manual_adjustment = AsyncMock(
            return_value=sample_moderation_event
        )

        adjustment = LoyaltyScoreAdjustment(
            user_pk=sample_user_pk,
            adjustment=10,
            reason="Manual bonus",
            admin_notes="Good behavior",
        )
        admin_pk = uuid4()

        result = await service.apply_manual_adjustment(adjustment, admin_pk)

        assert isinstance(result, ModerationEvent)
        service.repository.apply_manual_adjustment.assert_called_once_with(
            user_pk=adjustment.user_pk,
            adjustment=adjustment.adjustment,
            reason=adjustment.reason,
            admin_notes=adjustment.admin_notes,
            admin_pk=admin_pk,
        )
        # Verify cache invalidation
        assert mock_redis_client.delete.call_count >= 2

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_recalculate_user_score(
        self, mock_get_redis, service, sample_user_pk, mock_redis_client
    ):
        """Test recalculating user score."""
        mock_get_redis.return_value = mock_redis_client
        service.repository.recalculate_user_score = AsyncMock(return_value=150)

        result = await service.recalculate_user_score(sample_user_pk)

        assert result == 150
        service.repository.recalculate_user_score.assert_called_once_with(
            sample_user_pk
        )
        # Verify cache invalidation
        assert mock_redis_client.delete.call_count >= 3

    async def test_get_score_thresholds(self, service, sample_system_stats):
        """Test getting score thresholds."""
        service.get_system_stats = AsyncMock(return_value=sample_system_stats)

        result = await service.get_score_thresholds()

        assert isinstance(result, dict)
        assert result["topic_creation"] == sample_system_stats.topic_creation_threshold
        assert result["top_10_percent"] == sample_system_stats.top_10_percent_threshold
        assert result["priority_moderation"] == 500
        assert result["extended_appeals"] == 1000

    async def test_get_users_by_score_range(self, service, sample_user_pk):
        """Test getting users by score range."""
        mock_profiles = [
            UserLoyaltyProfile(
                user_pk=sample_user_pk,
                username="testuser",
                current_score=100,
                rank=5,
                percentile_rank=0.85,
                can_create_topics=True,
                breakdown=LoyaltyScoreBreakdown(
                    user_pk=sample_user_pk,
                    current_score=100,
                    post_score=50,
                    topic_score=30,
                    private_message_score=10,
                    appeal_adjustments=5,
                    manual_adjustments=5,
                    total_approved_posts=10,
                    total_rejected_posts=2,
                    total_approved_topics=6,
                    total_rejected_topics=0,
                    total_approved_messages=5,
                    total_rejected_messages=1,
                    last_updated=datetime.now(UTC),
                ),
                recent_events=[],
                score_history=[],
            )
        ]
        service.repository.get_users_by_score_range = AsyncMock(
            return_value=mock_profiles
        )

        result = await service.get_users_by_score_range(50, 150, 100)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].user_pk == sample_user_pk
        service.repository.get_users_by_score_range.assert_called_once_with(
            50, 150, 100
        )

    async def test_get_recent_events(self, service, sample_moderation_event):
        """Test getting recent events."""
        filters = LoyaltyEventFilters(event_type=ModerationEventType.POST_MODERATION)
        mock_events = [sample_moderation_event]
        service.repository.get_recent_events = AsyncMock(return_value=mock_events)

        result = await service.get_recent_events(filters, 100)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].pk == sample_moderation_event.pk
        service.repository.get_recent_events.assert_called_once_with(filters, 100)

    def test_calculate_score_delta_approved(self, service):
        """Test score delta calculation for approved content."""
        delta = service._calculate_score_delta(
            ContentType.POST,
            LoyaltyEventOutcome.APPROVED,
            ModerationEventType.POST_MODERATION,
        )
        assert delta == 1

        delta = service._calculate_score_delta(
            ContentType.TOPIC,
            LoyaltyEventOutcome.APPROVED,
            ModerationEventType.TOPIC_MODERATION,
        )
        assert delta == 5

        delta = service._calculate_score_delta(
            ContentType.PRIVATE_MESSAGE,
            LoyaltyEventOutcome.APPROVED,
            ModerationEventType.PRIVATE_MESSAGE_MODERATION,
        )
        assert delta == 1

    def test_calculate_score_delta_rejected(self, service):
        """Test score delta calculation for rejected content."""
        delta = service._calculate_score_delta(
            ContentType.POST,
            LoyaltyEventOutcome.REJECTED,
            ModerationEventType.POST_MODERATION,
        )
        assert delta == -1

        delta = service._calculate_score_delta(
            ContentType.TOPIC,
            LoyaltyEventOutcome.REJECTED,
            ModerationEventType.TOPIC_MODERATION,
        )
        assert delta == -5

    def test_calculate_score_delta_removed(self, service):
        """Test score delta calculation for removed content."""
        delta = service._calculate_score_delta(
            ContentType.POST,
            LoyaltyEventOutcome.REMOVED,
            ModerationEventType.POST_MODERATION,
        )
        assert delta == -1

    def test_calculate_score_delta_appeal_sustained(self, service):
        """Test score delta calculation for sustained appeals."""
        delta = service._calculate_score_delta(
            ContentType.POST,
            LoyaltyEventOutcome.APPEAL_SUSTAINED,
            ModerationEventType.APPEAL_RESOLUTION,
        )
        assert delta == 3  # base_weight (1) + appeal_bonus (2)

    def test_calculate_score_delta_appeal_denied(self, service):
        """Test score delta calculation for denied appeals."""
        delta = service._calculate_score_delta(
            ContentType.POST,
            LoyaltyEventOutcome.APPEAL_DENIED,
            ModerationEventType.APPEAL_RESOLUTION,
        )
        assert delta == -1  # appeal_penalty

    def test_calculate_score_delta_unknown_outcome(self, service):
        """Test score delta calculation for unknown outcome."""

        # Create a mock outcome that doesn't match any conditions
        class UnknownOutcome:
            pass

        delta = service._calculate_score_delta(
            ContentType.POST, UnknownOutcome(), ModerationEventType.POST_MODERATION
        )
        assert delta == 0

    @patch("therobotoverlord_api.services.loyalty_score_service.get_redis_client")
    async def test_invalidate_user_cache(
        self, mock_get_redis, service, sample_user_pk, mock_redis_client
    ):
        """Test user cache invalidation."""
        mock_get_redis.return_value = mock_redis_client

        await service._invalidate_user_cache(sample_user_pk)

        expected_keys = [
            f"loyalty_profile:{sample_user_pk}",
            f"score_breakdown:{sample_user_pk}",
            f"loyalty:{sample_user_pk}",
        ]
        assert mock_redis_client.delete.call_count == len(expected_keys)
        for key in expected_keys:
            mock_redis_client.delete.assert_any_call(key)


@pytest.mark.asyncio
class TestGetLoyaltyScoreService:
    """Test cases for get_loyalty_score_service function."""

    async def test_get_loyalty_score_service_singleton(self):
        """Test that get_loyalty_score_service returns the same instance."""
        # Reset the global variable
        therobotoverlord_api.services.loyalty_score_service._loyalty_score_service = (
            None
        )

        service1 = await get_loyalty_score_service()
        service2 = await get_loyalty_score_service()

        assert service1 is service2
        assert isinstance(service1, LoyaltyScoreService)

    async def test_get_loyalty_score_service_creates_instance(self):
        """Test that get_loyalty_score_service creates a new instance when needed."""
        # Reset the global variable
        therobotoverlord_api.services.loyalty_score_service._loyalty_score_service = (
            None
        )

        service = await get_loyalty_score_service()

        assert isinstance(service, LoyaltyScoreService)
        assert service.repository is not None
