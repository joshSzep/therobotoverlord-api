"""Appeals API endpoints for The Robot Overlord API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_moderator
from therobotoverlord_api.database.models.appeal import AppealCreate
from therobotoverlord_api.database.models.appeal import AppealDecision
from therobotoverlord_api.database.models.appeal import AppealEligibility
from therobotoverlord_api.database.models.appeal import AppealResponse
from therobotoverlord_api.database.models.appeal import AppealStats
from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal import AppealWithContent
from therobotoverlord_api.database.models.appeal_with_editing import (
    AppealDecisionWithEdit,
)
from therobotoverlord_api.database.models.base import ContentType
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.appeal_service import AppealService
from therobotoverlord_api.services.content_versioning_service import ContentVersioningService

router = APIRouter(prefix="/appeals", tags=["appeals"])


def get_appeal_service() -> AppealService:
    """Get appeal service instance."""
    return AppealService()


def get_content_versioning_service() -> ContentVersioningService:
    """Get content versioning service instance."""
    return ContentVersioningService()


# User-facing endpoints
@router.post("/", response_model=AppealWithContent, status_code=status.HTTP_201_CREATED)
async def submit_appeal(
    appeal_data: AppealCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Submit a new appeal."""
    appeal, error = await appeal_service.submit_appeal(current_user.pk, appeal_data)

    if not appeal:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Get the full appeal with content details
    appeal_with_content = await appeal_service.get_appeal_by_id(appeal.pk)
    if not appeal_with_content:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created appeal",
        )

    return appeal_with_content


