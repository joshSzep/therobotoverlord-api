"""Badge API endpoints for The Robot Overlord API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from therobotoverlord_api.api.auth import get_current_user
from therobotoverlord_api.api.rbac import require_admin_permission
from therobotoverlord_api.api.rbac import require_moderator_permission
from therobotoverlord_api.database.models.badge import Badge
from therobotoverlord_api.database.models.badge import BadgeCreate
from therobotoverlord_api.database.models.badge import BadgeEligibilityCheck
from therobotoverlord_api.database.models.badge import BadgeUpdate
from therobotoverlord_api.database.models.badge import UserBadgeSummary
from therobotoverlord_api.database.models.badge import UserBadgeWithDetails
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.repositories.user import UserRepository
from therobotoverlord_api.services.badge_service import BadgeService
from therobotoverlord_api.services.rbac_service import RBACService

router = APIRouter(prefix="/api/v1/badges", tags=["badges"])
badge_service = BadgeService()


# Public Badge Endpoints
@router.get("/", response_model=list[Badge])
async def get_all_badges():
    """Get all active badges available in the system."""
    return await badge_service.get_all_badges()


@router.get("/{badge_id}", response_model=Badge)
async def get_badge(badge_id: UUID):
    """Get a specific badge by ID."""
    badge = await badge_service.get_badge_by_id(badge_id)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )
    return badge


@router.get("/{badge_id}/recipients", response_model=list[UserBadgeWithDetails])
async def get_badge_recipients(badge_id: UUID, limit: int = 100):
    """Get users who have received a specific badge."""
    badge = await badge_service.get_badge_by_id(badge_id)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )

    limit = min(limit, 500)  # Prevent excessive queries

    return await badge_service.get_badge_recipients(badge_id, limit)


# User Badge Endpoints
@router.get("/users/{user_id}", response_model=list[UserBadgeWithDetails])
async def get_user_badges(user_id: UUID):
    """Get all badges for a specific user (public endpoint)."""
    return await badge_service.get_user_badges(user_id)


@router.get("/users/{user_id}/summary", response_model=UserBadgeSummary)
async def get_user_badge_summary(user_id: UUID):
    """Get badge summary for a user (public endpoint)."""
    # We need to get the username - this could be improved by joining in the service
    user_repo = UserRepository()
    user = await user_repo.get_by_pk(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return await badge_service.get_user_badge_summary(user_id, user.username)


@router.get("/users/{user_id}/eligibility", response_model=list[BadgeEligibilityCheck])
async def check_user_badge_eligibility(
    user_id: UUID, current_user: Annotated[User, Depends(get_current_user)]
):
    """Check badge eligibility for a user (user can check own, moderators can check any)."""
    # Users can check their own eligibility, moderators can check any user's eligibility
    if user_id != current_user.pk:
        rbac_service = RBACService()
        is_moderator = await rbac_service.is_user_moderator(current_user.pk)
        if not is_moderator:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot check other users' badge eligibility",
            )

    return await badge_service.evaluate_badge_criteria_for_user(user_id)


# Admin Badge Management Endpoints
@router.post("/", response_model=Badge, status_code=status.HTTP_201_CREATED)
async def create_badge(
    badge_data: BadgeCreate,
    current_user: Annotated[User, Depends(require_admin_permission)],
):
    """Create a new badge (admin only)."""
    return await badge_service.create_badge(badge_data)


@router.put("/{badge_id}", response_model=Badge)
async def update_badge(
    badge_id: UUID,
    badge_data: BadgeUpdate,
    current_user: Annotated[User, Depends(require_admin_permission)],
):
    """Update a badge (admin only)."""
    badge = await badge_service.update_badge(badge_id, badge_data)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )
    return badge


@router.delete("/{badge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_badge(
    badge_id: UUID, current_user: Annotated[User, Depends(require_admin_permission)]
):
    """Delete a badge (admin only) - soft delete by setting is_active=False."""
    success = await badge_service.delete_badge(badge_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )


# Badge Awarding Endpoints
@router.post("/users/{user_id}/award/{badge_id}", status_code=status.HTTP_201_CREATED)
async def award_badge_manually(
    user_id: UUID,
    badge_id: UUID,
    current_user: Annotated[User, Depends(require_moderator_permission)],
):
    """Manually award a badge to a user (moderator/admin only)."""
    # Verify user exists
    user_repo = UserRepository()
    user = await user_repo.get_by_pk(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    awarded_badge = await badge_service.manually_award_badge(
        user_id, badge_id, current_user.pk
    )

    if not awarded_badge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Badge could not be awarded (user may already have it or badge is inactive)",
        )

    return {"message": "Badge awarded successfully", "badge_id": badge_id}


@router.delete(
    "/users/{user_id}/revoke/{badge_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_badge(
    user_id: UUID,
    badge_id: UUID,
    current_user: Annotated[User, Depends(require_admin_permission)],
):
    """Revoke a badge from a user (admin only)."""
    success = await badge_service.revoke_badge(user_id, badge_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have this badge",
        )


@router.post("/users/{user_id}/evaluate", status_code=status.HTTP_200_OK)
async def trigger_badge_evaluation(
    user_id: UUID, current_user: Annotated[User, Depends(require_moderator_permission)]
):
    """Trigger badge evaluation for a user (moderator/admin only)."""
    # Verify user exists
    user_repo = UserRepository()
    user = await user_repo.get_by_pk(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    awarded_badges = await badge_service.auto_award_eligible_badges(
        user_id, f"manual_evaluation_by_{current_user.pk}"
    )

    return {
        "message": f"Badge evaluation completed for user {user_id}",
        "awarded_badges_count": len(awarded_badges),
        "awarded_badge_ids": [str(badge.badge_pk) for badge in awarded_badges],
    }
