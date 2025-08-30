"""Sanctions API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.rate_limiting import check_sanctions_rate_limit
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.sanction import Sanction
from therobotoverlord_api.database.models.sanction import SanctionCreate
from therobotoverlord_api.database.models.sanction import SanctionType
from therobotoverlord_api.database.models.sanction import SanctionUpdate
from therobotoverlord_api.database.models.sanction import SanctionWithDetails
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.sanction_service import SanctionService
from therobotoverlord_api.services.sanction_service import get_sanction_service

router = APIRouter(prefix="/sanctions", tags=["sanctions"])


def require_moderator_or_admin(current_user: User) -> None:
    """Ensure the current user is a moderator or admin."""
    if current_user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only moderators and admins can manage sanctions",
        )


@router.post("/")
async def apply_sanction(
    sanction_data: SanctionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
    _: Annotated[None, Depends(check_sanctions_rate_limit)] = None,
) -> Sanction | None:
    """Apply a sanction to a user (moderators and admins only)."""
    require_moderator_or_admin(current_user)

    try:
        return await sanction_service.apply_sanction(
            sanction_data,
            current_user.pk,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/")
async def get_all_sanctions(
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
    sanction_type: Annotated[SanctionType | None, Query()] = None,
    *,
    active_only: bool = False,
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    _: Annotated[None, Depends(check_sanctions_rate_limit)] = None,
) -> list[SanctionWithDetails]:
    """List all sanctions (moderators and admins only)."""
    require_moderator_or_admin(current_user)

    return await sanction_service.get_all_sanctions(
        sanction_type,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@router.get("/{sanction_id}")
async def get_sanction(
    sanction_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
    _: Annotated[None, Depends(check_sanctions_rate_limit)] = None,
) -> Sanction:
    """Get a specific sanction (moderators and admins only)."""
    require_moderator_or_admin(current_user)

    sanction = await sanction_service.sanction_repository.get_by_pk(sanction_id)
    if not sanction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sanction not found",
        )

    return sanction


@router.put("/{sanction_id}")
async def update_sanction(
    sanction_id: UUID,
    sanction_data: SanctionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
    _: Annotated[None, Depends(check_sanctions_rate_limit)] = None,
) -> Sanction:
    """Update a sanction (moderators and admins only)."""
    require_moderator_or_admin(current_user)

    try:
        updated_sanction = await sanction_service.update_sanction(
            sanction_id,
            sanction_data,
        )
        if not updated_sanction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sanction not found",
            )
        return updated_sanction
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/{sanction_id}")
async def remove_sanction(
    sanction_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
    _: Annotated[None, Depends(check_sanctions_rate_limit)] = None,
) -> dict:
    """Remove (deactivate) a sanction (moderators and admins only)."""
    require_moderator_or_admin(current_user)

    success = await sanction_service.remove_sanction(sanction_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sanction not found",
        )

    return {"message": "Sanction removed successfully"}


@router.get("/users/{user_id}")
async def get_user_sanctions(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
    *,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Sanction]:
    """Get sanctions for a specific user."""
    # Users can view their own sanctions, moderators/admins can view any user's sanctions
    if current_user.pk != user_id:
        require_moderator_or_admin(current_user)

    return await sanction_service.get_user_sanctions(
        user_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{user_id}/summary")
async def get_user_sanction_summary(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
) -> dict:
    """Get sanction summary for a specific user."""
    # Users can view their own summary, moderators/admins can view any user's summary
    if current_user.pk != user_id:
        require_moderator_or_admin(current_user)

    return await sanction_service.get_sanction_summary(user_id)


@router.get("/users/{user_id}/active")
async def get_user_active_sanctions(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
) -> list[Sanction]:
    """Get active sanctions for a specific user."""
    # Users can view their own active sanctions, moderators/admins can view any user's
    if current_user.pk != user_id:
        require_moderator_or_admin(current_user)

    return await sanction_service.get_active_user_sanctions(user_id)


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
) -> dict:
    """Get user's current permissions based on active sanctions."""
    # Users can check their own permissions, moderators/admins can check any user's
    if current_user.pk != user_id:
        require_moderator_or_admin(current_user)

    return {
        "user_pk": user_id,
        "is_banned": await sanction_service.is_user_banned(user_id),
        "can_post": await sanction_service.can_user_post(user_id),
        "can_create_topics": await sanction_service.can_user_create_topics(user_id),
    }


@router.post("/expire")
async def expire_sanctions(
    current_user: Annotated[User, Depends(get_current_user)],
    sanction_service: Annotated[SanctionService, Depends(get_sanction_service)],
) -> dict:
    """Expire sanctions that have passed their expiration date (admins only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can expire sanctions",
        )

    expired_count = await sanction_service.expire_sanctions()
    return {
        "message": f"Expired {expired_count} sanctions",
        "expired_count": expired_count,
    }
