"""Tests for user models."""

from datetime import UTC
from datetime import datetime
from uuid import uuid4

from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserCreate
from therobotoverlord_api.database.models.user import UserLeaderboard
from therobotoverlord_api.database.models.user import UserProfile
from therobotoverlord_api.database.models.user import UserUpdate


class TestUser:
    """Test User model."""

    def test_user_creation(self):
        """Test creating a User instance."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        user = User(
            pk=pk,
            created_at=created_at,
            updated_at=None,
            email="test@example.com",
            google_id="google123",
            username="testuser",
            role=UserRole.CITIZEN,
            loyalty_score=50,
            is_banned=False,
            is_sanctioned=False,
            email_verified=True,
        )

        assert user.pk == pk
        assert user.created_at == created_at
        assert user.updated_at is None
        assert user.email == "test@example.com"
        assert user.google_id == "google123"
        assert user.username == "testuser"
        assert user.role == UserRole.CITIZEN
        assert user.loyalty_score == 50
        assert user.is_banned is False
        assert user.is_sanctioned is False
        assert user.email_verified is True

    def test_user_default_values(self):
        """Test User model default values."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        user = User(
            pk=pk,
            created_at=created_at,
            email="test@example.com",
            google_id="google123",
            username="testuser",
        )

        assert user.role == UserRole.CITIZEN
        assert user.loyalty_score == 0
        assert user.is_banned is False
        assert user.is_sanctioned is False
        assert user.email_verified is False

    def test_user_with_different_role(self):
        """Test User with different role."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        user = User(
            pk=pk,
            created_at=created_at,
            email="admin@example.com",
            google_id="google456",
            username="admin",
            role=UserRole.ADMIN,
            loyalty_score=1000,
            email_verified=True,
        )

        assert user.role == UserRole.ADMIN
        assert user.loyalty_score == 1000

    def test_user_validation_from_dict(self):
        """Test User validation from dictionary."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        data = {
            "pk": pk,
            "created_at": created_at,
            "updated_at": None,
            "email": "test@example.com",
            "google_id": "google123",
            "username": "testuser",
            "role": "citizen",
            "loyalty_score": 75,
            "is_banned": False,
            "is_sanctioned": True,
            "email_verified": True,
        }

        user = User.model_validate(data)
        assert user.email == "test@example.com"
        assert user.role == UserRole.CITIZEN
        assert user.loyalty_score == 75
        assert user.is_sanctioned is True


class TestUserCreate:
    """Test UserCreate model."""

    def test_user_create_basic(self):
        """Test creating a UserCreate instance."""
        user_create = UserCreate(
            email="new@example.com",
            google_id="google789",
            username="newuser",
        )

        assert user_create.email == "new@example.com"
        assert user_create.google_id == "google789"
        assert user_create.username == "newuser"
        assert user_create.role == UserRole.CITIZEN
        assert user_create.email_verified is False

    def test_user_create_with_custom_values(self):
        """Test UserCreate with custom values."""
        user_create = UserCreate(
            email="mod@example.com",
            google_id="google999",
            username="moderator",
            role=UserRole.MODERATOR,
            email_verified=True,
        )

        assert user_create.role == UserRole.MODERATOR
        assert user_create.email_verified is True

    def test_user_create_model_dump(self):
        """Test UserCreate serialization."""
        user_create = UserCreate(
            email="test@example.com",
            google_id="google123",
            username="testuser",
            role=UserRole.ADMIN,
        )

        data = user_create.model_dump()
        expected = {
            "email": "test@example.com",
            "google_id": "google123",
            "username": "testuser",
            "password_hash": None,
            "role": "admin",
            "email_verified": False,
        }

        assert data == expected


