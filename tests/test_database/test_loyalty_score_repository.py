"""Comprehensive tests for LoyaltyScoreRepository."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.loyalty_score import ContentType
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventFilters
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventOutcome
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventResponse
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreBreakdown
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreHistory
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreStats
from therobotoverlord_api.database.models.loyalty_score import ModerationEvent
from therobotoverlord_api.database.models.loyalty_score import ModerationEventType
from therobotoverlord_api.database.models.loyalty_score import UserLoyaltyProfile
from therobotoverlord_api.database.repositories.loyalty_score import (
    LoyaltyScoreRepository,
)


class MockAsyncTransaction:
    """Custom async context manager for mocking database transactions."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class MockAsyncConnection:
    """Custom async connection mock with proper transaction support."""

    def __init__(self):
        self.fetchrow = AsyncMock()
        self.fetch = AsyncMock()
        self.fetchval = AsyncMock()
        self.execute = AsyncMock()
        self._transaction = MockAsyncTransaction()

    def transaction(self):
        return self._transaction


pytestmark = pytest.mark.asyncio


@pytest.fixture
def repository():
    """Create a LoyaltyScoreRepository instance."""
    return LoyaltyScoreRepository()


@pytest.fixture
def sample_user_pk():
    """Sample user UUID."""
    return uuid4()


@pytest.fixture
def sample_content_pk():
    """Sample content UUID."""
    return uuid4()


@pytest.fixture
def sample_moderator_pk():
    """Sample moderator UUID."""
    return uuid4()


@pytest.fixture
def sample_event_pk():
    """Sample event UUID."""
    return uuid4()


@pytest.fixture
def mock_db_record():
    """Mock database record for moderation event."""
    return {
        "pk": uuid4(),
        "user_pk": uuid4(),
        "event_type": "post_moderation",
        "content_type": "post",
        "content_pk": uuid4(),
        "outcome": "approved",
        "score_delta": 5,
        "previous_score": 10,
        "new_score": 15,
        "moderator_pk": uuid4(),
        "reason": "Test reason",
        "metadata": {"test": "data"},
        "created_at": datetime.now(UTC),
    }


