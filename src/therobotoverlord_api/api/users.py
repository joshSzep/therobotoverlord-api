"""User Management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.database.models.badge import UserBadge
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.post import Post
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.models.user import UserProfile
from therobotoverlord_api.database.models.user import UserUpdate
from therobotoverlord_api.services.user_service import UserService
from therobotoverlord_api.services.user_service import get_user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/profile")
async def get_user_profile(
    user_id: UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserProfile:
    """Get public user profile."""
    profile = await user_service.get_user_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return profile


@router.get("/{user_id}/graveyard")
async def get_user_graveyard(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Post]:
    """Get user's rejected posts (private - own posts only)."""
    # Users can only view their own graveyard
    if current_user.pk != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own graveyard",
        )

    return await user_service.get_user_graveyard(user_id, limit, offset)


@router.get("/registry")
async def get_user_registry(
    user_service: Annotated[UserService, Depends(get_user_service)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    role_filter: Annotated[UserRole | None, Query()] = None,
) -> list[UserProfile]:
    """Get public citizen registry."""
    return await user_service.get_user_registry(limit, offset, role_filter)


@router.put("/{user_id}")
async def update_user_profile(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """Update user profile."""
    # Users can only update their own profile, unless they're admin/moderator
    if current_user.pk != user_id and current_user.role not in [
        UserRole.ADMIN,
        UserRole.MODERATOR,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile",
        )

    # Non-admin users cannot change role, ban status, or sanction status
    if current_user.role != UserRole.ADMIN:
        user_data.role = None
        user_data.is_banned = None
        user_data.is_sanctioned = None
        user_data.loyalty_score = None

    try:
        updated_user = await user_service.update_user(user_id, user_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{user_id}/badges")
async def get_user_badges(
    user_id: UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> list[UserBadge]:
    """Get user's badges."""
    return await user_service.get_user_badges(user_id)


@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """Get user's activity feed."""
    return await user_service.get_user_activity(user_id, limit, offset)


@router.delete("/{user_id}")
async def delete_user_account(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict:
    """Delete user account (GDPR compliance)."""
    # Users can only delete their own account, unless they're admin
    if current_user.pk != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own account",
        )

    try:
        success = await user_service.delete_user_account(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return {"message": "User account deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
