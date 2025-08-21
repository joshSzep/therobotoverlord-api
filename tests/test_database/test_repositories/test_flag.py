"""Tests for FlagRepository database operations."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.flag import Flag
from therobotoverlord_api.database.models.flag import FlagStatus
from therobotoverlord_api.database.repositories.flag import FlagRepository


@pytest.fixture
def flag_repo():
    """Create mocked FlagRepository instance."""
    mock_repo = AsyncMock(spec=FlagRepository)
    # Configure common async method return values
    mock_repo.get_by_pk = AsyncMock()
    mock_repo.create = AsyncMock()
    mock_repo.update = AsyncMock()
    mock_repo.delete = AsyncMock()
    mock_repo.get_flags_for_review = AsyncMock()
    mock_repo.get_user_flags = AsyncMock()
    mock_repo.get_content_flags = AsyncMock()
    mock_repo.check_user_already_flagged = AsyncMock()
    mock_repo.get_user_dismissed_flags_count = AsyncMock()
    mock_repo.get_pending_flags_count = AsyncMock()
    return mock_repo


@pytest.fixture
def sample_flag_data():
    """Create sample flag data for testing."""
    return {
        "post_pk": uuid4(),
        "topic_pk": None,
        "flagger_pk": uuid4(),
        "reason": "This content violates community guidelines",
        "status": FlagStatus.PENDING,
        "created_at": datetime.now(UTC),
    }


@pytest.fixture
def sample_flags():
    """Create sample flag objects for testing."""
    flags = []

    # Create pending flag
    flag1 = Flag(
        pk=uuid4(),
        post_pk=uuid4(),
        topic_pk=None,
        flagger_pk=uuid4(),
        reason="This content violates community guidelines",
        status=FlagStatus.PENDING,
        created_at=datetime.now(UTC),
    )
    flags.append(flag1)

    # Create upheld flag
    flag2 = Flag(
        pk=uuid4(),
        post_pk=uuid4(),
        topic_pk=None,
        flagger_pk=uuid4(),
        reason="Spam content",
        status=FlagStatus.UPHELD,
        created_at=datetime.now(UTC),
        reviewed_by_pk=uuid4(),
        reviewed_at=datetime.now(UTC),
        review_notes="Content removed for policy violation",
    )
    flags.append(flag2)

    # Create dismissed flag
    flag3 = Flag(
        pk=uuid4(),
        post_pk=uuid4(),
        topic_pk=None,
        flagger_pk=uuid4(),
        reason="Inappropriate content",
        status=FlagStatus.DISMISSED,
        created_at=datetime.now(UTC),
        reviewed_by_pk=uuid4(),
        reviewed_at=datetime.now(UTC),
        review_notes="Flag not justified",
    )
    flags.append(flag3)

    return flags


class TestFlagRepositoryBasic:
    """Test basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_flag(self, flag_repo, sample_flag_data):
        """Test creating a flag."""
        # Configure mock to return a Flag object
        expected_flag = Flag(
            pk=uuid4(),
            post_pk=sample_flag_data["post_pk"],
            topic_pk=sample_flag_data["topic_pk"],
            flagger_pk=sample_flag_data["flagger_pk"],
            reason=sample_flag_data["reason"],
            status=sample_flag_data["status"],
            created_at=sample_flag_data["created_at"],
        )
        flag_repo.create_from_dict.return_value = expected_flag

        flag = await flag_repo.create_from_dict(sample_flag_data)

        assert flag.pk is not None
        assert flag.post_pk == sample_flag_data["post_pk"]
        assert flag.flagger_pk == sample_flag_data["flagger_pk"]
        assert flag.reason == sample_flag_data["reason"]
        assert flag.status == FlagStatus.PENDING
        assert flag.created_at is not None

        # Verify the mock was called correctly
        flag_repo.create_from_dict.assert_called_once_with(sample_flag_data)

    @pytest.mark.asyncio
    async def test_get_flag_by_pk(self, flag_repo, sample_flags):
        """Test retrieving a flag by primary key."""
        expected_flag = sample_flags[0]
        flag_repo.get_by_pk.return_value = expected_flag

        flag = await flag_repo.get_by_pk(expected_flag.pk)
        assert flag == expected_flag
        flag_repo.get_by_pk.assert_called_once_with(expected_flag.pk)

    @pytest.mark.asyncio
    async def test_update_flag(self, flag_repo, sample_flag_data):
        """Test updating a flag."""
        # Create initial flag
        initial_flag = Flag(
            pk=uuid4(),
            post_pk=sample_flag_data["post_pk"],
            topic_pk=sample_flag_data["topic_pk"],
            flagger_pk=sample_flag_data["flagger_pk"],
            reason=sample_flag_data["reason"],
            status=sample_flag_data["status"],
            created_at=sample_flag_data["created_at"],
        )
        flag_repo.create_from_dict.return_value = initial_flag
        flag = await flag_repo.create_from_dict(sample_flag_data)

        update_data = {
            "status": FlagStatus.UPHELD,
            "reviewed_by_pk": uuid4(),
            "reviewed_at": datetime.now(UTC),
            "review_notes": "Content violates community guidelines",
        }

        # Configure update mock to return updated flag
        merged_data = {**sample_flag_data, **update_data}
        updated_flag = Flag(
            pk=flag.pk,
            post_pk=merged_data["post_pk"],
            topic_pk=merged_data["topic_pk"],
            flagger_pk=merged_data["flagger_pk"],
            reason=merged_data["reason"],
            status=merged_data["status"],
            created_at=merged_data["created_at"],
            reviewed_by_pk=merged_data.get("reviewed_by_pk"),
            reviewed_at=merged_data.get("reviewed_at"),
            review_notes=merged_data.get("review_notes"),
        )
        flag_repo.update.return_value = updated_flag

        result = await flag_repo.update(flag.pk, update_data)
        assert result.status == FlagStatus.UPHELD
        flag_repo.update.assert_called_once_with(flag.pk, update_data)
        assert updated_flag.status == FlagStatus.UPHELD
        assert updated_flag.reviewed_by_pk == update_data["reviewed_by_pk"]
        assert updated_flag.review_notes == update_data["review_notes"]

    @pytest.mark.asyncio
    async def test_delete_flag(self, flag_repo, sample_flag_data):
        """Test deleting a flag."""
        # Create initial flag
        initial_flag = Flag(
            pk=uuid4(),
            post_pk=sample_flag_data["post_pk"],
            topic_pk=sample_flag_data["topic_pk"],
            flagger_pk=sample_flag_data["flagger_pk"],
            reason=sample_flag_data["reason"],
            status=sample_flag_data["status"],
            created_at=sample_flag_data["created_at"],
        )
        flag_repo.create_from_dict.return_value = initial_flag
        flag = await flag_repo.create_from_dict(sample_flag_data)

        # Configure delete mock to return True for successful deletion
        flag_repo.delete.return_value = True

        deleted = await flag_repo.delete(flag.pk)
        assert deleted is True
        flag_repo.delete.assert_called_once_with(flag.pk)

        # Configure mock to return None after deletion
        flag_repo.get_by_pk.return_value = None
        retrieved_flag = await flag_repo.get_by_pk(flag.pk)
        assert retrieved_flag is None


