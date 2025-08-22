"""Admin dashboard API endpoints for The Robot Overlord API."""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request

from therobotoverlord_api.auth.dependencies import require_admin
from therobotoverlord_api.database.models.admin_action import AdminActionResponse
from therobotoverlord_api.database.models.admin_action import AdminActionType
from therobotoverlord_api.database.models.admin_action import AuditLogResponse
from therobotoverlord_api.database.models.dashboard_snapshot import DashboardOverview
from therobotoverlord_api.database.models.system_announcement import AnnouncementCreate
from therobotoverlord_api.database.models.system_announcement import SystemAnnouncement
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.dashboard_service import DashboardService

router = APIRouter(tags=["admin"])


async def get_dashboard_service() -> DashboardService:
    """Dependency injection for dashboard service."""
    return DashboardService()


@router.get("/admin/dashboard")
async def get_admin_dashboard(
    current_user: Annotated[User, Depends(require_admin)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
    request: Request,
    period: Annotated[str, Query()] = "24h",
) -> DashboardOverview:
    """Get comprehensive admin dashboard with aggregated data from all systems."""

    # Log admin dashboard access
    await dashboard_service.log_admin_action(
        admin_pk=current_user.pk,
        action_type=AdminActionType.DASHBOARD_ACCESS,
        description="Admin dashboard accessed",
        ip_address=request.client.host if request.client else None,
    )

    return await dashboard_service.get_dashboard_overview(period)


@router.post("/admin/announcements")
async def create_announcement(
    announcement: AnnouncementCreate,
    current_user: Annotated[User, Depends(require_admin)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> SystemAnnouncement:
    """Create system announcement."""

    result = await dashboard_service.create_announcement(announcement, current_user.pk)

    # Log the action
    await dashboard_service.log_admin_action(
        admin_pk=current_user.pk,
        action_type=AdminActionType.SYSTEM_CONFIG,
        target_type="announcement",
        target_pk=result.pk,
        description=f"Created system announcement: {announcement.title}",
    )

    return result


@router.get("/admin/announcements")
async def get_announcements(
    current_user: Annotated[User, Depends(require_admin)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
    active_only: Annotated[bool, Query()] = True,  # noqa: FBT002
) -> list[SystemAnnouncement]:
    """Get system announcements."""

    return await dashboard_service.get_announcements(active_only)


@router.get("/admin/audit-log")
async def get_audit_log(
    current_user: Annotated[User, Depends(require_admin)],
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
    limit: Annotated[int, Query()] = 100,
    offset: Annotated[int, Query()] = 0,
) -> AuditLogResponse:
    """Get admin action audit log."""

    audit_data = await dashboard_service.get_audit_log(limit, offset)

    return AuditLogResponse(
        actions=[
            AdminActionResponse(
                pk=action.pk,
                admin_pk=action.admin_pk,
                action_type=action.action_type,
                target_type=action.target_type,
                target_pk=action.target_pk,
                description=action.description,
                metadata=action.metadata,
                ip_address=action.ip_address,
                created_at=action.created_at,
            )
            for action in audit_data["actions"]
        ],
        total_count=audit_data["total_count"],
        limit=limit,
        offset=offset,
    )
