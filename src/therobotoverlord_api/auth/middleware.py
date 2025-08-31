"""Authentication middleware for FastAPI."""

import logging

from uuid import UUID

from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from therobotoverlord_api.auth.jwt_service import JWTService
from therobotoverlord_api.auth.models import TokenClaims
from therobotoverlord_api.auth.session_service import SessionService
from therobotoverlord_api.config.auth import get_auth_settings
from therobotoverlord_api.database.models.user import UserRole
from therobotoverlord_api.database.repositories.user import UserRepository
from therobotoverlord_api.services.loyalty_score_service import (
    get_loyalty_score_service,
)


class AuthenticatedUser:
    """Authenticated user context."""

    def __init__(
        self,
        user_id: UUID,
        role: UserRole,
        permissions: list[str],
        session_id: str,
        token_version: int = 1,
    ):
        self.user_id = user_id
        self.role = role
        self.permissions = permissions
        self.session_id = session_id
        self.token_version = token_version

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role or higher."""
        role_hierarchy = {
            UserRole.CITIZEN: 0,
            UserRole.MODERATOR: 1,
            UserRole.ADMIN: 2,
            UserRole.SUPERADMIN: 3,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(role, 0)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for handling authentication and token refresh."""

    def __init__(self, app):
        super().__init__(app)
        self.jwt_service = JWTService()
        self.session_service = SessionService()
        self.user_repository = UserRepository()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with authentication handling."""
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        # Extract tokens from cookies
        access_token = request.cookies.get("__Secure-trl_at")
        refresh_token = request.cookies.get("__Secure-trl_rt")

        if not access_token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Access token required"},
            )

        # Try to validate access token
        claims = self.jwt_service.decode_token_claims(access_token)

        if claims:
            # Token is valid, set user context
            user = await self._get_authenticated_user(claims)
            if user:
                request.state.user = user
                return await call_next(request)

        # Access token invalid/expired, try refresh
        if refresh_token:
            new_tokens = await self._refresh_tokens(refresh_token, request)
            if new_tokens:
                access_token, refresh_token = new_tokens
                claims = self.jwt_service.decode_token_claims(access_token)

                if claims:
                    user = await self._get_authenticated_user(claims)
                    if user:
                        request.state.user = user
                        response = await call_next(request)

                        # Set new tokens in response cookies
                        self._set_auth_cookies(response, access_token, refresh_token)
                        return response

        # Authentication failed
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or expired authentication"},
        )

    async def _get_authenticated_user(
        self, claims: TokenClaims
    ) -> AuthenticatedUser | None:
        """Get authenticated user from token claims."""
        try:
            user = await self.user_repository.get_by_pk(claims.sub)
            if not user or user.is_banned:
                return None

            return AuthenticatedUser(
                user_id=user.pk,
                role=user.role,
                permissions=claims.permissions,
                session_id=claims.sid,
                token_version=claims.token_version,
            )
        except Exception:
            return None

    async def _refresh_tokens(
        self, refresh_token: str, request: Request
    ) -> tuple[str, str] | None:
        """Refresh access token using refresh token."""
        try:
            # Extract session ID from refresh token
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
            new_jwt_service = JWTService()
            token_pair = new_jwt_service.create_token_pair(
                user_id=user.pk,
                role=user.role,
                permissions=await self._get_user_permissions(user),
                session_id=session_id,
            )

            # Rotate refresh token
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent")

            success = await self.session_service.rotate_refresh_token(
                session_id=session_id,
                old_refresh_token=refresh_token,
                new_refresh_token=token_pair.refresh_token.token,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            if success:
                return token_pair.access_token.token, token_pair.refresh_token.token

        except Exception as e:
            # Log token refresh failure but don't raise
            # This allows the request to continue with expired token
            logger = logging.getLogger(__name__)
            logger.warning(f"Token refresh failed: {e}")

        return None

    async def _get_user_permissions(self, user) -> list[str]:
        """Get user permissions based on role and loyalty score."""
        permissions = ["view_content", "create_posts", "send_private_messages"]

        if user.role in [UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPERADMIN]:
            permissions.extend(
                [
                    "view_rejected_posts",
                    "apply_sanctions",
                    "adjudicate_appeals",
                    "moderate_flags",
                ]
            )

        if user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            permissions.extend(
                [
                    "view_private_messages",
                    "override_tags",
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

        # Check loyalty-based permissions using service
        loyalty_service = await get_loyalty_score_service()
        thresholds = await loyalty_service.get_score_thresholds()

        if user.loyalty_score >= thresholds.get("topic_creation", 0):
            permissions.append("create_topics")

        return permissions

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public and doesn't require authentication."""
        public_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/callback",
            "/api/v1/auth/jwks",
            "/api/v1/queue/overview",
            "/api/v1/leaderboard",
            "/api/v1/tags",
            "/docs",
            "/openapi.json",
            "/health",
        ]

        # Read-only endpoints for anonymous visitors (browse content)
        visitor_read_paths = [
            "/api/v1/topics/categories",
            "/api/v1/topics/feed",
            "/api/v1/topics/trending",
            "/api/v1/topics/popular",
            "/api/v1/topics/featured",
            "/api/v1/posts/feed",
            "/api/v1/posts/trending",
            "/api/v1/posts/popular",
        ]

        # Allow GET requests to specific topic and post endpoints
        if path.startswith("/api/v1/topics/") and not path.endswith("/moderate"):
            return True
        if path.startswith("/api/v1/posts/") and not path.endswith("/moderate"):
            return True

        return any(
            path.startswith(public_path)
            for public_path in public_paths + visitor_read_paths
        )

    def _set_auth_cookies(
        self, response: Response, access_token: str, refresh_token: str
    ) -> None:
        """Set authentication cookies on response."""
        settings = get_auth_settings()

        response.set_cookie(
            key="__Secure-trl_at",
            value=access_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            domain=settings.cookie_domain,
            path="/",
        )

        response.set_cookie(
            key="__Secure-trl_rt",
            value=refresh_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            domain=settings.cookie_domain,
            path="/",
        )

    def _get_client_ip(self, request: Request) -> str | None:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        if request.client and hasattr(request.client, "host"):
            return request.client.host

        return None


class OptionalAuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for optional authentication (sets user context if available)."""

    def __init__(self, app):
        super().__init__(app)
        self.jwt_service = JWTService()
        self.user_repository = UserRepository()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with optional authentication."""
        access_token = request.cookies.get("__Secure-trl_at")

        if access_token:
            claims = self.jwt_service.decode_token_claims(access_token)
            if claims:
                user = await self._get_authenticated_user(claims)
                if user:
                    request.state.user = user

        return await call_next(request)

    async def _get_authenticated_user(
        self, claims: TokenClaims
    ) -> AuthenticatedUser | None:
        """Get authenticated user from token claims."""
        try:
            user = await self.user_repository.get_by_pk(claims.sub)
            if not user or user.is_banned:
                return None

            return AuthenticatedUser(
                user_id=user.pk,
                role=user.role,
                permissions=claims.permissions,
                session_id=claims.sid,
                token_version=claims.token_version,
            )
        except Exception:
            return None


# Dependency for getting current user
async def get_current_user(request: Request) -> AuthenticatedUser:
    """Dependency to get current authenticated user."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required",
        )
    return user


# Dependency for optional current user
async def get_current_user_optional(request: Request) -> AuthenticatedUser | None:
    """Dependency to get current user if authenticated."""
    return getattr(request.state, "user", None)


# Security scheme for OpenAPI documentation
bearer_scheme = HTTPBearer(auto_error=False)
