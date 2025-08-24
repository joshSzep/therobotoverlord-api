"""Comprehensive tests for AppealRepository."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.appeal import Appeal
from therobotoverlord_api.database.models.appeal import AppealCreate
from therobotoverlord_api.database.models.appeal import AppealEligibility
from therobotoverlord_api.database.models.appeal import AppealStats
from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal import AppealType
from therobotoverlord_api.database.models.appeal import AppealUpdate
from therobotoverlord_api.database.models.appeal import AppealWithContent
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.repositories.appeal import AppealRepository


class TestAppealRepository:
    """Test class for AppealRepository."""

    @pytest.fixture
    def repository(self):
        """Create AppealRepository instance."""
        return AppealRepository()

    @pytest.fixture
    def mock_appeal_create(self):
        """Mock AppealCreate data."""
        return AppealCreate(
            content_type=ContentType.POST,
            content_pk=uuid4(),
            appeal_type=AppealType.POST_REMOVAL,
            reason="This post was removed unfairly",
            evidence="I have evidence that this was not spam",
        )

    @pytest.fixture
    def mock_appeal_record(self):
        """Mock appeal database record."""
        return {
            "pk": uuid4(),
            "appellant_pk": uuid4(),
            "content_type": "post",
            "content_pk": uuid4(),
            "appeal_type": "post_removal",
            "status": "pending",
            "reason": "Test reason",
            "evidence": "Test evidence",
            "reviewed_by": None,
            "review_notes": None,
            "submitted_at": datetime.now(UTC),
            "reviewed_at": None,
            "previous_appeals_count": 0,
            "priority_score": 50,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    @pytest.mark.asyncio
    async def test_record_to_model(self, repository, mock_appeal_record):
        """Test converting database record to Appeal model."""
        appeal = repository._record_to_model(type("Record", (), mock_appeal_record)())

        assert isinstance(appeal, Appeal)
        assert appeal.pk == mock_appeal_record["pk"]
        assert appeal.appellant_pk == mock_appeal_record["appellant_pk"]
        assert appeal.appeal_type == AppealType.POST_REMOVAL

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.appeal.AppealRepository._get_user_appeals_count"
    )
    @patch(
        "therobotoverlord_api.database.repositories.appeal.AppealRepository._calculate_priority_score"
    )
    @patch(
        "therobotoverlord_api.database.repositories.appeal.AppealRepository.create_from_dict"
    )
    async def test_create_appeal(
        self, mock_create, mock_priority, mock_count, repository, mock_appeal_create
    ):
        """Test creating a new appeal."""
        appellant_pk = uuid4()
        mock_count.return_value = 2
        mock_priority.return_value = 75
        mock_appeal = Appeal(
            pk=uuid4(),
            appellant_pk=appellant_pk,
            content_type=ContentType.POST,
            content_pk=mock_appeal_create.content_pk,
            appeal_type=AppealType.POST_REMOVAL,
            reason=mock_appeal_create.reason,
            evidence=mock_appeal_create.evidence,
            submitted_at=datetime.now(UTC),
            previous_appeals_count=2,
            priority_score=75,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_create.return_value = mock_appeal

        result = await repository.create_appeal(mock_appeal_create, appellant_pk)

        mock_count.assert_called_once_with(appellant_pk)
        mock_priority.assert_called_once_with(appellant_pk, AppealType.POST_REMOVAL)
        mock_create.assert_called_once()
        assert result == mock_appeal

    @pytest.mark.asyncio
    @patch(
        "therobotoverlord_api.database.repositories.appeal.AppealRepository.update_from_dict"
    )
    async def test_update_appeal(self, mock_update, repository):
        """Test updating an existing appeal."""
        appeal_pk = uuid4()
        appeal_update = AppealUpdate(
            status=AppealStatus.UNDER_REVIEW,
            review_notes="Under review",
            decision_reason="Decision pending",
        )
        mock_appeal = Appeal(
            pk=appeal_pk,
            appellant_pk=uuid4(),
            content_type=ContentType.POST,
            content_pk=uuid4(),
            appeal_type=AppealType.POST_REMOVAL,
            reason="Test reason",
            status=AppealStatus.UNDER_REVIEW,
            review_notes="Under review",
            submitted_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_update.return_value = mock_appeal

        result = await repository.update_appeal(appeal_pk, appeal_update)

        mock_update.assert_called_once_with(
            appeal_pk,
            {
                "status": "under_review",
                "review_notes": "Under review",
                "decision_reason": "Decision pending",
            },
        )
        assert result == mock_appeal

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_get_user_appeals(self, mock_get_connection, repository):
        """Test getting user appeals with content details."""
        user_pk = uuid4()
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        mock_records = [
            {
                "pk": uuid4(),
                "appellant_pk": user_pk,
                "content_type": "post",
                "content_pk": uuid4(),
                "appeal_type": "post_removal",
                "status": "pending",
                "reason": "Test reason",
                "evidence": "Test evidence",
                "appellant_username": "testuser",
                "reviewer_username": None,
                "content_title": None,
                "content_text": "Test post content",
                "submitted_at": datetime.now(UTC),
                "reviewed_at": None,
                "reviewed_by": None,
                "review_notes": None,
                "decision_reason": None,
                "previous_appeals_count": 0,
                "priority_score": 50,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        ]
        mock_connection.fetch.return_value = mock_records

        result = await repository.get_user_appeals(
            user_pk, status=AppealStatus.PENDING, limit=10, offset=0
        )

        assert len(result) == 1
        assert isinstance(result[0], AppealWithContent)
        assert result[0].appellant_username == "testuser"
        mock_connection.fetch.assert_called_once()

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_get_appeals_queue_priority_order(
        self, mock_get_connection, repository
    ):
        """Test getting appeals queue with priority ordering."""
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        mock_records = [
            {
                "pk": uuid4(),
                "appellant_pk": uuid4(),
                "content_type": "post",
                "content_pk": uuid4(),
                "appeal_type": "post_removal",
                "status": "pending",
                "reason": "High priority appeal",
                "evidence": None,
                "appellant_username": "user1",
                "reviewer_username": None,
                "content_title": None,
                "content_text": "Test content",
                "submitted_at": datetime.now(UTC),
                "reviewed_at": None,
                "reviewed_by": None,
                "review_notes": None,
                "decision_reason": None,
                "previous_appeals_count": 0,
                "priority_score": 100,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        ]
        mock_connection.fetch.return_value = mock_records

        result = await repository.get_appeals_queue(
            status=AppealStatus.PENDING, priority_order=True, limit=25, offset=0
        )

        assert len(result) == 1
        assert isinstance(result[0], AppealWithContent)
        assert result[0].priority_score == 100
        mock_connection.fetch.assert_called_once()

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_get_appeals_queue_chronological_order(
        self, mock_get_connection, repository
    ):
        """Test getting appeals queue with chronological ordering."""
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetch.return_value = []

        await repository.get_appeals_queue(
            status=AppealStatus.PENDING, priority_order=False, limit=25, offset=0
        )

        # Verify the query contains chronological ordering
        call_args = mock_connection.fetch.call_args[0]
        query = call_args[0]
        assert "ORDER BY a.submitted_at ASC" in query
        assert "ORDER BY a.priority_score DESC" not in query

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_check_appeal_eligibility_eligible(
        self, mock_get_connection, repository
    ):
        """Test appeal eligibility check when user is eligible."""
        user_pk = uuid4()
        content_pk = uuid4()
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        # Mock database responses for eligible user
        mock_connection.fetchrow.return_value = {"loyalty_score": 500}  # High loyalty
        mock_connection.fetchval.side_effect = [
            0,
            1,
            None,
            True,
        ]  # No existing appeals, 1 daily, no cooldown, valid age

        result = await repository.check_appeal_eligibility(
            user_pk, ContentType.POST, content_pk
        )

        assert isinstance(result, AppealEligibility)
        assert result.eligible is True
        assert (
            result.max_appeals_per_day == 6
        )  # Base 3 + loyalty bonus 3 (500+ gets +2, 1000+ gets +3)
        assert result.appeals_used_today == 1
        assert result.appeals_remaining == 5

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_check_appeal_eligibility_content_already_appealed(
        self, mock_get_connection, repository
    ):
        """Test appeal eligibility when content already appealed."""
        user_pk = uuid4()
        content_pk = uuid4()
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        # Mock database responses - content already appealed
        mock_connection.fetchrow.return_value = {"loyalty_score": 100}
        mock_connection.fetchval.side_effect = [
            1,
            0,
            None,
            True,
        ]  # 1 existing appeal for content

        result = await repository.check_appeal_eligibility(
            user_pk, ContentType.POST, content_pk
        )

        assert result.eligible is False
        assert result.reason == "Content has already been appealed"

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_check_appeal_eligibility_daily_limit_reached(
        self, mock_get_connection, repository
    ):
        """Test appeal eligibility when daily limit reached."""
        user_pk = uuid4()
        content_pk = uuid4()
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        # Mock database responses - daily limit reached
        mock_connection.fetchrow.return_value = {"loyalty_score": 0}
        mock_connection.fetchval.side_effect = [
            0,
            3,
            None,
            True,
        ]  # 0 content appeals, 3 daily (limit is 3)

        result = await repository.check_appeal_eligibility(
            user_pk, ContentType.POST, content_pk
        )

        assert result.eligible is False
        assert "Daily appeal limit reached" in result.reason

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_check_appeal_eligibility_cooldown_active(
        self, mock_get_connection, repository
    ):
        """Test appeal eligibility when cooldown is active."""
        user_pk = uuid4()
        content_pk = uuid4()
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        # Mock database responses - recent denial within cooldown
        recent_denial = datetime.now(UTC) - timedelta(
            hours=1
        )  # 1 hour ago, within 24h cooldown
        mock_connection.fetchrow.return_value = {"loyalty_score": 100}
        mock_connection.fetchval.side_effect = [0, 1, recent_denial, True]

        result = await repository.check_appeal_eligibility(
            user_pk, ContentType.POST, content_pk
        )

        assert result.eligible is False
        assert result.reason == "Appeal cooldown period active"
        assert result.cooldown_expires_at is not None

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_check_appeal_eligibility_content_too_old(
        self, mock_get_connection, repository
    ):
        """Test appeal eligibility when content is too old."""
        user_pk = uuid4()
        content_pk = uuid4()
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        # Mock database responses - content too old
        mock_connection.fetchrow.return_value = {"loyalty_score": 100}
        mock_connection.fetchval.side_effect = [
            0,
            1,
            None,
            False,
        ]  # Content age invalid

        result = await repository.check_appeal_eligibility(
            user_pk, ContentType.POST, content_pk
        )

        assert result.eligible is False
        assert "older than" in result.reason

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_get_appeal_statistics(self, mock_get_connection, repository):
        """Test getting appeal statistics."""
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection

        # Mock statistics data
        stats_record = {
            "total_pending": 5,
            "total_under_review": 2,
            "total_sustained": 10,
            "total_denied": 15,
            "total_withdrawn": 1,
            "total_count": 33,
            "total_today": 3,
            "avg_review_hours": 24.5,
        }

        type_records = [
            {"appeal_type": "post_removal", "count": 20},
            {"appeal_type": "topic_rejection", "count": 10},
        ]

        appellant_records = [
            {"username": "user1", "appeal_count": 5},
            {"username": "user2", "appeal_count": 3},
        ]

        reviewer_records = [
            {
                "username": "mod1",
                "reviews_completed": 15,
                "sustained_count": 5,
                "denied_count": 10,
            }
        ]

        mock_connection.fetchrow.return_value = stats_record
        mock_connection.fetch.side_effect = [
            type_records,
            appellant_records,
            reviewer_records,
        ]

        result = await repository.get_appeal_statistics()

        assert isinstance(result, AppealStats)
        assert result.total_pending == 5
        assert result.total_under_review == 2
        assert result.average_review_time_hours == 24.5
        assert result.appeals_by_type["post_removal"] == 20
        assert len(result.top_appellants) == 2
        assert len(result.reviewer_stats) == 1

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.AppealRepository.count")
    async def test_count_user_appeals_with_status(self, mock_count, repository):
        """Test counting user appeals with status filter."""
        user_pk = uuid4()
        mock_count.return_value = 3

        result = await repository.count_user_appeals(user_pk, AppealStatus.PENDING)

        mock_count.assert_called_once_with(
            "appellant_pk = $1 AND status = $2", [user_pk, "pending"]
        )
        assert result == 3

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.AppealRepository.count")
    async def test_count_user_appeals_all_statuses(self, mock_count, repository):
        """Test counting all user appeals."""
        user_pk = uuid4()
        mock_count.return_value = 7

        result = await repository.count_user_appeals(user_pk)

        mock_count.assert_called_once_with("appellant_pk = $1", [user_pk])
        assert result == 7

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.AppealRepository.count")
    async def test_get_user_appeals_count(self, mock_count, repository):
        """Test getting user appeals count (private method)."""
        user_pk = uuid4()
        mock_count.return_value = 5

        result = await repository._get_user_appeals_count(user_pk)

        mock_count.assert_called_once_with("appellant_pk = $1", [user_pk])
        assert result == 5

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_calculate_priority_score_high_loyalty(
        self, mock_get_connection, repository
    ):
        """Test calculating priority score for high loyalty user."""
        user_pk = uuid4()
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetchrow.return_value = {"loyalty_score": 500}  # High loyalty

        result = await repository._calculate_priority_score(
            user_pk, AppealType.SANCTION
        )

        # Base priority 100 * (1 + min(500/100, 5.0)) = 100 * 6 = 600
        assert result == 600

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_calculate_priority_score_low_loyalty(
        self, mock_get_connection, repository
    ):
        """Test calculating priority score for low loyalty user."""
        user_pk = uuid4()
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetchrow.return_value = {"loyalty_score": 50}

        result = await repository._calculate_priority_score(
            user_pk, AppealType.POST_REJECTION
        )

        # Base priority 25 * (1 + 50/100) = 25 * 1.5 = 37.5 -> 37
        assert result == 37

    @pytest.mark.asyncio
    @patch("therobotoverlord_api.database.repositories.appeal.get_db_connection")
    async def test_calculate_priority_score_no_user(
        self, mock_get_connection, repository
    ):
        """Test calculating priority score when user not found."""
        user_pk = uuid4()
        mock_connection = AsyncMock()
        mock_get_connection.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetchrow.return_value = None  # User not found

        result = await repository._calculate_priority_score(
            user_pk, AppealType.TOPIC_REJECTION
        )

        # Base priority 75 * (1 + 0) = 75
        assert result == 75

    def test_get_content_age_query_topic(self, repository):
        """Test getting content age query for topic."""
        query = repository._get_content_age_query(ContentType.TOPIC)

        assert "topics" in query
        assert "created_at" in query
        assert "INTERVAL '%s days'" in query

    def test_get_content_age_query_post(self, repository):
        """Test getting content age query for post."""
        query = repository._get_content_age_query(ContentType.POST)

        assert "posts" in query
        assert "created_at" in query

    def test_get_content_age_query_private_message(self, repository):
        """Test getting content age query for private message."""
        query = repository._get_content_age_query(ContentType.PRIVATE_MESSAGE)

        assert "private_messages" in query
        assert "sent_at" in query

    def test_get_content_age_query_invalid_type(self, repository):
        """Test getting content age query for invalid content type."""

        # Test with a mock content type that doesn't match any case
        class MockContentType:
            pass

        query = repository._get_content_age_query(MockContentType())

        assert query == "SELECT FALSE as valid"
