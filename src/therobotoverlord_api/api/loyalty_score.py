"""Loyalty Score Management API endpoints for The Robot Overlord."""

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
from therobotoverlord_api.database.models.loyalty_score import ContentType
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventFilters
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventOutcome
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventResponse
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreAdjustment
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreBreakdown
from therobotoverlord_api.database.models.loyalty_score import LoyaltyScoreStats
from therobotoverlord_api.database.models.loyalty_score import ModerationEvent
from therobotoverlord_api.database.models.loyalty_score import ModerationEventType
from therobotoverlord_api.database.models.loyalty_score import UserLoyaltyProfile
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.loyalty_score_service import (
    get_loyalty_score_service,
)

router = APIRouter(prefix="/loyalty", tags=["loyalty-score"])


@router.get("/me", response_model=UserLoyaltyProfile)
async def get_my_loyalty_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get complete loyalty profile for the authenticated user.

    Includes current score, rank, breakdown, recent events, and score history.
    """
    service = await get_loyalty_score_service()

    try:
        return await service.get_user_loyalty_profile(current_user.pk)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/user/{user_pk}", response_model=UserLoyaltyProfile)
async def get_user_loyalty_profile(user_pk: UUID):
    """
    Get loyalty profile for a specific user.

    Public endpoint - anyone can view loyalty profiles as part of the registry.
    """
    service = await get_loyalty_score_service()

    try:
        return await service.get_user_loyalty_profile(user_pk)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/me/breakdown", response_model=LoyaltyScoreBreakdown)
async def get_my_score_breakdown(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get detailed score breakdown for the authenticated user.

    Shows how loyalty score is calculated across different content types.
    """
    service = await get_loyalty_score_service()

    try:
        return await service.get_user_score_breakdown(current_user.pk)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/user/{user_pk}/breakdown", response_model=LoyaltyScoreBreakdown)
async def get_user_score_breakdown(user_pk: UUID):
    """
    Get detailed score breakdown for a specific user.

    Public endpoint for transparency in the loyalty scoring system.
    """
    service = await get_loyalty_score_service()

    try:
        return await service.get_user_score_breakdown(user_pk)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/me/events", response_model=LoyaltyEventResponse)
async def get_my_loyalty_events(
    current_user: Annotated[User, Depends(get_current_user)],
    event_type: Annotated[ModerationEventType | None, Query()] = None,
    content_type: Annotated[ContentType | None, Query()] = None,
    outcome: Annotated[LoyaltyEventOutcome | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """
    Get moderation events for the authenticated user.

    Citizens can view their own loyalty score history and understand
    how the Robot Overlord has evaluated their contributions.
    """
    service = await get_loyalty_score_service()

    filters = LoyaltyEventFilters(
        event_type=event_type,
        content_type=content_type,
        outcome=outcome,
    )

    return await service.get_user_events(current_user.pk, filters, page, page_size)


@router.get("/user/{user_pk}/events", response_model=LoyaltyEventResponse)
async def get_user_loyalty_events(
    user_pk: UUID,
    event_type: Annotated[ModerationEventType | None, Query()] = None,
    content_type: Annotated[ContentType | None, Query()] = None,
    outcome: Annotated[LoyaltyEventOutcome | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """
    Get moderation events for a specific user.

    Public endpoint for transparency - citizens can see how others
    have been evaluated by the Robot Overlord.
    """
    service = await get_loyalty_score_service()

    filters = LoyaltyEventFilters(
        event_type=event_type,
        content_type=content_type,
        outcome=outcome,
    )

    return await service.get_user_events(user_pk, filters, page, page_size)


@router.get("/stats", response_model=LoyaltyScoreStats)
async def get_loyalty_system_stats():
    """
    Get system-wide loyalty score statistics.

    Public endpoint showing overall health and distribution of the
    Robot Overlord's evaluation system.
    """
    service = await get_loyalty_score_service()
    return await service.get_system_stats()


@router.get("/thresholds")
async def get_score_thresholds():
    """
    Get current score thresholds for various privileges.

    Public endpoint so citizens know what they're working toward.
    """
    service = await get_loyalty_score_service()
    thresholds = await service.get_score_thresholds()

    return {
        "status": "ok",
        "data": thresholds,
        "description": {
            "topic_creation": "Minimum score to create topics (top 10%)",
            "top_10_percent": "Score threshold for top 10% of citizens",
            "priority_moderation": "Score for priority queue processing",
            "extended_appeals": "Score for additional appeal attempts",
        },
    }


@router.get("/range")
async def get_users_by_score_range(
    min_score: Annotated[int, Query()],
    max_score: Annotated[int, Query()],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """
    Get users within a specific loyalty score range.

    Useful for analyzing score distribution and finding peers.
    """
    if min_score > max_score:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_score cannot be greater than max_score",
        )

    service = await get_loyalty_score_service()
    users = await service.get_users_by_score_range(min_score, max_score, limit)

    return {
        "status": "ok",
        "data": users,
        "range": {"min": min_score, "max": max_score},
        "count": len(users),
    }


# Admin-only endpoints
@router.post("/adjust", response_model=ModerationEvent)
async def apply_manual_adjustment(
    adjustment: LoyaltyScoreAdjustment,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
):
    """
    Apply manual loyalty score adjustment (Admin only).

    For correcting errors or applying special circumstances that
    the Robot Overlord cannot handle automatically.
    """
    service = await get_loyalty_score_service()

    try:
        return await service.apply_manual_adjustment(adjustment, current_user.pk)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/user/{user_pk}/recalculate")
async def recalculate_user_score(
    user_pk: UUID,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
):
    """
    Recalculate a user's loyalty score from scratch (Admin only).

    Useful for fixing data inconsistencies or after algorithm changes.
    """
    service = await get_loyalty_score_service()

    try:
        new_score = await service.recalculate_user_score(user_pk)
        return {
            "status": "ok",
            "message": f"User {user_pk} score recalculated",
            "new_score": new_score,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/events/recent")
async def get_recent_system_events(
    current_user: Annotated[User, Depends(require_role(UserRole.MODERATOR))],
    event_type: Annotated[ModerationEventType | None, Query()] = None,
    content_type: Annotated[ContentType | None, Query()] = None,
    outcome: Annotated[LoyaltyEventOutcome | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    """
    Get recent moderation events across all users (Moderator+ only).

    For monitoring system activity and identifying patterns.
    """
    service = await get_loyalty_score_service()

    filters = LoyaltyEventFilters(
        event_type=event_type,
        content_type=content_type,
        outcome=outcome,
    )

    events = await service.get_recent_events(filters, limit)

    return {
        "status": "ok",
        "data": events,
        "count": len(events),
        "filters_applied": filters,
    }


@router.post("/events/record", response_model=ModerationEvent)
async def record_moderation_event(
    user_pk: UUID,
    event_type: ModerationEventType,
    content_type: ContentType,
    content_pk: UUID,
    outcome: LoyaltyEventOutcome,
    current_user: Annotated[User, Depends(require_role(UserRole.MODERATOR))],
    reason: Annotated[str | None, Query()] = None,
):
    """
    Manually record a moderation event (Moderator+ only).

    For cases where automatic event recording fails or needs correction.
    """
    service = await get_loyalty_score_service()

    try:
        return await service.record_moderation_event(
            user_pk=user_pk,
            event_type=event_type,
            content_type=content_type,
            content_pk=content_pk,
            outcome=outcome,
            moderator_pk=current_user.pk,
            reason=reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
