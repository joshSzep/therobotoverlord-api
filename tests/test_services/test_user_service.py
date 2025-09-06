"""Tests for UserService."""

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from therobotoverlord_api.database.models.badge import UserBadge
from therobotoverlord_api.database.models.base import ContentStatus
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.post import PostSummary
from therobotoverlord_api.database.models.topic import Topic
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserProfile
from therobotoverlord_api.database.models.user import UserUpdate
from therobotoverlord_api.services.user_service import UserService


@pytest.fixture
def mock_user_repo():
    """Create a mock user repository."""
    return AsyncMock()


@pytest.fixture
def mock_post_repo():
    """Create a mock post repository."""
    return AsyncMock()


@pytest.fixture
def mock_topic_repo():
    """Create a mock topic repository."""
    return AsyncMock()


@pytest.fixture
def mock_badge_repo():
    """Create a mock badge repository."""
    return AsyncMock()


@pytest.fixture
def mock_user_badge_repo():
    """Create a mock user badge repository."""
    return AsyncMock()


@pytest.fixture
def user_service(
    mock_user_repo,
    mock_post_repo,
    mock_topic_repo,
    mock_badge_repo,
    mock_user_badge_repo,
):
    """Create UserService with mocked dependencies."""
    return UserService(
        mock_user_repo,
        mock_post_repo,
        mock_topic_repo,
        mock_badge_repo,
        mock_user_badge_repo,
    )


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    now = datetime.now(UTC)
    return User(
        pk=uuid4(),
        email="test@example.com",
        google_id="google123",
        username="testuser",
        role=UserRole.CITIZEN,
        loyalty_score=100,
        is_banned=False,
        is_sanctioned=False,
        email_verified=True,
        created_at=now,
        updated_at=now,
    )


