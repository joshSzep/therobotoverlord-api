"""Comprehensive tests for AuthService to achieve high coverage."""

from datetime import datetime
from datetime import UTC
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from therobotoverlord_api.auth.adjectives import ADJECTIVES
from therobotoverlord_api.auth.models import AccessToken
from therobotoverlord_api.auth.models import AuthResponse
from therobotoverlord_api.auth.models import GoogleUserInfo
from therobotoverlord_api.auth.models import RefreshToken
from therobotoverlord_api.auth.models import SessionInfo
from therobotoverlord_api.auth.models import TokenPair
from therobotoverlord_api.auth.nouns import NOUNS
from therobotoverlord_api.auth.service import AuthService
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserRole
from therobotoverlord_api.database.models.user import UserUpdate


class TestAuthServiceComprehensive:
    """Comprehensive test class for AuthService."""

    @pytest.fixture
    def auth_service(self):
        """Create an AuthService instance with mocked dependencies."""
        service = AuthService()
        service.google_oauth = MagicMock()
        service.jwt_service = MagicMock()
        service.session_service = MagicMock()
        service.user_repository = MagicMock()
        return service

    @pytest.fixture
    def mock_google_user_info(self):
        """Mock Google user info."""
        return GoogleUserInfo(
            id="google_123",
            email="test@example.com",
            verified_email=True,
            name="Test User",
            given_name="Test",
            family_name="User",
            picture="https://example.com/pic.jpg",
        )

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        return User(
            pk=uuid4(),
            email="test@example.com",
            google_id="google_123",
            username="testuser",
            role=UserRole.CITIZEN,
            loyalty_score=100,
            email_verified=True,
            is_banned=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def mock_token_pair(self):
        """Mock token pair."""
        return TokenPair(
            access_token=AccessToken(
                token="access_token_123",
                expires_at=datetime.now(UTC),
                max_expires_at=datetime.now(UTC),
            ),
            refresh_token=RefreshToken(
                token="refresh_token_123",
                expires_at=datetime.now(UTC),
                session_id="session_123",
            ),
        )

    @pytest.mark.asyncio
    async def test_complete_login_new_user(
        self, auth_service, mock_google_user_info, mock_token_pair
    ):
        """Test complete login flow for new user."""
        # Setup mocks
        auth_service.google_oauth.exchange_code_for_tokens = AsyncMock(
            return_value=(mock_google_user_info, "google_access_token")
        )

        new_user = User(
            pk=uuid4(),
            email=mock_google_user_info.email,
            google_id=mock_google_user_info.id,
            username="testuser",
            role=UserRole.CITIZEN,
            loyalty_score=0,
            email_verified=True,
            is_banned=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        auth_service.user_repository.get_by_google_id = AsyncMock(return_value=None)
        auth_service.user_repository.get_by_email = AsyncMock(return_value=None)
        auth_service.user_repository.get_by_username = AsyncMock(return_value=None)
        auth_service.user_repository.create_user = AsyncMock(return_value=new_user)

        auth_service.jwt_service.create_token_pair = MagicMock(
            return_value=mock_token_pair
        )
        auth_service.session_service.create_session = AsyncMock()

        with patch.object(
            auth_service, "_get_user_permissions", return_value=["view_content"]
        ):
            auth_response, token_pair = await auth_service.complete_login(
                "auth_code", "state", "127.0.0.1", "test-agent"
            )

        # Verify calls
        auth_service.google_oauth.exchange_code_for_tokens.assert_called_once_with(
            "auth_code", "state"
        )
        auth_service.user_repository.get_by_google_id.assert_called_once_with(
            mock_google_user_info.id
        )
        auth_service.user_repository.get_by_email.assert_called_once_with(
            mock_google_user_info.email
        )
        auth_service.user_repository.create_user.assert_called_once()
        auth_service.session_service.create_session.assert_called_once()

        # Verify response
        assert isinstance(auth_response, AuthResponse)
        assert auth_response.user_id == new_user.pk
        assert auth_response.username == new_user.username
        assert auth_response.is_new_user is True
        assert token_pair == mock_token_pair

    @pytest.mark.asyncio
    async def test_complete_login_existing_user_by_google_id(
        self, auth_service, mock_google_user_info, mock_user, mock_token_pair
    ):
        """Test complete login for existing user found by Google ID."""
        # Setup mocks
        auth_service.google_oauth.exchange_code_for_tokens = AsyncMock(
            return_value=(mock_google_user_info, "google_access_token")
        )
        auth_service.user_repository.get_by_google_id = AsyncMock(
            return_value=mock_user
        )
        auth_service.jwt_service.create_token_pair = MagicMock(
            return_value=mock_token_pair
        )
        auth_service.session_service.create_session = AsyncMock()

        with patch.object(
            auth_service, "_get_user_permissions", return_value=["view_content"]
        ):
            auth_response, token_pair = await auth_service.complete_login("auth_code")

        # Verify existing user returned
        assert auth_response.is_new_user is False
        assert auth_response.user_id == mock_user.pk

    @pytest.mark.asyncio
    async def test_complete_login_existing_user_by_email_update_google_id(
        self, auth_service, mock_google_user_info, mock_user, mock_token_pair
    ):
        """Test complete login for existing user found by email, updating Google ID."""
        # Setup mocks
        auth_service.google_oauth.exchange_code_for_tokens = AsyncMock(
            return_value=(mock_google_user_info, "google_access_token")
        )
        auth_service.user_repository.get_by_google_id = AsyncMock(return_value=None)
        auth_service.user_repository.get_by_email = AsyncMock(return_value=mock_user)
        auth_service.user_repository.update_user = AsyncMock(return_value=mock_user)
        auth_service.jwt_service.create_token_pair = MagicMock(
            return_value=mock_token_pair
        )
        auth_service.session_service.create_session = AsyncMock()

        with patch.object(
            auth_service, "_get_user_permissions", return_value=["view_content"]
        ):
            auth_response, token_pair = await auth_service.complete_login("auth_code")

        # Verify Google ID update
        auth_service.user_repository.update_user.assert_called_once()
        update_call_args = auth_service.user_repository.update_user.call_args
        assert isinstance(update_call_args[0][1], UserUpdate)
        assert update_call_args[0][1].google_id == mock_google_user_info.id
        assert auth_response.is_new_user is False

    @pytest.mark.asyncio
    async def test_complete_login_existing_user_update_fails(
        self, auth_service, mock_google_user_info, mock_user, mock_token_pair
    ):
        """Test complete login when user update fails."""
        # Setup mocks
        auth_service.google_oauth.exchange_code_for_tokens = AsyncMock(
            return_value=(mock_google_user_info, "google_access_token")
        )
        auth_service.user_repository.get_by_google_id = AsyncMock(return_value=None)
        auth_service.user_repository.get_by_email = AsyncMock(return_value=mock_user)
        auth_service.user_repository.update_user = AsyncMock(
            return_value=None
        )  # Update fails
        auth_service.jwt_service.create_token_pair = MagicMock(
            return_value=mock_token_pair
        )
        auth_service.session_service.create_session = AsyncMock()

        with patch.object(
            auth_service, "_get_user_permissions", return_value=["view_content"]
        ):
            auth_response, token_pair = await auth_service.complete_login("auth_code")

        # Should fall back to original user
        assert auth_response.user_id == mock_user.pk

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(
        self, auth_service, mock_user, mock_token_pair
    ):
        """Test successful token refresh."""
        session_id = "session_123"
        refresh_token = "refresh_token_123"

        mock_session = SessionInfo(
            session_id=session_id,
            user_id=mock_user.pk,
            created_at=datetime.now(UTC),
            last_used_at=datetime.now(UTC),
            is_revoked=False,
            reuse_detected=False,
        )

        # Setup mocks
        auth_service.jwt_service.extract_session_id = MagicMock(return_value=session_id)
        auth_service.session_service.validate_refresh_token = AsyncMock(
            return_value=True
        )
        auth_service.session_service.get_session = AsyncMock(return_value=mock_session)
        auth_service.user_repository.get_by_pk = AsyncMock(return_value=mock_user)
        auth_service.jwt_service.create_token_pair = MagicMock(
            return_value=mock_token_pair
        )
        auth_service.session_service.rotate_refresh_token = AsyncMock(return_value=True)

        with patch.object(
            auth_service, "_get_user_permissions", return_value=["view_content"]
        ):
            result = await auth_service.refresh_tokens(
                refresh_token, "127.0.0.1", "test-agent"
            )

        # Verify calls
        auth_service.jwt_service.extract_session_id.assert_called_once_with(
            refresh_token
        )
        auth_service.session_service.validate_refresh_token.assert_called_once_with(
            session_id, refresh_token
        )
        auth_service.session_service.get_session.assert_called_once_with(session_id)
        auth_service.user_repository.get_by_pk.assert_called_once_with(
            mock_session.user_id
        )
        auth_service.session_service.rotate_refresh_token.assert_called_once()

        assert result == mock_token_pair

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_session_id(self, auth_service):
        """Test token refresh with invalid session ID."""
        auth_service.jwt_service.extract_session_id = MagicMock(return_value=None)

        result = await auth_service.refresh_tokens("invalid_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_refresh_token(self, auth_service):
        """Test token refresh with invalid refresh token."""
        session_id = "session_123"

        auth_service.jwt_service.extract_session_id = MagicMock(return_value=session_id)
        auth_service.session_service.validate_refresh_token = AsyncMock(
            return_value=False
        )

        result = await auth_service.refresh_tokens("invalid_refresh_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_tokens_revoked_session(self, auth_service):
        """Test token refresh with revoked session."""
        session_id = "session_123"

        mock_session = SessionInfo(
            session_id=session_id,
            user_id=uuid4(),
            created_at=datetime.now(UTC),
            last_used_at=datetime.now(UTC),
            is_revoked=True,  # Revoked session
            reuse_detected=False,
        )

        auth_service.jwt_service.extract_session_id = MagicMock(return_value=session_id)
        auth_service.session_service.validate_refresh_token = AsyncMock(
            return_value=True
        )
        auth_service.session_service.get_session = AsyncMock(return_value=mock_session)

        result = await auth_service.refresh_tokens("refresh_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_tokens_no_session(self, auth_service):
        """Test token refresh with non-existent session."""
        session_id = "session_123"

        auth_service.jwt_service.extract_session_id = MagicMock(return_value=session_id)
        auth_service.session_service.validate_refresh_token = AsyncMock(
            return_value=True
        )
        auth_service.session_service.get_session = AsyncMock(return_value=None)

        result = await auth_service.refresh_tokens("refresh_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_tokens_banned_user(self, auth_service):
        """Test token refresh with banned user."""
        session_id = "session_123"

        banned_user = User(
            pk=uuid4(),
            email="banned@example.com",
            google_id="google_123",
            username="banneduser",
            role=UserRole.CITIZEN,
            loyalty_score=0,
            email_verified=True,
            is_banned=True,  # Banned user
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_session = SessionInfo(
            session_id=session_id,
            user_id=banned_user.pk,
            created_at=datetime.now(UTC),
            last_used_at=datetime.now(UTC),
            is_revoked=False,
            reuse_detected=False,
        )

        auth_service.jwt_service.extract_session_id = MagicMock(return_value=session_id)
        auth_service.session_service.validate_refresh_token = AsyncMock(
            return_value=True
        )
        auth_service.session_service.get_session = AsyncMock(return_value=mock_session)
        auth_service.user_repository.get_by_pk = AsyncMock(return_value=banned_user)

        result = await auth_service.refresh_tokens("refresh_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_tokens_rotation_fails(
        self, auth_service, mock_user, mock_token_pair
    ):
        """Test token refresh when rotation fails."""
        session_id = "session_123"

        mock_session = SessionInfo(
            session_id=session_id,
            user_id=mock_user.pk,
            created_at=datetime.now(UTC),
            last_used_at=datetime.now(UTC),
            is_revoked=False,
            reuse_detected=False,
        )

        auth_service.jwt_service.extract_session_id = MagicMock(return_value=session_id)
        auth_service.session_service.validate_refresh_token = AsyncMock(
            return_value=True
        )
        auth_service.session_service.get_session = AsyncMock(return_value=mock_session)
        auth_service.user_repository.get_by_pk = AsyncMock(return_value=mock_user)
        auth_service.jwt_service.create_token_pair = MagicMock(
            return_value=mock_token_pair
        )
        auth_service.session_service.rotate_refresh_token = AsyncMock(
            return_value=False
        )  # Rotation fails

        with patch.object(
            auth_service, "_get_user_permissions", return_value=["view_content"]
        ):
            result = await auth_service.refresh_tokens("refresh_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_unique_username_from_given_name(
        self, auth_service, mock_google_user_info
    ):
        """Test username generation from given name."""
        auth_service.user_repository.get_by_username = AsyncMock(return_value=None)

        username = await auth_service._generate_unique_username(mock_google_user_info)

        assert username == "test"  # From given_name "Test"

    @pytest.mark.asyncio
    async def test_generate_unique_username_from_email(self, auth_service):
        """Test username generation from email when no given name."""
        google_info = GoogleUserInfo(
            id="google_123",
            email="testuser@example.com",
            verified_email=True,
            name="Test User",
            given_name="",  # Empty given name
            family_name="User",
            picture="https://example.com/pic.jpg",
        )

        auth_service.user_repository.get_by_username = AsyncMock(return_value=None)

        username = await auth_service._generate_unique_username(google_info)

        assert username == "testuser"  # From email prefix

    @pytest.mark.asyncio
    async def test_generate_unique_username_with_special_chars(self, auth_service):
        """Test username generation with special characters."""
        google_info = GoogleUserInfo(
            id="google_123",
            email="test.user+123@example.com",
            verified_email=True,
            name="Test User",
            given_name="Test@User!",  # Special characters
            family_name="User",
            picture="https://example.com/pic.jpg",
        )

        auth_service.user_repository.get_by_username = AsyncMock(return_value=None)

        username = await auth_service._generate_unique_username(google_info)

        assert username == "testuser"  # Special chars removed

    @pytest.mark.asyncio
    async def test_generate_unique_username_short_name(self, auth_service):
        """Test username generation with very short name."""
        google_info = GoogleUserInfo(
            id="google_123",
            email="a@example.com",
            verified_email=True,
            name="A",
            given_name="A",  # Very short
            family_name="",
            picture="https://example.com/pic.jpg",
        )

        auth_service.user_repository.get_by_username = AsyncMock(return_value=None)

        username = await auth_service._generate_unique_username(google_info)

        # Should generate natural citizen username like "citizen-brave-explorer-12345"
        assert username.startswith("citizen-")
        parts = username.split("-")
        assert len(parts) == 4  # citizen, adjective, noun, number

        # Verify format: citizen-adjective-noun-number
        assert parts[0] == "citizen"
        assert parts[1] in ADJECTIVES
        assert parts[2] in NOUNS
        assert parts[3].isdigit()
        assert 0 <= int(parts[3]) <= 65535  # 16-bit number

    @pytest.mark.asyncio
    async def test_generate_unique_username_with_conflicts(
        self, auth_service, mock_google_user_info
    ):
        """Test username generation with conflicts."""
        # Mock existing usernames
        existing_usernames = {"test", "test1", "test2"}

        def mock_get_by_username(username):
            return AsyncMock(
                return_value="existing" if username in existing_usernames else None
            )()

        auth_service.user_repository.get_by_username = mock_get_by_username

        username = await auth_service._generate_unique_username(mock_google_user_info)

        assert username == "test3"  # Should increment until unique

    @pytest.mark.asyncio
    async def test_generate_unique_username_infinite_loop_protection(
        self, auth_service, mock_google_user_info
    ):
        """Test username generation with infinite loop protection."""
        # Mock all usernames as existing to trigger random fallback
        auth_service.user_repository.get_by_username = AsyncMock(
            return_value="existing"
        )

        with patch("secrets.randbelow", return_value=12345):
            username = await auth_service._generate_unique_username(
                mock_google_user_info
            )

        assert username == "test12345"  # Should use random number

    @pytest.mark.asyncio
    async def test_get_user_permissions_citizen(self, auth_service):
        """Test permissions for citizen user."""
        user = User(
            pk=uuid4(),
            email="test@example.com",
            google_id="google_123",
            username="testuser",
            role=UserRole.CITIZEN,
            loyalty_score=100,
            email_verified=True,
            is_banned=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_loyalty_service = AsyncMock()
        mock_loyalty_service.get_score_thresholds = AsyncMock(
            return_value={"topic_creation": 50}
        )

        with patch(
            "therobotoverlord_api.auth.service.get_loyalty_score_service",
            return_value=mock_loyalty_service,
        ):
            permissions = await auth_service._get_user_permissions(user)

        expected_base = [
            "view_content",
            "create_posts",
            "send_private_messages",
            "appeal_rejections",
            "flag_content",
        ]

        assert all(perm in permissions for perm in expected_base)
        assert "create_topics" in permissions  # Loyalty score 100 >= 50
        assert "view_rejected_posts" not in permissions  # Not moderator

    @pytest.mark.asyncio
    async def test_get_user_permissions_moderator(self, auth_service):
        """Test permissions for moderator user."""
        user = User(
            pk=uuid4(),
            email="mod@example.com",
            google_id="google_123",
            username="moderator",
            role=UserRole.MODERATOR,
            loyalty_score=200,
            email_verified=True,
            is_banned=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_loyalty_service = AsyncMock()
        mock_loyalty_service.get_score_thresholds = AsyncMock(
            return_value={"topic_creation": 50}
        )

        with patch(
            "therobotoverlord_api.auth.service.get_loyalty_score_service",
            return_value=mock_loyalty_service,
        ):
            permissions = await auth_service._get_user_permissions(user)

        moderator_perms = [
            "view_rejected_posts",
            "apply_sanctions",
            "adjudicate_appeals",
            "moderate_flags",
            "content_preview",
        ]

        assert all(perm in permissions for perm in moderator_perms)
        assert "admin_dashboard" not in permissions  # Not admin

    @pytest.mark.asyncio
    async def test_get_user_permissions_admin(self, auth_service):
        """Test permissions for admin user."""
        user = User(
            pk=uuid4(),
            email="admin@example.com",
            google_id="google_123",
            username="admin",
            role=UserRole.ADMIN,
            loyalty_score=300,
            email_verified=True,
            is_banned=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_loyalty_service = AsyncMock()
        mock_loyalty_service.get_score_thresholds = AsyncMock(
            return_value={"topic_creation": 50}
        )

        with patch(
            "therobotoverlord_api.auth.service.get_loyalty_score_service",
            return_value=mock_loyalty_service,
        ):
            permissions = await auth_service._get_user_permissions(user)

        admin_perms = [
            "view_private_messages",
            "override_tags",
            "escalate_sanctions",
            "admin_dashboard",
        ]

        assert all(perm in permissions for perm in admin_perms)
        assert "change_user_roles" not in permissions  # Not superadmin

    @pytest.mark.asyncio
    async def test_get_user_permissions_superadmin(self, auth_service):
        """Test permissions for superadmin user."""
        user = User(
            pk=uuid4(),
            email="superadmin@example.com",
            google_id="google_123",
            username="superadmin",
            role=UserRole.SUPERADMIN,
            loyalty_score=600,  # High loyalty
            email_verified=True,
            is_banned=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_loyalty_service = AsyncMock()
        mock_loyalty_service.get_score_thresholds = AsyncMock(
            return_value={"topic_creation": 50}
        )

        with patch(
            "therobotoverlord_api.auth.service.get_loyalty_score_service",
            return_value=mock_loyalty_service,
        ):
            permissions = await auth_service._get_user_permissions(user)

        superadmin_perms = [
            "change_user_roles",
            "delete_accounts",
            "system_configuration",
        ]

        high_loyalty_perms = ["priority_moderation", "extended_appeals"]

        assert all(perm in permissions for perm in superadmin_perms)
        assert all(perm in permissions for perm in high_loyalty_perms)

    @pytest.mark.asyncio
    async def test_get_user_permissions_low_loyalty(self, auth_service):
        """Test permissions for user with low loyalty score."""
        user = User(
            pk=uuid4(),
            email="lowloyalty@example.com",
            google_id="google_123",
            username="lowloyalty",
            role=UserRole.CITIZEN,
            loyalty_score=10,  # Low loyalty
            email_verified=True,
            is_banned=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_loyalty_service = AsyncMock()
        mock_loyalty_service.get_score_thresholds = AsyncMock(
            return_value={"topic_creation": 50}
        )

        with patch(
            "therobotoverlord_api.auth.service.get_loyalty_score_service",
            return_value=mock_loyalty_service,
        ):
            permissions = await auth_service._get_user_permissions(user)

        assert "create_topics" not in permissions  # Loyalty score 10 < 50
        assert "priority_moderation" not in permissions  # Loyalty score 10 < 500
        assert "extended_appeals" not in permissions  # Loyalty score 10 < 500
