"""Tags API endpoints for The Robot Overlord API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from therobotoverlord_api.auth.dependencies import require_role
from therobotoverlord_api.database.models.base import UserRole
from therobotoverlord_api.database.models.tag import Tag
from therobotoverlord_api.database.models.tag import TagCreate
from therobotoverlord_api.database.models.tag import TagUpdate
from therobotoverlord_api.database.models.tag import TagWithTopicCount
from therobotoverlord_api.database.models.tag import TopicTag
from therobotoverlord_api.database.models.tag import TopicTagWithDetails
from therobotoverlord_api.database.models.user import User
from therobotoverlord_api.services.tag_service import get_tag_service

router = APIRouter(prefix="/tags", tags=["tags"])

# Create dependency instances to avoid function calls in defaults
admin_dependency = require_role(UserRole.ADMIN)
moderator_dependency = require_role(UserRole.MODERATOR)


@router.get("/")
async def get_tags(
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=100)] = None,
    with_counts: Annotated[bool, Query()] = False,  # noqa: FBT002
) -> list[Tag] | list[TagWithTopicCount]:
    """Get all tags with optional search and topic counts."""
    tag_service = get_tag_service()

    if search:
        tags = await tag_service.search_tags(search, limit=limit, offset=offset)
        return tags

    if with_counts:
        return await tag_service.get_tags_with_topic_count(limit=limit, offset=offset)

    return await tag_service.get_all_tags(limit=limit, offset=offset)


@router.get("/popular")
async def get_popular_tags(
    limit: Annotated[int, Query(le=50, ge=1)] = 20,
) -> list[TagWithTopicCount]:
    """Get most popular tags by topic count."""
    tag_service = get_tag_service()
    return await tag_service.get_popular_tags(limit=limit)


@router.get("/stats")
async def get_tag_stats(
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> dict[str, int]:
    """Get tag usage statistics (moderators and above only)."""
    tag_service = get_tag_service()
    return await tag_service.get_tag_usage_stats()


@router.get("/{tag_id}")
async def get_tag(tag_id: UUID) -> Tag:
    """Get a specific tag by ID."""
    tag_service = get_tag_service()
    tag = await tag_service.get_tag_by_pk(tag_id)

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    return tag


@router.get("/{tag_id}/topics")
async def get_topics_by_tag(
    tag_id: UUID,
    limit: Annotated[int, Query(le=100, ge=1)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UUID]:
    """Get topic IDs that have a specific tag."""
    tag_service = get_tag_service()

    try:
        return await tag_service.get_topics_by_tag(tag_id, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/")
async def create_tag(
    tag_data: TagCreate,
    current_user: Annotated[User, Depends(admin_dependency)],
) -> Tag:
    """Create a new tag (admins only)."""
    tag_service = get_tag_service()

    try:
        return await tag_service.create_tag(tag_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.put("/{tag_id}")
async def update_tag(
    tag_id: UUID,
    tag_data: TagUpdate,
    current_user: Annotated[User, Depends(admin_dependency)],
) -> Tag:
    """Update a tag (admins only)."""
    tag_service = get_tag_service()

    try:
        return await tag_service.update_tag(tag_id, tag_data)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: UUID,
    current_user: Annotated[User, Depends(admin_dependency)],
) -> dict[str, str]:
    """Delete a tag (admins only)."""
    tag_service = get_tag_service()

    try:
        success = await tag_service.delete_tag(tag_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete tag",
            )

        return {"message": "Tag deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# Topic tag assignment endpoints
@router.get("/topics/{topic_id}/tags")
async def get_topic_tags(topic_id: UUID) -> list[TopicTagWithDetails]:
    """Get all tags assigned to a specific topic."""
    tag_service = get_tag_service()
    return await tag_service.get_tags_for_topic(topic_id)


@router.put("/topics/{topic_id}/tags")
async def assign_tags_to_topic(
    topic_id: UUID,
    tag_names: list[str],
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> list[TopicTag]:
    """Assign multiple tags to a topic (moderators and above only)."""
    tag_service = get_tag_service()

    try:
        return await tag_service.assign_tags_to_topic(
            topic_id, tag_names, current_user.pk
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/topics/{topic_id}/tags/{tag_id}")
async def assign_tag_to_topic(
    topic_id: UUID,
    tag_id: UUID,
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> TopicTag:
    """Assign a specific tag to a topic (moderators and above only)."""
    tag_service = get_tag_service()

    try:
        return await tag_service.assign_tag_to_topic(topic_id, tag_id, current_user.pk)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.delete("/topics/{topic_id}/tags/{tag_id}")
async def remove_tag_from_topic(
    topic_id: UUID,
    tag_id: UUID,
    current_user: Annotated[User, Depends(moderator_dependency)],
) -> dict[str, str]:
    """Remove a tag from a topic (moderators and above only)."""
    tag_service = get_tag_service()

    try:
        success = await tag_service.remove_tag_from_topic(topic_id, tag_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tag assignment not found"
            )

        return {"message": "Tag removed from topic successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete("/topics/{topic_id}/tags")
async def remove_all_tags_from_topic(
    topic_id: UUID,
    current_user: Annotated[User, Depends(admin_dependency)],
) -> dict[str, str]:
    """Remove all tags from a topic (admins only)."""
    tag_service = get_tag_service()

    try:
        count = await tag_service.remove_all_tags_from_topic(topic_id)
        return {"message": f"Removed {count} tags from topic"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