class TestGetUserProfile:
    """Test get_user_profile method."""

    @pytest.mark.asyncio
    async def test_get_user_profile_success(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test successful user profile retrieval."""
        mock_user_repo.get_by_pk.return_value = sample_user

        result = await user_service.get_user_profile(sample_user.pk)

        assert result is not None
        assert isinstance(result, UserProfile)
        assert result.pk == sample_user.pk
        assert result.username == sample_user.username
        assert result.loyalty_score == sample_user.loyalty_score
        assert result.role == sample_user.role
        assert result.created_at == sample_user.created_at

        mock_user_repo.get_by_pk.assert_called_once_with(sample_user.pk)

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, user_service, mock_user_repo):
        """Test user profile retrieval when user not found."""
        mock_user_repo.get_by_pk.return_value = None

        result = await user_service.get_user_profile(uuid4())

        assert result is None


class TestGetUserGraveyard:
    """Test get_user_graveyard method."""

    @pytest.mark.asyncio
    async def test_get_user_graveyard_success(
        self, user_service, mock_post_repo, sample_user
    ):
        """Test successful user graveyard retrieval."""
        post_summary = PostSummary(
            pk=uuid4(),
            topic_pk=uuid4(),
            topic_title="Test Topic",
            content="Rejected post",
            status=ContentStatus.REJECTED,
            overlord_feedback="Content inappropriate",
            submitted_at=sample_user.created_at,
            approved_at=None,
            rejection_reason="Inappropriate content",
        )

        post = Post(
            pk=post_summary.pk,
            topic_pk=post_summary.topic_pk,
            author_pk=sample_user.pk,
            post_number=1,
            content=post_summary.content,
            status=post_summary.status,
            overlord_feedback=post_summary.overlord_feedback,
            submitted_at=post_summary.submitted_at,
            approved_at=post_summary.approved_at,
            rejection_reason=post_summary.rejection_reason,
            created_at=sample_user.created_at,
            updated_at=sample_user.updated_at,
        )

        mock_post_repo.get_graveyard_by_author.return_value = [post_summary]
        mock_post_repo.get_by_pk.return_value = post

        result = await user_service.get_user_graveyard(sample_user.pk, 50, 0)

        assert len(result) == 1
        assert result[0].pk == post.pk
        assert result[0].content == "Rejected post"

        mock_post_repo.get_graveyard_by_author.assert_called_once_with(
            sample_user.pk, 50, 0
        )
        mock_post_repo.get_by_pk.assert_called_once_with(post_summary.pk)


class TestGetUserRegistry:
    """Test get_user_registry method."""

    @pytest.mark.asyncio
    async def test_get_user_registry_no_filter(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test user registry retrieval without role filter."""
        mock_user_repo.get_all.return_value = [sample_user]

        result = await user_service.get_user_registry(50, 0, None)

        assert len(result) == 1
        assert isinstance(result[0], UserProfile)
        assert result[0].username == sample_user.username

        mock_user_repo.get_all.assert_called_once_with(limit=50, offset=0)

    @pytest.mark.asyncio
    async def test_get_user_registry_with_role_filter(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test user registry retrieval with role filter."""
        mock_user_repo.get_users_by_role.return_value = [sample_user]

        result = await user_service.get_user_registry(50, 0, UserRole.CITIZEN)

        assert len(result) == 1
        assert result[0].role == UserRole.CITIZEN

        mock_user_repo.get_users_by_role.assert_called_once_with("citizen")


class TestUpdateUser:
    """Test update_user method."""

    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user update."""
        update_data = UserUpdate(username="newusername")
        updated_user = User(
            pk=sample_user.pk,
            email=sample_user.email,
            google_id=sample_user.google_id,
            username="newusername",
            role=sample_user.role,
            loyalty_score=sample_user.loyalty_score,
            is_banned=sample_user.is_banned,
            is_sanctioned=sample_user.is_sanctioned,
            email_verified=sample_user.email_verified,
            created_at=sample_user.created_at,
            updated_at=sample_user.updated_at,
        )

        mock_user_repo.get_by_username.return_value = None
        mock_user_repo.update_user.return_value = updated_user

        result = await user_service.update_user(sample_user.pk, update_data)

        assert result is not None
        assert result.username == "newusername"

        mock_user_repo.get_by_username.assert_called_once_with("newusername")
        mock_user_repo.update_user.assert_called_once_with(sample_user.pk, update_data)

    @pytest.mark.asyncio
    async def test_update_user_username_taken(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test user update with taken username."""
        other_user = User(
            pk=uuid4(),
            email="other@example.com",
            google_id="other123",
            username="existinguser",
            role=UserRole.CITIZEN,
            created_at=datetime.now(UTC),
        )
        update_data = UserUpdate(username="existinguser")

        mock_user_repo.get_by_username.return_value = other_user

        with pytest.raises(ValueError, match="Username already taken"):
            await user_service.update_user(sample_user.pk, update_data)

        mock_user_repo.get_by_username.assert_called_once_with("existinguser")
        mock_user_repo.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_same_user_username(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test user update with same user's current username."""
        update_data = UserUpdate(username=sample_user.username)

        mock_user_repo.get_by_username.return_value = sample_user
        mock_user_repo.update_user.return_value = sample_user

        result = await user_service.update_user(sample_user.pk, update_data)

        assert result is not None
        mock_user_repo.update_user.assert_called_once_with(sample_user.pk, update_data)


class TestGetUserBadges:
    """Test get_user_badges method."""

    @pytest.mark.asyncio
    async def test_get_user_badges_success(
        self, user_service, mock_user_badge_repo, sample_user
    ):
        """Test successful user badges retrieval."""
        user_badge = UserBadge(
            pk=uuid4(),
            user_pk=sample_user.pk,
            badge_pk=uuid4(),
            awarded_at=sample_user.created_at,
            awarded_by_event="test_event",
            created_at=sample_user.created_at,
            updated_at=sample_user.updated_at,
        )
        mock_user_badge_repo.get_user_badges.return_value = [user_badge]

        result = await user_service.get_user_badges(sample_user.pk)

        assert len(result) == 1
        assert result[0].user_pk == sample_user.pk

        mock_user_badge_repo.get_user_badges.assert_called_once_with(sample_user.pk)


class TestGetUserActivity:
    """Test get_user_activity method."""

    @pytest.mark.asyncio
    async def test_get_user_activity_success(
        self, user_service, mock_post_repo, mock_topic_repo, sample_user
    ):
        """Test successful user activity retrieval."""
        post_summary = PostSummary(
            pk=uuid4(),
            topic_pk=uuid4(),
            topic_title="User Topic",
            content="User post",
            status=ContentStatus.APPROVED,
            overlord_feedback="Good content",
            submitted_at=sample_user.created_at,
            approved_at=sample_user.created_at,
            rejection_reason=None,
        )

        topic = Topic(
            pk=uuid4(),
            title="User topic",
            description="Topic description",
            author_pk=sample_user.pk,
            status=TopicStatus.APPROVED,
            created_at=sample_user.created_at,
            updated_at=sample_user.updated_at,
        )

        mock_post_repo.get_by_author.return_value = [post_summary]
        mock_topic_repo.get_by_author.return_value = [topic]

        result = await user_service.get_user_activity(sample_user.pk, 50, 0)

        assert "posts" in result
        assert "topics" in result
        assert "total_posts" in result
        assert "total_topics" in result
        assert result["total_posts"] == 1
        assert result["total_topics"] == 1

        mock_post_repo.get_by_author.assert_called_once_with(
            sample_user.pk, None, 25, 0
        )
        mock_topic_repo.get_by_author.assert_called_once_with(sample_user.pk, 25, 0)


class TestDeleteUserAccount:
    """Test delete_user_account method."""

    @pytest.mark.asyncio
    async def test_delete_user_account_success(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test successful user account deletion."""
        mock_user_repo.get_by_pk.return_value = sample_user
        mock_user_repo.update_user.return_value = sample_user

        result = await user_service.delete_user_account(sample_user.pk)

        assert result is True

        mock_user_repo.get_by_pk.assert_called_once_with(sample_user.pk)
        mock_user_repo.update_user.assert_called_once()

        # Verify the anonymization data
        call_args = mock_user_repo.update_user.call_args
        update_data = call_args[0][1]
        assert update_data.username == f"deleted_user_{sample_user.pk}"
        assert update_data.email_verified is False
        assert update_data.is_banned is True

    @pytest.mark.asyncio
    async def test_delete_user_account_not_found(self, user_service, mock_user_repo):
        """Test user account deletion when user not found."""
        mock_user_repo.get_by_pk.return_value = None

        result = await user_service.delete_user_account(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_user_account_update_failed(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test user account deletion when update fails."""
        mock_user_repo.get_by_pk.return_value = sample_user
        mock_user_repo.update_user.return_value = None

        result = await user_service.delete_user_account(sample_user.pk)

        assert result is False
