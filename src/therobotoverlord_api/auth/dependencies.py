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
    # Check if user is authenticated via middleware
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    user_repo = UserRepository()
    user = await user_repo.get_by_pk(request.state.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is banned"
        )

    return user


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
    if not hasattr(request.state, "user_id"):
        return None

    user_repo = UserRepository()
    user = await user_repo.get_by_pk(request.state.user_id)

    if not user or user.is_banned:
        return None

    return user