class TestUserUpdate:
    """Test UserUpdate model."""

    def test_user_update_empty(self):
        """Test creating an empty UserUpdate instance."""
        user_update = UserUpdate()

        assert user_update.username is None
        assert user_update.role is None
        assert user_update.loyalty_score is None
        assert user_update.is_banned is None
        assert user_update.is_sanctioned is None
        assert user_update.email_verified is None

    def test_user_update_partial(self):
        """Test UserUpdate with partial data."""
        user_update = UserUpdate(
            username="newusername",
            loyalty_score=100,
        )

        assert user_update.username == "newusername"
        assert user_update.loyalty_score == 100
        assert user_update.role is None
        assert user_update.is_banned is None

    def test_user_update_full(self):
        """Test UserUpdate with all fields."""
        user_update = UserUpdate(
            username="updateduser",
            role=UserRole.MODERATOR,
            loyalty_score=200,
            is_banned=True,
            is_sanctioned=False,
            email_verified=True,
        )

        assert user_update.username == "updateduser"
        assert user_update.role == UserRole.MODERATOR
        assert user_update.loyalty_score == 200
        assert user_update.is_banned is True
        assert user_update.is_sanctioned is False
        assert user_update.email_verified is True

    def test_user_update_model_dump_exclude_unset(self):
        """Test UserUpdate serialization excluding unset fields."""
        user_update = UserUpdate(
            username="newname",
            loyalty_score=50,
        )

        data = user_update.model_dump(exclude_unset=True)
        expected = {
            "username": "newname",
            "loyalty_score": 50,
        }

        assert data == expected


class TestUserLeaderboard:
    """Test UserLeaderboard model."""

    def test_user_leaderboard_creation(self):
        """Test creating a UserLeaderboard instance."""
        user_pk = uuid4()
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        leaderboard = UserLeaderboard(
            user_pk=user_pk,
            username="topuser",
            loyalty_score=500,
            rank=1,
            can_create_topics=True,
            created_at=created_at,
            updated_at=updated_at,
        )

        assert leaderboard.user_pk == user_pk
        assert leaderboard.username == "topuser"
        assert leaderboard.loyalty_score == 500
        assert leaderboard.rank == 1
        assert leaderboard.can_create_topics is True
        assert leaderboard.created_at == created_at
        assert leaderboard.updated_at == updated_at

    def test_user_leaderboard_without_updated_at(self):
        """Test UserLeaderboard without updated_at."""
        user_pk = uuid4()
        created_at = datetime.now(UTC)

        leaderboard = UserLeaderboard(
            user_pk=user_pk,
            username="user2",
            loyalty_score=300,
            rank=2,
            can_create_topics=False,
            created_at=created_at,
        )

        assert leaderboard.updated_at is None
        assert leaderboard.can_create_topics is False

    def test_user_leaderboard_config(self):
        """Test UserLeaderboard configuration."""
        config = UserLeaderboard.model_config
        assert config.get("from_attributes") is True


class TestUserProfile:
    """Test UserProfile model."""

    def test_user_profile_creation(self):
        """Test creating a UserProfile instance."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        profile = UserProfile(
            pk=pk,
            username="publicuser",
            loyalty_score=150,
            role=UserRole.CITIZEN,
            created_at=created_at,
        )

        assert profile.pk == pk
        assert profile.username == "publicuser"
        assert profile.loyalty_score == 150
        assert profile.role == UserRole.CITIZEN
        assert profile.created_at == created_at

    def test_user_profile_with_admin_role(self):
        """Test UserProfile with admin role."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        profile = UserProfile(
            pk=pk,
            username="admin",
            loyalty_score=1000,
            role=UserRole.ADMIN,
            created_at=created_at,
        )

        assert profile.role == UserRole.ADMIN
        assert profile.loyalty_score == 1000

    def test_user_profile_config(self):
        """Test UserProfile configuration."""
        config = UserProfile.model_config
        assert config.get("from_attributes") is True

    def test_user_profile_validation_from_dict(self):
        """Test UserProfile validation from dictionary."""
        pk = uuid4()
        created_at = datetime.now(UTC)

        data = {
            "pk": pk,
            "username": "testprofile",
            "loyalty_score": 75,
            "role": "moderator",
            "created_at": created_at,
        }

        profile = UserProfile.model_validate(data)
        assert profile.username == "testprofile"
        assert profile.role == UserRole.MODERATOR
        assert profile.loyalty_score == 75
