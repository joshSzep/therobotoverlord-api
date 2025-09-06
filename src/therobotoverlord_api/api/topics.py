"""Topics API endpoints for The Robot Overlord API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import get_current_user
from therobotoverlord_api.auth.dependencies import get_optional_user
from therobotoverlord_api.auth.dependencies import require_role
from therobotoverlord_api.database.models.base import TopicStatus
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.loyalty_score import ContentType
from therobotoverlord_api.database.models.loyalty_score import LoyaltyEventOutcome
from therobotoverlord_api.database.models.loyalty_score import ModerationEventType
from therobotoverlord_api.database.models.topic import Topic
from therobotoverlord_api.database.models.topic import TopicCreate
from therobotoverlord_api.database.models.topic import TopicSummary
from therobotoverlord_api.database.models.topic import TopicWithAuthor
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.database.repositories.topic import TopicRepository
from therobotoverlord_api.services.ai_tag_service import get_ai_tag_service
from therobotoverlord_api.services.loyalty_score_service import (
    get_loyalty_score_service,
)
from therobotoverlord_api.services.queue_service import get_queue_service

router = APIRouter(prefix="/topics", tags=["topics"])

# Authentication dependencies for testing
admin_dependency = require_role(UserRole.ADMIN)
moderator_dependency = require_role(UserRole.MODERATOR)
citizen_dependency = require_role(UserRole.CITIZEN)


@router.get("/categories")
async def get_categories() -> dict:
    """Get all topic categories (public endpoint)."""
    topic_repo = TopicRepository()
    categories = await topic_repo.get_categories_with_details()
    return {"status": "ok", "data": categories}


@router.get("/feed")
async def get_topics_feed(
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TopicSummary]:
    """Get approved topics feed (public endpoint)."""
    from therobotoverlord_api.database.connection import get_db_connection

    # Simple query without complex joins to test
    query = """
        SELECT
            pk,
            title,
            description,
            created_by_overlord,
            status,
            created_at,
            CASE WHEN created_by_overlord THEN 'The Overlord' ELSE 'Anonymous' END as author_username,
            0 as post_count,
            '{}' as tags
        FROM topics
        WHERE status = 'approved'
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
    """

    async with get_db_connection() as connection:
        records = await connection.fetch(query, limit, offset)
        results = []
        for record in records:
            # Convert record to dict to debug the issue
            record_dict = dict(record)
            # Convert tags from string to list
            if "tags" in record_dict and isinstance(record_dict["tags"], str):
                import json

                try:
                    record_dict["tags"] = (
                        json.loads(record_dict["tags"])
                        if record_dict["tags"] != "{}"
                        else []
                    )
                except json.JSONDecodeError:
                    record_dict["tags"] = []
            results.append(TopicSummary.model_validate(record_dict))
        return results


@router.get("/trending")
async def get_trending_topics(
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 20,
) -> list[TopicSummary]:
    """Get trending topics (public endpoint)."""
    topic_repo = TopicRepository()
    return await topic_repo.get_trending_topics(limit=limit)


@router.get("/overlord-only")
async def get_overlord_only_topics(
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 20,
) -> list[TopicSummary]:
    """Get popular topics (public endpoint)."""
    topic_repo = TopicRepository()
    return await topic_repo.get_popular_topics(limit=limit)


@router.get("/search")
async def search_topics(
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 10,
) -> list[TopicSummary]:
    """Get featured topics (public endpoint)."""
    topic_repo = TopicRepository()
    return await topic_repo.get_featured_topics(limit=limit)


@router.get("/popular")
async def get_popular_topics(
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 20,
) -> list[TopicSummary]:
    """Get popular topics (public endpoint)."""
    topic_repo = TopicRepository()
    return await topic_repo.get_popular_topics(limit=limit)


@router.get("/featured")
async def get_featured_topics(
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 10,
) -> list[TopicSummary]:
    """Get featured topics (public endpoint)."""
    topic_repo = TopicRepository()
    return await topic_repo.get_featured_topics(limit=limit)


@router.get("/")
async def get_topics(
    user: Annotated[User | None, Depends(get_optional_user)] = None,
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=100)] = None,
    overlord_only: Annotated[bool, Query()] = False,  # noqa: FBT002
    tags: Annotated[list[str] | None, Query()] = None,
) -> list[TopicSummary]:
    """Get approved topics with optional search and filtering (public endpoint)."""
    topic_repo = TopicRepository()

    if overlord_only:
        return await topic_repo.get_overlord_topics(limit=limit, offset=offset)
    if search:
        return await topic_repo.search_topics(search, limit=limit, offset=offset)
    return await topic_repo.get_approved_topics(
        limit=limit, offset=offset, tag_names=tags
    )


@router.get("/{topic_id}")
async def get_topic(
    topic_id: UUID,
    user: Annotated[User | None, Depends(get_optional_user)] = None,
) -> TopicWithAuthor:
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
    # Check if user can create topics using loyalty service
    if current_user.role == UserRole.CITIZEN:
        loyalty_service = await get_loyalty_score_service()
        thresholds = await loyalty_service.get_score_thresholds()
        if current_user.loyalty_score < thresholds["topic_creation"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient loyalty score to create topics. Required: {thresholds['topic_creation']}, Your score: {current_user.loyalty_score}",
            )

    # Set the author
    topic_data.author_pk = current_user.pk

    topic_repo = TopicRepository()
    topic = await topic_repo.create(topic_data)

    # Record topic creation event for loyalty scoring
    loyalty_service = await get_loyalty_score_service()
    await loyalty_service.record_moderation_event(
        user_pk=current_user.pk,
        event_type=ModerationEventType.TOPIC_MODERATION,
        content_type=ContentType.TOPIC,
        content_pk=topic.pk,
        outcome=LoyaltyEventOutcome.APPROVED,  # Topic creation is initially approved
        reason="Topic created by user",
    )

    # Add topic to moderation queue
    queue_service = await get_queue_service()
    queue_id = await queue_service.add_topic_to_queue(topic.pk, priority=0)

    if not queue_id:
        # If queue addition fails, log but don't fail the request
        # The topic is still created and awaiting approval
        pass

    return topic


@router.get("/{topic_id}/related")
async def get_related_topics(
    topic_id: UUID,
    limit: Annotated[int, Query(le=10, ge=1)] = 5,
    user: Annotated[User | None, Depends(get_optional_user)] = None,
) -> list[TopicSummary]:
    """Get topics related by shared tags."""
    topic_repo = TopicRepository()

    # Verify the topic exists and is approved
    topic = await topic_repo.get_with_author(topic_id)
    if not topic or topic.status != TopicStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found"
        )

    return await topic_repo.get_related_topics(topic_id, limit=limit)


# Remove duplicate - using the dependency defined above


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

    # Automatically assign tags via AI when topic is approved
    try:
        ai_tag_service = await get_ai_tag_service()
        assigned_tags = await ai_tag_service.assign_tags_to_topic(
            topic_id=topic.pk,
            title=topic.title,
            description=topic.description or "",
        )
        # Log successful tag assignment
        if assigned_tags:
            # Note: In a real implementation, you might want to log this
            pass
    except Exception as e:
        # Don't fail topic approval if tag assignment fails
        # The Overlord's judgment on content approval is more important
        # Log the error for debugging purposes
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to assign tags to topic {topic_id}: {e}")

    # Record moderation approval event for loyalty scoring
    if topic.author_pk:
        loyalty_service = await get_loyalty_score_service()
        await loyalty_service.record_moderation_event(
            user_pk=topic.author_pk,
            event_type=ModerationEventType.TOPIC_MODERATION,
            content_type=ContentType.TOPIC,
            content_pk=topic.pk,
            outcome=LoyaltyEventOutcome.APPROVED,
            moderator_pk=current_user.pk,
            reason="Topic approved by moderator",
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

    # Record moderation rejection event for loyalty scoring
    if topic.author_pk:
        loyalty_service = await get_loyalty_score_service()
        await loyalty_service.record_moderation_event(
            user_pk=topic.author_pk,
            event_type=ModerationEventType.TOPIC_MODERATION,
            content_type=ContentType.TOPIC,
            content_pk=topic.pk,
            outcome=LoyaltyEventOutcome.REJECTED,
            moderator_pk=current_user.pk,
            reason="Topic rejected by moderator",
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