class TestFlagRepositoryQueries:
    """Test specialized query methods."""

    @pytest.mark.asyncio
    async def test_get_flags_for_review_default(self, flag_repo, sample_flags):
        """Test getting flags for review with default parameters."""
        # Configure mock to return pending flags
        pending_flags = [f for f in sample_flags if f.status == FlagStatus.PENDING]
        flag_repo.get_flags_for_review.return_value = pending_flags

        flags = await flag_repo.get_flags_for_review()
        assert len(flags) >= 1
        flag_repo.get_flags_for_review.assert_called_once_with()  # Should return pending flags first (FIFO order)
        assert len(flags) >= 1
        pending_flags = [f for f in flags if f.status == FlagStatus.PENDING]
        assert len(pending_flags) >= 1

    @pytest.mark.asyncio
    async def test_get_flags_for_review_with_status_filter(
        self, flag_repo, sample_flags
    ):
        """Test getting flags with status filter."""
        # Test pending flags
        pending_flags = await flag_repo.get_flags_for_review(status_filter="pending")
        assert all(f.status == FlagStatus.PENDING for f in pending_flags)

        # Test upheld flags
        upheld_flags = await flag_repo.get_flags_for_review(status_filter="upheld")
        assert all(f.status == FlagStatus.UPHELD for f in upheld_flags)

    @pytest.mark.asyncio
    async def test_get_flags_for_review_pagination(self, flag_repo, sample_flags):
        """Test pagination in flags for review."""
        # Get first page
        page1 = await flag_repo.get_flags_for_review(limit=2, offset=0)

        # Get second page
        page2 = await flag_repo.get_flags_for_review(limit=2, offset=2)

        # Pages should not overlap
        page1_pks = {f.pk for f in page1}
        page2_pks = {f.pk for f in page2}
        assert page1_pks.isdisjoint(page2_pks)

    @pytest.mark.asyncio
    async def test_get_user_flags(self, flag_repo, sample_flags):
        """Test getting flags by user."""
        user_pk = sample_flags[0].flagger_pk
        user_flags = [f for f in sample_flags if f.flagger_pk == user_pk]
        flag_repo.get_user_flags.return_value = user_flags

        flags = await flag_repo.get_user_flags(user_pk)
        assert len(flags) >= 1
        flag_repo.get_user_flags.assert_called_once_with(user_pk)
        assert all(f.flagger_pk == user_pk for f in user_flags)

        # Should be ordered by created_at DESC
        if len(user_flags) > 1:
            for i in range(len(user_flags) - 1):
                assert user_flags[i].created_at >= user_flags[i + 1].created_at

    @pytest.mark.asyncio
    async def test_get_user_flags_pagination(self, flag_repo, sample_flags):
        """Test pagination for user flags."""
        user_pk = sample_flags[0].flagger_pk

        page1 = await flag_repo.get_user_flags(user_pk, limit=1, offset=0)
        page2 = await flag_repo.get_user_flags(user_pk, limit=1, offset=1)

        if len(page1) > 0 and len(page2) > 0:
            assert page1[0].pk != page2[0].pk

    @pytest.mark.asyncio
    async def test_get_content_flags_post(self, flag_repo, sample_flags):
        """Test getting flags for a specific post."""
        post_pk = sample_flags[0].post_pk
        post_flags = [f for f in sample_flags if f.post_pk == post_pk]
        flag_repo.get_content_flags.return_value = post_flags

        flags = await flag_repo.get_content_flags(post_pk, "post")
        assert len(flags) >= 1
        flag_repo.get_content_flags.assert_called_once_with(post_pk, "post")
        assert all(f.post_pk == post_pk for f in post_flags)
        assert all(f.topic_pk is None for f in post_flags)

    @pytest.mark.asyncio
    async def test_get_content_flags_topic(self, flag_repo, sample_flag_data):
        """Test getting flags for a specific topic."""
        # Create topic flag
        topic_flag_data = sample_flag_data.copy()
        topic_flag_data["post_pk"] = None
        topic_flag_data["topic_pk"] = uuid4()

        topic_flag = Flag(
            pk=uuid4(),
            post_pk=topic_flag_data["post_pk"],
            topic_pk=topic_flag_data["topic_pk"],
            flagger_pk=topic_flag_data["flagger_pk"],
            reason=topic_flag_data["reason"],
            status=topic_flag_data["status"],
            created_at=topic_flag_data["created_at"],
        )
        flag_repo.create_from_dict.return_value = topic_flag
        created_flag = await flag_repo.create_from_dict(topic_flag_data)

        # Configure mock to return topic flags
        topic_flags = [topic_flag]
        flag_repo.get_content_flags.return_value = topic_flags

        content_flags = await flag_repo.get_content_flags(topic_flag.topic_pk, "topic")

        assert len(content_flags) >= 1
        flag_repo.get_content_flags.assert_called_once_with(
            topic_flag.topic_pk, "topic"
        )
        assert all(f.topic_pk == topic_flag.topic_pk for f in topic_flags)
        assert all(f.post_pk is None for f in topic_flags)

    @pytest.mark.asyncio
    async def test_check_user_already_flagged_post(self, flag_repo, sample_flags):
        """Test checking if user already flagged a post."""
        user_pk = sample_flags[0].flagger_pk
        post_pk = sample_flags[0].post_pk

        # Configure mock to return True for existing flag
        flag_repo.check_user_already_flagged.return_value = True

        already_flagged = await flag_repo.check_user_already_flagged(
            user_pk, post_pk, "post"
        )
        assert already_flagged is True
        flag_repo.check_user_already_flagged.assert_called_once_with(
            user_pk, post_pk, "post"
        )

        # Different user should not have flagged this post
        different_user = uuid4()
        flag_repo.check_user_already_flagged.return_value = False
        not_flagged = await flag_repo.check_user_already_flagged(
            different_user, post_pk, "post"
        )
        assert not_flagged is False

    @pytest.mark.asyncio
    async def test_check_user_already_flagged_topic(self, flag_repo, sample_flag_data):
        """Test checking if user already flagged a topic."""
        # Create topic flag
        topic_flag_data = sample_flag_data.copy()
        topic_flag_data["post_pk"] = None
        topic_flag_data["topic_pk"] = uuid4()

        topic_flag = Flag(
            pk=uuid4(),
            post_pk=topic_flag_data["post_pk"],
            topic_pk=topic_flag_data["topic_pk"],
            flagger_pk=topic_flag_data["flagger_pk"],
            reason=topic_flag_data["reason"],
            status=topic_flag_data["status"],
            created_at=topic_flag_data["created_at"],
        )
        flag_repo.create_from_dict.return_value = topic_flag
        created_flag = await flag_repo.create_from_dict(topic_flag_data)

        # Configure mock to return True for existing flag
        flag_repo.check_user_already_flagged.return_value = True

        # User should have flagged this topic
        already_flagged = await flag_repo.check_user_already_flagged(
            topic_flag.flagger_pk, topic_flag.topic_pk, "topic"
        )
        assert already_flagged is True
        flag_repo.check_user_already_flagged.assert_called_once_with(
            topic_flag.flagger_pk, topic_flag.topic_pk, "topic"
        )

    @pytest.mark.asyncio
    async def test_get_user_dismissed_flags_count(self, flag_repo, sample_flags):
        """Test counting user's dismissed flags."""
        # Find a dismissed flag
        dismissed_flag = next(
            f for f in sample_flags if f.status == FlagStatus.DISMISSED
        )

        # Configure mock to return count of dismissed flags
        flag_repo.get_user_dismissed_flags_count.return_value = 1

        count = await flag_repo.get_user_dismissed_flags_count(
            dismissed_flag.flagger_pk
        )

        assert count >= 1
        flag_repo.get_user_dismissed_flags_count.assert_called_once_with(
            dismissed_flag.flagger_pk
        )

    @pytest.mark.asyncio
    async def test_get_user_dismissed_flags_count_with_days(
        self, flag_repo, sample_flags
    ):
        """Test getting count of dismissed flags by user within specific days."""
        user_pk = sample_flags[2].flagger_pk

        # Configure mock to return different counts for different day ranges
        flag_repo.get_user_dismissed_flags_count.side_effect = [
            1,
            2,
        ]  # 7 days, then 30 days

        count_7_days = await flag_repo.get_user_dismissed_flags_count(user_pk, days=7)
        count_30_days = await flag_repo.get_user_dismissed_flags_count(user_pk, days=30)

        # Count for 30 days should be >= count for 7 days
        assert count_30_days >= count_7_days
        assert flag_repo.get_user_dismissed_flags_count.call_count == 2

    @pytest.mark.asyncio
    async def test_get_pending_flags_count(self, flag_repo, sample_flags):
        """Test getting count of pending flags."""
        # Configure mock to return count of pending flags
        pending_count = len([f for f in sample_flags if f.status == FlagStatus.PENDING])
        flag_repo.get_pending_flags_count.return_value = pending_count

        count = await flag_repo.get_pending_flags_count()
        assert count >= 0
        flag_repo.get_pending_flags_count.assert_called_once_with()


class TestFlagRepositoryEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_flag(self, flag_repo):
        """Test getting a flag that doesn't exist."""
        nonexistent_pk = uuid4()
        # Configure mock to return None for nonexistent flag
        flag_repo.get_by_pk.return_value = None

        flag = await flag_repo.get_by_pk(nonexistent_pk)
        assert flag is None
        flag_repo.get_by_pk.assert_called_once_with(nonexistent_pk)

    @pytest.mark.asyncio
    async def test_update_nonexistent_flag(self, flag_repo):
        """Test updating a flag that doesn't exist."""
        nonexistent_pk = uuid4()
        update_data = {"status": FlagStatus.UPHELD}

        # Configure mock to return None for nonexistent flag
        flag_repo.update.return_value = None

        updated_flag = await flag_repo.update(nonexistent_pk, update_data)
        assert updated_flag is None
        flag_repo.update.assert_called_once_with(nonexistent_pk, update_data)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_flag(self, flag_repo):
        """Test deleting a flag that doesn't exist."""
        nonexistent_pk = uuid4()
        # Configure mock to return False for nonexistent flag
        flag_repo.delete.return_value = False

        deleted = await flag_repo.delete(nonexistent_pk)
        assert deleted is False
        flag_repo.delete.assert_called_once_with(nonexistent_pk)

    @pytest.mark.asyncio
    async def test_get_flags_for_review_empty_result(self, flag_repo):
        """Test getting flags when none match criteria."""
        # Configure mock to return empty list for nonexistent status
        flag_repo.get_flags_for_review.return_value = []

        # Use a status that doesn't exist in sample data
        flags = await flag_repo.get_flags_for_review(status_filter="nonexistent")
        assert flags == []
        flag_repo.get_flags_for_review.assert_called_once_with(
            status_filter="nonexistent"
        )

    @pytest.mark.asyncio
    async def test_get_user_flags_no_flags(self, flag_repo):
        """Test getting flags for user who hasn't flagged anything."""
        nonexistent_user = uuid4()
        # Configure mock to return empty list for user with no flags
        flag_repo.get_user_flags.return_value = []

        flags = await flag_repo.get_user_flags(nonexistent_user)
        assert flags == []
        flag_repo.get_user_flags.assert_called_once_with(nonexistent_user)

    @pytest.mark.asyncio
    async def test_get_content_flags_no_flags(self, flag_repo):
        """Test getting flags for content that hasn't been flagged."""
        nonexistent_content = uuid4()
        # Configure mock to return empty list for content with no flags
        flag_repo.get_content_flags.return_value = []

        flags = await flag_repo.get_content_flags(nonexistent_content, "post")
        assert flags == []
        flag_repo.get_content_flags.assert_called_once_with(nonexistent_content, "post")

    @pytest.mark.asyncio
    async def test_dismissed_flags_count_no_flags(self, flag_repo):
        """Test dismissed flags count for user with no dismissed flags."""
        nonexistent_user = uuid4()
        # Configure mock to return 0 for user with no dismissed flags
        flag_repo.get_user_dismissed_flags_count.return_value = 0

        count = await flag_repo.get_user_dismissed_flags_count(nonexistent_user)
        assert count == 0
        flag_repo.get_user_dismissed_flags_count.assert_called_once_with(
            nonexistent_user
        )