@router.get("/eligibility", response_model=AppealEligibility)
async def check_appeal_eligibility(
    content_type: Annotated[
        ContentType, Query(description="Type of content to appeal")
    ],
    content_pk: Annotated[UUID, Query(description="ID of content to appeal")],
    current_user: Annotated[User, Depends(get_current_user)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Check if user is eligible to appeal specific content."""
    return await appeal_service.check_appeal_eligibility(
        current_user.pk, content_type, content_pk
    )


@router.get("/my-appeals", response_model=AppealResponse)
async def get_my_appeals(
    current_user: Annotated[User, Depends(get_current_user)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
    status: Annotated[
        AppealStatus | None, Query(description="Filter by appeal status")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
):
    """Get current user's appeals."""
    return await appeal_service.get_user_appeals(
        current_user.pk, status, page, page_size
    )


@router.get("/my-appeals/{appeal_pk}", response_model=AppealWithContent)
async def get_my_appeal(
    appeal_pk: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Get a specific appeal by the current user."""
    appeal = await appeal_service.get_appeal_by_id(appeal_pk)

    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appeal not found"
        )

    # Verify ownership
    if appeal.appellant_pk != current_user.pk:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own appeals",
        )

    return appeal


@router.patch("/my-appeals/{appeal_pk}/withdraw", response_model=dict[str, str])
async def withdraw_appeal(
    appeal_pk: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Withdraw an appeal."""
    success, error = await appeal_service.withdraw_appeal(appeal_pk, current_user.pk)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "Appeal withdrawn successfully"}


@router.get("/content/{content_type}/{content_pk}", response_model=dict)
async def get_appealable_content(
    content_type: ContentType,
    content_pk: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Get content details for appeal submission."""
    content = await appeal_service.get_appealable_content(
        current_user.pk, content_type, content_pk
    )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found or not appealable",
        )

    return content


# Moderator/Admin endpoints
@router.get("/queue", response_model=AppealResponse)
async def get_appeals_queue(
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
    status: Annotated[
        AppealStatus, Query(description="Filter by status")
    ] = AppealStatus.PENDING,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
):
    """Get appeals queue for moderators."""
    return await appeal_service.get_appeals_queue(status, page, page_size)


@router.get("/queue/{appeal_pk}", response_model=AppealWithContent)
async def get_appeal_for_review(
    appeal_pk: UUID,
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Get a specific appeal for review."""
    appeal = await appeal_service.get_appeal_by_id(appeal_pk)

    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appeal not found"
        )

    return appeal


@router.patch("/queue/{appeal_pk}/assign", response_model=dict[str, str])
async def assign_appeal_for_review(
    appeal_pk: UUID,
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Assign an appeal to current moderator for review."""
    success, error = await appeal_service.assign_appeal_for_review(
        appeal_pk, current_user.pk
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "Appeal assigned for review"}


@router.patch("/queue/{appeal_pk}/sustain", response_model=dict[str, str])
async def sustain_appeal(
    appeal_pk: UUID,
    decision_data: AppealDecision,
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Sustain (grant) an appeal."""
    success, error = await appeal_service.decide_appeal(
        appeal_pk, current_user.pk, AppealStatus.SUSTAINED, decision_data
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "Appeal sustained successfully"}


@router.patch("/queue/{appeal_pk}/deny", response_model=dict[str, str])
async def deny_appeal(
    appeal_pk: UUID,
    decision_data: AppealDecision,
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Deny an appeal."""
    success, error = await appeal_service.decide_appeal(
        appeal_pk, current_user.pk, AppealStatus.DENIED, decision_data
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "Appeal denied successfully"}


@router.patch("/queue/{appeal_pk}/sustain-with-edit", response_model=dict[str, str])
async def sustain_appeal_with_edit(
    appeal_pk: UUID,
    decision_data: AppealDecisionWithEdit,
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
    edited_content: dict[str, str | None] | None = None,
):
    """Sustain (grant) an appeal with optional content editing."""
    success, error = await appeal_service.decide_appeal_with_edit(
        appeal_pk,
        current_user.pk,
        AppealStatus.SUSTAINED,
        decision_data,
        edited_content,
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "Appeal sustained with content restoration"}


@router.patch("/queue/{appeal_pk}/deny-with-edit", response_model=dict[str, str])
async def deny_appeal_with_edit(
    appeal_pk: UUID,
    decision_data: AppealDecisionWithEdit,
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Deny an appeal with detailed reasoning."""
    success, error = await appeal_service.decide_appeal_with_edit(
        appeal_pk, current_user.pk, AppealStatus.DENIED, decision_data
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"message": "Appeal denied"}


@router.get("/stats", response_model=AppealStats)
async def get_appeal_statistics(
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Get appeal statistics for moderators."""
    return await appeal_service.get_appeal_statistics()


@router.get("/user/{user_pk}/appeals", response_model=AppealResponse)
async def get_user_appeals_admin(
    user_pk: UUID,
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
    status: Annotated[
        AppealStatus | None, Query(description="Filter by appeal status")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
):
    """Get appeals for a specific user (admin/moderator only)."""
    return await appeal_service.get_user_appeals(user_pk, status, page, page_size)


@router.get("/content-versions/{content_pk}/history", response_model=list)
async def get_content_version_history(
    content_pk: UUID,
    current_user: Annotated[User, Depends(require_moderator)],
    versioning_service: Annotated[ContentVersioningService, Depends(get_content_versioning_service)],
):
    """Get version history for content (moderator only)."""
    return await versioning_service.get_content_history(content_pk)


@router.get("/content-versions/{content_pk}/{version_number}/diff")
async def get_content_version_diff(
    content_pk: UUID,
    version_number: int,
    current_user: Annotated[User, Depends(require_moderator)],
    versioning_service: Annotated[ContentVersioningService, Depends(get_content_versioning_service)],
):
    """Get diff between content versions (moderator only)."""
    # Get content history to find the version by number
    history = await versioning_service.get_content_history(content_pk)
    version = next((v for v in history if v.version_number == version_number), None)

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version diff not found"
        )

    diff = await versioning_service.get_version_diff(version.pk)

    if not diff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version diff not found"
        )

    return diff
