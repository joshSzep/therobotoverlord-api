"""Flag API endpoints for content reporting and moderation."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_role
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.flag import Flag
from therobotoverlord_api.database.models.flag import FlagCreate
from therobotoverlord_api.database.models.flag import FlagSummary
from therobotoverlord_api.database.models.flag import FlagUpdate
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.flag_service import FlagService
from therobotoverlord_api.services.flag_service import get_flag_service

router = APIRouter(prefix="/flags", tags=["flags"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_flag(
    flag_data: FlagCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    flag_service: Annotated[FlagService, Depends(get_flag_service)],
) -> Flag:
    """Flag content for review."""

    try:
        return await flag_service.create_flag(flag_data, current_user.pk)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/")
async def get_flags(
    _: Annotated[User, Depends(require_role(UserRole.MODERATOR))],
    flag_service: Annotated[FlagService, Depends(get_flag_service)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[str | None, Query()] = None,
) -> list[FlagSummary]:
    """List flags for moderation review (moderators only)."""
    flags = await flag_service.flag_repo.get_flags_for_review(
        limit, offset, status_filter
    )

    return [
        FlagSummary(
            pk=flag.pk,
            post_pk=flag.post_pk,
            topic_pk=flag.topic_pk,
            flagger_pk=flag.flagger_pk,
            reason=flag.reason,
            status=flag.status,
            reviewed_by_pk=flag.reviewed_by_pk,
            reviewed_at=flag.reviewed_at,
            created_at=flag.created_at,
        )
        for flag in flags
    ]


@router.put("/{flag_id}")
async def review_flag(
    flag_id: UUID,
    flag_update: FlagUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.MODERATOR))],
    flag_service: Annotated[FlagService, Depends(get_flag_service)],
) -> Flag:
    """Review a flag (moderators only)."""

    try:
        return await flag_service.review_flag(flag_id, flag_update, current_user.pk)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{flag_id}")
async def get_flag(
    flag_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    flag_service: Annotated[FlagService, Depends(get_flag_service)],
) -> Flag:
    """Get flag details."""
    flag = await flag_service.flag_repo.get_by_pk(flag_id)

    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flag not found",
        )

    # Only flagger, moderators, or admins can view flag details
    if flag.flagger_pk != current_user.pk and current_user.role not in [
        UserRole.MODERATOR,
        UserRole.ADMIN,
        UserRole.SUPERADMIN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return flag


@router.get("/user/{user_id}")
async def get_user_flags(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    flag_service: Annotated[FlagService, Depends(get_flag_service)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[FlagSummary]:
    """Get flags submitted by a user."""
    # Users can only see their own flags, moderators+ can see any user's flags
    if user_id != current_user.pk and current_user.role not in [
        UserRole.MODERATOR,
        UserRole.ADMIN,
        UserRole.SUPERADMIN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    flags = await flag_service.flag_repo.get_user_flags(user_id, limit, offset)

    return [
        FlagSummary(
            pk=flag.pk,
            post_pk=flag.post_pk,
            topic_pk=flag.topic_pk,
            flagger_pk=flag.flagger_pk,
            reason=flag.reason,
            status=flag.status,
            reviewed_by_pk=flag.reviewed_by_pk,
            reviewed_at=flag.reviewed_at,
            created_at=flag.created_at,
        )
        for flag in flags
    ]


@router.get("/content/{content_type}/{content_id}")
async def get_content_flags(
    content_type: str,
    content_id: UUID,
    current_user: Annotated[User, Depends(require_role(UserRole.MODERATOR))],
    flag_service: Annotated[FlagService, Depends(get_flag_service)],
) -> list[FlagSummary]:
    """Get all flags for specific content (moderators only)."""
    if content_type not in ["post", "topic"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type must be 'post' or 'topic'",
        )

    flags = await flag_service.flag_repo.get_content_flags(content_id, content_type)

    return [
        FlagSummary(
            pk=flag.pk,
            post_pk=flag.post_pk,
            topic_pk=flag.topic_pk,
            flagger_pk=flag.flagger_pk,
            reason=flag.reason,
            status=flag.status,
            reviewed_by_pk=flag.reviewed_by_pk,
            reviewed_at=flag.reviewed_at,
            created_at=flag.created_at,
        )
        for flag in flags
    ]


@router.get("/stats/user/{user_id}")
async def get_user_flag_stats(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    flag_service: Annotated[FlagService, Depends(get_flag_service)],
) -> dict[str, int]:
    """Get flag statistics for a user."""
    # Users can see their own stats, moderators+ can see any user's stats
    if user_id != current_user.pk and current_user.role not in [
        UserRole.MODERATOR,
        UserRole.ADMIN,
        UserRole.SUPERADMIN,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return await flag_service.get_user_flag_stats(user_id)


@router.get("/stats/content/{content_type}/{content_id}")
async def get_content_flag_stats(
    content_type: str,
    content_id: UUID,
    current_user: Annotated[User, Depends(require_role(UserRole.MODERATOR))],
    flag_service: Annotated[FlagService, Depends(get_flag_service)],
) -> dict[str, int]:
    """Get flag statistics for specific content (moderators only)."""
    if content_type not in ["post", "topic"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type must be 'post' or 'topic'",
        )

    return await flag_service.get_content_flag_summary(content_id, content_type)