class TestLoyaltyScoreRepository:
    """Test cases for LoyaltyScoreRepository."""

    def test_init(self, repository):
        """Test repository initialization."""
        assert repository.table_name == "moderation_events"

    def test_record_to_model(self, repository, mock_db_record):
        """Test conversion of database record to ModerationEvent model."""
        # Create a mock record object
        mock_record = MagicMock()
        for key, value in mock_db_record.items():
            mock_record.__getitem__.return_value = value
            setattr(mock_record, key, value)

        # Override specific getitem calls
        def getitem_side_effect(key):
            return mock_db_record[key]

        mock_record.__getitem__.side_effect = getitem_side_effect

        result = repository._record_to_model(mock_record)

        assert isinstance(result, ModerationEvent)
        assert result.pk == mock_db_record["pk"]
        assert result.user_pk == mock_db_record["user_pk"]
        assert result.event_type == ModerationEventType.POST_MODERATION
        assert result.content_type == ContentType.POST
        assert result.outcome == LoyaltyEventOutcome.APPROVED
        assert result.score_delta == 5
        assert result.previous_score == 10
        assert result.new_score == 15

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_record_moderation_event_success(
        self,
        mock_get_db_connection,
        repository,
        sample_user_pk,
        sample_content_pk,
        sample_moderator_pk,
    ):
        """Test successful moderation event recording."""
        # Mock database connection and transaction
        mock_conn = MockAsyncConnection()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock current user score lookup
        mock_conn.fetchrow.return_value = {"loyalty_score": 10}

        result = await repository.record_moderation_event(
            user_pk=sample_user_pk,
            event_type=ModerationEventType.POST_MODERATION,
            content_type=ContentType.POST,
            content_pk=sample_content_pk,
            outcome=LoyaltyEventOutcome.APPROVED,
            score_delta=5,
            moderator_pk=sample_moderator_pk,
            reason="Test event",
            metadata={"test": "data"},
        )

        # Verify database calls
        assert mock_conn.fetchrow.call_count == 1
        assert (
            mock_conn.execute.call_count == 3
        )  # Update user, insert event, insert history

        # Verify returned event
        assert isinstance(result, ModerationEvent)
        assert result.user_pk == sample_user_pk
        assert result.event_type == ModerationEventType.POST_MODERATION
        assert result.outcome == LoyaltyEventOutcome.APPROVED
        assert result.score_delta == 5
        assert result.previous_score == 10
        assert result.new_score == 15

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_record_moderation_event_user_not_found(
        self, mock_get_db_connection, repository, sample_user_pk, sample_content_pk
    ):
        """Test moderation event recording when user is not found."""
        mock_conn = MockAsyncConnection()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock user not found
        mock_conn.fetchrow.return_value = None

        with pytest.raises(ValueError, match=f"User {sample_user_pk} not found"):
            await repository.record_moderation_event(
                user_pk=sample_user_pk,
                event_type=ModerationEventType.POST_MODERATION,
                content_type=ContentType.POST,
                content_pk=sample_content_pk,
                outcome=LoyaltyEventOutcome.APPROVED,
                score_delta=5,
            )

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_user_loyalty_profile_success(
        self, mock_get_db_connection, repository, sample_user_pk
    ):
        """Test successful user loyalty profile retrieval."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock user data
        mock_conn.fetchrow.return_value = {
            "username": "testuser",
            "loyalty_score": 50,
            "rank": 10,
            "percentile_rank": 0.8,
            "topic_creation_enabled": True,
        }

        # Mock other method calls
        mock_breakdown = LoyaltyScoreBreakdown(
            user_pk=sample_user_pk,
            current_score=50,
            post_score=15,
            topic_score=10,
            private_message_score=5,
            appeal_adjustments=0,
            manual_adjustments=0,
            total_approved_posts=3,
            total_rejected_posts=1,
            total_approved_topics=2,
            total_rejected_topics=0,
            total_approved_messages=1,
            total_rejected_messages=0,
            last_updated=datetime.now(UTC),
        )
        mock_events = LoyaltyEventResponse(
            events=[],
            total_count=0,
            page=1,
            page_size=50,
            has_next=False,
            filters_applied=LoyaltyEventFilters(),
        )
        repository.get_score_breakdown = AsyncMock(return_value=mock_breakdown)
        repository.get_user_events = AsyncMock(return_value=mock_events)
        repository.get_user_score_history = AsyncMock(return_value=[])
        repository._get_score_thresholds = AsyncMock(
            return_value={"topic_creation": 30, "priority": 100}
        )

        result = await repository.get_user_loyalty_profile(sample_user_pk)

        assert isinstance(result, UserLoyaltyProfile)
        assert result.user_pk == sample_user_pk
        assert result.username == "testuser"
        assert result.current_score == 50
        assert result.rank == 10
        assert result.can_create_topics is True

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_user_loyalty_profile_user_not_found(
        self, mock_get_db_connection, repository, sample_user_pk
    ):
        """Test user loyalty profile retrieval when user is not found."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_conn.fetchrow.return_value = None

        with pytest.raises(ValueError, match=f"User {sample_user_pk} not found"):
            await repository.get_user_loyalty_profile(sample_user_pk)

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_score_breakdown_success(
        self, mock_get_db_connection, repository, sample_user_pk
    ):
        """Test successful score breakdown retrieval."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_conn.fetchrow.return_value = {
            "user_pk": sample_user_pk,
            "current_score": 50,
            "post_approved_score": 20,
            "post_rejected_score": -5,
            "topic_approved_score": 15,
            "topic_rejected_score": 0,
            "message_approved_score": 10,
            "message_rejected_score": -2,
            "appeal_adjustments": 5,
            "manual_adjustments": 7,
            "total_approved_posts": 4,
            "total_rejected_posts": 1,
            "total_approved_topics": 3,
            "total_rejected_topics": 0,
            "total_approved_messages": 2,
            "total_rejected_messages": 1,
            "last_updated": datetime.now(UTC),
        }

        result = await repository.get_score_breakdown(sample_user_pk)

        assert isinstance(result, LoyaltyScoreBreakdown)
        assert result.user_pk == sample_user_pk
        assert result.current_score == 50
        assert result.post_score == 15  # 20 + (-5)
        assert result.topic_score == 15  # 15 + 0
        assert result.private_message_score == 8  # 10 + (-2)
        assert result.appeal_adjustments == 5
        assert result.manual_adjustments == 7

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_score_breakdown_user_not_found(
        self, mock_get_db_connection, repository, sample_user_pk
    ):
        """Test score breakdown retrieval when user is not found."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_conn.fetchrow.return_value = None

        with pytest.raises(ValueError, match=f"User {sample_user_pk} not found"):
            await repository.get_score_breakdown(sample_user_pk)

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_user_events_success(
        self, mock_get_db_connection, repository, sample_user_pk, mock_db_record
    ):
        """Test successful user events retrieval."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock count and data queries
        mock_conn.fetchval.return_value = 1

        # Create mock record
        mock_record = MagicMock()
        for key, value in mock_db_record.items():
            setattr(mock_record, key, value)
        mock_record.__getitem__.side_effect = lambda k: mock_db_record[k]

        mock_conn.fetch.return_value = [mock_record]

        result = await repository.get_user_events(sample_user_pk)

        assert isinstance(result, LoyaltyEventResponse)
        assert result.total_count == 1
        assert result.page == 1
        assert result.page_size == 50
        assert len(result.events) == 1
        assert result.has_next is False

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_user_events_with_filters(
        self, mock_get_db_connection, repository, sample_user_pk, mock_db_record
    ):
        """Test user events retrieval with filters."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_conn.fetchval.return_value = 1

        mock_record = MagicMock()
        for key, value in mock_db_record.items():
            setattr(mock_record, key, value)
        mock_record.__getitem__.side_effect = lambda k: mock_db_record[k]

        mock_conn.fetch.return_value = [mock_record]

        filters = LoyaltyEventFilters(
            event_type=ModerationEventType.POST_MODERATION,
            content_type=ContentType.POST,
            outcome=LoyaltyEventOutcome.APPROVED,
        )

        result = await repository.get_user_events(sample_user_pk, filters=filters)

        assert isinstance(result, LoyaltyEventResponse)
        assert result.filters_applied == filters

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_user_score_history_success(
        self, mock_get_db_connection, repository, sample_user_pk
    ):
        """Test successful user score history retrieval."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_history_record = {
            "user_pk": sample_user_pk,
            "score": 50,
            "recorded_at": datetime.now(UTC),
            "event_pk": uuid4(),
        }

        mock_record = MagicMock()
        for key, value in mock_history_record.items():
            setattr(mock_record, key, value)
        mock_record.__getitem__.side_effect = lambda k: mock_history_record[k]

        mock_conn.fetch.return_value = [mock_record]

        result = await repository.get_user_score_history(sample_user_pk, days=30)

        assert len(result) == 1
        assert isinstance(result[0], LoyaltyScoreHistory)
        assert result[0].user_pk == sample_user_pk
        assert result[0].score == 50

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_system_stats_success(self, mock_get_db_connection, repository):
        """Test successful system stats retrieval."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock stats query result
        stats_row = {
            "total_users": 100,
            "average_score": 45.5,
            "median_score": 40,
            "top_10_threshold": 80,
        }

        # Mock distribution query result
        distribution_rows = [
            {"score_range": "negative", "count": 5},
            {"score_range": "zero", "count": 10},
            {"score_range": "1-10", "count": 20},
            {"score_range": "11-50", "count": 40},
            {"score_range": "51-100", "count": 20},
            {"score_range": "100+", "count": 5},
        ]

        # Mock events query result
        events_row = {"total_events": 500}

        mock_conn.fetchrow.side_effect = [stats_row, events_row]
        # Create proper mock records for distribution - use dict directly
        mock_conn.fetch.return_value = distribution_rows

        result = await repository.get_system_stats()

        assert isinstance(result, LoyaltyScoreStats)
        assert result.total_users == 100
        assert result.average_score == 45.5
        assert result.median_score == 40
        assert result.top_10_percent_threshold == 80
        assert result.topic_creation_threshold == 80
        assert result.total_events_processed == 500
        assert len(result.score_distribution) == 6

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_system_stats_no_data(self, mock_get_db_connection, repository):
        """Test system stats retrieval when no data is available."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_conn.fetchrow.side_effect = [None, None]

        with pytest.raises(ValueError, match="Failed to retrieve system statistics"):
            await repository.get_system_stats()

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_apply_manual_adjustment_success(
        self, mock_get_db_connection, repository, sample_user_pk, sample_moderator_pk
    ):
        """Test successful manual adjustment application."""
        # Mock the record_moderation_event method
        expected_event = ModerationEvent(
            pk=uuid4(),
            user_pk=sample_user_pk,
            event_type=ModerationEventType.MANUAL_ADJUSTMENT,
            content_type=ContentType.POST,
            content_pk=uuid4(),
            outcome=LoyaltyEventOutcome.APPROVED,
            score_delta=10,
            previous_score=50,
            new_score=60,
            moderator_pk=sample_moderator_pk,
            reason="Manual adjustment",
            metadata={"admin_notes": "Test adjustment"},
            created_at=datetime.now(UTC),
        )

        repository.record_moderation_event = AsyncMock(return_value=expected_event)

        result = await repository.apply_manual_adjustment(
            user_pk=sample_user_pk,
            adjustment=10,
            reason="Manual adjustment",
            admin_notes="Test adjustment",
            admin_pk=sample_moderator_pk,
        )

        assert result == expected_event
        repository.record_moderation_event.assert_called_once()

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_recalculate_user_score_success(
        self, mock_get_db_connection, repository, sample_user_pk
    ):
        """Test successful user score recalculation."""
        mock_conn = MockAsyncConnection()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock score calculation result
        mock_conn.fetchrow.return_value = {"total_score": 75}

        result = await repository.recalculate_user_score(sample_user_pk)

        assert result == 75
        assert mock_conn.execute.call_count == 1  # Update user score

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_recalculate_user_score_no_data(
        self, mock_get_db_connection, repository, sample_user_pk
    ):
        """Test user score recalculation when no data is available."""
        mock_conn = MockAsyncConnection()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_conn.fetchrow.return_value = None

        with pytest.raises(
            ValueError, match=f"Failed to calculate score for user {sample_user_pk}"
        ):
            await repository.recalculate_user_score(sample_user_pk)

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_users_by_score_range_success(
        self, mock_get_db_connection, repository
    ):
        """Test successful users by score range retrieval."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        user_pk = uuid4()
        mock_user_record = {
            "pk": user_pk,
            "username": "testuser",
            "loyalty_score": 50,
            "rank": 10,
            "percentile_rank": 0.8,
            "topic_creation_enabled": True,
        }

        mock_record = MagicMock()
        for key, value in mock_user_record.items():
            setattr(mock_record, key, value)
        mock_record.__getitem__.side_effect = lambda k: mock_user_record[k]

        mock_conn.fetch.return_value = [mock_record]

        # Mock get_score_breakdown method
        mock_breakdown = LoyaltyScoreBreakdown(
            user_pk=user_pk,
            current_score=50,
            post_score=15,
            topic_score=10,
            private_message_score=5,
            appeal_adjustments=0,
            manual_adjustments=0,
            total_approved_posts=3,
            total_rejected_posts=1,
            total_approved_topics=2,
            total_rejected_topics=0,
            total_approved_messages=1,
            total_rejected_messages=0,
            last_updated=datetime.now(UTC),
        )
        repository.get_score_breakdown = AsyncMock(return_value=mock_breakdown)

        result = await repository.get_users_by_score_range(
            min_score=40, max_score=60, limit=10
        )

        assert len(result) == 1
        assert isinstance(result[0], UserLoyaltyProfile)
        assert result[0].user_pk == user_pk
        assert result[0].username == "testuser"
        assert result[0].current_score == 50

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_recent_events_success(
        self, mock_get_db_connection, repository, mock_db_record
    ):
        """Test successful recent events retrieval."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_record = MagicMock()
        for key, value in mock_db_record.items():
            setattr(mock_record, key, value)
        mock_record.__getitem__.side_effect = lambda k: mock_db_record[k]

        mock_conn.fetch.return_value = [mock_record]

        result = await repository.get_recent_events(limit=10)

        assert len(result) == 1
        assert isinstance(result[0], ModerationEvent)

    @patch("therobotoverlord_api.database.repositories.loyalty_score.get_db_connection")
    async def test_get_recent_events_with_filters(
        self, mock_get_db_connection, repository, mock_db_record
    ):
        """Test recent events retrieval with filters."""
        mock_conn = AsyncMock()
        mock_get_db_connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_get_db_connection.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_record = MagicMock()
        for key, value in mock_db_record.items():
            setattr(mock_record, key, value)
        mock_record.__getitem__.side_effect = lambda k: mock_db_record[k]

        mock_conn.fetch.return_value = [mock_record]

        filters = LoyaltyEventFilters(
            event_type=ModerationEventType.POST_MODERATION,
            outcome=LoyaltyEventOutcome.APPROVED,
        )

        result = await repository.get_recent_events(filters=filters, limit=5)

        assert len(result) == 1
        assert isinstance(result[0], ModerationEvent)

    async def test_get_score_thresholds(self, repository):
        """Test score thresholds retrieval."""
        # Mock get_system_stats method
        mock_stats = LoyaltyScoreStats(
            total_users=100,
            average_score=45.5,
            median_score=40,
            score_distribution={},
            top_10_percent_threshold=80,
            topic_creation_threshold=80,
            total_events_processed=500,
            last_updated=datetime.now(UTC),
        )

        repository.get_system_stats = AsyncMock(return_value=mock_stats)

        result = await repository._get_score_thresholds()

        assert isinstance(result, dict)
        assert "topic_creation" in result
        assert "priority_moderation" in result
        assert "extended_appeals" in result
        assert result["topic_creation"] == 80
        assert result["priority_moderation"] == 500
        assert result["extended_appeals"] == 1000
