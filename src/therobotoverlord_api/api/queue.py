"""Queue status API endpoints for The Robot Overlord."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import get_optional_user
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.queue_service import get_queue_service
from therobotoverlord_api.workers.redis_connection import get_redis_client

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/status")
async def get_overall_queue_status():
    """Get overall queue status across all queue types."""
    queue_service = await get_queue_service()

    # Get status for all queue types
    topics_status = await queue_service.get_queue_status("topics")
    posts_status = await queue_service.get_queue_status("posts")
    messages_status = await queue_service.get_queue_status("messages")

    return {
        "status": "ok",
        "data": {
            "topics": topics_status,
            "posts": posts_status,
            "messages": messages_status,
            "system_status": "operational",
        },
    }


@router.get("/status/{queue_type}")
async def get_queue_type_status(
    queue_type: Annotated[str, Path(pattern="^(topics|posts|messages)$")],
    user: Annotated[User | None, Depends(get_optional_user)] = None,
):
    """Get detailed status for a specific queue type."""
    queue_service = await get_queue_service()

    queue_status = await queue_service.get_queue_status(queue_type)

    if "error" in queue_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=queue_status["error"],
        )

    return {
        "status": "ok",
        "data": queue_status,
    }


@router.get("/position/{content_type}/{content_id}")
async def get_content_queue_position(
    content_type: Annotated[str, Path(pattern="^(topics|posts|messages)$")],
    content_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get queue position for specific content (authenticated users only)."""
    queue_service = await get_queue_service()

    position_info = await queue_service.get_content_position(content_type, content_id)

    if not position_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found in queue or already processed",
        )

    return {
        "status": "ok",
        "data": position_info,
    }


@router.get("/visualization")
async def get_queue_visualization_data(
    limit: Annotated[int, Query(le=50, ge=1)] = 20,
    user: Annotated[User | None, Depends(get_optional_user)] = None,
):
    """Get data for public queue visualization (pneumatic tube system)."""
    queue_service = await get_queue_service()
    await queue_service._ensure_connections()

    try:
        # Get recent queue activity for visualization
        query = """
            WITH recent_activity AS (
                SELECT
                    'topic' as content_type,
                    topic_pk as content_id,
                    position_in_queue,
                    status,
                    entered_queue_at,
                    estimated_completion_at
                FROM topic_creation_queue
                WHERE entered_queue_at > NOW() - INTERVAL '1 hour'

                UNION ALL

                SELECT
                    'post' as content_type,
                    post_pk as content_id,
                    position_in_queue,
                    status,
                    entered_queue_at,
                    estimated_completion_at
                FROM post_moderation_queue
                WHERE entered_queue_at > NOW() - INTERVAL '1 hour'
            )
            SELECT * FROM recent_activity
            ORDER BY entered_queue_at DESC
            LIMIT $1
        """

        records = await queue_service.db.fetch(query, limit)

        visualization_data = [
            {
                "content_type": record["content_type"],
                "content_id": str(record["content_id"]),
                "position": record["position_in_queue"],
                "status": record["status"],
                "entered_at": record["entered_queue_at"],
                "estimated_completion": record["estimated_completion_at"],
            }
            for record in records
        ]

        return {
            "status": "ok",
            "data": {
                "recent_activity": visualization_data,
                "queue_stats": {
                    "topics": await queue_service.get_queue_status("topics"),
                    "posts": await queue_service.get_queue_status("posts"),
                },
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get visualization data",
        ) from e


@router.get("/health")
async def get_queue_health(
    user: Annotated[User | None, Depends(get_optional_user)] = None,
):
    """Get queue system health status."""
    queue_service = await get_queue_service()

    try:
        await queue_service._ensure_connections()

        # Test database connection
        db_healthy = await queue_service.db.fetchval("SELECT 1")

        # Test Redis connection
        try:
            redis_client = await get_redis_client()
            await redis_client.ping()
            redis_healthy = True
        except Exception:  # nosec B110
            # Redis connectivity check failed, redis_healthy remains False
            redis_healthy = False

        overall_healthy = db_healthy == 1 and redis_healthy

        return {
            "status": "ok" if overall_healthy else "degraded",
            "data": {
                "database": {"healthy": db_healthy == 1},
                "redis": {"healthy": redis_healthy},
                "workers": {
                    "topic_worker": "unknown",  # TODO(josh): Add worker health checks - Issue #TBD
                    "post_worker": "unknown",
                },
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "data": {
                "error": "Queue system health check failed",
                "database": {"healthy": False},
                "redis": {"healthy": False},
            },
        }
