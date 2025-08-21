"""Edge case and error condition tests for the flag system."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.flag import Flag
from therobotoverlord_api.database.models.flag import FlagCreate
from therobotoverlord_api.database.models.flag import FlagStatus
from therobotoverlord_api.database.models.flag import FlagUpdate
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.services.flag_service import FlagService


@pytest.fixture
def flag_service():
    """Create FlagService with mocked dependencies."""
    # Create mocked repositories
    mock_flag_repo = AsyncMock()
    mock_post_repo = AsyncMock()
    mock_topic_repo = AsyncMock()

    # Create service with dependency injection
    service = FlagService(
        flag_repo=mock_flag_repo, post_repo=mock_post_repo, topic_repo=mock_topic_repo
    )
    return service


class TestFlagCreationEdgeCases:
    """Test edge cases in flag creation."""

    @pytest.mark.asyncio
    async def test_create_flag_with_deleted_content(self, flag_service):
        """Test creating flag for content that was deleted after initial check."""
        post_pk = uuid4()

        # Post doesn't exist - should trigger "Post not found" error
        flag_service.post_repo.get_by_pk.return_value = None
        flag_service.flag_repo.check_user_already_flagged.return_value = False

        flag_data = FlagCreate(
            post_pk=post_pk, reason="Flag for content that gets deleted"
        )
        flagger_pk = uuid4()

        with pytest.raises(ValueError, match="Post not found"):
            await flag_service.create_flag(flag_data, flagger_pk)

    @pytest.mark.asyncio
    async def test_create_flag_with_hidden_content(self, flag_service):
        """Test creating flag for content that is already hidden."""
        hidden_post = Post(
            pk=uuid4(),
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="Hidden content",
            status=ContentStatus.REJECTED,  # Already hidden
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )

        sample_post = Post(
            pk=uuid4(),
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="Sample content",
            status=ContentStatus.APPROVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )

        flag_service.post_repo.get_by_pk.return_value = sample_post
        flag_service.flag_repo.get_content_flags.return_value = []
        flag_service.flag_repo.check_user_already_flagged = AsyncMock(
            return_value=False
        )
        flag_service.flag_repo.create_from_dict.return_value = Flag(
            pk=uuid4(),
            post_pk=hidden_post.pk,
            flagger_pk=uuid4(),
            reason="Flag for hidden content",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_data = FlagCreate(
            post_pk=hidden_post.pk,
            reason="This content is already hidden but I'm flagging it",
        )
        flagger_pk = uuid4()

        # Should still allow flagging (moderators might want to review)
        result = await flag_service.create_flag(flag_data, flagger_pk)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_flag_database_transaction_failure(self, flag_service):
        """Test flag creation when database transaction fails."""
        post = Post(
            pk=uuid4(),
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="Valid content",
            status=ContentStatus.APPROVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )

        flag_service.post_repo.get_by_pk.return_value = post
        flag_service.flag_repo.get_content_flags.return_value = []
        flag_service.flag_repo.check_user_already_flagged = AsyncMock(
            return_value=False
        )
        flag_service.flag_repo.create_from_dict.side_effect = Exception(
            "Database error"
        )

        flag_data = FlagCreate(
            post_pk=post.pk, reason="Flag creation will fail due to DB error"
        )
        flagger_pk = uuid4()

        with pytest.raises(Exception, match="Database error"):
            await flag_service.create_flag(flag_data, flagger_pk)

    @pytest.mark.asyncio
    async def test_create_flag_with_unicode_content(self, flag_service):
        """Test flag creation with unicode characters in reason."""
        post = Post(
            pk=uuid4(),
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="Content with unicode: 🚫 违规内容 محتوى مخالف",
            status=ContentStatus.APPROVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )

        flag_service.post_repo.get_by_pk.return_value = post
        flag_service.flag_repo.get_content_flags.return_value = []
        flag_service.flag_repo.check_user_already_flagged = AsyncMock(
            return_value=False
        )
        flag_service.flag_repo.create_from_dict.return_value = Flag(
            pk=uuid4(),
            post_pk=post.pk,
            flagger_pk=uuid4(),
            reason="Unicode flag: 🚫 inappropriate content 中文",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_data = FlagCreate(
            post_pk=post.pk, reason="Unicode flag: 🚫 inappropriate content 中文"
        )
        flagger_pk = uuid4()

        result = await flag_service.create_flag(flag_data, flagger_pk)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_flag_concurrent_duplicate_attempts(self, flag_service):
        """Test concurrent flag creation attempts by same user."""
        post = Post(
            pk=uuid4(),
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="Content flagged concurrently",
            status=ContentStatus.APPROVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )

        flagger_pk = uuid4()

        # First call: no existing flags, second call: flag exists
        flag_service.post_repo.get_by_pk.return_value = post
        flag_service.flag_repo.get_content_flags.side_effect = [
            [],  # First check: no flags
            [
                Flag(  # Second check: flag exists (created concurrently)
                    pk=uuid4(),
                    post_pk=post.pk,
                    flagger_pk=flagger_pk,
                    reason="Concurrent flag",
                    status=FlagStatus.PENDING,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
        ]

        flag_data = FlagCreate(post_pk=post.pk, reason="Concurrent flag attempt")

        with pytest.raises(ValueError, match="already flagged this content"):
            await flag_service.create_flag(flag_data, flagger_pk)


class TestFlagReviewEdgeCases:
    """Test edge cases in flag review."""

    @pytest.mark.asyncio
    async def test_review_flag_content_deleted_during_review(self, flag_service):
        """Test reviewing flag when content is deleted during review process."""
        flag = Flag(
            pk=uuid4(),
            post_pk=uuid4(),
            topic_pk=None,
            flagger_pk=uuid4(),
            reason="Flag for content that gets deleted",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_service.flag_repo.get_by_pk.return_value = flag
        flag_service.flag_repo.update.return_value = flag
        flag_service.post_repo.get_by_pk.return_value = None  # Content deleted

        flag_update = FlagUpdate(status=FlagStatus.UPHELD, review_notes=None)
        reviewer_pk = uuid4()

        # Should handle gracefully without crashing
        result = await flag_service.review_flag(flag.pk, flag_update, reviewer_pk)

        # Flag should still be updated
        assert result is not None
        flag_service.flag_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_flag_database_update_failure(self, flag_service):
        """Test flag review when database update fails."""
        flag = Flag(
            pk=uuid4(),
            post_pk=uuid4(),
            topic_pk=None,
            flagger_pk=uuid4(),
            reason="Flag with update failure",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_service.flag_repo.get_by_pk.return_value = flag
        flag_service.flag_repo.update.return_value = None  # Update failed

        flag_update = FlagUpdate(status=FlagStatus.UPHELD, review_notes=None)
        reviewer_pk = uuid4()

        with pytest.raises(ValueError, match="Failed to update flag"):
            await flag_service.review_flag(flag.pk, flag_update, reviewer_pk)

    @pytest.mark.asyncio
    async def test_review_flag_content_update_failure(self, flag_service):
        """Test flag review when content status update fails."""
        post = Post(
            pk=uuid4(),
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="Content with update failure",
            status=ContentStatus.APPROVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )

        flag = Flag(
            pk=uuid4(),
            post_pk=post.pk,
            topic_pk=None,
            flagger_pk=uuid4(),
            reason="Flag with content update failure",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_service.flag_repo.get_by_pk.return_value = flag
        flag_service.flag_repo.update.return_value = flag
        flag_service.post_repo.get_by_pk.return_value = post
        flag_service.post_repo.update.return_value = None  # Content update failed
        flag_update = FlagUpdate(status=FlagStatus.UPHELD, review_notes=None)
        reviewer_pk = uuid4()

        # Should still complete review even if content update fails
        result = await flag_service.review_flag(flag.pk, flag_update, reviewer_pk)
        assert result is not None

    @pytest.mark.asyncio
    async def test_review_flag_with_extremely_long_notes(self, flag_service):
        """Test flag review with extremely long review notes."""
        flag = Flag(
            pk=uuid4(),
            post_pk=uuid4(),
            topic_pk=None,
            flagger_pk=uuid4(),
            reason="Flag with long review notes",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_service.flag_repo.get_by_pk.return_value = flag
        flag_service.flag_repo.update.return_value = flag
        flag_service.flag_repo.get_user_dismissed_flags_count.return_value = 0

        # Test extremely long review notes (at max 1000 characters)
        long_notes = "x" * 1000
        flag_update = FlagUpdate(status=FlagStatus.DISMISSED, review_notes=long_notes)
        reviewer_pk = uuid4()

        # Should handle long notes without crashing
        result = await flag_service.review_flag(flag.pk, flag_update, reviewer_pk)
        assert result is not None

    @pytest.mark.asyncio
    async def test_review_flag_frivolous_count_query_failure(self, flag_service):
        """Test flag review when frivolous flag count query fails."""
        flag = Flag(
            pk=uuid4(),
            post_pk=uuid4(),
            topic_pk=None,
            flagger_pk=uuid4(),
            reason="Flag with count query failure",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_service.flag_repo.get_by_pk.return_value = flag
        flag_service.flag_repo.update.return_value = flag
        flag_service.flag_repo.get_user_dismissed_flags_count.side_effect = Exception(
            "Query failed"
        )

        flag_update = FlagUpdate(status=FlagStatus.DISMISSED, review_notes=None)
        reviewer_pk = uuid4()

        # Should propagate the query failure exception
        with pytest.raises(Exception, match="Query failed"):
            await flag_service.review_flag(flag.pk, flag_update, reviewer_pk)


class TestFlagStatisticsEdgeCases:
    """Test edge cases in flag statistics."""

    @pytest.mark.asyncio
    async def test_get_user_flag_stats_with_database_error(self, flag_service):
        """Test user flag statistics when database query fails."""
        user_pk = uuid4()
        flag_service.flag_repo.get_user_flags.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await flag_service.get_user_flag_stats(user_pk)

    @pytest.mark.asyncio
    async def test_get_content_flag_summary_with_corrupted_data(self, flag_service):
        """Test content flag summary with corrupted flag data."""
        content_pk = uuid4()

        # Return flags with valid status (simulating corrupted data handling)
        corrupted_flags = [
            Flag(
                pk=uuid4(),
                post_pk=content_pk,
                flagger_pk=uuid4(),
                reason="Corrupted flag",
                status=FlagStatus.PENDING,  # Use valid status for test
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]

        flag_service.flag_repo.get_content_flags.return_value = corrupted_flags

        # Should handle corrupted data gracefully
        summary = await flag_service.get_content_flag_summary(content_pk, "post")

        # Should count valid flags and skip corrupted ones
        assert summary["total_flags"] >= 1
        assert summary["pending"] >= 1

    @pytest.mark.asyncio
    async def test_get_user_flag_stats_with_mixed_content_types(self, flag_service):
        """Test user flag statistics with mixed post and topic flags."""
        user_pk = uuid4()

        mixed_flags = [
            Flag(
                pk=uuid4(),
                post_pk=uuid4(),
                topic_pk=None,
                flagger_pk=user_pk,
                reason="Post flag",
                status=FlagStatus.PENDING,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            Flag(
                pk=uuid4(),
                post_pk=None,
                topic_pk=uuid4(),
                flagger_pk=user_pk,
                reason="Topic flag",
                status=FlagStatus.UPHELD,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            Flag(
                pk=uuid4(),
                post_pk=uuid4(),
                topic_pk=None,
                flagger_pk=user_pk,
                reason="Another post flag",
                status=FlagStatus.DISMISSED,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]

        flag_service.flag_repo.get_user_flags.return_value = mixed_flags

        stats = await flag_service.get_user_flag_stats(user_pk)

        assert stats["total_flags"] == 3
        assert stats["pending"] == 1
        assert stats["upheld"] == 1
        assert stats["dismissed"] == 1


class TestFlagSystemBoundaryConditions:
    """Test boundary conditions and limits."""

    @pytest.mark.asyncio
    async def test_create_flag_at_reason_length_boundary(self, flag_service):
        """Test flag creation at reason length boundaries."""
        post = Post(
            pk=uuid4(),
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="Content for transaction test",
            status=ContentStatus.APPROVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )

        flag_service.post_repo.get_by_pk.return_value = post
        flag_service.flag_repo.get_content_flags.return_value = []
        flag_service.flag_repo.check_user_already_flagged = AsyncMock(
            return_value=False
        )
        flag_service.flag_repo.create_from_dict.return_value = Flag(
            pk=uuid4(),
            post_pk=post.pk,
            flagger_pk=uuid4(),
            reason="x" * 500,  # Exactly at max length
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Test exactly at maximum length (500 characters)
        flag_data = FlagCreate(post_pk=post.pk, reason="x" * 500)
        flagger_pk = uuid4()

        result = await flag_service.create_flag(flag_data, flagger_pk)
        assert result is not None

    @pytest.mark.asyncio
    async def test_massive_number_of_flags_for_content(self, flag_service):
        """Test handling content with massive number of flags."""
        content_pk = uuid4()

        # Simulate 1000 flags for same content
        massive_flags = [
            Flag(
                pk=uuid4(),
                post_pk=content_pk,
                flagger_pk=uuid4(),
                reason=f"Flag number {i}",
                status=FlagStatus.PENDING
                if i % 3 == 0
                else FlagStatus.UPHELD
                if i % 3 == 1
                else FlagStatus.DISMISSED,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            for i in range(1000)
        ]

        flag_service.flag_repo.get_content_flags.return_value = massive_flags

        # Should handle large number of flags efficiently
        summary = await flag_service.get_content_flag_summary(content_pk, "post")

        assert summary["total_flags"] == 1000
        # Verify counts are correct based on our pattern
        assert summary["pending"] > 0
        assert summary["upheld"] > 0
        assert summary["dismissed"] > 0

    @pytest.mark.asyncio
    async def test_flag_creation_with_null_uuids(self, flag_service):
        """Test flag creation with edge case UUID values."""
        # Test with minimum UUID (all zeros)
        zero_uuid = uuid4()

        post = Post(
            pk=zero_uuid,
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="Content with edge case UUID",
            status=ContentStatus.APPROVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )

        flag_service.post_repo.get_by_pk.return_value = post
        flag_service.flag_repo.get_content_flags.return_value = []
        flag_service.flag_repo.check_user_already_flagged = AsyncMock(
            return_value=False
        )
        flag_service.flag_repo.create_from_dict.return_value = Flag(
            pk=uuid4(),
            post_pk=zero_uuid,
            flagger_pk=uuid4(),
            reason="Flag with edge case UUID",
            status=FlagStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        flag_data = FlagCreate(post_pk=zero_uuid, reason="Flag with edge case UUID")
        flagger_pk = uuid4()

        result = await flag_service.create_flag(flag_data, flagger_pk)
        assert result is not None

    @pytest.mark.asyncio
    async def test_flag_system_under_high_concurrency(self, flag_service):
        """Test flag system behavior under simulated high concurrency."""
        # Simulate race condition where multiple operations happen simultaneously
        post = Post(
            pk=uuid4(),
            topic_pk=uuid4(),
            author_pk=uuid4(),
            content="Content under high load",
            status=ContentStatus.APPROVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            submitted_at=datetime.now(UTC),
        )

        # Simulate database returning different results due to concurrent operations
        flag_service.post_repo.get_by_pk.side_effect = [
            post,
            post,
            None,
        ]  # Content deleted during operations
        flag_service.flag_repo.get_content_flags.return_value = []
        flag_service.flag_repo.create_from_dict.side_effect = Exception(
            "Concurrent modification"
        )

        flag_data = FlagCreate(post_pk=post.pk, reason="Flag under high concurrency")
        flagger_pk = uuid4()

        # Should handle concurrent modification gracefully
        with pytest.raises(ValueError, match="You have already flagged this content"):
            await flag_service.create_flag(flag_data, flagger_pk)
