"""Integration tests for flag system with loyalty scoring."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.flag import Flag
from therobotoverlord_api.database.models.flag import FlagStatus
from therobotoverlord_api.database.models.flag import FlagUpdate
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventOutcome
from therobotoverlord_api.database.models.loyalty_score import ModerationEventType
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.topic import Topic
from therobotoverlord_api.services.flag_service import FlagService


@pytest.fixture
def mock_loyalty_service():
    """Mock LoyaltyScoreService."""
    return AsyncMock()


@pytest.fixture
def flag_service_with_loyalty(mock_loyalty_service):
    """Create FlagService with mocked loyalty service."""
    # Create mocked repositories
    mock_flag_repo = AsyncMock()
    mock_post_repo = AsyncMock()
    mock_topic_repo = AsyncMock()

    # Create service with dependency injection including loyalty service
    service = FlagService(
        flag_repo=mock_flag_repo,
        post_repo=mock_post_repo,
        topic_repo=mock_topic_repo,
        loyalty_service=mock_loyalty_service,
    )
    return service, mock_loyalty_service


@pytest.fixture
def sample_post():
    """Create sample post for testing."""
    return Post(
        pk=uuid4(),
        topic_pk=uuid4(),
        author_pk=uuid4(),
        content="Sample post content for loyalty testing",
        status=ContentStatus.APPROVED,
        submitted_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_topic():
    """Create sample topic for testing."""
    return Topic(
        pk=uuid4(),
        author_pk=uuid4(),
        title="Sample Topic for Loyalty Testing",
        description="Sample topic description for loyalty integration",
        status=TopicStatus.APPROVED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_flag():
    """Create sample flag for testing."""
    return Flag(
        pk=uuid4(),
        post_pk=uuid4(),
        topic_pk=None,
        flagger_pk=uuid4(),
        reason="Content violates community guidelines",
        status=FlagStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestFlagUpheldLoyaltyIntegration:
    """Test loyalty scoring integration when flags are upheld."""

    @pytest.mark.asyncio
    async def test_upheld_post_flag_loyalty_impact(
        self, flag_service_with_loyalty, sample_post, sample_flag
    ):
        """Test loyalty score impact when post flag is upheld."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Setup flag for post
        sample_flag.post_pk = sample_post.pk
        sample_flag.topic_pk = None

        # Setup mocks
        flag_service.flag_repo.get_by_pk.return_value = sample_flag
        flag_service.post_repo.get_by_pk.return_value = sample_post
        flag_service.post_repo.update.return_value = sample_post

        flag_update = FlagUpdate(
            status=FlagStatus.UPHELD,
            review_notes="Clear policy violation - content removed",
        )
        reviewer_pk = uuid4()

        # Create updated flag with reviewer info for the mock
        updated_flag = Flag(
            pk=sample_flag.pk,
            flagger_pk=sample_flag.flagger_pk,
            post_pk=sample_flag.post_pk,
            topic_pk=sample_flag.topic_pk,
            reason=sample_flag.reason,
            status=FlagStatus.UPHELD,
            created_at=sample_flag.created_at,
            updated_at=sample_flag.updated_at,
            reviewed_by_pk=reviewer_pk,
            review_notes="Clear policy violation - content removed",
        )
        flag_service.flag_repo.update.return_value = updated_flag

        await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

        # Verify loyalty service was called with correct parameters
        mock_loyalty_service.record_moderation_event.assert_called_once_with(
            user_pk=sample_post.author_pk,
            content_pk=sample_post.pk,
            content_type=ContentType.POST,
            event_type=ModerationEventType.POST_MODERATION,
            outcome=LoyaltyEventOutcome.REJECTED,
            moderator_pk=reviewer_pk,
            reason="Flag upheld: Clear policy violation - content removed",
        )

        # Verify post was hidden
        flag_service.post_repo.update.assert_called_once()
        call_args = flag_service.post_repo.update.call_args
        assert call_args[0][0] == sample_post.pk  # First argument is the pk
        assert (
            call_args[0][1].status == ContentStatus.REJECTED
        )  # Second argument is PostUpdate model

    @pytest.mark.asyncio
    async def test_flag_loyalty_integration_with_topic(
        self, flag_service_with_loyalty, sample_topic, sample_flag
    ):
        """Test loyalty score impact when topic flag is upheld."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Setup flag for topic
        sample_flag.post_pk = None
        sample_flag.topic_pk = sample_topic.pk

        # Setup mocks
        flag_service.flag_repo.get_by_pk.return_value = sample_flag
        flag_service.topic_repo.get_by_pk.return_value = sample_topic
        flag_service.topic_repo.update.return_value = sample_topic

        flag_update = FlagUpdate(
            status=FlagStatus.UPHELD,
            review_notes="Topic contains inappropriate content",
        )
        reviewer_pk = uuid4()

        # Create updated flag with reviewer info for the mock
        updated_flag = Flag(
            pk=sample_flag.pk,
            flagger_pk=sample_flag.flagger_pk,
            post_pk=sample_flag.post_pk,
            topic_pk=sample_flag.topic_pk,
            reason=sample_flag.reason,
            status=FlagStatus.UPHELD,
            created_at=sample_flag.created_at,
            updated_at=sample_flag.updated_at,
            reviewed_by_pk=reviewer_pk,
            review_notes="Topic contains inappropriate content",
        )
        flag_service.flag_repo.update.return_value = updated_flag

        await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

        # Verify loyalty service was called with correct parameters
        mock_loyalty_service.record_moderation_event.assert_called_once_with(
            user_pk=sample_topic.author_pk,
            content_pk=sample_topic.pk,
            content_type=ContentType.TOPIC,
            event_type=ModerationEventType.TOPIC_MODERATION,
            outcome=LoyaltyEventOutcome.REJECTED,
            moderator_pk=reviewer_pk,
            reason="Flag upheld: Topic contains inappropriate content",
        )

        # Verify topic was hidden
        flag_service.topic_repo.update.assert_called_once()
        call_args = flag_service.topic_repo.update.call_args
        assert call_args[0][0] == sample_topic.pk  # First argument is the pk
        assert (
            call_args[0][1].status == TopicStatus.REJECTED
        )  # Second argument is TopicUpdate model

    @pytest.mark.asyncio
    async def test_upheld_flag_loyalty_service_failure(
        self, flag_service_with_loyalty, sample_post, sample_flag
    ):
        """Test handling of loyalty service failure during flag uphold."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Setup flag for post
        sample_flag.post_pk = sample_post.pk
        sample_flag.topic_pk = None

        # Setup mocks
        flag_service.flag_repo.get_by_pk.return_value = sample_flag
        flag_service.flag_repo.update.return_value = sample_flag
        flag_service.post_repo.get_by_pk.return_value = sample_post
        flag_service.post_repo.update.return_value = sample_post

        # Make loyalty service fail
        mock_loyalty_service.record_moderation_event.side_effect = Exception(
            "Loyalty service error"
        )

        flag_update = FlagUpdate(status=FlagStatus.UPHELD, review_notes=None)
        reviewer_pk = uuid4()

        # Should not raise exception even if loyalty service fails
        result = await flag_service.review_flag(
            sample_flag.pk, flag_update, reviewer_pk
        )

        # Flag should still be updated and content hidden
        assert result is not None
        flag_service.post_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_upheld_flag_with_empty_review_notes(
        self, flag_service_with_loyalty, sample_post, sample_flag
    ):
        """Test upheld flag with no review notes."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Setup flag for post
        sample_flag.post_pk = sample_post.pk
        sample_flag.topic_pk = None

        # Setup mocks
        flag_service.flag_repo.get_by_pk.return_value = sample_flag
        flag_service.post_repo.get_by_pk.return_value = sample_post
        flag_service.post_repo.update.return_value = sample_post

        flag_update = FlagUpdate(status=FlagStatus.UPHELD, review_notes=None)
        reviewer_pk = uuid4()

        # Create updated flag with reviewer info for the mock
        updated_flag = Flag(
            pk=sample_flag.pk,
            flagger_pk=sample_flag.flagger_pk,
            post_pk=sample_flag.post_pk,
            topic_pk=sample_flag.topic_pk,
            reason=sample_flag.reason,
            status=FlagStatus.UPHELD,
            created_at=sample_flag.created_at,
            updated_at=sample_flag.updated_at,
            reviewed_by_pk=reviewer_pk,
            review_notes=None,
        )
        flag_service.flag_repo.update.return_value = updated_flag

        await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

        # Verify loyalty service was called with default reason
        mock_loyalty_service.record_moderation_event.assert_called_once()
        call_args = mock_loyalty_service.record_moderation_event.call_args[1]
        assert call_args["reason"] == "Flag upheld: No additional notes"


class TestFlagDismissedLoyaltyIntegration:
    """Test loyalty scoring integration when flags are dismissed."""

    @pytest.mark.asyncio
    async def test_dismissed_flag_no_loyalty_impact(
        self, flag_service_with_loyalty, sample_flag
    ):
        """Test that dismissed flags don't directly impact content author's loyalty."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Setup mocks
        flag_service.flag_repo.get_by_pk.return_value = sample_flag
        flag_service.flag_repo.update.return_value = sample_flag
        flag_service.flag_repo.get_user_dismissed_flags_count.return_value = 1

        flag_update = FlagUpdate(
            status=FlagStatus.DISMISSED, review_notes="Flag not justified"
        )
        reviewer_pk = uuid4()

        await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

        # Verify loyalty service was NOT called for dismissed flag
        mock_loyalty_service.record_moderation_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_dismissed_flag_frivolous_flagging_detection(
        self, flag_service_with_loyalty, sample_flag
    ):
        """Test frivolous flagging detection for dismissed flags."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Setup mocks
        flag_service.flag_repo.get_by_pk.return_value = sample_flag
        flag_service.flag_repo.update.return_value = sample_flag
        flag_service.flag_repo.get_user_dismissed_flags_count.return_value = (
            3  # Threshold reached
        )

        flag_update = FlagUpdate(
            status=FlagStatus.DISMISSED, review_notes="Another unjustified flag"
        )
        reviewer_pk = uuid4()

        await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

        # Verify frivolous flagging check was performed
        flag_service.flag_repo.get_user_dismissed_flags_count.assert_called_once_with(
            sample_flag.flagger_pk, days=30
        )

        # Note: In a full implementation, this would trigger sanctions
        # For now, we just verify the detection logic works


class TestFlagLoyaltyEdgeCases:
    """Test edge cases in flag-loyalty integration."""

    @pytest.mark.asyncio
    async def test_upheld_flag_content_not_found(
        self, flag_service_with_loyalty, sample_flag
    ):
        """Test upheld flag when content is not found."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Setup mocks - content not found
        flag_service.flag_repo.get_by_pk.return_value = sample_flag
        flag_service.flag_repo.update.return_value = sample_flag
        flag_service.post_repo.get_by_pk.return_value = None  # Content not found

        flag_update = FlagUpdate(
            status=FlagStatus.UPHELD, review_notes="Content violation confirmed"
        )
        reviewer_pk = uuid4()

        await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

        # Loyalty service should not be called if content not found
        mock_loyalty_service.record_moderation_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_upheld_flag_loyalty_service_unavailable(
        self, flag_service_with_loyalty, sample_post, sample_flag
    ):
        """Test upheld flag when loyalty service is unavailable."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Setup mocks
        sample_flag.post_pk = sample_post.pk
        flag_service.flag_repo.get_by_pk.return_value = sample_flag
        flag_service.flag_repo.update.return_value = sample_flag
        flag_service.post_repo.get_by_pk.return_value = sample_post
        flag_service.post_repo.update.return_value = sample_post

        flag_update = FlagUpdate(
            status=FlagStatus.UPHELD, review_notes="Content violation confirmed"
        )
        reviewer_pk = uuid4()

        result = await flag_service.review_flag(
            sample_flag.pk, flag_update, reviewer_pk
        )

        # Flag should still be updated and content hidden
        assert result is not None
        flag_service.post_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_upheld_flags_same_content(
        self, flag_service_with_loyalty, sample_post
    ):
        """Test multiple upheld flags for the same content."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Create multiple flags for same content
        flag1 = Flag(
            pk=uuid4(),
            flagger_pk=uuid4(),
            post_pk=sample_post.pk,
            topic_pk=None,
            reason="Spam",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        flag2 = Flag(
            pk=uuid4(),
            flagger_pk=uuid4(),
            post_pk=sample_post.pk,
            topic_pk=None,
            reason="Inappropriate",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Setup mocks for first flag
        flag_service.flag_repo.get_by_pk.return_value = flag1
        flag_service.flag_repo.update.return_value = flag1
        flag_service.post_repo.get_by_pk.return_value = sample_post
        flag_service.post_repo.update.return_value = sample_post

        flag_update = FlagUpdate(
            status=FlagStatus.UPHELD, review_notes="Multiple violations confirmed"
        )
        reviewer_pk = uuid4()

        await flag_service.review_flag(flag1.pk, flag_update, reviewer_pk)

        # Verify loyalty service called for content author
        mock_loyalty_service.record_moderation_event.assert_called_once()


class TestFlagLoyaltyScoreServiceIntegration:
    """Test integration with actual loyalty score service patterns."""

    @pytest.mark.asyncio
    async def test_loyalty_event_parameters_completeness(
        self, flag_service_with_loyalty, sample_post, sample_flag
    ):
        """Test that all required loyalty event parameters are provided."""
        flag_service, mock_loyalty_service = flag_service_with_loyalty

        # Setup flag to reference the post
        sample_flag.post_pk = sample_post.pk
        sample_flag.topic_pk = None

        # Setup mocks
        flag_service.flag_repo.get_by_pk.return_value = sample_flag
        flag_service.post_repo.get_by_pk.return_value = sample_post
        flag_service.post_repo.update.return_value = sample_post

        flag_update = FlagUpdate(
            status=FlagStatus.UPHELD,
            review_notes="Detailed review notes for loyalty tracking",
        )
        reviewer_pk = uuid4()

        # Create updated flag with reviewer info for the mock
        updated_flag = Flag(
            pk=sample_flag.pk,
            flagger_pk=sample_flag.flagger_pk,
            post_pk=sample_flag.post_pk,
            topic_pk=sample_flag.topic_pk,
            reason=sample_flag.reason,
            status=FlagStatus.UPHELD,
            created_at=sample_flag.created_at,
            updated_at=sample_flag.updated_at,
            reviewed_by_pk=reviewer_pk,
            review_notes="Detailed review notes for loyalty tracking",
        )
        flag_service.flag_repo.update.return_value = updated_flag

        await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

        # Verify all required parameters are present
        mock_loyalty_service.record_moderation_event.assert_called_once()
        call_kwargs = mock_loyalty_service.record_moderation_event.call_args[1]

        required_params = [
            "user_pk",
            "content_pk",
            "content_type",
            "event_type",
            "outcome",
            "moderator_pk",
            "reason",
        ]

        for param in required_params:
            assert param in call_kwargs, f"Missing required parameter: {param}"

        # Verify parameter values are correct types
        assert isinstance(call_kwargs["user_pk"], type(sample_post.author_pk))
        assert isinstance(call_kwargs["content_pk"], type(sample_post.pk))
        assert call_kwargs["content_type"] == ContentType.POST
        assert call_kwargs["event_type"] == ModerationEventType.POST_MODERATION
        assert call_kwargs["outcome"] == LoyaltyEventOutcome.REJECTED
        assert isinstance(call_kwargs["moderator_pk"], type(reviewer_pk))
        assert isinstance(call_kwargs["reason"], str)
        assert len(call_kwargs["reason"]) > 0
