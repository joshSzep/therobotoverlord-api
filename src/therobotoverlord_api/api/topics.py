"""Topics API endpoints for The Robot Overlord API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import require_role
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.topic import Topic
from therobotoverlord_api.database.models.topic import TopicCreate
from therobotoverlord_api.database.models.topic import TopicSummary
from therobotoverlord_api.database.models.topic import TopicWithAuthor
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.repositories.topic import TopicRepository
from therobotoverlord_api.database.repositories.user import UserRepository

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/")
async def get_topics(
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=100)] = None,
    overlord_only: Annotated[bool, Query()] = False,  # noqa: FBT002
) -> list[TopicSummary]:
    """Get approved topics with optional search and filtering."""
    topic_repo = TopicRepository()

    if overlord_only:
        return await topic_repo.get_overlord_topics(limit=limit, offset=offset)
    if search:
        return await topic_repo.search_topics(search, limit=limit, offset=offset)
    return await topic_repo.get_approved_topics(limit=limit, offset=offset)


@router.get("/{topic_id}")
async def get_topic(topic_id: UUID) -> TopicWithAuthor:
    """Get a specific topic by ID."""
    topic_repo = TopicRepository()
    topic = await topic_repo.get_with_author(topic_id)

    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found"
        )

    # Only show approved topics to non-moderators
    if topic.status != TopicStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found"
        )

    return topic


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_topic(
    topic_data: TopicCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Topic:
    """Create a new topic (requires authentication)."""
    # Check if user can create topics (top N% loyalty score for citizens)
    if current_user.role == UserRole.CITIZEN:
        user_repo = UserRepository()
        top_percent = 0.1  # 10% - configurable for future experimentation
        can_create = await user_repo.can_create_topic(current_user.pk, top_percent)
        if not can_create:
            threshold = await user_repo.get_top_percent_loyalty_threshold(top_percent)
            percent_display = int(top_percent * 100)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient loyalty score to create topics. You must be in the top {percent_display}% of citizens (minimum score: {threshold}). Your current score: {current_user.loyalty_score}",
            )

    # Set the author
    topic_data.author_pk = current_user.pk

    topic_repo = TopicRepository()
    return await topic_repo.create(topic_data)


# Create dependency instances to avoid function calls in defaults
moderator_dependency = require_role(UserRole.MODERATOR)


@router.patch("/{topic_id}/approve")
async def approve_topic(
    topic_id: UUID,
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> Topic:
    """Approve a topic (moderator+ only)."""
    topic_repo = TopicRepository()
    topic = await topic_repo.approve_topic(topic_id, current_user.pk)

    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found"
        )

    return topic


@router.patch("/{topic_id}/reject")
async def reject_topic(
    topic_id: UUID,
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> Topic:
    """Reject a topic (moderator+ only)."""
    topic_repo = TopicRepository()
    topic = await topic_repo.reject_topic(topic_id)

    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found"
        )

    return topic


@router.get("/pending/list")
async def get_pending_topics(
    current_user: Annotated[User, Depends(moderator_dependency)],
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Topic]:
    """Get pending topics for moderation (moderator+ only)."""
    topic_repo = TopicRepository()
    return await topic_repo.get_by_status(
        TopicStatus.PENDING_APPROVAL, limit=limit, offset=offset
    )
