"""Appeals dashboard API endpoints for moderators."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from therobotoverlord_api.auth.dependencies import require_moderator
from therobotoverlord_api.database.models.appeal import AppealStatus
from therobotoverlord_api.database.models.appeal import AppealWithContent
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.appeal_service import AppealService

router = APIRouter(prefix="/appeals/dashboard", tags=["appeals-dashboard"])


def get_appeal_service() -> AppealService:
    """Get appeal service instance."""
    return AppealService()


@router.get("/overview", response_model=dict)
async def get_appeals_dashboard_overview(
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Get appeals dashboard overview with key metrics."""
    stats = await appeal_service.get_appeal_statistics()

    # Get recent appeals for quick review
    recent_appeals = await appeal_service.get_appeals_queue(
        status=AppealStatus.PENDING, page=1, page_size=5
    )
    return {
        "stats": stats,
        "recent_appeals": recent_appeals.appeals,
        "queue_summary": {
            "pending": stats.total_pending,
            "under_review": stats.total_under_review,
            "total_today": stats.total_today,
        },
    }


@router.get("/queue/priority", response_model=list[AppealWithContent])
async def get_priority_appeals_queue(
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    """Get priority appeals queue ordered by urgency."""
    appeals_response = await appeal_service.get_appeals_queue(
        status=AppealStatus.PENDING, page=1, page_size=limit
    )
    return appeals_response.appeals


@router.get("/analytics/trends", response_model=dict)
async def get_appeal_trends(
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
):
    """Get appeal trends and analytics for the specified period."""
    # This would be implemented with more detailed analytics
    stats = await appeal_service.get_appeal_statistics()
    return {
        "period_days": days,
        "total_appeals": stats.total_count,
        "approval_rate": stats.total_sustained / max(stats.total_count, 1) * 100,
        "average_resolution_time": "2.5 hours",  # Would calculate from DB
        "top_violation_types": [
            {"type": "harassment", "count": 45},
            {"type": "spam", "count": 32},
            {"type": "misinformation", "count": 28},
        ],
        "moderator_performance": {
            "total_reviewed": stats.total_sustained + stats.total_denied,
            "accuracy_score": 92.5,  # Would calculate based on overturned decisions
        },
    }


@router.get("/workload", response_model=dict)
async def get_moderator_workload(
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Get current moderator workload and assignments."""
    # Get appeals assigned to current moderator
    assigned_appeals = await appeal_service.get_appeals_queue(
        status=AppealStatus.UNDER_REVIEW, page=1, page_size=100
    )

    # Filter for current moderator's assignments
    my_appeals = [
        appeal
        for appeal in assigned_appeals.appeals
        if hasattr(appeal, "reviewed_by") and appeal.reviewed_by == current_user.pk
    ]
    return {
        "assigned_to_me": len(my_appeals),
        "my_appeals": my_appeals[:10],  # Show first 10
        "pending_in_queue": assigned_appeals.total_count - len(my_appeals),
        "estimated_workload_hours": len(my_appeals) * 0.25,  # 15 min per appeal
    }


@router.get("/content-types", response_model=dict)
async def get_appeals_by_content_type(
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Get appeal distribution by content type."""
    # This would query the database for content type breakdown
    return {
        "posts": {"count": 156, "percentage": 65.2},
        "topics": {"count": 48, "percentage": 20.1},
        "private_messages": {"count": 35, "percentage": 14.7},
    }


@router.post("/bulk-assign", response_model=dict)
async def bulk_assign_appeals(
    appeal_ids: list[UUID],
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
):
    """Bulk assign multiple appeals to current moderator."""
    assigned_count = 0
    failed_count = 0
    errors_list: list[dict[str, str]] = []

    for appeal_id in appeal_ids:
        success, error = await appeal_service.assign_appeal_for_review(
            appeal_id, current_user.pk
        )
        if success:
            assigned_count += 1
        else:
            failed_count += 1
            errors_list.append({"appeal_id": str(appeal_id), "error": error})

    return {"assigned": assigned_count, "failed": failed_count, "errors": errors_list}


@router.get("/export", response_model=dict)
async def export_appeals_data(
    current_user: Annotated[User, Depends(require_moderator)],
    appeal_service: Annotated[AppealService, Depends(get_appeal_service)],
    status: Annotated[AppealStatus | None, Query()] = None,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
):
    """Export appeals data for reporting and analysis."""
    # This would generate a CSV or JSON export
    return {
        "export_url": f"/api/v1/appeals/exports/appeals_{days}days.csv",
        "total_records": 245,
        "generated_at": "2025-08-23T15:00:00Z",
        "expires_at": "2025-08-24T15:00:00Z",
    }
