"""Authentication service for The Robot Overlord API."""

import re
import secrets

from uuid import UUID

from therobotoverlord_api.auth.adjectives import ADJECTIVES_LIST
from therobotoverlord_api.auth.google_oauth import GoogleOAuthService
from therobotoverlord_api.auth.jwt_service import JWTService
from therobotoverlord_api.auth.models import AuthResponse
from therobotoverlord_api.auth.models import GoogleUserInfo
from therobotoverlord_api.auth.models import TokenPair
from therobotoverlord_api.auth.nouns import NOUNS_LIST
from therobotoverlord_api.auth.session_service import SessionService
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserCreate
from therobotoverlord_api.database.models.user import UserRole
from therobotoverlord_api.database.models.user import UserUpdate
from therobotoverlord_api.database.repositories.user import UserRepository
from therobotoverlord_api.services.loyalty_score_service import (
    get_loyalty_score_service,
)


class AuthService:
    """Main authentication service orchestrating OAuth, JWT, and user management."""

    def __init__(self):
        self.google_oauth = GoogleOAuthService()
        self.jwt_service = JWTService()
        self.session_service = SessionService()
        self.user_repository = UserRepository()

    async def initiate_login(self) -> tuple[str, str]:
        """Initiate Google OAuth login flow."""
        return self.google_oauth.get_authorization_url()

    async def complete_login(
        self,
        authorization_code: str,
        state: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[AuthResponse, TokenPair]:
        """Complete OAuth login and create user session."""
        # Exchange code for Google user info
        (
            google_user_info,
            google_access_token,
        ) = await self.google_oauth.exchange_code_for_tokens(authorization_code, state)

        # Get or create user
        user, is_new_user = await self._get_or_create_user(google_user_info)

        # Generate user permissions
        permissions = await self._get_user_permissions(user)

        # Create JWT token pair
        token_pair = self.jwt_service.create_token_pair(
            user_id=user.pk,
            role=user.role,
            permissions=permissions,
        )

        # Create session
        await self.session_service.create_session(
            user_id=user.pk,
            session_id=token_pair.refresh_token.session_id,
            refresh_token=token_pair.refresh_token.token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Create auth response
        auth_response = AuthResponse(
            user_id=user.pk,
            username=user.username,
            role=user.role,
            loyalty_score=user.loyalty_score,
            is_new_user=is_new_user,
        )

        # Broadcast user online status via WebSocket
        from therobotoverlord_api.websocket.events import get_event_broadcaster
        from therobotoverlord_api.websocket.manager import websocket_manager

        event_broadcaster = get_event_broadcaster(websocket_manager)
        await event_broadcaster.broadcast_user_activity_update(
            user_id=user.pk,
            username=user.username,
            status="online",
        )

        return auth_response, token_pair

    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPair | None:
        """Refresh access token using refresh token."""
        # Extract session ID
        session_id = self.jwt_service.extract_session_id(refresh_token)
        if not session_id:
            return None

        # Validate refresh token
        if not await self.session_service.validate_refresh_token(
            session_id, refresh_token
        ):
            return None

        # Get session info
        session = await self.session_service.get_session(session_id)
        if not session or session.is_revoked:
            return None

        # Get user info
        user = await self.user_repository.get_by_pk(session.user_id)
        if not user or user.is_banned:
            return None

        # Generate new token pair
        permissions = await self._get_user_permissions(user)
        new_token_pair = self.jwt_service.create_token_pair(
            user_id=user.pk,
            role=user.role,
            permissions=permissions,
            session_id=session_id,
        )

        # Rotate refresh token
        success = await self.session_service.rotate_refresh_token(
            session_id=session_id,
            old_refresh_token=refresh_token,
            new_refresh_token=new_token_pair.refresh_token.token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return new_token_pair if success else None

    async def logout(self, session_id: str) -> bool:
        """Logout user by revoking session."""
        # Get session info before revoking to broadcast offline status
        session = await self.session_service.get_session(session_id)
        if session:
            user = await self.user_repository.get_by_pk(session.user_id)
            if user:
                # Broadcast user offline status via WebSocket
                from therobotoverlord_api.websocket.events import get_event_broadcaster
                from therobotoverlord_api.websocket.manager import websocket_manager

                event_broadcaster = get_event_broadcaster(websocket_manager)
                await event_broadcaster.broadcast_user_activity_update(
                    user_id=user.pk,
                    username=user.username,
                    status="offline",
                )

        return await self.session_service.revoke_session(session_id)

    async def logout_all_sessions(self, user_id: UUID) -> int:
        """Logout user from all sessions."""
        # Get user info to broadcast offline status
        user = await self.user_repository.get_by_pk(user_id)
        if user:
            # Broadcast user offline status via WebSocket
            from therobotoverlord_api.websocket.events import get_event_broadcaster
            from therobotoverlord_api.websocket.manager import websocket_manager

            event_broadcaster = get_event_broadcaster(websocket_manager)
            await event_broadcaster.broadcast_user_activity_update(
                user_id=user.pk,
                username=user.username,
                status="offline",
            )

        return await self.session_service.revoke_all_user_sessions(user_id)

    async def get_user_info(self, user_id: UUID) -> User | None:
        """Get user information by ID."""
        return await self.user_repository.get_by_pk(user_id)

    async def _get_or_create_user(
        self, google_user_info: GoogleUserInfo
    ) -> tuple[User, bool]:
        """Get existing user or create new one from Google user info."""
        # Try to find existing user by Google ID
        existing_user = await self.user_repository.get_by_google_id(google_user_info.id)
        if existing_user:
            return existing_user, False

        # Try to find by email (in case Google ID changed)
        existing_user = await self.user_repository.get_by_email(google_user_info.email)
        if existing_user:
            # Update Google ID

            update_data = UserUpdate(google_id=google_user_info.id)
            updated_user = await self.user_repository.update_user(
                existing_user.pk, update_data
            )
            return updated_user or existing_user, False

        # Create new user
        username = await self._generate_unique_username(google_user_info)

        user_data = UserCreate(
            email=google_user_info.email,
            google_id=google_user_info.id,
            username=username,
            email_verified=google_user_info.verified_email,
        )

        new_user = await self.user_repository.create_user(user_data)
        return new_user, True

    async def _generate_unique_username(self, google_user_info: GoogleUserInfo) -> str:
        """Generate unique username from Google user info."""
        # Start with given name or email prefix
        base_username = (
            google_user_info.given_name or google_user_info.email.split("@")[0]
        )

        # Clean username (remove non-alphanumeric characters)

        base_username = re.sub(r"[^a-zA-Z0-9]", "", base_username).lower()

        # Ensure minimum length - generate natural citizen username
        if len(base_username) < 3:
            base_username = self._generate_citizen_username()

        # Check if username is available
        username = base_username
        counter = 1

        while await self.user_repository.get_by_username(username):
            username = f"{base_username}{counter}"
            counter += 1

            # Prevent infinite loop
            if counter > 9999:
                username = f"{base_username}{secrets.randbelow(99999)}"
                break

        return username

    def _generate_citizen_username(self) -> str:
        """Generate a natural citizen username using cryptographically secure random words."""
        adjective = secrets.choice(ADJECTIVES_LIST)
        noun = secrets.choice(NOUNS_LIST)
        random_number = secrets.randbelow(65536)  # 16-bit number (0-65535)
        return f"citizen-{adjective}-{noun}-{random_number}"

    async def _get_user_permissions(self, user: User) -> list[str]:
        """Get user permissions based on role and loyalty score."""

        permissions = [
            "view_content",
            "create_posts",
            "send_private_messages",
            "appeal_rejections",
            "flag_content",
        ]

        if user.role in [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPERADMIN]:
            permissions.extend(
                [
                    "view_rejected_posts",
                    "apply_sanctions",
                    "adjudicate_appeals",
                    "moderate_flags",
                    "content_preview",
                ]
            )

        if user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            permissions.extend(
                [
                    "view_private_messages",
                    "override_tags",
                    "escalate_sanctions",
                    "admin_dashboard",
                ]
            )

        if user.role == UserRole.SUPERADMIN:
            permissions.extend(
                [
                    "change_user_roles",
                    "delete_accounts",
                    "system_configuration",
                ]
            )

        # Loyalty-based permissions using service
        loyalty_service = await get_loyalty_score_service()
        thresholds = await loyalty_service.get_score_thresholds()

        if user.loyalty_score >= thresholds.get("topic_creation", 0):
            permissions.append("create_topics")

        # Additional high-loyalty permissions
        if user.loyalty_score >= 500:  # High loyalty threshold
            permissions.extend(["priority_moderation", "extended_appeals"])

        return permissions
