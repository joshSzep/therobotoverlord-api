"""Tests for FlagService business logic."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.flag import Flag
from therobotoverlord_api.database.models.flag import FlagCreate
from therobotoverlord_api.database.models.flag import FlagStatus
from therobotoverlord_api.database.models.flag import FlagUpdate
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.topic import Topic
from therobotoverlord_api.services.flag_service import FlagService


@pytest.fixture
def mock_flag_repo():
    """Mock FlagRepository."""
    return AsyncMock()


@pytest.fixture
def mock_post_repo():
    """Mock PostRepository."""
    return AsyncMock()


@pytest.fixture
def mock_topic_repo():
    """Mock TopicRepository."""
    return AsyncMock()


@pytest.fixture
def flag_service(mock_flag_repo, mock_post_repo, mock_topic_repo):
    """Create FlagService instance with mocked dependencies for testing."""
    service = FlagService(
        flag_repo=mock_flag_repo, post_repo=mock_post_repo, topic_repo=mock_topic_repo
    )

    return service


@pytest.fixture
def sample_post():
    """Create sample post for testing."""
    return Post(
        pk=uuid4(),
        topic_pk=uuid4(),
        author_pk=uuid4(),
        content="Sample post content",
        post_number=1,
        status=ContentStatus.APPROVED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        submitted_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_topic():
    """Create sample topic for testing."""
    return Topic(
        pk=uuid4(),
        author_pk=uuid4(),
        title="Sample Topic",
        description="Sample topic description",
        status=TopicStatus.APPROVED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_flag():
    """Create sample flag for testing."""

    def _create_flag():
        return Flag(
            pk=uuid4(),
            post_pk=uuid4(),
            topic_pk=None,
            flagger_pk=uuid4(),
            reason="This content violates guidelines",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    return _create_flag()


class TestFlagServiceCreateFlag:
    """Test flag creation logic."""

    @pytest.mark.asyncio
    async def test_create_flag_for_post_success(
        self, flag_service, mock_flag_repo, mock_post_repo, sample_post
    ):
        """Test successfully creating a flag for a post."""
        # Setup mocks
        mock_post_repo.get_by_pk.return_value = sample_post
        mock_flag_repo.check_user_already_flagged = AsyncMock(return_value=False)
        mock_flag_repo.create_from_dict.return_value = Flag(
            pk=uuid4(),
            post_pk=sample_post.pk,
            flagger_pk=uuid4(),
            reason="Inappropriate content",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_data = FlagCreate(post_pk=sample_post.pk, reason="Inappropriate content")
        flagger_pk = uuid4()

        result = await flag_service.create_flag(flag_data, flagger_pk)

        # Verify post was checked
        mock_post_repo.get_by_pk.assert_called_once_with(sample_post.pk)

        # Verify duplicate check was performed
        mock_flag_repo.check_user_already_flagged.assert_called_once_with(
            flagger_pk, sample_post.pk, "post"
        )

        # Verify flag was created
        mock_flag_repo.create_from_dict.assert_called_once()
        create_args = mock_flag_repo.create_from_dict.call_args[0][0]
        assert create_args["post_pk"] == sample_post.pk
        assert create_args["flagger_pk"] == flagger_pk
        assert create_args["reason"] == "Inappropriate content"

    @pytest.mark.asyncio
    async def test_create_flag_for_topic_success(
        self, flag_service, mock_flag_repo, mock_topic_repo, sample_topic
    ):
        """Test successfully creating a flag for a topic."""
        # Setup mocks
        mock_topic_repo.get_by_pk.return_value = sample_topic
        mock_flag_repo.check_user_already_flagged = AsyncMock(return_value=False)
        mock_flag_repo.create_from_dict.return_value = Flag(
            pk=uuid4(),
            topic_pk=sample_topic.pk,
            flagger_pk=uuid4(),
            reason="Inappropriate topic",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_data = FlagCreate(topic_pk=sample_topic.pk, reason="Inappropriate topic")
        flagger_pk = uuid4()

        result = await flag_service.create_flag(flag_data, flagger_pk)

        # Verify topic was checked
        mock_topic_repo.get_by_pk.assert_called_once_with(sample_topic.pk)

        # Verify flag was created
        mock_flag_repo.create_from_dict.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_flag_no_content_specified(self, flag_service):
        """Test error when neither post nor topic is specified."""
        flag_data = FlagCreate(reason="Invalid flag")
        flagger_pk = uuid4()

        with pytest.raises(ValueError, match="Must specify either post_pk or topic_pk"):
            await flag_service.create_flag(flag_data, flagger_pk)

    @pytest.mark.asyncio
    async def test_create_flag_both_content_specified(self, flag_service):
        """Test error when both post and topic are specified."""
        flag_data = FlagCreate(post_pk=uuid4(), topic_pk=uuid4(), reason="Invalid flag")
        flagger_pk = uuid4()

        with pytest.raises(ValueError, match="Cannot flag both post and topic"):
            await flag_service.create_flag(flag_data, flagger_pk)

    @pytest.mark.asyncio
    async def test_create_flag_post_not_found(self, flag_service, mock_post_repo):
        """Test error when post doesn't exist."""
        mock_post_repo.get_by_pk.return_value = None

        flag_data = FlagCreate(post_pk=uuid4(), reason="Flag for nonexistent post")
        flagger_pk = uuid4()

        with pytest.raises(ValueError, match="Post not found"):
            await flag_service.create_flag(flag_data, flagger_pk)

    @pytest.mark.asyncio
    async def test_create_flag_topic_not_found(self, flag_service, mock_topic_repo):
        """Test error when topic doesn't exist."""
        mock_topic_repo.get_by_pk.return_value = None

        flag_data = FlagCreate(topic_pk=uuid4(), reason="Flag for nonexistent topic")
        flagger_pk = uuid4()

        with pytest.raises(ValueError, match="Topic not found"):
            await flag_service.create_flag(flag_data, flagger_pk)

    @pytest.mark.asyncio
    async def test_create_flag_self_flagging_prevention(
        self, flag_service, mock_post_repo, sample_post
    ):
        """Test prevention of self-flagging."""
        mock_post_repo.get_by_pk.return_value = sample_post

        flag_data = FlagCreate(post_pk=sample_post.pk, reason="Self flag attempt")
        # Use same user as post author
        flagger_pk = sample_post.author_pk

        with pytest.raises(ValueError, match="Cannot flag your own content"):
            await flag_service.create_flag(flag_data, flagger_pk)

    @pytest.mark.asyncio
    async def test_create_flag_duplicate_prevention(
        self, flag_service, mock_flag_repo, mock_post_repo, sample_post
    ):
        """Test prevention of duplicate flags."""
        flagger_pk = uuid4()

        # Setup mocks - simulate existing flag by same user
        mock_post_repo.get_by_pk.return_value = sample_post
        mock_flag_repo.get_content_flags.return_value = [
            Flag(
                pk=uuid4(),
                post_pk=sample_post.pk,
                flagger_pk=flagger_pk,
                reason="Previous flag",
                status=FlagStatus.PENDING,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]

        flag_data = FlagCreate(post_pk=sample_post.pk, reason="Duplicate flag attempt")

        with pytest.raises(ValueError, match="You have already flagged this content"):
            await flag_service.create_flag(flag_data, flagger_pk)


class TestFlagServiceReviewFlag:
    """Test flag review logic."""

    @pytest.mark.asyncio
    async def test_review_flag_upheld_post(
        self, flag_service, mock_flag_repo, mock_post_repo, sample_post, sample_flag
    ):
        """Test reviewing a flag as upheld for a post."""
        # Setup mocks
        test_flag = Flag(
            pk=uuid4(),
            post_pk=sample_post.pk,
            topic_pk=None,
            flagger_pk=uuid4(),
            reason="Test flag",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_flag_repo.get_by_pk.return_value = test_flag
        mock_flag_repo.update.return_value = test_flag
        mock_post_repo.get_by_pk.return_value = sample_post
        mock_post_repo.update.return_value = sample_post

        flag_update = FlagUpdate(
            status=FlagStatus.UPHELD, review_notes="Clear policy violation"
        )
        reviewer_pk = uuid4()

        result = await flag_service.review_flag(test_flag.pk, flag_update, reviewer_pk)

        # Verify flag was updated
        mock_flag_repo.update.assert_called_once()
        update_args = mock_flag_repo.update.call_args[0][1]
        assert update_args["status"] == FlagStatus.UPHELD
        assert update_args["reviewed_by_pk"] == reviewer_pk
        assert update_args["review_notes"] == "Clear policy violation"

        # Verify post was hidden
        mock_post_repo.update.assert_called_once()
        call_args = mock_post_repo.update.call_args
        assert call_args[0][0] == sample_post.pk  # First argument is the pk
        assert (
            call_args[0][1].status == ContentStatus.REJECTED
        )  # Second argument is PostUpdate model

    @pytest.mark.asyncio
    async def test_review_flag_upheld_topic(
        self, flag_service, mock_flag_repo, mock_topic_repo, sample_topic, sample_flag
    ):
        """Test reviewing a flag as upheld for a topic."""
        # Setup mocks
        sample_flag.post_pk = None
        sample_flag.topic_pk = sample_topic.pk
        sample_flag.status = FlagStatus.PENDING  # Ensure flag is pending
        mock_flag_repo.get_by_pk.return_value = sample_flag
        mock_flag_repo.update.return_value = sample_flag
        mock_topic_repo.get_by_pk.return_value = sample_topic
        mock_topic_repo.update.return_value = sample_topic

        flag_update = FlagUpdate(status=FlagStatus.UPHELD, review_notes=None)
        reviewer_pk = uuid4()

        await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

        # Verify topic was hidden
        mock_topic_repo.update.assert_called_once()
        call_args = mock_topic_repo.update.call_args
        assert call_args[0][0] == sample_topic.pk  # First argument is the pk
        assert (
            call_args[0][1].status == TopicStatus.REJECTED
        )  # Second argument is TopicUpdate model

    @pytest.mark.asyncio
    async def test_review_flag_dismissed(
        self, flag_service, mock_flag_repo, sample_flag
    ):
        """Test reviewing a flag as dismissed."""
        sample_flag.status = FlagStatus.PENDING  # Ensure flag is pending
        mock_flag_repo.get_by_pk.return_value = sample_flag
        mock_flag_repo.update.return_value = sample_flag
        mock_flag_repo.get_user_dismissed_flags_count.return_value = 1

        flag_update = FlagUpdate(
            status=FlagStatus.DISMISSED, review_notes="Flag not justified"
        )
        reviewer_pk = uuid4()

        result = await flag_service.review_flag(
            sample_flag.pk, flag_update, reviewer_pk
        )

        # Verify flag was updated
        mock_flag_repo.update.assert_called_once()

        # Verify frivolous flagging check was performed
        mock_flag_repo.get_user_dismissed_flags_count.assert_called_once_with(
            sample_flag.flagger_pk, days=30
        )

    @pytest.mark.asyncio
    async def test_review_flag_not_found(self, flag_service, mock_flag_repo):
        """Test error when flag doesn't exist."""
        mock_flag_repo.get_by_pk.return_value = None

        flag_update = FlagUpdate(status=FlagStatus.UPHELD, review_notes=None)
        reviewer_pk = uuid4()

        with pytest.raises(ValueError, match="Flag not found"):
            await flag_service.review_flag(uuid4(), flag_update, reviewer_pk)

    @pytest.mark.asyncio
    async def test_review_flag_already_reviewed(
        self, flag_service, mock_flag_repo, sample_flag
    ):
        """Test error when flag is already reviewed."""
        sample_flag.status = FlagStatus.UPHELD
        mock_flag_repo.get_by_pk.return_value = sample_flag

        flag_update = FlagUpdate(status=FlagStatus.DISMISSED, review_notes=None)
        reviewer_pk = uuid4()

        with pytest.raises(ValueError, match="Flag has already been reviewed"):
            await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

    @pytest.mark.asyncio
    async def test_review_flag_update_failed(
        self, flag_service, mock_flag_repo, sample_flag
    ):
        """Test error when flag update fails."""
        sample_flag.status = FlagStatus.PENDING  # Ensure flag is pending
        mock_flag_repo.get_by_pk.return_value = sample_flag
        mock_flag_repo.update.return_value = None  # Update failed

        flag_update = FlagUpdate(status=FlagStatus.UPHELD, review_notes=None)
        reviewer_pk = uuid4()

        with pytest.raises(ValueError, match="Failed to update flag"):
            await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)


class TestFlagServiceFrivolousDetection:
    """Test frivolous flagging detection."""

    @pytest.mark.asyncio
    async def test_frivolous_flagging_detection(
        self, flag_service, mock_flag_repo, sample_flag
    ):
        """Test detection of frivolous flagging pattern."""
        sample_flag.status = FlagStatus.PENDING  # Ensure flag is pending
        mock_flag_repo.get_by_pk.return_value = sample_flag
        mock_flag_repo.update.return_value = sample_flag
        mock_flag_repo.get_user_dismissed_flags_count.return_value = 3  # Threshold

        flag_update = FlagUpdate(status=FlagStatus.DISMISSED, review_notes=None)
        reviewer_pk = uuid4()

        # Should not raise error but should detect pattern
        await flag_service.review_flag(sample_flag.pk, flag_update, reviewer_pk)

        # Verify frivolous check was performed
        mock_flag_repo.get_user_dismissed_flags_count.assert_called_once_with(
            sample_flag.flagger_pk, days=30
        )


class TestFlagServiceStatistics:
    """Test flag statistics methods."""

    @pytest.mark.asyncio
    async def test_get_user_flag_stats(self, flag_service, mock_flag_repo):
        """Test getting user flag statistics."""
        user_pk = uuid4()
        mock_flags = [
            Flag(
                pk=uuid4(),
                post_pk=uuid4(),
                flagger_pk=user_pk,
                reason="Flag 1",
                status=FlagStatus.PENDING,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            Flag(
                pk=uuid4(),
                post_pk=uuid4(),
                flagger_pk=user_pk,
                reason="Flag 2",
                status=FlagStatus.UPHELD,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            Flag(
                pk=uuid4(),
                post_pk=uuid4(),
                flagger_pk=user_pk,
                reason="Flag 3",
                status=FlagStatus.DISMISSED,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]
        mock_flag_repo.get_user_flags.return_value = mock_flags

        stats = await flag_service.get_user_flag_stats(user_pk)

        assert stats["total_flags"] == 3
        assert stats["pending"] == 1
        assert stats["upheld"] == 1
        assert stats["dismissed"] == 1

    @pytest.mark.asyncio
    async def test_get_content_flag_summary(self, flag_service, mock_flag_repo):
        """Test getting content flag summary."""
        content_pk = uuid4()
        mock_flags = [
            Flag(
                pk=uuid4(),
                post_pk=content_pk,
                flagger_pk=uuid4(),
                reason="Flag 1",
                status=FlagStatus.PENDING,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            Flag(
                pk=uuid4(),
                post_pk=content_pk,
                flagger_pk=uuid4(),
                reason="Flag 2",
                status=FlagStatus.UPHELD,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]
        mock_flag_repo.get_content_flags.return_value = mock_flags

        summary = await flag_service.get_content_flag_summary(content_pk, "post")

        assert summary["total_flags"] == 2
        assert summary["pending"] == 1
        assert summary["upheld"] == 1
        assert summary["dismissed"] == 0

    @pytest.mark.asyncio
    async def test_get_user_flag_stats_empty(self, flag_service, mock_flag_repo):
        """Test getting stats for user with no flags."""
        user_pk = uuid4()
        mock_flag_repo.get_user_flags.return_value = []

        stats = await flag_service.get_user_flag_stats(user_pk)

        assert stats["total_flags"] == 0
        assert stats["pending"] == 0
        assert stats["upheld"] == 0
        assert stats["dismissed"] == 0


class TestFlagServiceDependencyInjection:
    """Test dependency injection."""

    @pytest.mark.asyncio
    async def test_get_flag_service(self, flag_service):
        """Test getting flag service instance."""
        assert flag_service is not None
        assert isinstance(flag_service, FlagService)
        assert flag_service.flag_repo is not None
        assert flag_service.post_repo is not None
        assert flag_service.topic_repo is not None
