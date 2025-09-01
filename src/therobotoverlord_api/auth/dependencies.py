"""Authentication dependencies for FastAPI endpoints."""

from collections.abc import Callable

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status

from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.repositories.user import UserRepository


async def get_current_user(request: Request) -> User:
    """Get the current authenticated user from the request."""
    # Extract tokens from cookies
    access_token = request.cookies.get("__Secure-trl_at")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token required"
        )

    # Import here to avoid circular imports
    from therobotoverlord_api.auth.jwt_service import JWTService

    jwt_service = JWTService()

    try:
        # Validate token
        payload = jwt_service.decode_token(access_token)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        # Get user from database
        user_repo = UserRepository()
        user = await user_repo.get_by_pk(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if user.is_banned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is banned"
            )

        return user

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from e


# Create dependency instance to avoid function calls in defaults
get_current_user_dependency = Depends(get_current_user)


def require_role(required_role: UserRole) -> Callable:
    """Dependency factory to require a specific role or higher."""

    async def role_dependency(current_user: User = get_current_user_dependency) -> User:
        """Check if user has required role."""
        role_hierarchy = {
            UserRole.CITIZEN: 0,
            UserRole.MODERATOR: 1,
            UserRole.ADMIN: 2,
            UserRole.SUPERADMIN: 3,
        }

        user_level = role_hierarchy.get(current_user.role, -1)
        required_level = role_hierarchy.get(required_role, 999)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}",
            )

        return current_user

    return role_dependency


async def get_optional_user(request: Request) -> User | None:
    """Get the current user if authenticated, otherwise None."""
    # Extract tokens from cookies for optional auth
    access_token = request.cookies.get("__Secure-trl_at")
    if not access_token:
        return None

    # Import here to avoid circular imports
    from therobotoverlord_api.auth.jwt_service import JWTService

    jwt_service = JWTService()

    try:
        # Validate token
        payload = jwt_service.decode_token(access_token)
        user_id = payload.get("user_id")

        if not user_id:
            return None

        # Get user from database
        user_repo = UserRepository()
        user = await user_repo.get_by_pk(user_id)

        if not user or user.is_banned:
            return None

        return user

    except Exception:
        # Invalid token, return None for optional auth
        return None


# Convenience dependencies for common roles
require_moderator = require_role(UserRole.MODERATOR)
require_admin = require_role(UserRole.ADMIN)
require_superadmin = require_role(UserRole.SUPERADMIN)
